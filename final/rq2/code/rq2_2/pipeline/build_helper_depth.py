#!/usr/bin/env python3
"""
rq2.2 structure: MethodSource provider 的 helper 委托深度分析

数据来源:
  - /Users/immortal/PT_Empirical_Auto/pt_random_sampled_methods_v2.csv
    （之前抽样的 1604 条 PT，筛出 parameter_source == 'MethodSource'）
  - /Volumes/SSKSSD/apache-projects/<project>/AAA/*.json
    （每个测试方法一份，parsedStatementsSequence 是已解析好的、带缩进/tag 的调用轨迹）

方法学（写进论文前请核对，本脚本严格照此实现）:
  - depth: provider 方法本身 = depth 0，provider 直接调用的 helper = depth 1，
    以此类推；直接用 parsedStatementsSequence 的缩进层数 (缩进/4) 表示。
  - test-scope / production-scope: 直接信任 AAA parser 自带的 tag——
      TEST / TEST GET / TEST SET          -> test-scope
      裸签名(无前缀) / GET / SET           -> production-scope
      THIRD / THIRD GET / THIRD SET       -> 第三方或 JDK，排除
      NEW_JDK_CLASS                       -> JDK 构造函数，排除
      NEW                                 -> 项目内构造函数，默认不计入 helper
                                              （可调，见 COUNT_CONSTRUCTORS_AS_HELPER）
      ASSERT / MOCK / EXPECTEDEXCEPTION_* -> 断言/mock/异常规则脚手架，排除
      METHOD_REF_TEST / METHOD_REF_PROD   -> 方法引用，parser 已带作用域，分别入 test/prod
      METHOD_REF_THIRD / METHODSOURCE_EXTERNAL -> JDK/第三方，排除
      LOCAL_METHOD                        -> 匿名/局部类内部方法（#11），本身不算 helper，
                                              其子行照常分类（NEUTRAL_TAGS）
      SOURCE_FILE_NOT_FOUND / METHOD_NOT_FOUND_IN_SOURCE / METHODSOURCE_NOT_FOUND /
      UNRESOLVED_*: / UNKNOWN_PROJECT_CODE / MAX_DEPTH_REACHED
                                          -> 记为 unresolved，单独统计
      DIRECT_RECURSIVE / RECURSIVE_TO_ENTRY / INDIRECT_RECURSIVE
                                          -> 递归保护点，正确终止，单独计数
      METHOD_REF（旧数据裸 tag）           -> 用 file_index_cache 按声明类路径反查作用域
      其它全大写 token                     -> <unknown_tag>，报警不猜
  - 同一个测试若有多个 @MethodSource provider，把它们的子树池化在一起统计
    （max_depth 取并集最大值，distinct_helpers/total_calls 在池化后的调用集合上算）。

输出:
  rq2/rq2_2_structure/pt_methodsource_helper_depth.csv   主结果
  rq2/rq2_2_structure/unmatched_or_unresolved.csv        需要人工核对的行
  rq2/rq2_2_structure/project_coverage_summary.csv       按项目的覆盖率汇总
"""

# 向上找到 final/（paths.py 所在处）—— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO_ROOT = _paths.REPO
AAA_ROOT = _paths.APACHE_PROJECTS
BASE_DIR = _paths.RQ22_WORK
# 全量跑（run_full_rq22.sh）时用环境变量切换：样本清单 / 输出目录 / 项目范围（ALL = 清单里出现的全部项目）
# 全量运行时由驱动脚本 run_rq22.sh 通过 RQ22_SAMPLE_CSV 指定清单；缺省值是早期 pilot 抽样的清单（不随包分发）
SAMPLE_CSV = os.environ.get("RQ22_SAMPLE_CSV", os.path.join(REPO_ROOT, "pt_random_sampled_methods_v2.csv"))
OUT_DIR = os.environ.get("RQ22_OUT_DIR", BASE_DIR)
PROJECT_SCOPE = os.environ.get("RQ22_PROJECTS", "PILOT")

COUNT_CONSTRUCTORS_AS_HELPER = False  # 见文件头方法学说明，需要的话改 True

# 确认过的 18(clean) + 14(good) pilot 项目，文件夹名已核对与 AAA_ROOT 下实际目录一致
PILOT_PROJECTS = [
    # 完全干净 (0% unresolved), 18 个
    "commons-io", "commons-lang", "commons-compress", "commons-jexl", "commons-codec",
    "commons-imaging", "commons-cli", "commons-net", "commons-text", "commons-bcel",
    "creadur-rat", "opennlp", "mina-sshd", "orc", "jmeter", "storm", "jena",
    "httpcomponents-client",
    # 质量很好 (<3% unresolved), 14 个
    "commons-rng", "zookeeper", "poi", "wicket", "hudi", "qpid-broker-j",
    "james-project", "nifi", "avro", "uima-uimaj", "flink", "druid",
    "logging-log4j2", "ozone",
]

PROJECT_ALIAS = {
    "rat": "creadur-rat",
    "james": "james-project",
    "qpid": "qpid-broker-j",
    "uima": "uima-uimaj",
    "log4j": "logging-log4j2",
}

