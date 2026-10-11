#!/usr/bin/env python3
"""PDAR v4 第二阶段批处理：逐个项目 bare clone 全量 → pdar_v4_method_level.py → 立刻删除。

  - 仓库 URL 唯一来源：pdar_repo_map.csv
  - 项目清单默认 = rq1_bins.load(adopters_only=True)（107 个采纳者）
  - 已有 `{project}_method_summary.json` 的项目跳过（可断点续跑）
  - 每个项目的分析在独立子进程里跑，日志写到 result_v4/logs/{project}.log
  - 分析失败不删 clone 以外的任何东西；clone 无论成败都删
  - 本地找到的已发表提交比例 < 95% 的项目照常出结果，但汇总时会被标记，需人工确认
  - `--with-stage1`：在同一个 clone 上先跑第一阶段（pdar_v4_commit_table.py），把逐提交表
    写到 PT_PDAR_RESULT，再跑第二阶段。**会得到新快照**，与论文数字不可比；论文那一轮的
    第一阶段输出就是 result_v3/，复现论文数字时不要加这个开关

用法：
    python batch_pdar_v4.py [--projects list.txt] [--jobs 3] [--work D:\\pt\\pdar_work]
                                [--fullscan Commons-IO,Rat] [--no-pickaxe]
"""

# 向上找到 final/（paths.py 所在处）并加入 sys.path —— 不依赖本文件在目录树里的深度
import os as _os_root, sys as _sys_root
_root = _os_root.path.dirname(_os_root.path.abspath(__file__))
while not _os_root.path.exists(_os_root.path.join(_root, 'paths.py')):
    _root = _os_root.path.dirname(_root)
_sys_root.path.insert(0, _root)

import argparse
import csv
import os
import shutil
import stat
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from pdar_v4_method_level import OUT_DIR  # noqa: E402

DEFAULT_WORK = os.environ.get('PT_PDAR_WORK_METHOD', r'D:\pt\pdar_work' if os.name == 'nt' else '/tmp/pdar_work')


def load_map():
    with open(os.path.join(HERE, 'pdar_repo_map.csv'), newline='', encoding='utf-8') as f:
        return {r['project']: r for r in csv.DictReader(f)}


def rmtree(path):
    def onerr(func, p, _):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    for _ in range(3):
        if not os.path.exists(path):
            return
        try:
            shutil.rmtree(path, onerror=onerr)
        except OSError:
            time.sleep(5)


def run_one(project, url, work, out_dir, fullscan, no_pickaxe, with_stage1=False):
    log_dir = os.path.join(out_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log = open(os.path.join(log_dir, f'{project}.log'), 'a', encoding='utf-8')
    dest = os.path.join(work, project + '.git')
    t0 = time.time()
    try:
        rmtree(dest)
        for attempt in range(3):
            log.write(f'[{time.ctime()}] clone {url} (attempt {attempt + 1})\n'); log.flush()
            p = subprocess.run(['git', 'clone', '--quiet', '--bare', url, dest],
                               stdout=log, stderr=log)
            if p.returncode == 0 and os.path.isdir(os.path.join(dest, 'objects')):
                break
            rmtree(dest)
            time.sleep(30)
        else:
            return project, 'clone_failed', time.time() - t0
        t_clone = time.time() - t0
        if with_stage1:
            from paths import PDAR_RESULT
            log.write(f'[{time.ctime()}] stage 1 -> {PDAR_RESULT}\n'); log.flush()
            p = subprocess.run([sys.executable, os.path.join(HERE, 'pdar_v4_commit_table.py'), project,
                                '--repo', dest, '--out', PDAR_RESULT], stdout=log, stderr=log)
            if p.returncode != 0:
                return project, f'stage1_failed_rc{p.returncode}', time.time() - t0
        cmd = [sys.executable, os.path.join(HERE, 'pdar_v4_method_level.py'), project,
               '--repo', dest, '--out', out_dir]
        if fullscan:
            cmd.append('--fullscan')
        if no_pickaxe:
            cmd.append('--no-pickaxe')
        log.write(f'[{time.ctime()}] clone done in {t_clone:.0f}s; analyze\n'); log.flush()
        p = subprocess.run(cmd, stdout=log, stderr=log)
        status = 'ok' if p.returncode == 0 else f'analyze_failed_rc{p.returncode}'
        return project, status, time.time() - t0
    finally:
        rmtree(dest)
        log.write(f'[{time.ctime()}] removed clone\n')
        log.close()


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--projects', help='每行一个项目名；缺省为 107 个采纳者')
    ap.add_argument('--jobs', type=int, default=3)
    ap.add_argument('--work', default=DEFAULT_WORK)
    ap.add_argument('--out', default=OUT_DIR)
    ap.add_argument('--fullscan', default='', help='逗号分隔：这些项目关掉路径过滤并逐提交比对')
    ap.add_argument('--no-pickaxe', action='store_true')
    ap.add_argument('--with-stage1', action='store_true', help='先跑第一阶段（新快照，与论文不可比）')
    a = ap.parse_args()

    if a.projects:
        with open(a.projects, encoding='utf-8') as f:
            projects = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    else:
        import rq1_bins
        projects = sorted(rq1_bins.load(adopters_only=True)['project'])
    repo_map = load_map()
    unknown = [p for p in projects if p not in repo_map]
    if unknown:
        raise SystemExit(f'pdar_repo_map.csv 里没有：{unknown}')
    full = set(x for x in a.fullscan.split(',') if x)

    todo = [p for p in projects
            if not os.path.exists(os.path.join(a.out, f'{p}_method_summary.json'))]
    print(f'{len(projects)} 个项目，{len(projects) - len(todo)} 个已完成，待跑 {len(todo)} 个；'
          f'工作区 {a.work}，并发 {a.jobs}', flush=True)
    os.makedirs(a.work, exist_ok=True)

    results = []
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(run_one, p, repo_map[p]['git_url'], a.work, a.out, p in full,
                          a.no_pickaxe, a.with_stage1): p for p in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            p, status, secs = fut.result()
            results.append((p, status))
            print(f'[{i}/{len(todo)}] {p:28} {status:22} {secs / 60:6.1f} min', flush=True)

    bad = [(p, s) for p, s in results if s != 'ok']
    print(f'\n完成。失败 {len(bad)} 个：{bad}')


if __name__ == '__main__':
    main()
