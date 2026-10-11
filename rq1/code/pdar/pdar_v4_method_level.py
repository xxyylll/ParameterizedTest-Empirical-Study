#!/usr/bin/env python3
"""PDAR v4 第二阶段：方法级 Layer 1 ——「改动行 ∩ PT 方法行区间」。

方法定义、验证与结果见 PDAR_METHOD.md；本文件只记实现层面的要点。

### 分工

第一阶段的逐提交表（`result_v3/{project}_commits.csv`，即论文快照）提供提交集合、分母
`touched_test` 与作者 email，原样复用。分子的两层由本脚本**完整重算**：

  - L1（JUnit 5）：方法级，见下。
  - L2（JUnit 4）：类级、两侧 —— 改动行落在改动前或改动后版本里某个
    `@RunWith(...Parameterized...)` 类的区间内（扣除其中嵌套的独立测试类，见 `pt_spans.py`）。
    第一阶段的 L2 是文件级的，有路径解析 bug（正则 `b/(.+\.java)$` 会从 a/ 路径中间以 b 结尾的
    目录处开始匹配，如 `iotdb/`、`db/`、`lib/`），模式漏掉 `value =` 写法，且只看改动后的版本。
  - L3（pickaxe）不再进入分子：L1、L2 已覆盖 .java 里 PT 注解的一切增删。

新判定（定义见 `pt_spans.py`）：

    取 -U0 diff。`-` 行的行号属于父提交的文件，`+` 行属于本提交的文件（-M 识别重命名）。
    任一改动行落在对应那一侧快照里某个 PT 区间内 → 命中。

两种口径同时算：`l1m_pt`（只算 PT 方法本身）与 `l1m_prov`（再加同文件的 provider /
field / enum / ArgumentsProvider 类；主口径）。

### 和已发表口径一致的细节

  - **merge 提交与根提交不判定。** 已发表那轮用 `git diff-tree -p <c>`：对 merge 默认
    无输出，对根提交（无 `--root`）也无输出，所以这两类在表里恒为 0。这里保持原值。
  - **快照截断。** 只判定表里出现过的提交；新 clone 里快照之后的提交一律忽略。
    表里有、本地却找不到的提交保留原值，并计入 `missing_in_repo`。
### 只读必要的文件快照

逐提交读两侧完整文件太贵（上百万提交 × 每提交若干 .java）。一个文件快照要含 PT，
它的内容必然曾经以 `+` 行进入过某个路径。因此按拓扑序（父先于子）流式读 diff，
维护「曾出现过 ParameterizedTest 的路径」集合（含重命名传递），只对这些路径、
或本次 diff 本身提到 ParameterizedTest 的文件读快照。这只是性能上的过滤：
`--fullscan` 关掉它、对每个改动文件都读快照，并逐提交比对两者结果（应 0 差异）。

### 旧 Layer 1 命中而新判定未命中：逐个归因

对每个已发表 `junit5_hunk` 而 `l1m_pt == 0` 的提交，用与第一阶段相同的命令
（`git diff-tree -p -U3`）重放旧判定，找到触发它的那一行，再看那一行落在哪：

  - `rename`              该文件在 -M 下是重命名；旧口径（无重命名识别）把整文件当新增
  - `pt_mention_not_method` 触发它的 `@ParameterizedTest` 文本不在任何 PT 方法里（注释、字符串等）
  - `overrun_prev`        前一行规则：注解前一行有改动，但那行不属于 PT 方法
  - `overrun_forward`     前向扫描越过了 PT 方法末尾
  - `parse_error`         相关快照解析出错（该提交回退到旧判定，不算误差）
  - `not_reproduced`      重放旧判定得不到命中（diff 取不到等）
  - `unexplained`         触发行在 PT 区间内却未命中 —— **应为 0，否则是 bug**

### Layer 3 重跑

pickaxe 用与第一阶段完全相同的命令重跑（`git log --all -G ...`），但**不静默超时**：
上限 3 小时，每个 pattern 的耗时、返回码、是否完成都写进 summary。另外逐提交从
diff 直接判 `core_diff`（± 行匹配同样两个正则），两者逐提交对比。

用法：
    python pdar_v4_method_level.py <project> --repo <bare-or-normal clone> [--fullscan]
"""

