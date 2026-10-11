#!/usr/bin/env python3
"""从 ssk 快照重建 RQ1 的项目级底表：merged_data_219_ssk.csv（218 + Parquet）。

为什么要重建：
  旧底表 merged_data_218.csv 的计数来自 2025-10-15 跑的一批 parser 输出，那批输出后来被
  部分重跑覆盖，磁盘上已经不存在（parser_result/ 里 Accumulo 是 10-28、Hudi 是 12-04 的版本）。
  拿现存的两批去比，12 个项目里旧批只吻合 2 个、ssk 只吻合 3 个 —— 旧底表已无法复现。
  ssk 快照（SSD 上 apache-projects/，HEAD 在 2025-10-16 ~ 10-21）是 RQ2 / RQ3 用的同一次 clone，
  parser 输出也还在（parser_result_ssk/），所以 RQ1 统一切到它。
  切换本身几乎不动头条数字：174 个项目里 61 个计数有变，但无一采纳状态翻转，
  CAR 60.9%、采纳者 106、PAI 中位 2.21% 均不变。

新增 Parquet：
  它在 263 → 218 那一步被漏掉了（当时其余被漏的 Flume / Fluo / Fluo Recipes / Fluo YARN
  本就该排除：dormant / 停更 / retired）。category 取自 projects.apache.org（big-data）。

各列的来源：
  total_tests, pt_total, junit4_pt, junit5_pt, pt_share,
  junit4_total, junit5_total, junit4_param_share, junit5_param_share
      ssk 的 parser 输出，计算逻辑直接调用 pt_summary.py（与旧底表同一份代码）
  files_java
      SSD 快照 HEAD 上 `git ls-tree -r --name-only HEAD | grep -F '.java' | wc -l`
      —— 与 trigger.sh 生成旧底表时是同一条命令，只是换成 ssk 的那次 clone
  date
      ssk 快照里该项目 HEAD 的提交时间（旧底表里这一列是运行时刻）
  first_commit_iso, first_commit, age
      沿用旧底表（仓库历史的起点不随快照变）；Parquet 取自全量 clone
  categories
      沿用旧底表；Parquet 见上

用法：python build_merged_ssk.py      （输出到本目录）
"""
import csv
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from paths import REPO, FINAL, PARSER_SSK, APACHE_PROJECTS, require   # noqa: E402

OLD = os.path.join(HERE, 'merged_data_218.csv')
OUT = os.path.join(HERE, 'merged_data_219_ssk.csv')
NAME_MAP = os.path.join(FINAL, 'project_name_map.json')
YEAR_NOW = 2026

# 新增项目：显示名 → (ssk 键, 首次提交, categories)
ADDED = {
    'Parquet': ('parquet-mr', '2012-08-31T15:17:05-07:00', 'big-data'),
}


def load_pt_summary():
    import importlib.util
    spec = importlib.util.spec_from_file_location('pt_summary', os.path.join(REPO, 'pt_summary.py'))
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
    repo = os.path.join(APACHE_PROJECTS, key)
    if not os.path.isdir(repo):
        return None
    out = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', 'HEAD'],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return sum(1 for line in out.stdout.splitlines() if '.java' in line)


def main():
    require(PARSER_SSK, 'ssk 的 parser 输出')
    require(APACHE_PROJECTS, 'ssk 的源码快照（用于 files_java）')
    ps = load_pt_summary()
    inv = {v: k for k, v in json.load(open(NAME_MAP)).items()}

    old = list(csv.DictReader(open(OLD)))
    fields = list(old[0].keys())

    rows, problems = [], []
    todo = [(r['project'], r) for r in old] + [(p, None) for p in ADDED]
    for project, base in todo:
        if project in ADDED:
            key, first_iso, cats = ADDED[project]
        else:
            key, first_iso, cats = ssk_key(project, inv), base['first_commit_iso'], base['categories']
        if not key:
            # 底表保持完整：原样沿用旧行。目前只有 Commons-HttpClient，它在 DATA_INTEGRITY_EXCL 里，
            # 本就不进 RQ1 的分析集合，所以不影响任何结果。
            problems.append(f'{project}: 没有 ssk parser 输出，原样沿用旧底表的行')
            rows.append(dict(base))
            continue
        recs = ps.load_json_records(os.path.join(PARSER_SSK, f'{key}_output.json'))[0]
        total, pt, j4pt, j5pt, share = ps.compute_stats(recs)
        j4t, j5t, j4s, j5s = ps.compute_flavor_breakdown(recs)
        fj = files_java(key)
        if fj is None:
            problems.append(f'{project}: SSD 上没有可读的源码快照，files_java 沿用旧值')
            fj = base['files_java'] if base else ''
        year = int(first_iso[:4]) if first_iso else ''
        rows.append({
            'project': project, 'date': snapshot_date(key),
            'total_tests': total, 'pt_total': pt, 'junit4_pt': j4pt, 'junit5_pt': j5pt, 'pt_share': share,
            'junit4_total': j4t, 'junit5_total': j5t,
            'junit4_param_share': j4s, 'junit5_param_share': j5s,
            'files_java': float(fj) if fj != '' else '',
            'first_commit_iso': first_iso, 'uses_pt': int(pt > 0), 'categories': cats,
            'first_commit': year, 'age': (YEAR_NOW - year) if year != '' else '',
        })

    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {os.path.relpath(OUT, REPO)}: {len(rows)} 行')
    for p in problems:
        print('  ⚠️ ', p)


if __name__ == '__main__':
    main()
