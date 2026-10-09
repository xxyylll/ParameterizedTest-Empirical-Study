#!/usr/bin/env python3
"""PDAR 对 git diff 上下文行数（-U）的敏感性。

### 要回答的问题

Layer 1 是在 diff **文本**上做的：它定位 `@ParameterizedTest` 所在行，然后看
附近有没有 `+`/`-`。因此它能看到多少周围代码，完全由 git 的上下文行数决定。
`git diff-tree -p` 默认给 3 行（即论文口径），于是同一个 PT 方法内部的改动只要
离注解超过 3 行，就不与注解同处一个 hunk —— Layer 1 看不见它。

这不是个无关的细节：在全语料上把 Layer 1 整个拿掉，PDAR 中位数从 14.52% 掉到
10.56%（−3.96pp），对 JUnit5-only 的项目甚至掉三十多个百分点（Hudi、
Commons-Statistics、Commons-Numbers）—— 因为 Layer 2 只认 JUnit 4，帮不上忙。
Layer 1 是承重的，所以它的召回率值得实测。

### 影响方向并非单一

  (+) Layer 1 召回上升 —— 原先落在 hunk 外的改动现在看得见。
  (-) 分母也上升 —— `check_touched_test` 在 diff 的**所有行**（含上下文行）上找
      `@Test` / `import org.junit`，上下文越大越多提交被判为「碰过测试」。
  (?) 假阳性上升 —— Layer 1 的前向扫描只在 `@Test` / `@ParameterizedTest` /
      新 hunk 处停止。上下文调大后相邻 hunk 合并，扫描可能越过 PT 方法末尾进入
      下一个**无注解**的方法（helper、字段声明），把那里的 +/- 误记到 PT 上。

所以 PDAR 是升是降必须测，不能先验断定。

### 为什么不是把 find_pt_developers.py 跑几遍

三层里**只有 Layer 1 和 `check_touched_test` 依赖上下文**：

  - Layer 3（pickaxe）是整仓一次 `git log --all -G`，与上下文无关 ——
    而且在万级提交的仓库上它经常跑到超时（实测 Fineract 两个 pattern 各 600s
    全部 Timeout），重复跑它纯属浪费且不可靠。
  - Layer 2 用 `git show commit:file` 读**整个文件**，只依赖 diff 的文件名列表；
    文件名来自 `diff --git` 头，不随 -U 变化 —— 也与上下文无关。
    它恰好是最贵的一步（每个改动的 .java 一次 git show）。

这两层的结果**已经存在**于已发表的逐提交表 `{project}_commits.csv` 的
`detection_layer` 列里：`junit4_file` / `pickaxe` 即 Layer 2/3 命中。
于是本脚本直接复用它作基线，只重算 Layer 1 —— 省掉全部 git show 与 pickaxe，
并且基线天然与已发表数字同源。

### 两个必要的限定

  - **只取交集**。本机克隆与已发表那轮的快照日期不同（本机更早，命中
    Fineract 94.3% / Druid 87.1%），所以只在两边都有的提交上比较，
    保证各上下文面对的是同一批提交。基线 PDAR 由同一张表在同一交集上重算，
    因此可能与已发表的全量数字略有差异 —— 这是口径限定，不是不一致。
  - **跳过 merge 提交**。`git diff-tree -p` 对 merge 默认无输出（实测 Fineract
    前 213 个提交里 89 个为空），这在任何 -U 下都成立，所以它们保持基线取值。

### U3 不重算

已发表的逐提交表本身就是 U3 口径的结果：`touched_test` 与
`detection_layer == 'junit5_hunk'` 分别就是 U3 下的分母判定与 Layer 1 判定。
所以基线**直接取表里的值**，一次 git 调用都不用花 —— 每个非 merge 提交只需
算大上下文那一轮。这把 git 调用数从「上下文个数 × 提交数」降到「提交数」。

这个复用是经过验证的：在 Fineract 的 600 个非 merge 提交上重算 U3 的 Layer 1，
与表里的 `detection_layer` **不一致 0 个**（`--selfcheck N` 可随时复查 N 个提交）。
若自校验不为 0，说明本机克隆与已发表那轮不同源，后面的 ΔPDAR 不可用。

输出 pdar_context_sensitivity.csv。
"""
import argparse
import csv
import os
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from find_pt_developers import (                      # noqa: E402
    get_commit_diff, check_junit5_in_diff, check_touched_test, load_repo_mapping,
    is_git_dir, shallow_marker,
)