# 向上找到 仓库根（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import Counter, OrderedDict
from typing import Dict, List, Optional, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pt_spans import EMPTY, FileSpans, J4_RE, compute_spans, lines_hit  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from paths import PDAR_RESULT, PDAR_V4_RESULT  # noqa: E402

PUBLISHED_DIR = PDAR_RESULT          # 第一阶段的逐提交表（pdar_v4_commit_table.py 的输出）
OUT_DIR = PDAR_V4_RESULT

# JUNIT5_PT_PATTERN 与第一阶段相同（只用于重放 v3 的 L1）。
# JUNIT4_PT_PATTERN 定义在 pt_spans.J4_RE，比第一阶段的 `@RunWith\s*\(\s*Parameterized` 宽：
# 第一阶段漏掉了 `@RunWith(value = Parameterized.class)` 与全限定名写法
# （Commons-OGNL / Commons-RNG / Cayenne / Commons-Digester 全用前者）。
JUNIT5_PT_PATTERN = re.compile(rb'@ParameterizedTest')
JUNIT4_PT_PATTERN = J4_RE
PICKAXE_PATTERNS = ['@ParameterizedTest', 'RunWith.*Parameterized']
PICKAXE_RE = [re.compile(rb'@ParameterizedTest'), re.compile(rb'RunWith.*Parameterized')]
PT_TOKEN = b'ParameterizedTest'
PCLASS_TOKEN = b'@ParameterizedClass'
J4_TOKEN = b'Parameterized'
NULL_SHA = '0' * 40
PICKAXE_TIMEOUT = 3 * 3600

GIT = ['git', '-c', 'core.quotepath=false', '-c', 'log.showRoot=true',
       '-c', 'diff.noprefix=false', '-c', 'color.ui=never']

