#!/usr/bin/env python3
"""从 ssk 快照构建 RQ1 的项目级底表 merged_data_219_ssk.csv（219 行，筛选在分析时由 rq1_bins 做）。

输入：
  project_metadata.csv（同目录）   项目清单与不随快照变化的元数据：首次提交时间、ASF category。
                                   ssk_key 列为空时按 project_name_map.json 找 parser 输出；
                                   Commons-HttpClient 与 HttpComponents-Client 是同一仓库，没有单独的 clone，
                                   指向后者（它在分析时作为重复项排除，见 rq1_bins.DATA_INTEGRITY_EXCL）。
  PT_PARSER_SSK                    轻量 parser 的逐项目 JSON
  PT_SSD/apache-projects           源码快照（files_java 与 date）

各列的来源：
  total_tests, pt_total, junit4_pt, junit5_pt, pt_share,
  junit4_total, junit5_total, junit4_param_share, junit5_param_share
      parser 输出，计算逻辑在 pt_summary.py
  files_java
      快照 HEAD 上 `git ls-tree -r --name-only HEAD | grep -F '.java' | wc -l`；Size 分组用它
  files_java_suffix
      同一棵树上严格以 .java 结尾的文件数（仅供核对，分组不用它）
  date
      快照里该项目 HEAD 的提交时间
  first_commit_iso, first_commit, age, categories
      取自 project_metadata.csv；age = 2026 − 首次提交年份
"""

# 向上找到 仓库根（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _paths.RQ1_RESULTS
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import csv
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from paths import FINAL, PARSER_SSK, APACHE_PROJECTS, require   # noqa: E402

META = os.path.join(HERE, 'project_metadata.csv')
OUT = os.path.join(RESULTS_DIR, 'merged_data_219_ssk.csv')
NAME_MAP = os.path.join(FINAL, 'project_name_map.json')
YEAR_NOW = 2026

FIELDS = ['project', 'date', 'total_tests', 'pt_total', 'junit4_pt', 'junit5_pt', 'pt_share',
          'junit4_total', 'junit5_total', 'junit4_param_share', 'junit5_param_share', 'files_java',
          'first_commit_iso', 'uses_pt', 'categories', 'first_commit', 'age', 'files_java_suffix']


def load_pt_summary():
    import importlib.util
    spec = importlib.util.spec_from_file_location('pt_summary', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pt_summary.py'))
    m = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ['pt_summary']
    spec.loader.exec_module(m)
    sys.argv = argv
    return m


def ssk_key(project, inv):
    for k in (inv.get(project), project.lower(), project):
        if k and os.path.exists(os.path.join(PARSER_SSK, f'{k}_output.json')):
            return k
    return None


def snapshot_date(key):
    """ssk 快照里该项目 HEAD 的提交时间 —— 作为 date 列，使底表可重复生成（不随运行时刻变）。"""
    out = subprocess.run(['git', '-C', os.path.join(APACHE_PROJECTS, key), 'log', '-1', '--format=%cI'],
                         capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ''


def files_java(key):
    """返回 (子串计数, 严格后缀计数)。子串计数即原定义（与 trigger.sh 相同），Size 分组用它；
    严格后缀计数单独存为 files_java_suffix 列，供核对两种口径的差别。"""
    repo = os.path.join(APACHE_PROJECTS, key)
    if not os.path.isdir(repo):
        return None, None
    out = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', 'HEAD'],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None, None
    lines = out.stdout.splitlines()
    return sum('.java' in x for x in lines), sum(x.endswith('.java') for x in lines)


def main():
    require(PARSER_SSK, 'ssk 的 parser 输出')
    require(APACHE_PROJECTS, 'ssk 的源码快照（用于 files_java）')
    ps = load_pt_summary()
    inv = {v: k for k, v in json.load(open(NAME_MAP)).items()}

    meta = list(csv.DictReader(open(META, newline='', encoding='utf-8')))

    rows, problems = [], []
    for m in meta:
        project, first_iso, cats = m['project'], m['first_commit_iso'], m['categories']
        key = m['ssk_key'] or ssk_key(project, inv)
        if not key:
            raise SystemExit(f'{project}: 找不到 parser 输出（{PARSER_SSK}）')
        recs = ps.load_json_records(os.path.join(PARSER_SSK, f'{key}_output.json'))[0]
        total, pt, j4pt, j5pt, share = ps.compute_stats(recs)
        j4t, j5t, j4s, j5s = ps.compute_flavor_breakdown(recs)
        fj, fj_suffix = files_java(key)
        if fj is None:
            problems.append(f'{project}: 没有可读的源码快照，files_java 留空')
            fj = ''
        year = int(first_iso[:4]) if first_iso else ''
        rows.append({
            'project': project, 'date': snapshot_date(key),
            'total_tests': total, 'pt_total': pt, 'junit4_pt': j4pt, 'junit5_pt': j5pt, 'pt_share': share,
            'junit4_total': j4t, 'junit5_total': j5t,
            'junit4_param_share': j4s, 'junit5_param_share': j5s,
            'files_java': float(fj) if fj != '' else '',
            'files_java_suffix': fj_suffix if fj_suffix is not None else '',
            'first_commit_iso': first_iso, 'uses_pt': int(pt > 0), 'categories': cats,
            'first_commit': year, 'age': (YEAR_NOW - year) if year != '' else '',
        })

    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {os.path.relpath(OUT, FINAL)}: {len(rows)} 行')
    for p in problems:
        print('  ⚠️ ', p)


if __name__ == '__main__':
    main()
