#!/usr/bin/env python3
"""生成发给评分者的材料包：每人一个 Markdown（看代码）+ 一个 CSV（填答案）。

Markdown 里**只有代码**，没有任何标签、没有分析器算出的依赖链和等级。
评分者不需要 clone 任何项目。
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import paths as _paths
RESULTS_DIR = _paths.RQ2_2_IRR_RESULTS
_os_root.makedirs(RESULTS_DIR, exist_ok=True)
import csv
import os
from collections import Counter

import extract_snippets as E
from resolve_paths import resolve, AP

HERE = os.path.dirname(os.path.abspath(__file__))
DIMS = {
    'MethodSource': ['equivalence_class', 'semantic_role', 'methodsource_intent',
                     'type_complexity', 'value_complexity', 'behavior_carrying'],
    'ValueSource':  ['equivalence_class', 'semantic_role'],
    'CsvSource':    ['equivalence_class', 'semantic_role'],
    'EnumSource':   ['equivalence_class', 'enum_structure', 'enum_usage_intent', 'behavior_carrying'],
}


def rel(path):
    return path[len(AP) + 1:] if path.startswith(AP) else path


def build_item(r):
    """返回 (markdown 片段, 抽取状态)。"""
    path = resolve(r['file_path'], r['project'])
    if not path:
        return None, 'path-unresolved'
    test = E.method(path, r['test_name'])
    if not test:
        return None, 'test-not-found'
    parts = [f"## {r['item_id']}  ·  {r['source']}",
             '',
             f"**项目** `{r['project']}`  **文件** `{rel(path)}`  **测试** `{r['test_name']}`",
             '',
             '### Test method', '', '```java', test, '```', '']
    status = 'ok'
    ann = E.annotation_of(path, r['test_name'])

    if r['source'] == 'MethodSource':
        names = E.provider_names(ann)
        found = 0
        for nm in names:
            cls, _, meth = nm.rpartition('#')
            proj_root = os.path.join(AP, rel(path).split('/')[0])
            target, label = path, f'同文件内的 `{meth}`'
            if cls:
                simple = cls.split('.')[-1]
                hits = E.find_type(proj_root, simple, decl_kw='class|interface|enum')
                if hits:
                    target, label = hits[0], f'`{simple}#{meth}`（{rel(hits[0])}）'
            src = E.method(target, meth)
            if not src:                      # provider 可能继承自父类 / 在别处声明
                for fp in E.find_method_file(proj_root, meth):
                    src = E.method(fp, meth)
                    if src:
                        label = f'`{meth}`（{rel(fp)}）'
                        break
            if src:
                parts += [f'### Parameter provider — {label}', '', '```java', src, '```', '']
                found += 1
        if not found:
            parts += ['### Parameter provider', '', '> ⚠️ 未能自动定位 provider，请对照上方注解自行判断。', '']
            status = 'provider-missing'

    elif r['source'] == 'EnumSource':
        types = E.enum_types(ann) or E.param_types(path, r['test_name'])
        found = 0
        for t in types:
            hits = E.find_type(os.path.join(AP, rel(path).split('/')[0]), t, decl_kw='enum')
            for h in hits[:1]:
                d = E.enum_decl(h, t)
                if d:
                    parts += [f'### Enum declaration — `{t}` ({rel(h)})', '', '```java', d, '```', '']
                    found += 1
        if not types:
            parts += ['### 枚举声明', '', '> 注解未显式给出枚举类型，且未能从参数声明推断。', '']
            status = 'enum-implicit'
        elif not found:
            parts += ['### 枚举声明', '', '> ⚠️ 未能定位枚举声明。', '']
            status = 'enum-missing'

    # 测试体调用到的同文件 helper。codebook：依参数而变的分支可能不在测试体里而在 helper 里，
    # 判 equivalence_class 与 enum_usage_intent 都必须看得到它们。
    hs = E.helpers(path, r['test_name'])
    if hs:
        parts += [f'### Test-side helpers called by this test ({len(hs)})', '',
                  '> Parameter-dependent branching may live here rather than in the test body — '
                  'check these before deciding.', '']
        for nm, code in hs:
            parts += [f'**`{nm}`**', '', '```java', code, '```', '']

    parts += ['### To classify', '', ' / '.join(f'`{d}`' for d in DIMS[r['source']]), '', '---', '']
    return '\n'.join(parts), status


def main():
    rows = list(csv.DictReader(open(os.path.join(RESULTS_DIR, 'sample_items.csv'))))
    stat = Counter()
    for rid in ('R1', 'R2', 'R3'):
        mine = sorted([r for r in rows if rid in r['assigned'].split(';')], key=lambda x: x['item_id'])
        out = [f'# Rating packet {rid}',
               '',
               f'{len(mine)} items. For each one, classify only the dimensions that apply to its '
               'source — the rules are in `rater_guide.md`.',
               '',
               f'Record your answers in `packet_{rid}.csv`, one row per item, matched by `item_id`. '
               'If the code shown does not let you decide, answer `unclear` and write one line in `notes`.',
               '', '---', '']
        for r in mine:
            md, st = build_item(r)
            stat[st] += 1
            if md:
                out.append(md)
            else:
                out.append(f"## {r['item_id']}  ·  {r['source']}\n\n> ⚠️ 代码抽取失败（{st}）：`{r['file_path']}`\n\n---\n")
        with open(os.path.join(RESULTS_DIR, f'packet_{rid}.md'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(out))
        print(f'  packet_{rid}.md  {len(mine)} 条')
    print('\n抽取状态:', dict(stat))


if __name__ == '__main__':
    main()
