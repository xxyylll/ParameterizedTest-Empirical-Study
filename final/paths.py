#!/usr/bin/env python3
"""所有外部路径的唯一解析处。

为什么需要它：`final/` 里的脚本原本是从各自的工作目录复制过来的，路径按原位置硬编码
（`/Users/immortal/Complexity_Analysis/...`、`/Volumes/SSKSSD/...`），
换一台机器、甚至只是从 `final/` 里直接运行就会失败。

设计：
  - **小体积的数据与 `final/` 同级放好**（merged_data_218.csv、rq22_*_all.csv 等），
    脚本优先用这些，不依赖任何外部目录。
  - **大体积的数据**（外置盘上的源码快照、AAA 轨迹、CCFinderSW 结果、
    parser 的逐项目 JSON）用环境变量指定，带一个本机默认值。

环境变量（都可选，不设则用默认值）：
  PT_SSD          外置盘根目录            默认 /Volumes/SSKSSD
  PT_PARSER_SSK   轻量 parser 的逐项目 JSON   默认 <repo>/parser_result_ssk
  PT_METRICS      RQ3 的指标中间表目录        默认 /Users/immortal/Complexity_Analysis
  PT_MANUAL       人工标注表目录             默认 $PT_SSD/rq2.2_manual

用法：
    from paths import FINAL, SSD, APACHE_PROJECTS, require
    p = require(APACHE_PROJECTS, "RQ3 指标计算")   # 缺失时给出可读的报错
"""
import os

FINAL = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(FINAL)

_env = os.environ.get

SSD = _env('PT_SSD', '/Volumes/SSKSSD')
PARSER_SSK = _env('PT_PARSER_SSK', os.path.join(REPO, 'parser_result_ssk'))
METRICS_DIR = _env('PT_METRICS', '/Users/immortal/Complexity_Analysis')
MANUAL_DIR = _env('PT_MANUAL', os.path.join(SSD, 'rq2.2_manual'))

APACHE_PROJECTS = os.path.join(SSD, 'apache-projects')     # 源码快照 + 各项目的 AAA/
DUP_RESULT = os.path.join(SSD, 'dup_result_ssk')           # CCFinderSW 输出

# 随 final/ 一同分发的小文件
PROJECT_NAME_MAP = os.path.join(FINAL, 'project_name_map.json')
RQ1_DIR = os.path.join(FINAL, 'rq1')
RQ2_1_DIR = os.path.join(FINAL, 'rq2_1')
RQ2_2_DIR = os.path.join(FINAL, 'rq2_2')
RQ3_1_DIR = os.path.join(FINAL, 'rq3_1')

MERGED_DATA = os.path.join(RQ1_DIR, 'merged_data_218.csv')
PDAR_SUMMARY = os.path.join(RQ1_DIR, 'pdar_summary_ssk.csv')


def require(path, what):
    """路径不存在时给出能照着修的报错，而不是裸的 FileNotFoundError。"""
    if os.path.exists(path):
        return path
    hint = {
        SSD: 'PT_SSD', PARSER_SSK: 'PT_PARSER_SSK',
        METRICS_DIR: 'PT_METRICS', MANUAL_DIR: 'PT_MANUAL',
    }
    var = next((v for k, v in hint.items() if path.startswith(k)), None)
    msg = f'{what} 需要的路径不存在：{path}'
    if var:
        msg += f'\n   用环境变量 {var} 指定实际位置，例如：\n   export {var}=/your/path'
    raise FileNotFoundError(msg)


if __name__ == '__main__':
    print(f'{"FINAL":18}{FINAL}')
    print(f'{"REPO":18}{REPO}')
    for name, p in (('SSD', SSD), ('PARSER_SSK', PARSER_SSK), ('METRICS_DIR', METRICS_DIR),
                    ('MANUAL_DIR', MANUAL_DIR), ('APACHE_PROJECTS', APACHE_PROJECTS),
                    ('DUP_RESULT', DUP_RESULT), ('MERGED_DATA', MERGED_DATA),
                    ('PDAR_SUMMARY', PDAR_SUMMARY)):
        print(f'{name:18}{p:60}{"OK" if os.path.exists(p) else "缺失"}')
