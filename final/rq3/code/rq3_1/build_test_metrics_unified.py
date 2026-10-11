#!/usr/bin/env python3
"""
Unified tree-sitter pipeline: for each test (across 12 Apache Commons
projects), compute THREE metrics -- LOC, CC (McCabe), and CCTR (N+A+M+T) --
for the test's own body and for every test-scope helper it calls, then sum
into self/helper/total per metric. One parse per snippet feeds all three
scores, so results are internally consistent.

No Understand CSV is used anywhere in this pipeline: helper resolution reads
straight from each project's own src/test/java source (tree-sitter parse +
name/arity match), exactly like build_test_cctr_multi.py's approach, just
extended to also compute LOC/CC alongside CCTR from the same parsed node.
This lets projects with no Understand export (the 9 new ones) be analyzed
the same way as the original 3 (commons-numbers/io/rng), for a
methodologically consistent cross-project comparison.

LOC definition (meant to approximate Understand's CountLineCode): the count
of distinct source lines touched by at least one non-comment leaf token
within the snippet's node span (so leading javadoc -- a sibling node, never
part of the declaration's span -- is naturally excluded; blank lines and
comment-only lines are excluded by never being touched by a counted token;
annotation lines above the signature ARE included, since they're inside the
declaration node's own span).

CC definition (McCabe, calibrated earlier against Understand's own numbers
via a regex prototype -- see build_test_complexity.py's compute_cc): 1 +
count(if_statement, for_statement, enhanced_for_statement, while_statement,
do_statement, catch_clause, ternary_expression, and each 'case' switch_label
-- NOT 'default', NOT the switch statement itself, NOT && / ||).
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict

from tree_sitter import Language, Parser
import tree_sitter_java as tsjava
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SSD, METRICS_DIR, APACHE_PROJECTS, DUP_RESULT, FINAL  # noqa: E402


VOLUME = APACHE_PROJECTS
OUT_CSV = _os.path.join(METRICS_DIR, "test_metrics_unified_46projects_v2.csv")
REPORT_CSV = _os.path.join(METRICS_DIR, "test_metrics_unified_46projects_v2_report.csv")

# module_glob is no longer needed -- build_source_class_sets now discovers every
# src/main/java and src/test/java under base_dir recursively, at any depth, so
# one project entry works regardless of how its modules are laid out.
# 2026-09-22：RQ3 扩到 44 个项目（all_47_projects.txt 去掉 hive/storm/camel——那三个的 AAA 还是 Phase 2 之前的旧
# parser 口径，而且 hive 有一半测试因依赖损坏没解析出来；等它们重跑完再并进来）。
SKIP_PROJECTS = {l.strip() for l in open(_paths.RQ3_EXCLUDED) if l.strip()}
PROJECT_NAMES = [l.strip() for l in open(_paths.RQ3_PROJECTS)
                 if l.strip() and l.strip() not in SKIP_PROJECTS]


def make_projects(names):
    return [{'name': name, 'aaa_dir': f'{VOLUME}/{name}/AAA', 'base_dir': f'{VOLUME}/{name}'}
            for name in names]


PROJECTS = make_projects(PROJECT_NAMES)

SKIP_PREFIXES = {
    'ASSERT', 'THIRD', 'THIRD GET', 'THIRD SET', 'NEW_JDK_CLASS',
    'METHOD_NOT_FOUND_IN_SOURCE', 'SOURCE_FILE_NOT_FOUND',
    # Phase 2/3 analyzer tags: third-party method refs, JDK providers, truncation / lookup markers.
    'METHOD_REF_THIRD', 'METHODSOURCE_EXTERNAL', 'METHODSOURCE_NOT_FOUND', 'MAX_DEPTH_REACHED',
    'UNKNOWN_PROJECT_CODE', 'LOCAL_METHOD',
}

LINE_RANGE_RE = re.compile(r'#\[\d+-\d+\]\s*$')
# Phase 3 ③: the analyzer appends " ctx=<context>" to METHOD_REF_* signatures. A method reference
# passed as *data* (argument of Arguments.of / List.of / a constructor, returned, assigned, ...) is
# not a call this test makes — it is invoked by someone else later — so it and its expanded subtree
# are dropped before scoring (same rule as rq2.2's build_helper_depth.py, keep the two in sync).
CTX_RE = re.compile(r'\s+ctx=(\S+)$')
DATA_CTX_CALLS = {
    'of', 'arguments', 'argumentSet', 'asList', 'add', 'addAll', 'put', 'putAll', 'set', 'singletonList',
    'singleton', 'listOf', 'setOf', 'mapOf', 'build', 'named', 'withArgs', 'with', 'append', 'offer', 'push',
}


def method_ref_ctx_is_data(ctx):
    if ctx.startswith('call:'):
        return ctx[5:] in DATA_CTX_CALLS
    if ctx.startswith('target:'):
        return False
    return True


def drop_data_method_refs(lines):
    """dfsAnalyze writes children *before* their parent line (post-order): a METHOD_REF_* line at
    depth k owns the run of lines immediately before it with depth > k. Drop both when its ctx
    says the reference was passed as data."""
    out = []
    for line in lines:
        stripped = line.strip()
        depth = (len(line) - len(line.lstrip(' '))) // 4
        if stripped.startswith(('METHOD_REF_TEST ', 'METHOD_REF_PROD ', 'METHOD_REF_THIRD ')):
            m = CTX_RE.search(LINE_RANGE_RE.sub('', stripped))
            if m and method_ref_ctx_is_data(m.group(1)):
                while out and (len(out[-1]) - len(out[-1].lstrip(' '))) // 4 > depth:
                    out.pop()
                continue
        out.append(line)
    return out
CALL_RE = re.compile(r'^(.*?)\(([^()]*)\)$')
GENERIC_RE = re.compile(r'<[^<>]*>')

JAVA_LANGUAGE = Language(tsjava.language())
TS_PARSER = Parser(JAVA_LANGUAGE)

COMMENT_TYPES = {'line_comment', 'block_comment'}
CC_NODE_TYPES = {'if_statement', 'for_statement', 'enhanced_for_statement',
                  'while_statement', 'do_statement', 'catch_clause', 'ternary_expression'}



# ---------------------------------------------------------------------------
# JUnit API 判定：把每个测试归到 junit5 / junit4 / other
# ---------------------------------------------------------------------------
# 研究问题承诺的是 JUnit5 PT vs JUnit5 non-PT，但此前 non-PT 是「所有非参数化测试」，
# 把 JUnit4 / TestNG 也算了进去。druid（88% 文件是 JUnit4）、jena（43%）尤其受影响。
# 判定优先级：源码里的全限定注解 > @ParameterizedTest（jupiter 独有）> import 列表。
J5_MARKERS = ('org.junit.jupiter.',)
J4_MARKERS = ('org.junit.Test', 'org.junit.Assert', 'org.junit.Before', 'org.junit.After',
              'org.junit.Rule', 'org.junit.ClassRule', 'org.junit.runner.', 'org.junit.runners.',
              'org.junit.experimental.')


def classify_junit_api(imports, source, is_pt):
    src = source or ''
    if '@org.junit.jupiter.' in src:
        return 'junit5'
    if '@org.junit.Test' in src or '@org.junit.Ignore' in src:
        return 'junit4'
    if is_pt:
        return 'junit5'          # @ParameterizedTest 只存在于 JUnit5
    imports = imports or []
    has5 = any(i.startswith(J5_MARKERS) for i in imports)
    has4 = any(i == m or i.startswith(m) for i in imports for m in J4_MARKERS)
    if has5 and not has4:
        return 'junit5'
    if has4 and not has5:
        return 'junit4'
    if has5 and has4:
        # 同一文件里两套 API 混用（迁移中）。按测试方法自己的 @Test 归属判断：
        # 只 import 了其中一个 Test 注解时可判，都 import 了则无法用语法区分。
        t5 = 'org.junit.jupiter.api.Test' in imports
        t4 = 'org.junit.Test' in imports
        if t5 and not t4:
            return 'junit5'
        if t4 and not t5:
            return 'junit4'
        return 'mixed'
    if any('org.testng' in i for i in imports):
        return 'testng'
    return 'unknown'


# ---------------------------------------------------------------------------
# Per-snippet scorer: one tree-sitter parse -> (loc, cc, n, a, m, t, cctr)
# ---------------------------------------------------------------------------

class SnippetScorer:
    def __init__(self, code, method_name=None):
        self.code = code.encode('utf-8') if isinstance(code, str) else code
        self.method_name = method_name
        self.loc_lines = set()
        self.cc = 1
        self.n = 0
        self.a = 0
        self.m = 0
        self.t = 0
        # t_eq：CCTR 的 T 分量把 @ParameterizedTest 记 2 分、@Test 记 1 分，等于每个 PT
        # 白得 1 分，对 PT vs non-PT 的比较是结构性偏置。t_eq 是同权版本（都记 1 分），
        # 用于敏感性分析，不替换主口径。
        self.t_eq = 0
        self.nesting_level = 0

    def compute(self):
        tree = TS_PARSER.parse(self.code)
        self._walk(tree.root_node)
        return {
            'loc': len(self.loc_lines), 'cc': self.cc,
            'n': self.n, 'a': self.a, 'm': self.m, 't': self.t, 't_eq': self.t_eq,
            'cctr': self.n + self.a + self.m + self.t,
            'cctr_eq': self.n + self.a + self.m + self.t_eq,
        }

    def _text(self, node):
        return self.code[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

    def _walk(self, node):
        # LOC: any non-comment leaf token contributes every row it spans.
        if node.child_count == 0 and node.type not in COMMENT_TYPES:
            for row in range(node.start_point[0], node.end_point[0] + 1):
                self.loc_lines.add(row)

        kind = node.type
        text = None
        if kind in CC_NODE_TYPES:
            self.cc += 1
        elif kind == 'switch_label':
            t = self._text(node)
            if t.startswith('case'):
                self.cc += 1

        # CCTR (N/A/M/T), ported from build_test_cctr_multi.py's CCTRCalculator
        if kind in ('if_statement', 'for_statement', 'enhanced_for_statement',
                    'while_statement', 'do_statement', 'switch_expression', 'switch_statement',
                    'catch_clause'):
            self.n += 1 + self.nesting_level
            self.nesting_level += 1
            for c in node.children:
                self._walk(c)
            self.nesting_level -= 1
            return
        elif kind == 'binary_expression':
            text = self._text(node)
            if '&&' in text or '||' in text:
                self.n += 1
        elif kind == 'labeled_statement':
            text = self._text(node)
            if any(k in text for k in ('break', 'continue', 'goto')):
                self.n += 1
        elif kind == 'method_invocation':
            text = self._text(node)
            if self.method_name and self.method_name in text:
                self.n += 1
            if any(x in text for x in ('mock(', 'when(', 'verify(')):
                self.m += 1
            if 'assert' in text or 'fail(' in text:
                self.a += 1
        elif kind in ('annotation', 'marker_annotation'):
            text = self._text(node)
            if '@Test' in text:
                self.t += 1
                self.t_eq += 1
            elif '@ParameterizedTest' in text:
                self.t += 2
                self.t_eq += 1          # 敏感性版本：与 @Test 同权
            elif '@BeforeEach' in text or '@AfterEach' in text:
                self.t += 1
                self.t_eq += 1

        for c in node.children:
            self._walk(c)


def score_of(code, method_name=None):
    return SnippetScorer(code, method_name).compute()


ZERO_SCORE = {'loc': 0, 'cc': 0, 'n': 0, 'a': 0, 'm': 0, 't': 0, 't_eq': 0, 'cctr': 0, 'cctr_eq': 0}
SCORE_KEYS = ('loc', 'cc', 'n', 'a', 'm', 't', 't_eq', 'cctr', 'cctr_eq')


def add_score(dst, src):
    for k in SCORE_KEYS:
        dst[k] += src[k]


# ---------------------------------------------------------------------------
# Shared call-sequence parsing (identical to build_test_cctr_multi.py)
# ---------------------------------------------------------------------------

def strip_generics(qualified_name):
    prev = None
    s = qualified_name
    while prev != s:
        prev = s
        s = GENERIC_RE.sub('', s)
    return s


def count_top_level_commas(s):
    depth = 0
    count = 0
    for ch in s:
        if ch in '([<':
            depth += 1
        elif ch in ')]>':
            depth -= 1
        elif ch == ',' and depth == 0:
            count += 1
    return count


def arity_of(params_text):
    t = params_text.strip()
    if not t:
        return 0
    return count_top_level_commas(t) + 1


PRUNE_DIRS = {'target', '.git', 'node_modules', 'build', '.idea', 'dist-archive', 'out', '.svn'}


# 目录名里出现这些片段 → 该源根其实是测试基础设施（放在 main/其它源集下的 fixture、harness、testkit）
TEST_INFRA_SEGMENTS = ('testkit', 'test-harness', 'testharness', 'testfixtures', 'test-fixtures', 'testsupport', 'test-support')
TEST_INFRA_SOURCESETS = ('src/integration/java', 'src/it/java', 'src/testFixtures/java', 'src/integrationTest/java',
                         'src/intTest/java', 'src/test-integration/java')


def _looks_like_test_infrastructure(rel_path):
    """rel_path: 源根相对项目根的路径，如 'testkit/src/main/java'、'test/src/main/java'、'aws/src/integration/java'。"""
    low = rel_path.lower()
    if any(low.endswith(ss.lower()) or ('/' + ss.lower() + '/') in ('/' + low + '/') for ss in TEST_INFRA_SOURCESETS):
        return True
    # 模块目录（src 之前的路径段）名为 test / 含 testkit、harness 等
    module = low.split('/src/')[0] if '/src/' in low else ''
    segs = [x for x in module.split('/') if x]
    if segs and (segs[-1] == 'test' or any(t in segs[-1] for t in TEST_INFRA_SEGMENTS)):
        return True
    return False


def find_module_source_roots(base_dir):
    """Find every 'src/main/java' and 'src/test/java' directory anywhere
    under base_dir, at any nesting depth -- robust to arbitrarily-shaped
    multi-module layouts (flat 'project-module' globs, deeply nested
    modules, or a mix of a root-level src/ plus submodules) without needing
    a hand-written glob pattern per project. Prunes common non-source
    directories (build output, VCS, IDE metadata) for speed and to avoid
    picking up generated-source copies."""
    main_roots = []
    test_roots = []
    for root, dirs, _files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in PRUNE_DIRS and not d.startswith('.')]
        base = os.path.basename(root)
        parent = os.path.dirname(root)
        # Standard Maven layout: .../src/{main,test}/java/<pkg>；另外把 src/<其它源集>/java 也纳入
        # （iceberg 的 src/integration/java、Gradle 的 src/testFixtures/java 等），由下面的
        # _looks_like_test_infrastructure 决定算 test 还是 main。
        if base == 'java' and os.path.basename(os.path.dirname(parent)) == 'src':
            sourceset = os.path.basename(parent)
            if sourceset in ('main', 'test'):
                kind = sourceset
            elif _looks_like_test_infrastructure(os.path.relpath(root, base_dir).replace(os.sep, '/')):
                kind = 'test'
            else:
                dirs[:] = []       # src/jmh/java 等：既不是被测生产代码也不是测试，两边都不收
                continue
        # Non-standard layout (#12, e.g. Apache ORC): .../src/{main,test}/<pkg> with no `java` level.
        # Only treat src/test or src/main itself as the root when it has no `java` child, otherwise
        # the standard branch above would already have matched one level deeper.
        elif base in ('main', 'test') and os.path.basename(parent) == 'src' and 'java' not in dirs:
            kind = base
        # Ant-style layout (also ORC): .../src/java/<pkg> is the production root, no `main` level at all.
        elif base == 'java' and os.path.basename(parent) == 'src':
            kind = 'main'
        else:
            continue
        # 2026-09-22: 一批项目把测试基础设施放在 main 树下或非 test 的源集里（calcite testkit/src/main/java、
        # accumulo test|iterator-test-harness/src/main/java、iceberg src/integration/java、jmeter src/testFixtures/java）。
        # 按路径它们会落进 production 集合，于是标准布局测试调用这些 fixture 时被记成"调了生产代码"：helper 指标低估、
        # hits_production 高估（calcite 7,576 条 AAA 里 5,919 条、28k 调用行受影响）。这里按源集/模块名把它们改判为 test。
        rel = os.path.relpath(root, base_dir).replace(os.sep, '/')
        if kind == 'main' and _looks_like_test_infrastructure(rel):
            kind = 'test' 
        if kind == 'main':
            main_roots.append(root)
            dirs[:] = []  # nothing further to discover inside a matched source root
        elif kind == 'test':
            test_roots.append(root)
            dirs[:] = []
    return main_roots, test_roots


def build_source_class_sets(base_dir):
    production_classes = set()
    test_classes = set()
    test_class_files = {}
    main_roots, test_roots = find_module_source_roots(base_dir)
    for src_root, target in [(r, production_classes) for r in main_roots] + \
                             [(r, test_classes) for r in test_roots]:
        for java_file in glob.glob(os.path.join(src_root, '**', '*.java'), recursive=True):
            rel = os.path.relpath(java_file, src_root)
            qualified = rel[:-len('.java')].replace(os.sep, '.')
            target.add(qualified)
            if target is test_classes:
                test_class_files[qualified] = java_file
    return production_classes, test_classes, test_class_files


def classify_declaring_class(declaring_class, production_classes, test_classes):
    parts = declaring_class.split('.')
    for cut in range(len(parts), 0, -1):
        candidate = '.'.join(parts[:cut])
        if candidate in test_classes:
            return 'test'
        if candidate in production_classes:
            return 'production'
    return 'external'


def get_prefix_and_rest(s):
    if s.startswith('NEW ANONYMOUS_CLASS'):
        return 'NEW ANONYMOUS_CLASS', ''
    tokens = s.split(' ')
    pre = []
    i = 0
    while i < len(tokens) and tokens[i] and tokens[i].isupper():
        pre.append(tokens[i])
        i += 1
    rest = ' '.join(tokens[i:])
    return ' '.join(pre), rest


def parse_rest(rest):
    rest = CTX_RE.sub('', LINE_RANGE_RE.sub('', rest).strip())
    m = CALL_RE.match(rest)
    if not m:
        return None, None, None
    qualified = strip_generics(m.group(1).strip())
    params = m.group(2)
    return qualified, params, arity_of(params)


def load_test_jsons(aaa_dir):
    all_files = sorted(glob.glob(os.path.join(aaa_dir, '**', '*.json'), recursive=True))
    test_files = [f for f in all_files
                  if not os.path.basename(f).startswith('.') and not f.endswith('-log.json')]
    parsed_tests = []
    for fp in test_files:
        with open(fp, encoding='utf-8') as fh:
            d = json.load(fh)
        d['_file'] = fp
        parsed_tests.append(d)
    return parsed_tests


# ---------------------------------------------------------------------------
# Helper snippet resolution: name+arity matched against the actual
# src/test/java source file of the call's declaring class.
# ---------------------------------------------------------------------------
_FILE_METHOD_POOL_CACHE = {}


def _parse_java_file(file_path):
    with open(file_path, 'rb') as f:
        code = f.read()
    tree = TS_PARSER.parse(code)
    return tree, code


def _arity_of_params_node(params_node):
    if params_node is None:
        return 0
    return sum(1 for c in params_node.children if c.type in ('formal_parameter', 'spread_parameter'))


def _is_static_node(node, code):
    for c in node.children:
        if c.type == 'modifiers':
            txt = code[c.start_byte:c.end_byte].decode('utf-8')
            return 'static' in txt.split()
    return False


TYPE_DECL_TYPES = ('class_declaration', 'interface_declaration', 'enum_declaration', 'record_declaration')


def build_file_method_pool(file_path):
    """simple_name -> [entry, ...] for every method/constructor declared
    anywhere in the file (any nesting level). Each entry is a dict with
    arity, snippet (source text), start_line/end_line (1-indexed, inclusive),
    is_static, and class_path (tuple of enclosing type names, outermost
    first, e.g. ('ValidateTest', 'ExclusiveBetween', 'WithMessage') for a
    method inside a JUnit5 @Nested class -- needed because sibling @Nested
    classes commonly reuse the same method name, which would otherwise
    collide in a flat by-name pool). Callers needing just (arity, snippet)
    as a 2-tuple can still do `e['arity'], e['snippet']`."""
    if file_path in _FILE_METHOD_POOL_CACHE:
        return _FILE_METHOD_POOL_CACHE[file_path]

    pool = defaultdict(list)
    try:
        tree, code = _parse_java_file(file_path)
    except OSError:
        _FILE_METHOD_POOL_CACHE[file_path] = pool
        return pool

    class_path_stack = []

    def walk(node):
        pushed = False
        if node.type in TYPE_DECL_TYPES:
            name_node = node.child_by_field_name('name')
            if name_node is not None:
                class_path_stack.append(code[name_node.start_byte:name_node.end_byte].decode('utf-8'))
                pushed = True
        if node.type in ('method_declaration', 'constructor_declaration'):
            name_node = node.child_by_field_name('name')
            if name_node is not None:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                arity = _arity_of_params_node(node.child_by_field_name('parameters'))
                snippet = code[node.start_byte:node.end_byte].decode('utf-8')
                pool[name].append({
                    'arity': arity,
                    'snippet': snippet,
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'is_static': _is_static_node(node, code),
                    'class_path': tuple(class_path_stack),
                })
        for c in node.children:
            walk(c)
        if pushed:
            class_path_stack.pop()

    walk(tree.root_node)
    _FILE_METHOD_POOL_CACHE[file_path] = pool
    return pool


def resolve_test_class_file(declaring_class, test_class_files):
    parts = declaring_class.split('.')
    for cut in range(len(parts), 0, -1):
        candidate = '.'.join(parts[:cut])
        if candidate in test_class_files:
            return test_class_files[candidate]
    return None


def resolve_test_class_file_with_chain(declaring_class, test_class_files):
    """Same match as resolve_test_class_file, but also returns the expected
    class_path (from the matched top-level class name down through any
    @Nested chain) to filter build_file_method_pool entries with."""
    parts = declaring_class.split('.')
    for cut in range(len(parts), 0, -1):
        candidate = '.'.join(parts[:cut])
        if candidate in test_class_files:
            return test_class_files[candidate], tuple(parts[cut - 1:])
    return None, None


def filter_by_class_path(candidates, expected_chain):
    """Prefer entries whose class_path matches expected_chain exactly; if
    that yields nothing (e.g. an edge case the chain heuristic doesn't
    cover), fall back to the unfiltered candidate list rather than losing
    a resolution that used to work under plain by-name matching."""
    if not expected_chain:
        return candidates
    filtered = [c for c in candidates if c['class_path'] == expected_chain]
    return filtered if filtered else candidates


IMPLICIT_DEFAULT_CTOR_ENTRY = {'arity': 0, 'snippet': '', 'start_line': None, 'end_line': None, 'is_static': False}


def resolve_helper_entry(lookup_name, declaring_class, arity_hint, test_class_files, stats, is_new):
    """Same resolution as before, but returns the full pool entry (dict with
    arity/snippet/start_line/end_line/is_static) instead of just snippet text,
    so callers needing line spans (e.g. duplication analysis) don't need to
    re-parse. Disambiguates by arity, then by uniqueness of (start_line,
    end_line) among same-named candidates (source-identical bodies collapse
    to one entry; genuinely different overloads at the same arity remain
    ambiguous)."""
    file_path, expected_chain = resolve_test_class_file_with_chain(declaring_class, test_class_files)
    if file_path is None:
        stats['not_found'] += 1
        return 'not_found', None

    pool = build_file_method_pool(file_path)
    simple_name = lookup_name.rsplit('.', 1)[-1]
    candidates = filter_by_class_path(pool.get(simple_name, []), expected_chain)

    if not candidates:
        if is_new:
            stats['implicit_default_ctor'] += 1
            return 'ok', IMPLICIT_DEFAULT_CTOR_ENTRY
        stats['not_found'] += 1
        return 'not_found', None

    def unique_by_span(entries):
        distinct = {(e['start_line'], e['end_line']): e for e in entries}
        return list(distinct.values())

    def unique_by_score(entries):
        # Different declarations (different spans/signatures) can still score
        # identically -- e.g. two single-arg constructors that each just do
        # `field = new Wrapper(arg);`. When that happens the *specific*
        # overload is still genuinely unknown, but the numeric contribution
        # isn't, so it's safe to resolve anyway (mirrors the "uniform metric"
        # shortcut the Understand-CSV pipeline used).
        scored = {}
        for e in entries:
            sc = score_of(e['snippet']) if e['snippet'] else dict(ZERO_SCORE)
            key = tuple(sc[k] for k in SCORE_KEYS)
            scored[key] = e
        return list(scored.values())

    arity_matches = [c for c in candidates if c['arity'] == arity_hint] if arity_hint is not None else []

    if arity_matches:
        distinct = unique_by_span(arity_matches)
        if len(distinct) == 1:
            stats['resolved_by_arity'] += 1
            return 'ok', distinct[0]
        distinct = unique_by_score(arity_matches)
        if len(distinct) == 1:
            stats['resolved_by_arity_uniform_score'] += 1
            return 'ok', distinct[0]

    distinct_all = unique_by_span(candidates)
    if len(distinct_all) == 1:
        stats['resolved_uniform'] += 1
        return 'ok', distinct_all[0]
    distinct_all = unique_by_score(candidates)
    if len(distinct_all) == 1:
        stats['resolved_uniform_score'] += 1
        return 'ok', distinct_all[0]

    stats['ambiguous'] += 1
    return 'ambiguous', None


def resolve_helper_snippet(lookup_name, declaring_class, arity_hint, test_class_files, stats, is_new):
    """Back-compat wrapper: same as resolve_helper_entry but returns just the
    snippet text, for callers that only need the source (e.g. CC/LOC/CCTR
    scoring)."""
    status, entry = resolve_helper_entry(lookup_name, declaring_class, arity_hint, test_class_files, stats, is_new)
    return status, (entry['snippet'] if entry is not None else None)


# ---------------------------------------------------------------------------
# Per-test processing
# ---------------------------------------------------------------------------

def process_tests(parsed_tests, production_classes, test_classes, test_class_files, project_label):
    stats = defaultdict(int)
    rows = []
    report_rows = []

    for d in parsed_tests:
        test_class = d.get('testClassName', '')
        test_name = d.get('testCaseName', '')
        is_pt = d.get('isParameterized', False)
        test_qname = f'{test_class}.{test_name}'
        source = d.get('testCaseSourceCode', '') or ''

        self_score = score_of(source, method_name=test_name)

        helper_totals = dict(ZERO_SCORE)
        helpers_seen = set()
        ambiguous_helpers = set()
        unresolved_helpers = set()
        seen_non_test = set()

        for raw in drop_data_method_refs(d.get('parsedStatementsSequence', [])):
            s = raw.strip()
            if not s:
                continue
            prefix, rest = get_prefix_and_rest(s)
            if prefix in SKIP_PREFIXES or prefix == 'NEW ANONYMOUS_CLASS':
                continue

            qualified, params, arity = parse_rest(rest)
            if qualified is None:
                continue

            if prefix == 'NEW':
                declaring_class = qualified
                last = qualified.rsplit('.', 1)[-1]
                lookup_name = f'{qualified}.{last}'
            else:
                declaring_class = qualified.rsplit('.', 1)[0] if '.' in qualified else qualified
                lookup_name = qualified

            source_kind = classify_declaring_class(declaring_class, production_classes, test_classes)
            if source_kind != 'test':
                if lookup_name not in seen_non_test:
                    seen_non_test.add(lookup_name)
                    stats[f'filtered_{source_kind}'] += 1
                continue

            if lookup_name in helpers_seen or lookup_name in ambiguous_helpers or lookup_name in unresolved_helpers:
                continue

            status, snippet = resolve_helper_snippet(lookup_name, declaring_class, arity, test_class_files, stats,
                                                       is_new=(prefix == 'NEW'))
            if status == 'ok':
                helpers_seen.add(lookup_name)
                helper_score = score_of(snippet, method_name=lookup_name.rsplit('.', 1)[-1]) if snippet else dict(ZERO_SCORE)
                add_score(helper_totals, helper_score)
            elif status == 'ambiguous':
                ambiguous_helpers.add(lookup_name)
                report_rows.append({'project': project_label, 'test': test_qname, 'helper': lookup_name, 'issue': 'ambiguous'})
            else:
                unresolved_helpers.add(lookup_name)
                report_rows.append({'project': project_label, 'test': test_qname, 'helper': lookup_name, 'issue': 'not_found'})

        total = dict(self_score)
        add_score(total, helper_totals)

        row = {
            'project': project_label,
            'test_class': test_class,
            'test_name': test_name,
            'category': 'pt' if is_pt else 'nonpt',
            'junit_api': classify_junit_api(d.get('importedPackages'), source, is_pt),
            'helper_count': len(helpers_seen),
            'ambiguous_helper_count': len(ambiguous_helpers),
            'unresolved_helper_count': len(unresolved_helpers),
            'helper_names': ';'.join(sorted(helpers_seen)),
            'ambiguous_helper_names': ';'.join(sorted(ambiguous_helpers)),
            'unresolved_helper_names': ';'.join(sorted(unresolved_helpers)),
        }
        for k in SCORE_KEYS:
            row[f'self_{k}'] = self_score[k]
            row[f'helper_{k}_sum'] = helper_totals[k]
            row[f'total_{k}'] = total[k]
        rows.append(row)

    return rows, report_rows, stats


def run_project(proj):
    print(f"\n=== {proj['name']} ===", file=sys.stderr)
    parsed_tests = load_test_jsons(proj['aaa_dir'])
    print(f'  {len(parsed_tests)} test JSON files', file=sys.stderr)

    production_classes, test_classes, test_class_files = build_source_class_sets(proj['base_dir'])
    print(f'  {len(production_classes)} production classes, {len(test_classes)} test classes', file=sys.stderr)

    rows, report_rows, stats = process_tests(parsed_tests, production_classes, test_classes, test_class_files, proj['name'])
    from collections import Counter as _C
    print(f'  pt={sum(1 for r in rows if r["category"]=="pt")} '
          f'nonpt={sum(1 for r in rows if r["category"]=="nonpt")}'
          f'  junit_api={dict(_C(r["junit_api"] for r in rows))}', file=sys.stderr)
    print(f'  Resolution stats: {dict(stats)}', file=sys.stderr)
    return rows, report_rows


def main():
    # Usage: build_test_metrics_unified.py [project_name ...] [--out path] [--report path]
    # With no project names given, runs the full PROJECTS list. Lets a subset
    # (e.g. just the newly-parsed projects) be run and written to its own
    # output file, to be concatenated with an already-computed CSV instead of
    # re-running everything.
    args = sys.argv[1:]
    out_csv, report_csv = OUT_CSV, REPORT_CSV
    names = []
    i = 0
    while i < len(args):
        if args[i] == '--out':
            out_csv = args[i + 1]
            i += 2
        elif args[i] == '--report':
            report_csv = args[i + 1]
            i += 2
        else:
            names.append(args[i])
            i += 1
    projects = make_projects(names) if names else PROJECTS

    all_rows = []
    all_report_rows = []
    for proj in projects:
        rows, report_rows = run_project(proj)
        all_rows.extend(rows)
        all_report_rows.extend(report_rows)

    fieldnames = ['project', 'test_class', 'test_name', 'category', 'junit_api', 'helper_count']
    for k in SCORE_KEYS:
        fieldnames += [f'self_{k}', f'helper_{k}_sum', f'total_{k}']
    fieldnames += ['ambiguous_helper_count', 'unresolved_helper_count',
                   'helper_names', 'ambiguous_helper_names', 'unresolved_helper_names']

    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)

    with open(report_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['project', 'test', 'helper', 'issue'])
        w.writeheader()
        w.writerows(all_report_rows)

    print(f'\nWrote {len(all_rows)} test rows to {out_csv}', file=sys.stderr)
    print(f'Wrote {len(all_report_rows)} issue rows to {report_csv}', file=sys.stderr)


if __name__ == '__main__':
    main()