# Authoritative tag vocabulary, read directly off Javalang-analyzing-cli's
# TestCaseAnalyzer.java dfsAnalyze() (the only place that emits these strings) rather than
# inferred from observed data — anything dfsAnalyze can emit is listed here, whether or not
# it happened to show up in the pilot sample yet. Two tag shapes exist:
#   "TAG content#[start-end]"   (space-separated; most tags)
#   "TAG: content#[start-end]"  (colon-separated; the four UNRESOLVED_*: tags below)
# Getting a tag's shape wrong means it silently falls through to the `<untagged>` bucket,
# which is exactly the failure mode this file used to have for UNRESOLVED_INVOCATION etc.
SPACE_TAGS = (
    "THIRD GET", "THIRD SET", "THIRD", "TEST GET", "TEST SET", "TEST",
    "GET", "SET",  # bare production getter/setter — must be listed, or these fall through
    # to UNKNOWN_TAG_MARKER since they're indistinguishable in shape from an unrecognized tag.
    "NEW_JDK_CLASS", "NEW", "ASSERT", "MOCK",
    "SOURCE_FILE_NOT_FOUND", "METHOD_NOT_FOUND_IN_SOURCE",
    # METHOD_REF_* are emitted by the fixed analyzer (see TestCaseAnalyzer.java's
    # ExpressionMethodReference branch): a method reference now carries its resolved scope, and a
    # _TEST one has additionally had its body expanded into the trace. Bare "METHOD_REF" is the
    # legacy shape from data generated before that fix — still listed because a small number of
    # pre-fix JSONs remain (commons-jexl CacheTest, kept deliberately; see the re-run notes) and
    # because dropping it would turn those lines into <unknown_tag> noise rather than something
    # the FALLBACK_TAGS path can still resolve by file path.
    "METHOD_REF_TEST", "METHOD_REF_PROD", "METHOD_REF_THIRD", "METHOD_REF",
    "METHODSOURCE_NOT_FOUND", "METHODSOURCE_EXTERNAL", "METHODSOURCE", "FIELDSOURCE",
    # LOCAL_METHOD (Phase 2 fix #11): a call to a method declared on an anonymous/local class
    # *inside* the method being expanded (typical: double-brace `new ArrayList<>() {{ add(..); }}`
    # with private helpers on the anonymous class). Previously these came out as
    # METHOD_NOT_FOUND_IN_SOURCE. The analyzer now expands the local method's body as children.
    "LOCAL_METHOD",
    "EXPECTEDEXCEPTION_RULE", "EXPECTEDEXCEPTION_ANNOTATION",
    "DIRECT_RECURSIVE", "RECURSIVE_TO_ENTRY", "UNKNOWN_PROJECT_CODE",
    # Phase 2: dfsAnalyze now keeps the whole expansion path, so mutual recursion (A -> B -> A,
    # e.g. hadoop AllocationFileWriter.printQueues <-> AllocationFileQueue.render) terminates with
    # INDIRECT_RECURSIVE instead of a StackOverflowError that lost the entire test. MAX_DEPTH_REACHED
    # is the hard cap (60 levels) — a genuine truncation, counted as unresolved.
    "INDIRECT_RECURSIVE", "MAX_DEPTH_REACHED",
)
COLON_TAGS = (
    "UNRESOLVED_INVOCATION", "UNRESOLVED_METHOD_REF",
    "UNRESOLVED_CONSTRUCTOR", "UNRESOLVED_DECLARING_CLASS",
)
# Longest-first within each group so e.g. "THIRD GET" matches before the "THIRD" prefix does
# (matters for readability of the regex, not correctness here since every alternative is
# followed by a literal space/colon boundary — but keep the ordering to avoid future foot-guns
# if a shorter tag name is ever added that's a true prefix of a longer one without a
# space/underscore boundary between them).
_SPACE_ALT = "|".join(re.escape(t) for t in sorted(SPACE_TAGS, key=len, reverse=True))
_COLON_ALT = "|".join(re.escape(t) for t in sorted(COLON_TAGS, key=len, reverse=True))
# re.DOTALL is essential, not cosmetic: when the analyzer can't resolve a binding it embeds
# `mi.toString()` / `cic.toString()` in the tag content, and for a lambda or an anonymous
# class that rendering is MULTI-LINE (real example from camel:
#   "UNRESOLVED_CONSTRUCTOR: new Processor(){\n  public void process(...){\n ... }\n}\n#[59-70]").
# Without DOTALL the `(.*)` stops at the first newline, the whole pattern fails to match, and
# the line silently fell through to the `<untagged>` bucket — i.e. was counted as PRODUCTION
# code. 1552 such lines exist across the corpus. The only `.` metacharacters in this pattern
# are the two content groups (tag names are re.escape'd), so DOTALL is safe here.
TAG_RE = re.compile(rf"^(?:({_COLON_ALT}):\s(.*)|({_SPACE_ALT})\s(.*))$", re.DOTALL)

# A line that doesn't match TAG_RE is either (a) a bare production-method signature — the
# analyzer emits these with NO prefix at all by design (see TestCaseAnalyzer.java's plain
# `statementDetails = qualifiedName + getParameters(binding)` branch) and every one of those
# starts with a lowercase package segment (`org.foo.Bar.baz(...)`), or (b) a genuinely
# unrecognized tag we haven't accounted for above — by convention every real tag is an
# ALL_CAPS_WITH_UNDERSCORES token. Telling these apart is exactly what used to be missing:
# previously *anything* unmatched became `<untagged>` and was silently counted as production.
_LOOKS_LIKE_UNKNOWN_TAG = re.compile(r"^[A-Z][A-Z0-9_]*(:|\s|$)")

