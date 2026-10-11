#!/usr/bin/env python3
"""判断一条抽样条目的材料能不能完整做出来。

做不出材料的条目不该被抽中 —— 评分者看不到 provider 或枚举声明就没法判定，
强行放进样本只会制造无效数据。抽样时用它过滤，抽到不合格的就换一条。
"""
import os

import extract_snippets as E
from resolve_paths import resolve, AP


def usable(row):
    """返回 (是否可用, 原因)。"""
    path = resolve(row['file_path'], row['project'])
    if not path:
        return False, 'path-unresolved'
    if not E.method(path, row['test_name']):
        return False, 'test-not-found'
    ann = E.annotation_of(path, row['test_name'])
    src = row.get('source') or row.get('_source')   # 抽样阶段用 _source，成品表用 source
    root = os.path.join(AP, path[len(AP) + 1:].split('/')[0])

    if src == 'MethodSource':
        names = E.provider_names(ann)
        if not names:
            return False, 'no-provider-ref'
        for nm in names:
            cls, _, meth = nm.rpartition('#')
            if cls:
                hits = E.find_type(root, cls.split('.')[-1], decl_kw='class|interface|enum')
                if hits and E.method(hits[0], meth):
                    return True, 'ok'
            if E.method(path, meth):
                return True, 'ok'
            for fp in E.find_method_file(root, meth):
                if E.method(fp, meth):
                    return True, 'ok'
        return False, 'provider-missing'

    if src == 'EnumSource':
        types = E.enum_types(ann) or E.param_types(path, row['test_name'])
        if not types:
            return False, 'enum-type-unknown'
        for t in types:
            for h in E.find_type(root, t, decl_kw='enum')[:2]:
                if E.enum_decl(h, t):
                    return True, 'ok'
        return False, 'enum-decl-missing'

    # ValueSource / CsvSource：取值就在注解里，注解抽到了即可
    tag = '@ValueSource' if src == 'ValueSource' else '@CsvSource'
    return (True, 'ok') if tag in ann else (False, 'annotation-missing')
