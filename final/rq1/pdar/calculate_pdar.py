#!/usr/bin/env python3
"""PDAR 的汇总步骤：把逐项目的提交表折算成项目级比例。

    PDAR = 改过 PT 的开发者数 / 改过测试代码的开发者数   （×100，单位是 %）

是**开发者比例，不是提交比例**。两个计数都按 author email 去重并转小写
（同一个人可能用不同大小写提交）。分母用「改过测试代码的人」而不是「所有提交者」，
这样比例回答的是「在碰测试的人里，有多少比例碰过 PT」，
不会被只改生产代码的贡献者稀释。

另外报告 core_pdar：分子换成 `is_core`（由 Layer 3 的 pickaxe 判定，
即**新增或删除**过 PT 注解的人，而非只是改动 PT 内部的人）。

输入：PT_PDAR_RESULT 下的 {project}_commits.csv，由 find_pt_developers.py 产出。
输出：同目录的 pdar_summary.csv。

用 --context N 读取敏感性分析那一轮的结果（它们写在 result_U{N}/ 里）。
"""

import argparse
import csv
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from paths import PDAR_RESULT, PT_PROJECTS_LIST, require   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# main() 会按 --context 覆盖这两个；这里给出模块级默认值，避免被 import 时 NameError
RESULT_V3_DIR = PDAR_RESULT
OUTPUT_CSV = os.path.join(PDAR_RESULT, 'pdar_summary.csv')


def get_unique_emails(email_list):
    """Returns set of unique lowercase emails"""
    return set(e.strip().lower() for e in email_list if e and e.strip())


def find_file_case_insensitive(directory, pattern):
    """Find file with case-insensitive matching"""
    import glob
    # Try exact match first
    exact_path = os.path.join(directory, pattern)
    if os.path.exists(exact_path):
        return exact_path
    
    # Try case-insensitive search
    for f in os.listdir(directory):
        if f.lower() == pattern.lower():
            return os.path.join(directory, f)
    
    return None


def process_project(project_name):
    # Paths - use case-insensitive file finding
    commits_file = find_file_case_insensitive(RESULT_V3_DIR, f"{project_name}_commits.csv")
    
    # Check existence
    if not commits_file:
        print(f"[Warning] Missing commits file for {project_name}")
        return None
    
    # Read all commits and count unique developers
    test_dev_emails = set()  # Developers who touched test code
    pt_emails = set()        # Developers who modified PT
    core_emails = set()      # Core PT developers (add/delete PT)
    
    with open(commits_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('author_email', '').strip().lower()
            if email:
                # Count test developers (touched_test = 1)
                if row.get('touched_test', '0') == '1':
                    test_dev_emails.add(email)
                # Count PT participants
                if row.get('modifiedPT', '0') == '1':
                    pt_emails.add(email)
                # Count core developers
                if row.get('is_core', '0') == '1':
                    core_emails.add(email)
    
    # Calculate PDAR (denominator = test developers, not all developers)
    pt_count = len(pt_emails)
    core_count = len(core_emails)
    test_dev_count = len(test_dev_emails)
    
    if test_dev_count == 0:
        pdar = 0.0
        core_pdar = 0.0
    else:
        pdar = (pt_count / test_dev_count) * 100
        core_pdar = (core_count / test_dev_count) * 100
    
    return {
        'project': project_name,
        'pt_participants': pt_count,
        'core_developers': core_count,
        'test_developers': test_dev_count,
        'pdar': round(pdar, 2),
        'core_pdar': round(core_pdar, 2)
    }


def main():
    ap = argparse.ArgumentParser(description='把逐项目提交表汇总为项目级 PDAR')
    ap.add_argument('--context', type=int, default=3,
                    help='读哪一轮的结果：3 = 论文口径（result/），其它 N 读 result_U{N}/')
    ap.add_argument('--result-dir', default=None, help='直接指定结果目录')
    args = ap.parse_args()

    global RESULT_V3_DIR, OUTPUT_CSV
    if args.result_dir:
        RESULT_V3_DIR = args.result_dir
    else:
        RESULT_V3_DIR = PDAR_RESULT if args.context == 3 else f'{PDAR_RESULT}_U{args.context}'
    require(RESULT_V3_DIR, f'PDAR 汇总（-U{args.context} 那一轮的逐项目提交表）')
    OUTPUT_CSV = os.path.join(RESULT_V3_DIR, 'pdar_summary.csv')
    print(f'结果目录: {RESULT_V3_DIR}   (diff 上下文 -U{args.context})')

    with open(PT_PROJECTS_LIST, 'r') as f:
        projects = [line.strip() for line in f if line.strip()]
    
    print(f"Processing {len(projects)} projects...")
    print()
    
    results = []
    for project in projects:
        print(f"Processing {project}...")
        result = process_project(project)
        if result:
            results.append(result)
            print(f"  PT Participants: {result['pt_participants']}")
            print(f"  Core Developers: {result['core_developers']}")
            print(f"  Test Developers: {result['test_developers']}")
            print(f"  PDAR: {result['pdar']}%")
            print(f"  Core PDAR: {result['core_pdar']}%")
        print()
    
    # Save to CSV
    if results:
        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"Results saved to: {OUTPUT_CSV}")
        
        # Print summary table
        print("\n" + "="*90)
        print("PDAR Summary (v3) - Denominator: Test Developers (touched test code)")
        print("="*90)
        print(f"{'Project':<25} {'PT Part.':<12} {'Core Dev.':<12} {'Test Dev.':<12} {'PDAR':<10} {'Core PDAR':<10}")
        print("-"*90)
        for r in sorted(results, key=lambda x: -x['pdar']):
            print(f"{r['project']:<25} {r['pt_participants']:<12} {r['core_developers']:<12} {r['test_developers']:<12} {r['pdar']:<10.2f}% {r['core_pdar']:<10.2f}%")
        print("="*90)


if __name__ == '__main__':
    main()