EXCLUDED_TAGS = {
    "THIRD", "THIRD GET", "THIRD SET", "NEW_JDK_CLASS", "ASSERT", "MOCK",
    "EXPECTEDEXCEPTION_RULE", "EXPECTEDEXCEPTION_ANNOTATION",
    # A method reference into JDK/third-party code, classified as such by the analyzer itself —
    # same status as a plain THIRD call and excluded for the same reason.
    "METHOD_REF_THIRD", "SYNTHETIC_ENUM_MEMBER",  # == SYNTHETIC_TAG (defined below)
    # METHODSOURCE_EXTERNAL (Phase 2): @MethodSource("java.util.Locale#getAvailableLocales")-style
    # providers living in the JDK. Not a lookup failure — the provider is simply outside the
    # project, same status as a THIRD call.
    "METHODSOURCE_EXTERNAL",
}
# Structural/transparent lines: the line itself is not a helper *call* to count, but its children
# (deeper-indented lines) are real calls and are classified normally. LOCAL_METHOD is textually
# part of the provider body (its Cognitive Complexity is already counted there by the
# TypeDeclarationStatement/AnonymousClassDeclaration walk in CognitiveComplexityCalculator), so
# counting it as a distinct test-scope helper would double-count. Known residual: calls made
# *from* a local method sit one indent deeper than they conceptually are, so max_depth can be
# over-stated by the local-method nesting level for those (rare) providers.
NEUTRAL_TAGS = {"LOCAL_METHOD"}
# Cycle guards: dfsAnalyze deliberately stops here (it detected a genuine recursive call back
# to the entry test method or to the method currently being expanded) — this is correct,
# intentional termination, not a traversal gap like METHOD_REF/NEW are.
RECURSIVE_TAGS = {"DIRECT_RECURSIVE", "RECURSIVE_TO_ENTRY", "INDIRECT_RECURSIVE"}
# Binding/lookup failures and UNKNOWN_PROJECT_CODE (source+method found, but the file matched
# neither the production nor test path heuristic — a genuine "couldn't classify" case, not a
# missing-tag problem) all represent the analyzer being unable to resolve or classify something,
# as opposed to a genuinely unrecognized tag string (see UNKNOWN_TAG_MARKER below).
UNRESOLVED_TAGS = {
    "SOURCE_FILE_NOT_FOUND", "METHOD_NOT_FOUND_IN_SOURCE", "METHODSOURCE_NOT_FOUND",
    "UNRESOLVED_INVOCATION", "UNRESOLVED_METHOD_REF", "UNRESOLVED_CONSTRUCTOR",
    "UNRESOLVED_DECLARING_CLASS", "UNKNOWN_PROJECT_CODE", "MAX_DEPTH_REACHED",
}
# METHOD_REF_TEST / _PROD come from the fixed analyzer with scope already resolved from the
# declaring class's source path — exactly the information the legacy bare METHOD_REF lacked, so
# they join the normal scope buckets directly instead of going through the FALLBACK_TAGS
# file-index lookup. A _TEST reference also had its body expanded into the trace, so the helpers
# it reaches are counted from those expanded lines just like any other test-scope call chain.
TEST_TAGS = {"TEST", "TEST GET", "TEST SET", "METHOD_REF_TEST"}
PROD_TAGS = {"<untagged>", "GET", "SET", "METHOD_REF_PROD"}
# NEW is deliberately not in here: dfsAnalyze never recurses into a constructor body (see
# ClassInstanceCreation handling), so "helper" in the FALLBACK_TAGS sense (a tag whose scope
# needs to be resolved via the file index, same as METHOD_REF) doesn't apply to it the same
# way; whether to count constructor calls as helpers at all is COUNT_CONSTRUCTORS_AS_HELPER's
# job, unchanged from before.
FALLBACK_TAGS = {"METHOD_REF"}
ENTRY_TAG = "METHODSOURCE"
ENTRY_TAGS = ("METHODSOURCE", "FIELDSOURCE")   # @FieldSource 的入口行（Phase 4）与 @MethodSource / @ArgumentsSource 同形
# Sentinel tag for a line that looked like it should be a real tag (all-caps token) but isn't
# in SPACE_TAGS/COLON_TAGS above — i.e. dfsAnalyze started emitting something new that this
# script's vocabulary hasn't caught up to. Must NEVER be classified as production; see
# classify_line() and compute_metrics().
UNKNOWN_TAG_MARKER = "<unknown_tag>"
# Compiler-synthesised enum members have no source body, so the analyzer reports them as
# METHOD_NOT_FOUND_IN_SOURCE although nothing is actually unresolved (zookeeper: all 450 residual
# MNF lines after the Phase 2 rerun are Enum.values()). classify_line() rewrites those to this
# tag, which is excluded like a JDK call. Record accessors / Lombok getters (causeway) are the
# other residual MNF family; they cannot be told apart syntactically here and stay unresolved.
SYNTHETIC_TAG = "SYNTHETIC_ENUM_MEMBER"
_SYNTHETIC_ENUM_RE = re.compile(r"\.(values\(\)|valueOf\([^,()]*\)|ordinal\(\)|name\(\))$")