HUNK_RE = re.compile(rb'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


# ============== git 访问 ==============

def git_out(repo: str, args: List[str], timeout: Optional[int] = None) -> Tuple[int, bytes, bytes]:
    p = subprocess.run(GIT + args, cwd=repo, capture_output=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


class BlobReader:
    """常驻的 `git cat-file --batch`；按对象名（sha 或 rev:path）取内容。"""

    def __init__(self, repo: str):
        self.p = subprocess.Popen(GIT + ['cat-file', '--batch'], cwd=repo,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def get(self, name: str) -> Optional[bytes]:
        self.p.stdin.write(name.encode('utf-8') + b'\n')
        self.p.stdin.flush()
        header = self.p.stdout.readline()
        if header.endswith(b' missing\n') or header.endswith(b' ambiguous\n') or not header:
            return None
        size = int(header.split()[2])
        data = self.p.stdout.read(size)
        self.p.stdout.read(1)
        return data

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=30)
        except Exception:
            self.p.kill()


class SpanCache:
    """blob sha → (FileSpans, 是否 JUnit 4 参数化类)。同一个 blob 版本会被很多提交两侧重复引用。"""

    def __init__(self, reader: BlobReader, cap: int = 300_000):
        self.reader, self.cap = reader, cap
        self.d: 'OrderedDict[str, Tuple[FileSpans, bool]]' = OrderedDict()
        self.blobs_read = 0
        self.blobs_parsed = 0
        self.parse_error_blobs = 0
        self.xrefs = 0
        self.j4_fallback_blobs = 0

    def _load(self, sha: str) -> Tuple[FileSpans, bool]:
        if sha == NULL_SHA:
            return EMPTY, False
        v = self.d.get(sha)
        if v is not None:
            self.d.move_to_end(sha)
            return v
        data = self.reader.get(sha)
        self.blobs_read += 1
        if data is None:
            v = (EMPTY, False)
        else:
            spans = compute_spans(data)
            if spans is not EMPTY:
                self.blobs_parsed += 1
                self.parse_error_blobs += spans.has_error
                self.j4_fallback_blobs += spans.j4_fallback
                self.xrefs += spans.xrefs
            v = (spans, bool(JUNIT4_PT_PATTERN.search(data)))
        self.d[sha] = v
        if len(self.d) > self.cap:
            self.d.popitem(last=False)
        return v

    def get(self, sha: str) -> FileSpans:
        return self._load(sha)[0]

    def j4(self, sha: str) -> bool:
        return self._load(sha)[1]


# ============== diff 流解析 ==============

class FilePatch:
    __slots__ = ('old_path', 'new_path', 'old_sha', 'new_sha', 'rename',
                 'old_lines', 'new_lines', 'mentions_pt', 'mentions_j4', 'core', 'pclass')

    def __init__(self):
        self.old_path = self.new_path = None
        self.old_sha = self.new_sha = NULL_SHA
        self.rename = False
        self.old_lines: List[int] = []
        self.new_lines: List[int] = []
        self.mentions_pt = False      # ± 行里出现 ParameterizedTest
        self.core = False             # ± 行匹配 pickaxe 的任一正则
        self.pclass = False
        self.mentions_j4 = False      # ± 行里出现 Parameterized（JUnit 4 候选路径用）


def _unquote(p: bytes) -> str:
    s = p.decode('utf-8', errors='surrogateescape')
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1].encode('latin-1', errors='backslashreplace').decode('unicode_escape')
        s = s.encode('latin-1', errors='ignore').decode('utf-8', errors='replace')
    return s


def iter_commits(stream):
    """解析 `git log -p -U0 --full-index --format=%x00%H %P` 的输出。

    逐行状态机；hunk 体按 hunk 头里的行数精确消费，所以内容行以 `---`/`+++`/`diff `
    开头也不会被误认作头部。产出 (hash, parents, [FilePatch])。
    """
    commit = None
    parents: List[str] = []
    files: List[FilePatch] = []
    fp: Optional[FilePatch] = None
    old_left = new_left = 0
    old_ln = new_ln = 0

    for line in stream:
        if old_left or new_left:
            if line.startswith(b'-'):
                fp.old_lines.append(old_ln); old_ln += 1; old_left -= 1
                body = line[1:]
            elif line.startswith(b'+'):
                fp.new_lines.append(new_ln); new_ln += 1; new_left -= 1
                body = line[1:]
            elif line.startswith(b'\\'):
                continue
            else:       # -U0 下不应出现上下文行；防御性地当作两侧各一行
                old_ln += 1; new_ln += 1
                old_left = max(old_left - 1, 0); new_left = max(new_left - 1, 0)
                continue
            if PT_TOKEN in body:
                fp.mentions_pt = True
            if J4_TOKEN in body:
                fp.mentions_j4 = True
            if PCLASS_TOKEN in body:
                fp.pclass = True
            if not fp.core and (PICKAXE_RE[0].search(body) or PICKAXE_RE[1].search(body)):
                fp.core = True
            continue
        if line.startswith(b'\\'):
            continue

        if line.startswith(b'\x00'):
            if commit is not None:
                yield commit, parents, files
            parts = line[1:].split()
            commit = parts[0].decode()
            parents = [x.decode() for x in parts[1:]]
            files, fp = [], None
        elif line.startswith(b'diff --git '):
            fp = FilePatch()
            files.append(fp)
        elif fp is None:
            continue
        elif line.startswith(b'@@'):
            m = HUNK_RE.match(line)
            if m:
                old_ln = int(m.group(1)); old_left = int(m.group(2) or 1)
                new_ln = int(m.group(3)); new_left = int(m.group(4) or 1)
                # 计数为 0 时起始行号指向「插入点之前」那一行，不属于任何改动行
        elif line.startswith(b'index '):
            rng = line.split()[1].split(b'..')
            if len(rng) == 2:
                fp.old_sha, fp.new_sha = rng[0].decode(), rng[1].decode()
        elif line.startswith(b'--- '):
            # 路径含空格时 git 会在行尾补一个 TAB
            p = line[4:].rstrip(b'\r\n').rstrip(b'\t')
            fp.old_path = None if p == b'/dev/null' else _unquote(p)[2:]
        elif line.startswith(b'+++ '):
            p = line[4:].rstrip(b'\r\n').rstrip(b'\t')
            fp.new_path = None if p == b'/dev/null' else _unquote(p)[2:]
        elif line.startswith(b'rename from '):
            fp.rename = True
            fp.old_path = _unquote(line[12:].rstrip(b'\r\n'))
        elif line.startswith(b'rename to '):
            fp.rename = True
            fp.new_path = _unquote(line[10:].rstrip(b'\r\n'))
    if commit is not None:
        yield commit, parents, files


# ============== 判定 ==============

def judge(files: List[FilePatch], cache: SpanCache, cand: Optional[Set[str]],
          cand4: Optional[Set[str]] = None):
    """返回 (l1m_pt, l1m_prov, parse_err, l2)。cand=None 表示不过滤（fullscan）。

    L2（JUnit 4，类级，两侧）：`-` 行落在父提交版本、或 `+` 行落在本提交版本里某个
    `@RunWith(...Parameterized...)` 类的区间内即命中（区间定义见 pt_spans._j4_regions）。
    纯重命名 / 只改权限位（无改动行）不算；只改 import / package 也不算 —— 与 L1 一致。
    """
    hit_pt = hit_prov = perr = l2 = False
    for fp in files:
        if not fp.old_lines and not fp.new_lines:
            continue
        if not l2 and (cand is None or fp.mentions_j4 or fp.old_path in cand4 or fp.new_path in cand4):
            o4 = cache.get(fp.old_sha) if fp.old_lines else EMPTY
            n4 = cache.get(fp.new_sha) if fp.new_lines else EMPTY
            if lines_hit(fp.old_lines, o4.j4) or lines_hit(fp.new_lines, n4.j4):
                l2 = True
        if cand is not None and not (fp.mentions_pt or fp.old_path in cand or fp.new_path in cand):
            continue
        o = cache.get(fp.old_sha) if fp.old_lines else EMPTY
        n = cache.get(fp.new_sha) if fp.new_lines else EMPTY
        perr |= (o.has_error and o.n_pt_methods > 0) or (n.has_error and n.n_pt_methods > 0)
        if not hit_pt and (lines_hit(fp.old_lines, o.pt) or lines_hit(fp.new_lines, n.pt)):
            hit_pt = True
        if not hit_prov and (lines_hit(fp.old_lines, o.prov) or lines_hit(fp.new_lines, n.prov)):
            hit_prov = True
    return hit_pt, hit_prov, perr, l2


def update_candidates(files: List[FilePatch], cand: Set[str], cand4: Set[str]):
    for fp in files:
        if fp.mentions_pt and fp.new_path:
            cand.add(fp.new_path)
        if fp.mentions_j4 and fp.new_path:
            cand4.add(fp.new_path)
        if fp.rename and fp.new_path:
            if fp.old_path in cand:
                cand.add(fp.new_path)
            if fp.old_path in cand4:
                cand4.add(fp.new_path)


# ============== 旧 Layer 1 的重放与归因 ==============

def old_l1_trigger(diff: bytes):
    """逐字复刻 pdar_v4_commit_table.check_junit5_in_diff，额外返回触发信息。

    返回 None（未命中）或 dict(kind, side, ln, blob, pt_side, pt_ln, pt_blob, path)。
    """
    lines = diff.split(b'\n')
    # 先给每一行标注 (side, 行号, blob, path)
    info = [None] * len(lines)
    old_sha = new_sha = NULL_SHA
    path = None
    o = n = 0
    in_hunk = False
    for i, ln in enumerate(lines):
        if ln.startswith(b'diff --git'):
            in_hunk = False
            old_sha = new_sha = NULL_SHA
            m = re.search(rb' b/(.+)$', ln)
            path = m.group(1).decode('utf-8', errors='replace') if m else None
            continue
        if ln.startswith(b'index '):
            rng = ln.split()[1].split(b'..')
            if len(rng) == 2:
                old_sha, new_sha = rng[0].decode(), rng[1].decode()
            continue
        m = HUNK_RE.match(ln)
        if m:
            o, n = int(m.group(1)), int(m.group(3))
            in_hunk = True
            continue
        if not in_hunk or ln.startswith(b'\\'):
            continue
        if ln.startswith(b'-') and not ln.startswith(b'---'):
            info[i] = ('old', o, old_sha, path); o += 1
        elif ln.startswith(b'+') and not ln.startswith(b'+++'):
            info[i] = ('new', n, new_sha, path); n += 1
        else:
            info[i] = ('new', n, new_sha, path); o += 1; n += 1   # 上下文行：两侧都有，取新侧

    def is_mod(s: bytes) -> bool:
        return (s.startswith(b'+') and not s.startswith(b'+++')) or \
               (s.startswith(b'-') and not s.startswith(b'---'))

    for i, line in enumerate(lines):
        if line.startswith(b'+++') or line.startswith(b'---'):
            continue
        if JUNIT5_PT_PATTERN.search(line):
            if i > 0:
                prev = lines[i - 1]
                if not prev.startswith(b'+++') and not prev.startswith(b'---'):
                    if prev.startswith(b'+') or prev.startswith(b'-'):
                        return dict(kind='prev', at=info[i - 1], pt=info[i])
            for j in range(i + 1, len(lines)):
                nl = lines[j]
                content = nl[1:] if nl.startswith((b'+', b'-')) and not nl.startswith((b'+++', b'---')) else nl
                if nl.startswith(b'@@') or nl.startswith(b'diff --git'):
                    break
                if re.search(rb'^\s*@(Test|ParameterizedTest)\b', content):
                    break
                if is_mod(nl):
                    return dict(kind='forward', at=info[j], pt=info[i])
    return None


def attribute(repo: str, cache: SpanCache, commit: str, renamed_paths: Set[str], perr: bool) -> str:
    rc, diff, _ = git_out(repo, ['diff-tree', '-p', '-U3', '--full-index', commit])
    trig = old_l1_trigger(diff) if rc == 0 else None
    if trig is None or trig['at'] is None or trig['pt'] is None:
        return 'not_reproduced'
    at_side, at_ln, at_blob, at_path = trig['at']
    pt_side, pt_ln, pt_blob, pt_path = trig['pt']
    # 旧判定不分文件类型；论文的 PT 计数（JavaParser）只认 .java，Kotlin/Scala/Groovy 里的
    # @ParameterizedTest 不算 PT。触发行或注解所在文件不是 .java 的，单独归类。
    if not (at_path or '').endswith('.java') or not (pt_path or '').endswith('.java'):
        return 'non_java_file'
    if at_path in renamed_paths:
        return 'rename'
    if perr:
        return 'parse_error'
    pt_spans = cache.get(pt_blob).pt
    if not lines_hit([pt_ln], pt_spans):
        return 'pt_mention_not_method'
    if not lines_hit([at_ln], cache.get(at_blob).pt):
        return 'overrun_prev' if trig['kind'] == 'prev' else 'overrun_forward'
    return 'unexplained'


# ============== pickaxe ==============

def run_pickaxe(repo: str, result: dict):
    commits: Set[str] = set()
    status = []
    for pat in PICKAXE_PATTERNS:
        t0 = time.time()
        try:
            p = subprocess.run(['git', 'log', '--all', '-G', pat, '--format=%H'],
                               cwd=repo, capture_output=True, timeout=PICKAXE_TIMEOUT)
            ok = p.returncode == 0
            if ok:
                commits.update(x.decode() for x in p.stdout.split() if x)
            status.append(dict(pattern=pat, rc=p.returncode, completed=ok,
                               seconds=round(time.time() - t0, 1)))
        except subprocess.TimeoutExpired:
            status.append(dict(pattern=pat, rc=None, completed=False,
                               seconds=round(time.time() - t0, 1), timeout=True))
    result['commits'] = commits
    result['status'] = status


# ============== 主流程 ==============

def load_published(project: str) -> Dict[str, dict]:
    path = os.path.join(PUBLISHED_DIR, f'{project}_commits.csv')
    with open(path, newline='', encoding='utf-8') as f:
        return {r['commit_hash']: r for r in csv.DictReader(f)}


def analyze(project: str, repo: str, fullscan: bool = False, out_dir: str = OUT_DIR,
            published: Optional[Dict[str, dict]] = None, run_pickaxe_layer: bool = True) -> dict:
    t_start = time.time()
    if os.path.exists(os.path.join(repo, 'shallow')) or os.path.exists(os.path.join(repo, '.git', 'shallow')):
        raise SystemExit(f'{repo} 是浅克隆，不能用于 PDAR')
    table = published if published is not None else load_published(project)

    pick: dict = {}
    pick_thread = None
    if run_pickaxe_layer:
        pick_thread = threading.Thread(target=run_pickaxe, args=(repo, pick), daemon=True)
        pick_thread.start()

    rc, out, err = git_out(repo, ['rev-list', '--all', '--parents'])
    if rc != 0:
        raise SystemExit(f'rev-list 失败: {err.decode(errors="replace")[:300]}')
    nparents = {}
    for line in out.split(b'\n'):
        if line:
            parts = line.split()
            nparents[parts[0].decode()] = len(parts) - 1
    found = [h for h in table if h in nparents]

    reader = BlobReader(repo)
    cache = SpanCache(reader)
    cand: Set[str] = set()
    cand4: Set[str] = set()
    res: Dict[str, dict] = {}
    renamed: Dict[str, Set[str]] = {}
    stats = Counter()

    # --full-history 必须加：带路径过滤时 git log 默认做历史简化，merge 若与某个父提交在
    # 这些路径上相同，就只沿那一侧走，另一侧分支上的提交会被整个跳过（Commons-IO 实测漏 3 个）。
    cmd = GIT + ['log', '--all', '--full-history', '--reverse', '--topo-order', '-p', '-U0', '-M',
                 '--full-index', '--no-ext-diff', '--no-textconv',
                 '--src-prefix=a/', '--dst-prefix=b/', '--format=%x00%H %P', '--', '*.java']
    proc = subprocess.Popen(cmd, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            bufsize=1 << 20)
    stderr_buf = []
    threading.Thread(target=lambda: stderr_buf.append(proc.stderr.read()), daemon=True).start()

    for commit, parents, files in iter_commits(proc.stdout):
        stats['stream_commits'] += 1
        if commit in table and len(parents) == 1:
            stats['judged'] += 1
            hit_pt, hit_prov, perr, l2 = judge(files, cache, cand, cand4)
            core = any(fp.core for fp in files)
            r = dict(l1m_pt=int(hit_pt), l1m_prov=int(hit_prov), parse_err=int(perr), l2=int(l2),
                     core_diff=int(core), pclass=int(any(fp.pclass for fp in files)))
            if fullscan:
                f_pt, f_prov, _, f_l2 = judge(files, cache, None)
                if (f_pt, f_prov, f_l2) != (hit_pt, hit_prov, l2):
                    stats['fullscan_mismatch'] += 1
                    r['fullscan_mismatch'] = 1
            rn = {fp.new_path for fp in files if fp.rename} | {fp.old_path for fp in files if fp.rename}
            if rn:
                renamed[commit] = rn
            res[commit] = r
        update_candidates(files, cand, cand4)
    proc.stdout.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit(f'git log 失败 rc={proc.returncode}: '
                         f'{(stderr_buf[0] if stderr_buf else b"").decode(errors="replace")[:300]}')

    # 已发表 L2 命中的提交一定改过 .java，必须出现在流里（应为 0）。
    # 已发表 L1 命中却不在流里的非 merge 提交，只改了非 .java 文件（Kotlin/Scala 测试里的
    # @ParameterizedTest）：按「只算 Java」的口径，新 L1 与 L2 都为 0，作为判定过的提交写出。
    not_in_stream: List[str] = []
    for h, row in table.items():
        if h not in nparents or h in res:
            continue
        if row['detection_layer'] == 'junit4_file':
            stats['published_hit_not_in_stream'] += 1
            not_in_stream.append(h)
        elif row['detection_layer'] == 'junit5_hunk' and nparents[h] == 1:
            stats['nonjava_only_old_l1'] += 1
            res[h] = dict(l1m_pt=0, l1m_prov=0, parse_err=0, core_diff=0, pclass=0,
                          l2=0, attr='non_java_file')

    # 旧 L1 归因
    attr = Counter()
    if stats['nonjava_only_old_l1']:
        attr['non_java_file'] += stats['nonjava_only_old_l1']
    for h, row in table.items():
        if row['detection_layer'] != 'junit5_hunk' or h not in res or 'attr' in res[h]:
            continue
        r = res[h]
        if not r['l1m_pt']:
            a = attribute(repo, cache, h, renamed.get(h, set()), bool(r['parse_err']))
            r['attr'] = a
            attr[a] += 1

    reader.close()

    if pick_thread is not None:
        pick_thread.join()
        pk = pick.get('commits', set())
        for h, r in res.items():
            r['pickaxe_new'] = int(h in pk)
        stats['pickaxe_commits'] = len(pk & set(table))
        # pickaxe 不限文件类型：只改了非 .java 文件（CI 脚本、文档里写着 @ParameterizedTest）
        # 的提交会被它命中，却不在 *.java 的 diff 流里。这类差异是 pickaxe 的误报，单独计数。
        stats['pickaxe_not_judged'] = len((pk & set(table)) - set(res))
        stats['core_pickaxe_disagree'] = sum(1 for r in res.values() if r['core_diff'] != r['pickaxe_new'])

    # 写结果（稀疏）：被判定过、且新标记非零 / 已发表 junit5_hunk / 已发表 is_core 的提交。
    # 没写出的提交在所有口径下都取已发表原值 —— 对被判定过的提交这与新判定一致
    # （新标记全 0、已发表 L1 与 L3 也是 0），对未判定的（merge / 根 / 本地缺失）就是保留原值。
    os.makedirs(out_dir, exist_ok=True)
    cols = ['commit_hash', 'l1m_pt', 'l1m_prov', 'l2', 'parse_err', 'core_diff',
            'pickaxe_new', 'pclass', 'attr', 'fullscan_mismatch']
    with open(os.path.join(out_dir, f'{project}_method_commits.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for h, r in res.items():
            pub = table[h]
            if any(r.get(k) for k in cols[1:]) or pub['modifiedPT'] == '1' or pub['is_core'] == '1':
                w.writerow({'commit_hash': h, **{k: r.get(k, '') for k in cols[1:]}})

    summary = dict(
        project=project,
        table_commits=len(table),
        found_in_repo=len(found),
        missing_in_repo=len(table) - len(found),
        found_ratio=round(len(found) / len(table), 4) if table else None,
        judged=stats['judged'],
        stream_commits=stats['stream_commits'],
        published_hit_not_in_stream=stats['published_hit_not_in_stream'],
        published_hit_not_in_stream_sample=not_in_stream[:20],
        nonjava_only_old_l1=stats['nonjava_only_old_l1'],
        blobs_read=cache.blobs_read,
        blobs_with_pt=cache.blobs_parsed,
        parse_error_blobs=cache.parse_error_blobs,
        j4_fallback_blobs=cache.j4_fallback_blobs,
        xrefs=cache.xrefs,
        commits_l1m_pt=sum(r['l1m_pt'] for r in res.values()),
        commits_l1m_prov=sum(r['l1m_prov'] for r in res.values()),
        commits_l2=sum(r.get('l2', 0) for r in res.values()),
        old_l2_hits=sum(1 for row in table.values() if row['detection_layer'] == 'junit4_file'),
        commits_parse_err=sum(r['parse_err'] for r in res.values()),
        commits_core_diff=sum(r['core_diff'] for r in res.values()),
        commits_pclass=sum(r['pclass'] for r in res.values()),
        old_l1_hits=sum(1 for row in table.values() if row['detection_layer'] == 'junit5_hunk'),
        attribution=dict(attr),
        fullscan=fullscan,
        fullscan_mismatch=stats['fullscan_mismatch'],
        pickaxe=pick.get('status'),
        pickaxe_commits=stats.get('pickaxe_commits'),
        pickaxe_not_judged=stats.get('pickaxe_not_judged'),
        core_pickaxe_disagree=stats.get('core_pickaxe_disagree'),
        seconds=round(time.time() - t_start, 1),
    )
    with open(os.path.join(out_dir, f'{project}_method_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--fullscan', action='store_true', help='不做路径过滤，逐提交比对过滤前后结果')
    ap.add_argument('--no-pickaxe', action='store_true')
    ap.add_argument('--out', default=OUT_DIR)
    a = ap.parse_args()
    s = analyze(a.project, a.repo, fullscan=a.fullscan, out_dir=a.out,
                run_pickaxe_layer=not a.no_pickaxe)
    print(json.dumps(s, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
