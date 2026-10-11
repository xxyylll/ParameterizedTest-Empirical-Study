#!/usr/bin/env python3
"""把手工编码表里的 file_path 还原成外置盘上的真实路径。

编码时记录的路径有两种，现在都失效了：
  /Users/.../temp_project/<项目内相对路径>   —— 临时检出目录，早已删除
  /Volumes/SSK Drive/apache-projects/...     —— 旧挂载名，现为 /Volumes/SSKSSD
两者都能还原：`project` 列给出项目名，`temp_project/` 之后是项目内相对路径。
项目名到目录名多数可由归一化匹配，少数几个是历史别名，列在 ALIAS 里。
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)
import sys as _sys, os as _os
import os
import re

_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
from paths import APACHE_PROJECTS as AP  # noqa: E402
ALIAS = {
    'log4j': 'logging-log4j2',
    'rat': 'creadur-rat',
    'james': 'james-project',
    'qpid': 'qpid-broker-j',
    'commonshttpclient': 'httpcomponents-client',
    'httpcomponentsclient': 'httpcomponents-client',
    'httpcomponentscore': 'httpcomponents-core',
}
_norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())


def _index():
    avail = os.listdir(AP)
    idx = {_norm(p): p for p in avail}
    for k, v in ALIAS.items():
        if v in avail:
            idx[k] = v
    return idx


_IDX = None


def resolve(file_path, project):
    """返回真实路径，解析不出来返回 None。"""
    global _IDX
    if _IDX is None:
        _IDX = _index()
    if '/apache-projects/' in file_path:
        cand = os.path.join(AP, file_path.split('/apache-projects/', 1)[1])
        return cand if os.path.exists(cand) else None
    if '/temp_project/' in file_path:
        rel = file_path.split('/temp_project/', 1)[1]
        d = _IDX.get(_norm(project))
        if not d:
            return None
        cand = os.path.join(AP, d, rel)
        return cand if os.path.exists(cand) else None
    return None


if __name__ == '__main__':
    import csv
    rows = list(csv.DictReader(open('sample_items.csv')))
    ok = [r for r in rows if resolve(r['file_path'], r['project'])]
    print(f'可解析 {len(ok)}/{len(rows)}')
    for r in rows:
        if not resolve(r['file_path'], r['project']):
            print(f"   未解析 [{r['project']}] {r['file_path'][-80:]}")