def norm_project(name):
    key = name.strip().lower()
    key = PROJECT_ALIAS.get(key, key)
    return key


def load_pilot_sample():
    rows = []
    seen = set()
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["parameter_source"] not in os.environ.get("RQ22_PARAM_SOURCE", "MethodSource").split(","):
                continue
            canon = norm_project(row["project"])
            if PROJECT_SCOPE == "PILOT" and canon not in PILOT_PROJECTS:
                continue
            fqcn = derive_fqcn(row["file_path"])
            key = (canon, fqcn, row["test_name"])
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "project": canon,
                "project_raw": row["project"],
                "test_class": fqcn,
                "test_name": row["test_name"],
                "file_path_raw": row["file_path"],
            })
    return rows


def derive_fqcn(file_path):
    """从 file_path 里抠出 package.ClassName。

    先按标准 Maven 布局 src/{test,it}/java/<pkg>/X.java 匹配；不中再退到 src/{test,it}/<pkg>/X.java
    （#12：orc 这类项目 src/test/ 下直接就是包目录，没有 java/ 这一层）。仍不中返回 None。
    """
    for pat in (r"src/(?:test|it)/java/(.+)\.java$", r"src/(?:test|it)/(.+)\.java$"):
        m = re.search(pat, file_path)
        if m:
            return m.group(1).replace("/", ".")
    return None


def split_aaa_body(body):
    """把文件名主体 '<fqcn>_<testCaseName>' 拆成 (fqcn, testCaseName)。

    #6：不能 rsplit('_', 1)——测试方法名本身常含下划线（test_Equality_Hash、gsp_dft_user0）。
    fqcn 是带点的全限定名而 testCaseName 不含点，所以先定位最后一个 '.'，其后第一个 '_'
    才是类名与方法名的分界。只有当简单类名自己带下划线（如 jena 的 Test_schemagen）时仍会
    拆错，这种情况靠 find_json_file 的"直接拼文件名"路径兜住，不依赖这里。
    """
    dot = body.rfind(".")
    us = body.find("_", dot + 1 if dot >= 0 else 0)
    if us < 0:
        return None, None
    return body[:us], body[us + 1:]


def build_aaa_index(project):
    """建立该项目 AAA 目录下 (fqcn, testCaseName) -> 真实文件名 的索引，一次性建好复用。
    只作为 find_json_file 的兜底查找用；主路径是直接按已知 fqcn+test_name 拼文件名。"""
    aaa_dir = os.path.join(AAA_ROOT, project, "AAA")
    index = {}
    test_classes = set()
    if not os.path.isdir(aaa_dir):
        return index, test_classes, aaa_dir
    prefix = f"{project}_"
    for fname in os.listdir(aaa_dir):
        if fname.startswith("._") or fname.endswith("-log.json") or not fname.endswith(".json"):
            continue
        if not fname.startswith(prefix):
            continue
        fqcn, test_name = split_aaa_body(fname[len(prefix):-len(".json")])
        if fqcn is None:
            continue
        index[(fqcn, test_name)] = fname
        test_classes.add(fqcn)
    return index, test_classes, aaa_dir


# ⑤: 重载测试的文件名带 "-p<参数个数>[-<序号>]"；④: @Nested / 静态嵌套类里声明的测试，AAA 文件名
# 里的类是 Outer.Inner，而样本表只记外层类。两种情况都在这里兜底。
_OVERLOAD_SUFFIX_RE = re.compile(r"-p\d+(?:-\d+)?$")
LAST_MATCH_NOTE = {}   # (project, fqcn, test_name) -> 说明（ambiguous 等），供 problems 输出


