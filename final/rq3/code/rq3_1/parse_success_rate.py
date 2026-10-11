#!/usr/bin/env python3
"""RQ3 的 AAA 解析成功率 —— 46 个项目，分 PT / 非 PT。

分母：轻量 parser 在源码里识别出的测试方法数（`parser_result_ssk/{proj}_output.json`）。
      这是「应该被分析到」的全集，与 RQ1/RQ2.1 同源，所以三个 RQ 的分母口径一致。
分子：进入 RQ3 指标表的测试数（`test_metrics_all_46projects_v2.csv`）。
      能进表意味着它拿到了可用的 AAA 轨迹且指标算得出来。

**PT 的定义两边必须一致**：指标表的 `category=pt` 只含 JUnit5 的 `@ParameterizedTest`
（AAA 轨迹的 isParameterized 是 jupiter 专有），所以分母也只把 JUnit5 的参数化测试算作 PT，
JUnit4 的 `@RunWith(Parameterized)` 归入非 PT。
不统一的话 druid 这类 JUnit4 大户会出现「PT 14%、非 PT 113%」的荒谬结果。

本表衡量的是 **AAA 解析覆盖率**，与 RQ3 最终分析集合不是一回事 —— 后者还要再过一道
JUnit5 筛选（非 PT 组剔掉 20,093 个 JUnit4 测试）。

两个 parser 的分歧是双向的，个别项目会算出 >100%：
  - **低于 100%**：AAA 管线没覆盖到轻量 parser 找到的测试。集中在测试代码放在
    非标准源根的项目（calcite `testkit/src/main/java`、accumulo `test/src/main/java`、
    iceberg `src/integration/java`）。
  - **高于 100%**：轻量 parser 漏了 AAA 管线找到的测试。目前只有 nifi（188 vs 176，
    多 12 个 PT），属于 RQ1 parser 的假阴性，在 validity 部分应当提及。
所以本表是「两个独立实现的覆盖度对照」，不是单向的成功率 —— 论文里要这么描述。

输出 parse_success_rate.csv
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _paths.RQ3_1_RESULTS
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import csv
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, _paths.RQ2_1_CODE)
from paths import PARSER_SSK as SSK, METRICS_DIR, require   # noqa: E402

METRICS = os.path.join(METRICS_DIR, 'test_metrics_all_46projects_v2.csv')
from method_source_analysis import is_parameterized_test  # noqa: E402


def main():
    require(METRICS, 'RQ3 解析覆盖率')
    require(SSK, 'RQ3 解析覆盖率的分母')
    rows = list(csv.DictReader(open(METRICS)))
    projects = sorted({r['project'] for r in rows})

    got = defaultdict(lambda: {'pt': 0, 'nonpt': 0})
    for r in rows:
        got[r['project']][r['category']] += 1

    out = []
    tot = defaultdict(int)
    for p in projects:
        src = {'pt': 0, 'nonpt': 0}
        path = os.path.join(SSK, f'{p}_output.json')
        for m in json.load(open(path)):
            ann, jv = m.get('annotations', []), m.get('junit', 'unknown')
            is_pt = jv == 'junit5' and is_parameterized_test(ann, jv)
            src['pt' if is_pt else 'nonpt'] += 1
        g = got[p]
        row = [p]
        for k in ('pt', 'nonpt'):
            rate = 100 * g[k] / src[k] if src[k] else float('nan')
            row += [src[k], g[k], f'{rate:.1f}']
            tot[f'src_{k}'] += src[k]; tot[f'got_{k}'] += g[k]
        out.append(row)

    out.sort(key=lambda r: -(r[1] + r[4]))
    with open(os.path.join(RESULTS_DIR, 'parse_success_rate.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['project', 'pt_in_source', 'pt_parsed', 'pt_rate_pct',
                    'nonpt_in_source', 'nonpt_parsed', 'nonpt_rate_pct'])
        w.writerows(out)
        w.writerow(['TOTAL', tot['src_pt'], tot['got_pt'],
                    f"{100*tot['got_pt']/tot['src_pt']:.1f}",
                    tot['src_nonpt'], tot['got_nonpt'],
                    f"{100*tot['got_nonpt']/tot['src_nonpt']:.1f}"])

    print(f"{'project':20}{'PT 源码':>9}{'PT 解析':>9}{'PT %':>8}{'非PT 源码':>11}{'非PT 解析':>11}{'非PT %':>9}")
    print('-' * 78)
    for r in out:
        print(f'{r[0]:20}{r[1]:>9}{r[2]:>9}{r[3]:>8}{r[4]:>11}{r[5]:>11}{r[6]:>9}')
    print('-' * 78)
    print(f"{'合计':20}{tot['src_pt']:>9}{tot['got_pt']:>9}"
          f"{100*tot['got_pt']/tot['src_pt']:>8.1f}{tot['src_nonpt']:>11}{tot['got_nonpt']:>11}"
          f"{100*tot['got_nonpt']/tot['src_nonpt']:>9.1f}")


if __name__ == '__main__':
    main()