BASELINE = 3
L23 = {'junit4_file', 'pickaxe'}        # 与上下文无关的两层


def _rev(repo, *args):
    return subprocess.run(['git', '-C', repo, *args],
                          capture_output=True, text=True).stdout.split()


def merge_commits(repo):
    """一次 rev-list 取出所有 merge 提交（父提交 >1 个）。"""
    out = subprocess.run(['git', '-C', repo, 'rev-list', '--all', '--parents'],
                         capture_output=True, text=True).stdout
    return {p[0] for p in (l.split() for l in out.splitlines()) if len(p) > 2}


def expected_empty(repo):
    """`diff-tree -p` 本就不会有输出的提交，与 -U 无关，不应算作异常。

    两类（实测 Fineract 共 27 个，占非 merge 提交的 0.3%）：
      - **root 提交**：没有父提交，`diff-tree` 不加 `--root` 就没有输出（2 个）。
      - **git 自己认为没改动文件的提交**：只改文件权限、空提交之类（25 个）。

    这两类在论文那一轮里同样取不到 diff，所以基线把它们标成
    `touched_test=0, modifiedPT=0, detection_layer=''`（实测 25/25 全是）。
    各上下文对它们的处理一致，不构成污染 —— 真正需要告警的是**此外**的空 diff，
    那才意味着仓库损坏或 git 调用失败。
    """
    out = subprocess.run(['git', '-C', repo, 'rev-list', '--all', '--parents'],
                         capture_output=True, text=True).stdout
    roots = {p[0] for p in (l.split() for l in out.splitlines()) if len(p) == 1}
    nonmerge = set(_rev(repo, 'rev-list', '--all', '--no-merges'))
    changed = set(_rev(repo, 'log', '--all', '--no-merges', '--format=%H',
                       '--diff-filter=ACDMRTUXB'))
    return roots | (nonmerge - changed)


