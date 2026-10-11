#!/usr/bin/env python3
"""Backwards-compatible alias for the shared statistics module.

The implementation now lives in ../pt_stats.py so that RQ3.2, RQ3.3 and the
EnumSource analysis cannot drift apart. Validated against scipy/statsmodels.
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _os_root.path.join(_paths.RQ3_2_RESULTS, 'methodsource')
_os_root.makedirs(RESULTS_DIR, exist_ok=True)

# pt_stats 位于 rq3_2/ 根目录，四个子分析共用
import sys as _s2, os as _o2
_s2.path.insert(0, _o2.path.dirname(_o2.path.dirname(_o2.path.abspath(__file__))))
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pt_stats import (  # noqa: F401
    mann_whitney_u, cliffs_magnitude, kruskal_wallis, chi2_sf, gammq,
    holm_adjust, bh_adjust, quantile, describe, cohens_kappa,
)
