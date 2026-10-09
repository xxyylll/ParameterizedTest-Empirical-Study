#!/usr/bin/env python3
"""三层检测各自对 PDAR 贡献了多少 —— 全语料精确值，无需重跑 git。

每个提交在 `{project}_commits.csv` 里都带 `detection_layer`，所以「把某一层拿掉
会怎样」可以直接从已有数据算出来，不必重新遍历仓库。这给出的是**精确值**，
而不是抽样估计。

为什么要看这个：PDAR 的已知局限集中在 Layer 1 —— 它在 diff 文本上做判定，
能看到多少周围代码取决于 git 的上下文行数（默认 3 行）。要判断这个局限
值不值得花力气，先得知道 Layer 1 到底承了多少重。

口径说明：
  - 只统计 106 个采纳 PT 的项目（语料筛选复用 rq1_bins.load，与 RQ1 同源）。
  - 「拿掉某一层」= 该层命中的提交不再计入分子，分母（碰过测试的开发者）不变。
    这不等于重跑 —— 重跑时被拿掉的提交可能被其它层接住。但 detection_layer
    记录的是**首次命中的层**（判定顺序 1→2→3），所以「拿掉 Layer 1」在这里
    的含义是：原本靠 Layer 1 认出的提交，其作者若没有别的 PT 提交就不再计入。
    这正是我们想问的「Layer 1 独有的贡献」。

输出 pdar_layer_attribution.csv，并打印汇总。
"""
import argparse
import collections
import csv
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # rq1/，为了 rq1_bins
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

LAYERS = ['junit5_hunk', 'junit4_file', 'pickaxe']


def main():
    ap = argparse.ArgumentParser(description='三层检测对 PDAR 的贡献归属')
    ap.add_argument('--result-dir', default=None,
                    help='逐提交表所在目录；省略则用 paths.py 的 PDAR_RESULT')
    ap.add_argument('--out', default=os.path.join(HERE, 'pdar_layer_attribution.csv'))
    args = ap.parse_args()

    from paths import PDAR_RESULT, require
    import rq1_bins
    d = args.result_dir or PDAR_RESULT
    require(d, '层归属分析（逐提交表）')

    adopters = set(rq1_bins.load(adopters_only=True)['project'])
    commit_layers = collections.Counter()
    rows = []

    for fn in sorted(os.listdir(d)):
        if not fn.endswith('_commits.csv'):
            continue
        project = fn[:-len('_commits.csv')]
        if project not in adopters:
            continue

        test = set()
        pt = {None: set(), **{L: set() for L in LAYERS}}   # None = 保留全部层
        for r in csv.DictReader(open(os.path.join(d, fn))):
            email = (r['author_email'] or '').strip().lower()
            if not email:
                continue
            layer = r.get('detection_layer') or ''
            commit_layers[layer or 'none'] += 1
            if r['touched_test'] == '1':
                test.add(email)
            if r['modifiedPT'] == '1':
                pt[None].add(email)
                for L in LAYERS:
                    if layer != L:            # 「拿掉 L」：不计 L 命中的提交
                        pt[L].add(email)
        if not test:
            continue

        row = {'project': project, 'test_developers': len(test),
               'pdar': round(len(pt[None]) / len(test) * 100, 2)}
        for L in LAYERS:
            row[f'pdar_without_{L}'] = round(len(pt[L]) / len(test) * 100, 2)
            row[f'drop_{L}'] = round(row['pdar'] - row[f'pdar_without_{L}'], 2)
        rows.append(row)

    with open(args.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    tot = sum(commit_layers.values())
    print(f'=== 提交级的层归属（{len(rows)} 个采纳者，{tot:,} 个提交）===')
    for k, v in commit_layers.most_common():
        print(f'  {k:14}{v:>10,}  {v / tot * 100:6.2f}%')

    print(f'\n=== 逐层拿掉后的 PDAR ===')
    print(f"  {'':22}{'中位数':>9}{'Δ中位':>9}{'逐项目Δ中位':>13}{'最大Δ':>8}{'Δ=0 的项目':>12}")
    base = statistics.median(r['pdar'] for r in rows)
    print(f"  {'保留全部层':22}{base:>9.2f}")
    for L in LAYERS:
        med = statistics.median(r[f'pdar_without_{L}'] for r in rows)
        ds = [r[f'drop_{L}'] for r in rows]
        print(f"  {'拿掉 ' + L:22}{med:>9.2f}{med - base:>+9.2f}"
              f"{statistics.median(ds):>13.2f}{max(ds):>8.2f}"
              f"{sum(1 for x in ds if x == 0):>8}/{len(ds)}")

    print(f'\n=== Layer 1 贡献最大的 10 个项目 ===')
    for r in sorted(rows, key=lambda x: -x['drop_junit5_hunk'])[:10]:
        print(f"  {r['project']:24}{r['pdar']:>7.2f}% → {r['pdar_without_junit5_hunk']:>6.2f}%"
              f"   ({-r['drop_junit5_hunk']:+.2f})")
    print(f'\nwrote {args.out}')


if __name__ == '__main__':
    main()