def selfcheck(repo, rows, merges, n):
    """验证本机重算的 U3 Layer 1 与已发表标签一致。

    **必须按正负例分别验。** 早先的版本只抽前 n 个提交数不一致个数 —— 这会**假通过**：
    `junit5_hunk` 在提交里极其稀疏（Fineract 10,064 个提交里只有 52 个），
    随机 300 个样本很可能一个正例都没有，此时即便所有 diff 都返回空
    （例如仓库对象损坏、git 报 rc=128），`check_junit5_in_diff('')` 一律为 False，
    与「绝大多数提交不是 junit5_hunk」完全吻合，不一致数就是 0。
    这正是一次真实踩过的坑：从 exFAT 外置盘做本地 clone 时，`._pack-*.idx`
    这类 AppleDouble 文件让 git 误用了错误的 pack 索引，产出缺对象的仓库，
    所有 diff 都 fatal，而旧自校验照样报 0。

    所以这里强制纳入正例，并分开报告；正例数为 0 直接视为无法验证。
    返回 (正例不一致数, 负例不一致数, 正例总数)。
    """
    nonmerge = [r for r in rows if r['commit_hash'] not in merges]
    pos = [r for r in nonmerge if r.get('detection_layer') == 'junit5_hunk']
    neg = [r for r in nonmerge if r.get('detection_layer') != 'junit5_hunk']
    pos, neg = pos[:max(1, n // 2)], neg[:n - min(len(pos), max(1, n // 2))]

    mism_pos = sum(1 for r in pos
                   if not check_junit5_in_diff(get_commit_diff(repo, r['commit_hash'], BASELINE)))
    mism_neg = sum(1 for r in neg
                   if check_junit5_in_diff(get_commit_diff(repo, r['commit_hash'], BASELINE)))
    print(f'  自校验（U3 复现已发表标签）：'
          f'正例 {len(pos)} 个，未复现 {mism_pos}；负例 {len(neg)} 个，误报 {mism_neg}', flush=True)
    if not pos:
        print('  ⚠️  样本里没有 junit5_hunk 正例 —— 无法验证，结果不可用', file=sys.stderr)
    return mism_pos, mism_neg, len(pos)


def analyse(project, repo, baseline_csv, contexts, n_selfcheck=0):
    rows = list(csv.DictReader(open(baseline_csv)))
    local = set(subprocess.run(['git', '-C', repo, 'rev-list', '--all'],
                               capture_output=True, text=True).stdout.split())
    merges = merge_commits(repo)
    exp_empty_pre = expected_empty(repo)
    rows = [r for r in rows if r['commit_hash'] in local]      # 只取交集
    n_merge = sum(1 for r in rows if r['commit_hash'] in merges)
    print(f'  交集 {len(rows)} 个提交（merge {n_merge} 个，diff 恒为空；'
          f'另有 {len(exp_empty_pre)} 个 root/无改动提交同样恒为空）', flush=True)

    if n_selfcheck:
        mp, mn, npos = selfcheck(repo, rows, merges, n_selfcheck)
        if npos == 0 or mp or mn:
            print(f'  ⚠️  {project} 自校验未通过（正例未复现 {mp}，负例误报 {mn}，'
                  f'正例数 {npos}）—— ΔPDAR 不可用', file=sys.stderr)

    extra = [c for c in contexts if c != BASELINE]
    exp_empty = exp_empty_pre                # 本就无输出的提交，不算异常
    empty_diffs = {c: 0 for c in extra}      # 此外的空 diff —— 真正的异常信号
    sets = {c: {'test': set(), 'pt': set(), 'core': set()} for c in contexts}
    flips = {c: {'gained': 0, 'lost': 0} for c in extra}
    l1_hits = {c: 0 for c in contexts}

    for i, r in enumerate(rows):
        if (i + 1) % 1000 == 0:
            print(f'    {i + 1}/{len(rows)}', flush=True)
        h = r['commit_hash']
        email = (r['author_email'] or '').strip().lower()
        if not email:
            continue
        layer = r.get('detection_layer', '')
        l23 = layer in L23                  # Layer 2/3：与上下文无关
        base_pt = r['modifiedPT'] == '1'
        base_test = r['touched_test'] == '1'
        base_core = r['is_core'] == '1'

        # —— 基线（U3）直接取表里的值 ——
        if base_test:
            sets[BASELINE]['test'].add(email)
        if base_pt:
            sets[BASELINE]['pt'].add(email)
            if base_core:
                sets[BASELINE]['core'].add(email)
        if layer == 'junit5_hunk':
            l1_hits[BASELINE] += 1

        if h in merges:
            # diff 在任何 -U 下都为空 → 各上下文沿用基线
            for c in extra:
                if base_test:
                    sets[c]['test'].add(email)
                if base_pt:
                    sets[c]['pt'].add(email)
                    if base_core:
                        sets[c]['core'].add(email)
            continue

        for c in extra:
            diff = get_commit_diff(repo, h, c)
            if not diff and h not in exp_empty:
                empty_diffs[c] += 1
            l1 = check_junit5_in_diff(diff)
            if l1:
                l1_hits[c] += 1
            if check_touched_test(diff):
                sets[c]['test'].add(email)
            pt = l1 or l23
            if pt:
                sets[c]['pt'].add(email)
                if base_core:
                    sets[c]['core'].add(email)
            if pt and not base_pt:
                flips[c]['gained'] += 1
            elif base_pt and not pt:
                flips[c]['lost'] += 1

    # 不变量：更大的上下文给出的 diff 是更小上下文的**超集**，所以
    # touched_test 与 Layer 1 命中都只能单调不减。违反它必定是取 diff 本身出了问题
    # （仓库损坏、git 超时、rc != 0 被静默吞成空串），而不是真实的敏感性效应。
    for c in extra:
        if len(sets[c]['test']) < len(sets[BASELINE]['test']) or l1_hits[c] < l1_hits[BASELINE]:
            print(f'  ⚠️  单调性被违反：-U{c} 的 touched_test 开发者 '
                  f'{len(sets[c]["test"])} < U{BASELINE} 的 {len(sets[BASELINE]["test"])}，'
                  f'或 L1 命中 {l1_hits[c]} < {l1_hits[BASELINE]}。'
                  f'几乎可以肯定是 diff 取不到（仓库损坏/超时），结果不可用。',
                  file=sys.stderr)

    out = []
    for c in contexts:
        s = sets[c]
        nd = len(s['test'])
        out.append({
            'project': project, 'context': c, 'n_commits_compared': len(rows),
            'n_merge_commits': n_merge,
            'pt_participants': len(s['pt']), 'core_developers': len(s['core']),
            'test_developers': nd,
            'pdar': round(len(s['pt']) / nd * 100, 2) if nd else 0.0,
            'core_pdar': round(len(s['core']) / nd * 100, 2) if nd else 0.0,
            'layer1_commits': l1_hits[c],
            'commits_gained_vs_U3': flips.get(c, {}).get('gained', 0),
            'commits_lost_vs_U3': flips.get(c, {}).get('lost', 0),
            'empty_diffs_nonmerge': empty_diffs.get(c, 0),
        })
    for c in extra:
        if empty_diffs[c]:
            print(f'  ⚠️  -U{c}：{empty_diffs[c]} 个非 merge 提交取不到 diff '
                  f'（应为 0）—— 检查仓库完整性与超时', file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser(description='PDAR 对 diff 上下文行数的敏感性')
    ap.add_argument('projects', nargs='+')
    ap.add_argument('--repo-root', required=True, help='全量克隆所在的父目录')
    ap.add_argument('--baseline-dir', required=True,
                    help='已发表的逐提交表目录（含 {project}_commits.csv）')
    ap.add_argument('--contexts', default='3,25')
    ap.add_argument('--selfcheck', type=int, default=300,
                    help='抽多少个提交复查 U3 复现；0 表示跳过')
    ap.add_argument('--out', default=os.path.join(HERE, 'pdar_context_sensitivity.csv'))
    args = ap.parse_args()

    contexts = sorted(int(x) for x in args.contexts.split(','))
    if BASELINE not in contexts:
        ap.error(f'--contexts 必须含基线 {BASELINE}（用于自校验与计算相对变化）')

    name_map = load_repo_mapping()
    all_rows = []
    for project in args.projects:
        entry = name_map.get(project)
        rd = entry['repo'] if entry else project.lower()
        repo = next((p for p in (os.path.join(args.repo_root, project),
                                 os.path.join(args.repo_root, project + '.git'),
                                 os.path.join(args.repo_root, rd),
                                 os.path.join(args.repo_root, rd + '.git'))
                     if is_git_dir(p)), None)
        base = os.path.join(args.baseline_dir, f'{project}_commits.csv')
        if not repo:
            print(f'[跳过] {project}: 找不到全量克隆', file=sys.stderr); continue
        if shallow_marker(repo):
            print(f'[跳过] {project}: 浅克隆', file=sys.stderr); continue
        if not os.path.exists(base):
            print(f'[跳过] {project}: 没有基线表 {base}', file=sys.stderr); continue
        print(f'\n=== {project}  ({repo}) ===', flush=True)
        all_rows += analyse(project, repo, base, contexts, args.selfcheck)

    if not all_rows:
        sys.exit('没有可分析的项目')
    with open(args.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader(); w.writerows(all_rows)
    print(f'\nwrote {args.out}')

    base = {r['project']: r['pdar'] for r in all_rows if r['context'] == BASELINE}
    print(f"\n{'project':14}{'-U':>4}{'L1命中':>8}{'PT':>5}{'TestDev':>8}"
          f"{'PDAR':>8}{'ΔPDAR':>8}{'+提交':>7}{'-提交':>7}")
    print('-' * 68)
    for r in all_rows:
        d = r['pdar'] - base.get(r['project'], 0)
        print(f"{r['project']:14}{r['context']:>4}{r['layer1_commits']:>8}"
              f"{r['pt_participants']:>5}{r['test_developers']:>8}{r['pdar']:>8.2f}"
              f"{('—' if r['context'] == BASELINE else f'{d:+.2f}'):>8}"
              f"{r['commits_gained_vs_U3']:>7}{r['commits_lost_vs_U3']:>7}")


if __name__ == '__main__':
    main()
