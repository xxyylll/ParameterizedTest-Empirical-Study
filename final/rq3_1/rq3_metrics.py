#!/usr/bin/env python3
"""RQ3.1 的指标清单与 Mann–Whitney U / Cliff's delta —— 共享定义的唯一来源。

这三个定义原先住在 `heatmap_unified_44projects.py`（旧的横向热图脚本，已被
`plot_rq3_heatmap_portrait.py` 取代）里。那个脚本的全部逻辑都在模块级，
没有 `__main__` 保护，所以**只是 import 它就会重新读 CSV 并重画一张图**；
`plot_rq3_forest.py` 和 `plot_rq3_heatmap_portrait.py` 都只需要这三个符号，
却因此被迫依赖一个大 CSV 的存在。这里把它们抽出来，去掉那条副作用。

`mann_whitney_u` 与原实现逐字一致（含连续性校正与 tie 校正），故两套脚本的
数值与此前的产物完全可比。`rq3_bh_correction.py` 当时为了绕开上述副作用
内联了同一份实现，现已统一从本模块导入。
"""
import math

METRICS = ['self_loc', 'self_cc', 'self_cctr', 'self_dupPerc',
           'helper_loc_sum', 'helper_cc_sum', 'helper_cctr_sum', 'helper_dupPerc',
           'total_loc', 'total_cc', 'total_cctr', 'total_dupPerc']
METRIC_LABELS = ['LOC (test)', 'CC (test)', 'CCTR (test)', 'DUP% (test)',
                 'LOC (helpers)', 'CC (helpers)', 'CCTR (helpers)', 'DUP% (helpers)',
                 'LOC (total)', 'CC (total)', 'CCTR (total)', 'DUP% (total)']


def mann_whitney_u(group1, group2):
    """返回 (cliffs_delta, p)。正的 delta = group1 更大。

    双侧正态近似，带连续性校正；sigma 用并列校正项。
    delta 由 U 直接换算：delta = 2U/(n1*n2) - 1。
    """
    n1, n2 = len(group1), len(group2)
    N = n1 + n2
    combined = [(x, 1) for x in group1] + [(x, 2) for x in group2]
    combined.sort(key=lambda t: t[0])
    ranks = [0.0] * N
    i = 0
    tie_term_sum = 0
    while i < N:
        j = i
        while j + 1 < N and combined[j + 1][0] == combined[i][0]:
            j += 1
        tie_size = j - i + 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        if tie_size > 1:
            tie_term_sum += tie_size ** 3 - tie_size
        i = j + 1
    R1 = sum(r for r, (val, grp) in zip(ranks, combined) if grp == 1)
    U1 = R1 - n1 * (n1 + 1) / 2.0
    mean_U = n1 * n2 / 2.0
    sigma_U = math.sqrt((n1 * n2 / 12.0) * ((N + 1) - tie_term_sum / (N * (N - 1))))
    if sigma_U == 0:
        z = 0.0
    else:
        z = (U1 - 0.5 - mean_U) / sigma_U if U1 > mean_U else ((U1 + 0.5 - mean_U) / sigma_U if U1 < mean_U else 0.0)
    p = max(0.0, min(1.0, 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))))
    cliffs_delta = (2 * U1) / (n1 * n2) - 1
    return cliffs_delta, p
