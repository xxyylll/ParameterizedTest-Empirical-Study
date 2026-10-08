#!/usr/bin/env python3
"""
分析所有项目的参数化测试方法中使用的数据源类型
"""
import json
import os
import csv
import pandas as pd
import sys
from collections import defaultdict, Counter
from datetime import datetime

# 设置日志输出
class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()
        
    def close(self):
        self.log.close()

# 创建日志文件和输出目录
script_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(script_dir, 'logs')
outputs_dir = os.path.join(script_dir, 'outputs')

# 确保目录存在
os.makedirs(logs_dir, exist_ok=True)
os.makedirs(outputs_dir, exist_ok=True)

log_filename = os.path.join(logs_dir, f"method_source_analysis_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
logger = Logger(log_filename)
sys.stdout = logger

print(f"Method Source Analysis Started at {datetime.now()}")
print("="*80)

def extract_source_annotations(annotations, junit_version):
    """从注解列表中提取数据源相关的注解"""
    source_annotations = []
    for annotation in annotations:
        # JUnit 5的数据源注解（扩展版本）
        if annotation in ['MethodSource', 'ValueSource', 'CsvSource', 'CsvFileSource', 
                         'EnumSource', 'ArgumentsSource', 'FieldSource', 'NullSource', 
                         'EmptySource', 'NullAndEmptySource', 'Arguments']:
            source_annotations.append(f"JUnit5_{annotation}")
        # JUnit 4的参数化测试注解 - 统一映射为 JUnit4_Parameters
        elif annotation in ['RunWith(Parameterized.class)', 'Parameterized', 'Parameters']:
            source_annotations.append("JUnit4_Parameters")
        # 检查是否包含JUnit 4参数化相关的注解
        elif 'Parameterized' in str(annotation) and junit_version == 'junit4':
            source_annotations.append("JUnit4_Parameters")
        elif 'RunWith' in str(annotation) and 'Parameterized' in str(annotation):
            source_annotations.append("JUnit4_Parameters")
    return source_annotations

def is_parameterized_test(annotations, junit_version):
    """判断是否为参数化测试"""
    if junit_version == 'junit5':
        return 'ParameterizedTest' in annotations
    elif junit_version == 'junit4':
        # JUnit 4的参数化测试标识
        for annotation in annotations:
            if any(marker in str(annotation) for marker in ['Parameterized', 'RunWith(Parameterized.class)']):
                return True
    return False

def analyze_project_sources(json_path):
    """分析单个项目的参数化测试数据源"""
    project_sources = defaultdict(int)
    total_pt_methods = 0
    junit4_pt_methods = 0
    junit5_pt_methods = 0
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for method in data:
            if 'annotations' in method:
                annotations = method['annotations']
                junit_version = method.get('junit', 'unknown')
                
                # 检查是否为参数化测试
                if is_parameterized_test(annotations, junit_version):
                    total_pt_methods += 1
                    
                    if junit_version == 'junit4':
                        junit4_pt_methods += 1
                    elif junit_version == 'junit5':
                        junit5_pt_methods += 1
                    
                    source_annotations = extract_source_annotations(annotations, junit_version)
                    
                    if source_annotations:
                        for source in source_annotations:
                            project_sources[source] += 1
                    else:
                        # 如果没有明确的数据源注解，根据JUnit版本标记
                        unknown_key = f"Unknown_{junit_version}" if junit_version in ['junit4', 'junit5'] else "Unknown"
                        project_sources[unknown_key] += 1
                    
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error processing {json_path}: {e}")
        return {}, 0, 0, 0
    
    return dict(project_sources), total_pt_methods, junit4_pt_methods, junit5_pt_methods

def main():
    """主函数：分析所有项目的参数化测试数据源"""
    parser_dir = "../parser_result"
    
    if not os.path.exists(parser_dir):
        print(f"Error: {parser_dir} directory not found")
        return
    
    # 定义最终确定的源类型列（按你要求的顺序）
    expected_junit5_sources = [
        'JUnit5_MethodSource',
        'JUnit5_FieldSource',          # 官方已有
        'JUnit5_CsvSource', 
        'JUnit5_CsvFileSource',
        'JUnit5_EnumSource',
        'JUnit5_ValueSource',
        'JUnit5_NullSource',
        'JUnit5_EmptySource',
        'JUnit5_NullAndEmptySource',
        'JUnit5_ArgumentsSource'       # 保留：给真正的自定义 provider 用
    ]
    
    expected_junit4_sources = [
        'JUnit4_Parameters'            # JUnit4Parameters
    ]
    
    all_expected_sources = expected_junit4_sources + expected_junit5_sources
    
    # 存储所有项目的数据源统计
    all_projects_data = []
    global_source_counter = Counter()
    total_projects = 0
    total_pt_methods_global = 0
    total_junit4_pt_methods = 0
    total_junit5_pt_methods = 0
    
    print("Analyzing parameterized test method sources...")
    print(f"Scanning directory: {parser_dir}")
    
    for filename in sorted(os.listdir(parser_dir)):
        if not filename.endswith("_output.json"):
            continue
            
        project = filename.replace("_output.json", "")
        json_path = os.path.join(parser_dir, filename)
        
        print(f"Processing: {project}")
        
        project_sources, pt_methods_count, junit4_count, junit5_count = analyze_project_sources(json_path)
        
        if pt_methods_count > 0:
            total_projects += 1
            total_pt_methods_global += pt_methods_count
            total_junit4_pt_methods += junit4_count
            total_junit5_pt_methods += junit5_count
            
            # 更新全局计数器
            for source, count in project_sources.items():
                global_source_counter[source] += count
            
            # 准备项目数据行
            project_data = {
                'project': project,
                'total_pt_methods': pt_methods_count,
                'junit4_pt_methods': junit4_count,
                'junit5_pt_methods': junit5_count
            }
            
            # 添加各种数据源的统计
            for source, count in project_sources.items():
                project_data[source] = count
            
            all_projects_data.append(project_data)
    
    print(f"\nProcessed {total_projects} projects with parameterized tests")
    print(f"Total parameterized test methods: {total_pt_methods_global}")
    print(f"  - JUnit 4 PT methods: {total_junit4_pt_methods}")
    print(f"  - JUnit 5 PT methods: {total_junit5_pt_methods}")
    
    # 获取所有出现过的数据源类型
    all_sources = sorted(global_source_counter.keys())
    print(f"\nFound {len(all_sources)} different source types:")
    
    # 分别显示JUnit 4和JUnit 5的数据源
    junit4_sources = [s for s in all_sources if s.startswith('JUnit4_')]
    junit5_sources = [s for s in all_sources if s.startswith('JUnit5_')]
    other_sources = [s for s in all_sources if not s.startswith(('JUnit4_', 'JUnit5_'))]
    
    if junit4_sources:
        print(f"\nJUnit 4 Sources:")
        for source in junit4_sources:
            print(f"  {source}: {global_source_counter[source]} methods")
    
    if junit5_sources:
        print(f"\nJUnit 5 Sources:")
        for source in junit5_sources:
            print(f"  {source}: {global_source_counter[source]} methods")
    
    if other_sources:
        print(f"\nOther Sources:")
        for source in other_sources:
            print(f"  {source}: {global_source_counter[source]} methods")
    
    # 创建DataFrame并填充缺失值
    df = pd.DataFrame(all_projects_data)
    
    # 只保留预期的源类型列，过滤掉其他发现的源类型
    all_sources = all_expected_sources
    
    # 确保所有预期的数据源列都存在，填充0
    for source in all_sources:
        if source not in df.columns:
            df[source] = 0
        else:
            df[source] = df[source].fillna(0).astype(int)
    
    # 重新排序列：基础列 + 按确定顺序的源列
    base_columns = ['project', 'total_pt_methods', 'junit4_pt_methods', 'junit5_pt_methods']
    columns_order = base_columns + all_sources
    df = df.reindex(columns=columns_order, fill_value=0)
    
    # 保存到CSV
    output_file = os.path.join(outputs_dir, "parameterized_test_sources_analysis.csv")
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")
    
    # 输出统计摘要
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}")
    print(f"Total projects analyzed: {len(df)}")
    print(f"Total parameterized test methods: {df['total_pt_methods'].sum()}")
    print(f"  - JUnit 4 PT methods: {df['junit4_pt_methods'].sum()}")
    print(f"  - JUnit 5 PT methods: {df['junit5_pt_methods'].sum()}")
    print(f"Average PT methods per project: {df['total_pt_methods'].mean():.1f}")
    print(f"Median PT methods per project: {df['total_pt_methods'].median():.1f}")
    
    # JUnit版本统计
    junit4_projects = (df['junit4_pt_methods'] > 0).sum()
    junit5_projects = (df['junit5_pt_methods'] > 0).sum()
    print(f"Projects using JUnit 4 PT: {junit4_projects}/{len(df)} ({junit4_projects/len(df)*100:.1f}%)")
    print(f"Projects using JUnit 5 PT: {junit5_projects}/{len(df)} ({junit5_projects/len(df)*100:.1f}%)")
    
    print(f"\nData Source Usage Distribution:")
    for source in all_sources:
        count = df[source].sum()
        projects_using = (df[source] > 0).sum()
        percentage = (count / total_pt_methods_global) * 100 if total_pt_methods_global > 0 else 0
        print(f"  {source:20s}: {count:5d} methods ({percentage:5.1f}%) used in {projects_using:3d} projects")
    
    # 分析项目级别的数据源使用模式
    print(f"\nProject-level Source Usage Patterns:")
    source_usage_by_project = {}
    for source in all_sources:
        projects_count = (df[source] > 0).sum()
        percentage = (projects_count / len(df)) * 100
        source_usage_by_project[source] = projects_count
        print(f"  {source:20s}: {projects_count:3d}/{len(df)} projects ({percentage:5.1f}%)")
    
    # 找出最常用的数据源组合
    print(f"\nMost Common Source Type Combinations:")
    source_combinations = []
    for _, row in df.iterrows():
        used_sources = []
        for source in all_sources:
            if row[source] > 0:
                used_sources.append(source)
        if used_sources:
            source_combinations.append(", ".join(sorted(used_sources)))
        else:
            source_combinations.append("None")
    
    combination_counter = Counter(source_combinations)
    for combination, count in combination_counter.most_common(10):
        percentage = (count / len(df)) * 100
        print(f"  {combination:40s}: {count:3d} projects ({percentage:5.1f}%)")
    
    # 输出前10个使用PT最多的项目
    print(f"\nTop 10 Projects by Parameterized Test Count:")
    top_projects = df.nlargest(10, 'total_pt_methods')
    for _, row in top_projects.iterrows():
        used_sources = []
        for source in all_sources:
            if row[source] > 0:
                used_sources.append(f"{source}({int(row[source])})")
        sources_str = ", ".join(used_sources) if used_sources else "None"
        print(f"  {row['project']:20s}: {int(row['total_pt_methods']):4d} PT methods - {sources_str}")

    print(f"\n{'='*80}")
    print(f"Analysis completed at {datetime.now()}")
    print(f"Results saved to: {output_file}")
    print(f"Log saved to: {log_filename}")

    # 关闭日志
    logger.close()
    sys.stdout = logger.terminal

if __name__ == "__main__":
    main()