def _is_methodsource_pt(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return False
    return any("MethodSource" in str(p) for p in d.get("parameterSources", []))


def _earliest_declared(project, aaa_dir, fns):
    """在测试类源码里找各候选 JSON 的 testCaseSourceCode 出现的位置，返回最靠前的那个。"""
    best = None
    for fn in fns:
        try:
            d = json.load(open(os.path.join(aaa_dir, fn), encoding="utf-8"))
        except Exception:
            return None
        cls = d.get("testClassName", "")
        simple = next((seg for seg in cls.split(".") if seg[:1].isupper()), cls.split(".")[-1])
        path = (load_file_index(project) or {}).get(simple)
        if isinstance(path, list):
            path = path[0] if len(path) == 1 else None
        src_code = (d.get("testCaseSourceCode") or "").strip()
        if not path or not src_code:
            return None
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            return None
        # 用签名行（去掉注解）定位，避免注解顺序/格式差异
        sig_line = next((l.strip() for l in src_code.splitlines() if not l.strip().startswith("@") and l.strip()), "")
        pos = text.find(sig_line) if sig_line else -1
        if pos < 0:
            return None
        if best is None or pos < best[0]:
            best = (pos, fn)
    return best[1] if best else None


def find_json_file(project, index, aaa_dir, fqcn, test_name):
    # 主路径：fqcn 和 test_name 都已知时直接拼出确切文件名——零歧义，不受任何拆分规则影响。
    if fqcn is not None:
        direct = os.path.join(aaa_dir, f"{project}_{fqcn}_{test_name}.json")
        if os.path.exists(direct):
            return direct
        if (fqcn, test_name) in index:
            return os.path.join(aaa_dir, index[(fqcn, test_name)])
        # ⑤ 同类重载：<fqcn>_<test>-pN.json；④ 嵌套类：<fqcn>.<Inner>_<test>[-pN].json
        cands = []
        for (fq, tn), fn in index.items():
            base = _OVERLOAD_SUFFIX_RE.sub("", tn)
            if base != test_name:
                continue
            if fq == fqcn or fq.startswith(fqcn + "."):
                cands.append(fn)
        if len(cands) > 1:
            # 重载里只有一个是 MethodSource PT（commons-io NullInputStreamTest.testReadAfterClose 的
            # @Test / @ParameterizedTest 双胞胎）；嵌套类各有一份同名 PT 时无法唯一确定（avro）。
            pt = [fn for fn in cands if _is_methodsource_pt(os.path.join(aaa_dir, fn))]
            if len(pt) == 1:
                cands = pt
            elif len(pt) > 1:
                # 同名的多个 MethodSource PT（ozone TestDurationUtil.testDuration(String,Duration) /
                # testDuration(Duration)）：样本行只记了名字，本身就分不出是哪一个。与 Java 侧
                # findTestMethodByName（取源码里最先声明的）保持一致：按声明位置取第一个。
                first = _earliest_declared(project, aaa_dir, pt)
                if first is not None:
                    LAST_MATCH_NOTE[(project, fqcn, test_name)] = "OVERLOAD_PICKED_FIRST_DECLARED:" + first
                    cands = [first]
        if len(cands) == 1:
            return os.path.join(aaa_dir, cands[0])
        if len(cands) > 1:
            LAST_MATCH_NOTE[(project, fqcn, test_name)] = "AMBIGUOUS_NESTED_OR_OVERLOAD:" + "|".join(sorted(cands))
            return None
    # 兜底：fqcn 未知（非标准布局等），按 test_name 找唯一匹配
    candidates = [fn for (fq, tn), fn in index.items() if _OVERLOAD_SUFFIX_RE.sub("", tn) == test_name]
    if len(candidates) == 1:
        return os.path.join(aaa_dir, candidates[0])
    return None


def classify_line(line, test_classes):
    stripped = line.strip()
    m = TAG_RE.match(stripped)
    if m:
        # Exactly one of the two alternatives (colon-tag vs space-tag) matched; the other
        # pair of groups is None.
        tag = m.group(1) if m.group(1) is not None else m.group(3)
        rest = m.group(2) if m.group(2) is not None else m.group(4)
    elif _LOOKS_LIKE_UNKNOWN_TAG.match(stripped):
        # Looks like a tag (leading ALL_CAPS token) but isn't one we know about — dfsAnalyze
        # started emitting something new. Never fall through to production for this; see
        # compute_metrics()/UNKNOWN_TAG_MARKER.
        tag, rest = UNKNOWN_TAG_MARKER, stripped
    else:
        # Genuine bare production-method signature (starts with a lowercase package segment,
        # e.g. "org.foo.Bar.baz(...)") — dfsAnalyze emits these with no tag prefix at all.
        tag, rest = "<untagged>", stripped
    signature = re.sub(r"#\[\d+-\d+\]\s*$", "", rest).strip()
    if tag == "METHOD_NOT_FOUND_IN_SOURCE" and _SYNTHETIC_ENUM_RE.search(signature):
        tag = SYNTHETIC_TAG
    # ③: analyzer appends " ctx=<context>" to METHOD_REF_* signatures; strip it here so every
    # consumer keeps seeing a plain signature. The context itself is consumed by
    # drop_data_method_refs() before lines reach compute_metrics().
    m_ctx = _CTX_RE.search(signature)
    if m_ctx:
        signature = signature[:m_ctx.start()].rstrip()
    return tag, signature


_CTX_RE = re.compile(r"\s+ctx=(\S+)$")
# ③ (user decision 2026-09-15, option (b) "context-sensitive"): a method reference is only a call the
# provider makes when the provider's own pipeline invokes it. Passed as *data* it is invoked by someone
# else later, so neither the reference nor its (expanded) subtree counts as a helper call. Data
# contexts = argument of a data-construction call (below), constructor argument, returned, assigned,
# array element, conditional branch, or a bare lambda body. `call:<anything else>` (map, forEach,
# collect, assertThrows, ...) and `target:` (the reference itself is invoked) count. Lines without a
# ctx (pre-Phase-3 data; only METHOD_REF_THIRD ones remain, which are excluded anyway) count as before.
DATA_CTX_CALLS = {
    "of", "arguments", "argumentSet", "asList", "add", "addAll", "put", "putAll", "set", "singletonList",
    "singleton", "listOf", "setOf", "mapOf", "build", "named", "withArgs", "with", "append", "offer", "push",
}
def method_ref_ctx_is_data(ctx):
    if ctx is None:
        return False
    if ctx.startswith("call:"):
        return ctx[5:] in DATA_CTX_CALLS
    if ctx.startswith("target:"):
        return False
    return True   # new:*, return, assign, array, lambda, conditional, other


def kept_indices_after_dropping_data_method_refs(lines):
    """Indices of `lines` that survive removing METHOD_REF_* lines whose ctx says "passed as data",
    together with their expanded subtree. dfsAnalyze emits children *before* the parent line
    (post-order), so a reference at depth k owns the maximal run of lines immediately before it
    with depth > k."""
    out = []   # indices
    for i, line in enumerate(lines):
        stripped = line.strip()
        depth = (len(line) - len(line.lstrip(" "))) // 4
        m_tag = re.match(r"^(METHOD_REF_TEST|METHOD_REF_PROD|METHOD_REF_THIRD)\s", stripped)
        if m_tag:
            m_ctx = _CTX_RE.search(re.sub(r"#\[\d+-\d+\]\s*$", "", stripped))
            if m_ctx and method_ref_ctx_is_data(m_ctx.group(1)):
                while out and (len(lines[out[-1]]) - len(lines[out[-1]].lstrip(" "))) // 4 > depth:
                    out.pop()
                continue
        out.append(i)
    return out


def drop_data_method_refs(lines):
    return [lines[i] for i in kept_indices_after_dropping_data_method_refs(lines)]


def declaring_class_of(signature):
    # signature 形如 pkg.Class.method(Params) 或含泛型的复杂形式，做 best-effort 截断
    head = signature.split("(", 1)[0]
    if "." not in head:
        return None
    return head.rsplit(".", 1)[0]


# METHOD_REF/DIRECT_RECURSIVE 这两个 tag，Javalang-analyzing-cli 自己没有像普通调用那样
# 判断 test/prod（见 TestCaseAnalyzer.java 里 ExpressionMethodReference 分支，没调用
# isTestCode/isProductionCode），只给了声明类全限定名。之前退化用"是不是某个 AAA testClassName"
# 判断，对纯工具类（自己没有 @Test 方法，但确实在 src/test 下）会判错。
# 这里改成按声明类反查文件路径，复用已经建好并缓存到磁盘的 file_index_cache/<project>.idx
# （跟 Cognitive Complexity 那批用的是同一份缓存，不需要重新扫文件系统），
# 用解析器自己判 test/prod 的同一条规则：路径含 /src/test/ -> test，
# 含 /src/main/ 或者压根找不到 /src/test/ -> prod；项目源码树里根本查不到这个类
# （大概率是 JDK/第三方，比如 java.nio.file.Path::toString）-> 视同第三方，直接跳过。
FILE_INDEX_CACHE_DIR = os.path.join(BASE_DIR, "file_index_cache")
_file_index_cache = {}


def load_file_index(project):
    if project in _file_index_cache:
        return _file_index_cache[project]
    path = os.path.join(FILE_INDEX_CACHE_DIR, f"{project}.idx")
    index = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if "\t" not in line:
                    continue
                simple, file_path = line.rstrip("\n").split("\t", 1)
                index.setdefault(simple, []).append(file_path)
    _file_index_cache[project] = index
    return index


def resolve_scope_via_path(declaring_class, file_index):
    """按声明类反查文件路径，判断 test/prod；项目里完全找不到就返回 None（视同第三方）。"""
    if not declaring_class:
        return None
    parts = declaring_class.split(".")
    top_idx = next((i for i, p in enumerate(parts) if p[:1].isupper()), len(parts) - 1)
    simple = parts[top_idx]
    candidates = file_index.get(simple)
    if not candidates:
        return None
    # 多个候选（同名类在不同包），优先选包路径匹配的那个
    pkg_path = "/".join(parts[:top_idx])
    chosen = None
    if pkg_path:
        for c in candidates:
            if pkg_path.replace(".", "/") in c.replace(os.sep, "/"):
                chosen = c
                break
    if chosen is None:
        chosen = candidates[0]
    normalized = chosen.replace(os.sep, "/")
    if "/src/test/" in normalized:
        return "test"
    return "prod"


def extract_provider_subtrees(seq):
    """返回池化后的 (depth, tag, signature) 列表，以及解析到的 provider 数量。"""
    pooled = []
    n_resolved = 0
    i = 0
    while i < len(seq):
        line = seq[i]
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0 and stripped.startswith(tuple(t + " " for t in ENTRY_TAGS)):
            n_resolved += 1
            j = i + 1
            while j < len(seq):
                nxt = seq[j]
                nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                if nxt_indent == 0:
                    break
                pooled.append(nxt)
                j += 1
            i = j
        else:
            i += 1
    return pooled, n_resolved


def compute_metrics(pooled_lines, test_classes, file_index=None):
    """Computes helper-depth metrics for one pooled provider subtree.

    ③: method references passed as data (and their expanded subtrees) are removed first.

    Classification never falls back to production silently: every line's tag lands in exactly
    one of TEST_TAGS / PROD_TAGS / EXCLUDED_TAGS / FALLBACK_TAGS(METHOD_REF, resolved via file
    index) / RECURSIVE_TAGS / UNRESOLVED_TAGS / UNKNOWN_TAG_MARKER. Only the first two
    contribute to max_depth_*/distinct_helpers_*/total_calls_*; everything else is tracked
    separately (unresolved_*, unknown_*, recursive_*) so it can be surfaced instead of quietly
    contaminating the production-dependency counts.
    """
    scopes = {
        "test": {"depths": [], "sigs": set(), "n": 0},
        "prod": {"depths": [], "sigs": set(), "n": 0},
    }
    unresolved_count = 0
    unresolved_types = Counter()
    unknown_count = 0
    unknown_lines = []  # first few raw lines, for debugging/audit — not every occurrence
    recursive_count = 0
    recursive_types = Counter()
    method_ref_count = 0  # every METHOD_REF line, regardless of resolved scope: dfsAnalyze
    # never recurses into a method reference's target (see TestCaseAnalyzer.java's
    # ExpressionMethodReference branch), so any METHOD_REF means the subtree below it — if
    # the target is project-defined — is simply absent from this JSON, not merely
    # misclassified. That's a traversal gap, not something this script can repair.
    method_ref_unresolved_scope = 0  # target not found anywhere in the project's file index

    for line in drop_data_method_refs(pooled_lines):
        indent = len(line) - len(line.lstrip(" "))
        depth = indent // 4
        tag, sig = classify_line(line, test_classes)

        if tag == UNKNOWN_TAG_MARKER:
            unknown_count += 1
            if len(unknown_lines) < 5:
                unknown_lines.append(line.strip())
            continue
        if tag in UNRESOLVED_TAGS:
            unresolved_count += 1
            unresolved_types[tag] += 1
            continue
        if tag in RECURSIVE_TAGS:
            recursive_count += 1
            recursive_types[tag] += 1
            continue
        if tag in EXCLUDED_TAGS:
            continue
        if tag == "NEW" and not COUNT_CONSTRUCTORS_AS_HELPER:
            continue
        if tag in ENTRY_TAGS or tag in NEUTRAL_TAGS:
            continue

        if tag in TEST_TAGS:
            scope = "test"
        elif tag in PROD_TAGS or (tag == "NEW" and COUNT_CONSTRUCTORS_AS_HELPER):
            scope = "prod"
        elif tag in FALLBACK_TAGS:  # METHOD_REF
            method_ref_count += 1
            dc = declaring_class_of(sig)
            resolved = resolve_scope_via_path(dc, file_index) if file_index is not None else None
            if resolved is None:
                if file_index is not None:
                    method_ref_unresolved_scope += 1
                continue  # 项目源码树里查不到，视同第三方/JDK，跳过，不计入任何 scope
            scope = resolved
        else:
            # Should be unreachable: every tag in SPACE_TAGS/COLON_TAGS is handled by one of
            # the branches above, and anything else already became UNKNOWN_TAG_MARKER in
            # classify_line(). If this fires, the vocabulary tables and this dispatch have
            # drifted apart — surface it the same way as a real unknown tag rather than
            # guessing "prod".
            unknown_count += 1
            if len(unknown_lines) < 5:
                unknown_lines.append(line.strip())
            continue

        scopes[scope]["depths"].append(depth)
        scopes[scope]["sigs"].add(sig)
        scopes[scope]["n"] += 1

    out = {}
    for scope in ("test", "prod"):
        s = scopes[scope]
        out[f"max_depth_{scope}"] = max(s["depths"]) if s["depths"] else 0
        out[f"distinct_helpers_{scope}"] = len(s["sigs"])
        out[f"total_calls_{scope}"] = s["n"]
    out["unresolved_count"] = unresolved_count
    out["has_unresolved"] = unresolved_count > 0
    out["unresolved_types"] = ";".join(sorted(unresolved_types)) if unresolved_types else ""
    out["unknown_tag_count"] = unknown_count
    out["has_unknown_tag"] = unknown_count > 0
    out["unknown_tag_examples"] = " | ".join(unknown_lines)
    out["recursive_count"] = recursive_count
    out["recursive_types"] = ";".join(sorted(recursive_types)) if recursive_types else ""
    out["method_ref_count"] = method_ref_count
    out["method_ref_unresolved_scope_count"] = method_ref_unresolved_scope
    # A METHOD_REF always means an unexpanded subtree is missing (structural gap in the JSON
    # itself, not a classification issue); an unresolved binding/lookup means the analyzer gave
    # up on that branch. Either way the metrics above are a LOWER BOUND for this provider, not
    # necessarily the true value — recursive cycle-guards don't count here since those are
    # correct, complete terminations, not gaps.
    out["traversal_may_be_incomplete"] = (unresolved_count > 0) or (method_ref_count > 0)
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    sample_rows = load_pilot_sample()
    print(f"pilot MethodSource 样本行数（已归一化项目名 + 去重）: {len(sample_rows)}", file=sys.stderr)

    aaa_cache = {}
    results = []
    problems = []
    coverage = Counter()

    for row in sample_rows:
        project = row["project"]
        if project not in aaa_cache:
            aaa_cache[project] = build_aaa_index(project)
        index, test_classes, aaa_dir = aaa_cache[project]

        coverage[(project, "sampled")] += 1

        if not os.path.isdir(aaa_dir):
            problems.append({**row, "reason": "aaa_dir_not_found"})
            coverage[(project, "aaa_dir_missing")] += 1
            continue

        json_path = find_json_file(project, index, aaa_dir, row["test_class"], row["test_name"])
        if json_path is None:
            note = LAST_MATCH_NOTE.get((project, row["test_class"], row["test_name"]))
            problems.append({**row, "reason": note or "json_not_found"})
            coverage[(project, "json_not_found")] += 1
            continue

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            problems.append({**row, "reason": f"json_parse_error:{e}"})
            coverage[(project, "json_parse_error")] += 1
            continue

        seq = data.get("parsedStatementsSequence", [])
        param_sources = data.get("parameterSources", [])
        n_expected = sum(1 for p in param_sources if "MethodSource" in str(p))
        pooled, n_resolved = extract_provider_subtrees(seq)

        if n_resolved == 0:
            # ⑥: provider 是 JDK/第三方方法（METHODSOURCE_EXTERNAL）——不是解析失败，是没有项目内 provider
            # 可分析；单列一类，三个维度 N/A。
            reason = ("external_provider" if any(l.startswith("METHODSOURCE_EXTERNAL") for l in seq)
                      else "no_methodsource_line_in_trace")
            problems.append({**row, "reason": reason, "n_expected_providers": n_expected})
            coverage[(project, "external_provider" if reason == "external_provider" else "no_methodsource_resolved")] += 1
            continue

        metrics = compute_metrics(pooled, test_classes, load_file_index(project))
        results.append({
            "project": project,
            # ④: 键用样本表里的类名（外层类），不用 AAA 里的声明类（可能是 Outer.Inner），否则 merge 对不上；
            # AAA 里的实际声明类另存一列。
            "test_class": row["test_class"],
            "test_name": row["test_name"],
            "aaa_test_class": data.get("testClassName", ""),
            "aaa_test_name": data.get("testCaseName", ""),
            "n_providers_expected": n_expected,
            "n_providers_resolved": n_resolved,
            **metrics,
        })
        coverage[(project, "ok")] += 1

    # 主结果
    out_csv = os.path.join(OUT_DIR, "pt_methodsource_helper_depth.csv")
    # 新增列全部追加在末尾，不改动/不重排已有列，保持对下游脚本(build_dependency_v2.py 等)
    # 和已经写好的分析代码的兼容——只是"打补丁"，不是重做这份 CSV 的 schema。
    fieldnames = ["project", "test_class", "test_name", "n_providers_expected", "n_providers_resolved",
                  "max_depth_test", "distinct_helpers_test", "total_calls_test",
                  "max_depth_prod", "distinct_helpers_prod", "total_calls_prod", "unresolved_count",
                  "has_unresolved", "unresolved_types",
                  "unknown_tag_count", "has_unknown_tag", "unknown_tag_examples",
                  "recursive_count", "recursive_types",
                  "method_ref_count", "method_ref_unresolved_scope_count",
                  "traversal_may_be_incomplete", "aaa_test_class", "aaa_test_name"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    # 未匹配 / 未解析
    prob_csv = os.path.join(OUT_DIR, "unmatched_or_unresolved.csv")
    prob_fields = ["project", "project_raw", "test_class", "test_name", "file_path_raw",
                   "reason", "n_expected_providers"]
    with open(prob_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=prob_fields)
        w.writeheader()
        for p in problems:
            w.writerow({k: p.get(k, "") for k in prob_fields})

    # 覆盖率汇总
    cov_csv = os.path.join(OUT_DIR, "project_coverage_summary.csv")
    statuses = ["sampled", "ok", "json_not_found", "no_methodsource_resolved", "external_provider",
                "aaa_dir_missing", "json_parse_error"]
    with open(cov_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["project"] + statuses)
        for project in (PILOT_PROJECTS if PROJECT_SCOPE == "PILOT" else sorted({r["project"] for r in sample_rows})):
            w.writerow([project] + [coverage[(project, s)] for s in statuses])

    print(f"\n主结果: {out_csv} ({len(results)} 行)")
    print(f"待核对: {prob_csv} ({len(problems)} 行)")
    print(f"覆盖率汇总: {cov_csv}")

    n_unresolved = sum(1 for r in results if r["has_unresolved"])
    n_unknown = sum(1 for r in results if r["has_unknown_tag"])
    n_method_ref = sum(1 for r in results if r["method_ref_count"] > 0)
    n_incomplete = sum(1 for r in results if r["traversal_may_be_incomplete"])
    print(f"\n[fail-safe 分类统计] 共 {len(results)} 条 OK 结果里：")
    print(f"  含 unresolved 的: {n_unresolved} 条")
    print(f"  含未知 tag（词表需要补充）的: {n_unknown} 条")
    print(f"  含 METHOD_REF（子树天然缺失，见 dfsAnalyze 的架构性限制）的: {n_method_ref} 条")
    print(f"  traversal_may_be_incomplete（上述任一，metrics 为下界而非精确值）的: {n_incomplete} 条")
    if n_unknown:
        print("  ⚠️ 出现未知 tag，说明 SPACE_TAGS/COLON_TAGS 词表需要跟 TestCaseAnalyzer.java 重新核对，"
              "已保守地不计入 prod/test，但建议检查 unmatched_or_unresolved 之外的这批未知 tag 具体内容。")


if __name__ == "__main__":
    main()
