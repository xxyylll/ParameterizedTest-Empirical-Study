#!/usr/bin/env python3
"""RQ1 的分组口径 —— **唯一定义处**。

这些常量曾经散落在五个脚本里，彼此不一致（年龄分档有三套、规模分档闭合方向有两套），
导致同一张表的不同图给出不同的 n。所有 RQ1 分析一律从这里导入，不要再各自写一遍。

年龄分档：≤2005 / 2006–2011 / 2012–2017 / ≥2018
  用 right=False 搭配 [0, 2006, 2012, 2018, 2030]，即 [0,2006) = ≤2005。

规模分档：`files_java` 三等分，切点 625 / 1806，**左闭右开**
  [0,625) / [625,1806) / [1806,inf) → <625 / 625–1805 / >=1806
  只有 Ranger 正好是 1806 个文件，归入 Large。

语料：218 − 42 retired − 2 data integrity = 174；其中采纳 PT 的 106 个。
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # final/ 下的 paths.py
from paths import MERGED_DATA as MERGED, PDAR_SUMMARY as PDAR_CSV   # noqa: E402

# 与 HttpComponents-Client 数据完全相同（同仓库重复计入）/ 子模块
DATA_INTEGRITY_EXCL = {'Commons-HttpClient', 'Lucene-Core'}

AGE_BINS = [0, 2006, 2012, 2018, 2030]
AGE_LABELS = ['<=2005', '2006-2011', '2012-2017', '>=2018']
AGE_RIGHT = False

SIZE_BINS = [0, 625, 1806, np.inf]
SIZE_LABELS = ['Small (<625)', 'Medium (625-1805)', 'Large (>=1806)']
SIZE_RIGHT = False

DOMAIN_MAPPING = {
    'Data & Analytics': ['big-data', 'database'],
    'Network & Comm.':  ['network-server', 'network-client'],
    'Dev. & Tools':     ['library', 'build-management', 'xml'],
    'Web & Content':    ['web-framework', 'content', 'http'],
}
DOMAIN_ORDER = list(DOMAIN_MAPPING)
# 9 个采纳 PT 的项目其 ASF category 落不进四大类（cloud / javaee / testing / ide /
# observability / identity-management，以及 3 个 category 为空）。不补就只能覆盖 97 个。
DOMAIN_MANUAL = {
    'jdo': 'Data & Analytics', 'fineract': 'Data & Analytics', 'uima': 'Data & Analytics',
    'spatial-information-system': 'Data & Analytics', 'unomi': 'Data & Analytics',
    'cloudstack': 'Dev. & Tools', 'deltaspike': 'Dev. & Tools', 'jmeter': 'Dev. & Tools',
    'netbeans': 'Dev. & Tools', 'openwebbeans': 'Dev. & Tools', 'skywalking': 'Dev. & Tools',
    'syncope': 'Dev. & Tools',
    'eventmesh': 'Network & Comm.', 'lingo': 'Network & Comm.', 'oltu-parent': 'Network & Comm.',
}


def first_commit_year(df):
    iso = pd.to_datetime(df.get('first_commit_iso'), errors='coerce', utc=True)
    return iso.dt.year.astype('Float64').fillna(pd.to_numeric(df.get('first_commit'), errors='coerce'))


def assign_domain(row):
    key = str(row['project']).strip().lower()
    if key in DOMAIN_MANUAL:
        return DOMAIN_MANUAL[key]
    cats = [c.strip() for c in str(row.get('categories') or '').split(',')]
    for d in DOMAIN_ORDER:                       # 优先级顺序，保证互斥
        if any(k in cats for k in DOMAIN_MAPPING[d]):
            return d
    return None


def load(adopters_only=False, with_pdar=False):
    """RQ1 的 174 个项目（或其中采纳 PT 的 106 个），已带好分组列。"""
    df = pd.read_csv(MERGED)
    df = df[~df['categories'].fillna('').str.contains('retired')]
    df = df[~df['project'].isin(DATA_INTEGRITY_EXCL)].drop_duplicates('project').copy()
    if adopters_only:
        df = df[df['uses_pt'] == 1].copy()

    df['pai'] = pd.to_numeric(df['pt_total'], errors='coerce') / \
                pd.to_numeric(df['total_tests'], errors='coerce') * 100
    df['year'] = first_commit_year(df)
    df['size_grp'] = pd.cut(pd.to_numeric(df['files_java'], errors='coerce'),
                            bins=SIZE_BINS, labels=SIZE_LABELS, right=SIZE_RIGHT)
    df['age_grp'] = pd.cut(df['year'], bins=AGE_BINS, labels=AGE_LABELS, right=AGE_RIGHT)
    df['domain_grp'] = df.apply(assign_domain, axis=1)

    if with_pdar:
        p = pd.read_csv(PDAR_CSV)
        p['key'] = p['project'].str.strip().str.lower()
        df['key'] = df['project'].str.strip().str.lower()
        df = df.merge(p[['key', 'pdar']], on='key', how='left')
    return df


if __name__ == '__main__':
    for flag in (False, True):
        d = load(adopters_only=flag, with_pdar=True)
        tag = '采纳者' if flag else '全部'
        print(f'{tag}: N={len(d)}  size={list(d["size_grp"].value_counts().reindex(SIZE_LABELS).values)}'
              f'  age={list(d["age_grp"].value_counts().reindex(AGE_LABELS).values)}'
              f'  domain={list(d["domain_grp"].value_counts().reindex(DOMAIN_ORDER).values)}')
