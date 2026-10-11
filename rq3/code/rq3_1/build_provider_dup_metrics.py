#!/usr/bin/env python3
"""RQ3.1 source-DUP check：parameter source（provider）本身有多重复？

动机：主分析发现 PT 的 **helper 层** 重复率显著高于非 PT（37/46 项目，中位 delta +0.30），
而 **total 层** 反过来是非 PT 更高。一个自洽的解释是「参数化把重复从测试体转移到了
parameter construction 代码里」。这个脚本把 PT 的 helper 聚合拆成两半来直接验证：

  provider      —— AAA 轨迹里被标成 METHODSOURCE / FIELDSOURCE 的方法（即 @MethodSource
                   / @FieldSource 指向的参数供给方法）
  other helper  —— 该测试调用的其余 test-scope 辅助方法

如果 provider 的 dupPerc 明显高于 other helper，那么「重复藏进了 parameter construction」
就从一个推测变成一个可量化的结论。

口径与 build_test_dup_metrics.py 完全一致（同一套 helper 解析、同一份 CCFinderSW 克隆数据、
同样的 line-ratio、同样先加后除），只是把 helper 分成了两组。

输出 provider_dup_metrics.csv
"""

# 向上找到 仓库根（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from paths import SSD, METRICS_DIR, APACHE_PROJECTS, DUP_RESULT, FINAL  # noqa: E402
import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_test_metrics_unified import (  # noqa: E402
    SKIP_PREFIXES, make_projects, build_source_class_sets, classify_declaring_class,
    get_prefix_and_rest, parse_rest, load_test_jsons, drop_data_method_refs,
    resolve_helper_entry, PROJECTS,
)
from build_test_dup_metrics import parse_ccfinder_result, dup_span, DUP_ROOT  # noqa: E402


OUT_CSV = _os.path.join(METRICS_DIR, 'provider_dup_metrics.csv')
PROVIDER_PREFIXES = {'METHODSOURCE', 'FIELDSOURCE'}


def process_project(proj, writer):
    name = proj['name']
    result_path = os.path.join(DUP_ROOT, f'{name}_dup', 'result.txt')
    if not os.path.isfile(result_path):
        print(f'  SKIPPED {name}: no CCFinderSW result', file=sys.stderr)
        return 0
    dup_lines_by_file, _, _ = parse_ccfinder_result(result_path, proj['base_dir'])
    parsed = load_test_jsons(proj['aaa_dir'])
    production_classes, test_classes, test_class_files = build_source_class_sets(proj['base_dir'])
    stats = defaultdict(int)
    n = 0

    for d in parsed:
        if not d.get('isParameterized'):
            continue                      # provider 只有 PT 才有
        buckets = {'provider': [0, 0, 0], 'other': [0, 0, 0]}   # dup, total, count
        seen = set()

        for raw in drop_data_method_refs(d.get('parsedStatementsSequence', [])):
            s = raw.strip()
            if not s:
                continue
            prefix, rest = get_prefix_and_rest(s)
            if prefix in SKIP_PREFIXES or prefix == 'NEW ANONYMOUS_CLASS':
                continue
            qualified, params, arity = parse_rest(rest)
            if qualified is None:
                continue
            if prefix == 'NEW':
                declaring_class = qualified
                lookup_name = f'{qualified}.{qualified.rsplit(".", 1)[-1]}'
            else:
                declaring_class = qualified.rsplit('.', 1)[0] if '.' in qualified else qualified
                lookup_name = qualified
            if classify_declaring_class(declaring_class, production_classes, test_classes) != 'test':
                continue
            if lookup_name in seen:
                continue
            seen.add(lookup_name)

            status, entry = resolve_helper_entry(lookup_name, declaring_class, arity,
                                                 test_class_files, stats, is_new=(prefix == 'NEW'))
            if status != 'ok' or entry['start_line'] is None:
                continue
            h_file = None
            for cand in (declaring_class,):
                from build_test_metrics_unified import resolve_test_class_file
                h_file = resolve_test_class_file(cand, test_class_files)
            dup, tot = dup_span(h_file, entry['start_line'], entry['end_line'], dup_lines_by_file)
            b = buckets['provider' if prefix in PROVIDER_PREFIXES else 'other']
            b[0] += dup
            b[1] += tot
            b[2] += 1

        p, o = buckets['provider'], buckets['other']
        writer.writerow({
            'project': name,
            'test_class': d.get('testClassName', ''),
            'test_name': d.get('testCaseName', ''),
            'n_providers': p[2], 'provider_dupLines': p[0], 'provider_totalLines': p[1],
            'provider_dupPerc': round(p[0] / p[1], 6) if p[1] else '',
            'n_other_helpers': o[2], 'other_dupLines': o[0], 'other_totalLines': o[1],
            'other_dupPerc': round(o[0] / o[1], 6) if o[1] else '',
        })
        n += 1
    print(f'  {name}: {n} PTs', file=sys.stderr)
    return n


def main():
    names = [a for a in sys.argv[1:] if not a.startswith('-')]
    projects = make_projects(names) if names else PROJECTS
    fields = ['project', 'test_class', 'test_name',
              'n_providers', 'provider_dupLines', 'provider_totalLines', 'provider_dupPerc',
              'n_other_helpers', 'other_dupLines', 'other_totalLines', 'other_dupPerc']
    total = 0
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for proj in projects:
            total += process_project(proj, w)
    print(f'\nWrote {total} PT rows to {OUT_CSV}', file=sys.stderr)


if __name__ == '__main__':
    main()
