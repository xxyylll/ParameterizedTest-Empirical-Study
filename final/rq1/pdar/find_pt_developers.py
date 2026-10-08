#!/usr/bin/env python3
"""
PT Developer Finder v3 - Three-Layer Detection

Layer 1 (JUnit5 Hunk Detection):
   - Search for @ParameterizedTest in diff
   - Check if there are +/- lines AFTER @ParameterizedTest within the same hunk
   - If yes → modifiedPT = 1

Layer 2 (JUnit4 File Detection):
   - If Layer 1 didn't match
   - Extract modified .java files from diff
   - Use `git show commit:file` to check if file contains @RunWith(Parameterized
   - If yes → modifiedPT = 1

Layer 3 (Pickaxe Detection - Core Developers):
   - If Layer 1 and 2 didn't match
   - Check if this commit is in git log -G results (add/delete PT keywords)
   - If yes → modifiedPT = 1, is_core = 1

Output:
   - {project}_commits.csv: All commits with modifiedPT, is_core flags
   - {project}_developer_summary.csv: Aggregated by author email

Diff 上下文（--context，默认 3）:
   Layer 1 是在 diff 文本上做的：它找到 @ParameterizedTest 所在行，再看周围有没有
   +/- 行。因此**能看到多少周围代码，完全由 git 的上下文行数决定**。
   git diff-tree 默认给 3 行上下文，于是：同一个 PT 方法内部的改动，只要离
   @ParameterizedTest 注解超过 3 行，就不会与注解出现在同一个 hunk 里 ——
   Layer 1 看不到它，该提交只能靠 Layer 2/3 兜。结果是 PDAR **系统性偏低**。
   论文报告的数字用的是默认 3（即 --context 3）。
   用 --context N 可改为 N 行以评估这一口径的敏感性；见 README 的敏感性分析。

Usage:
    python find_pt_developers.py <project_name> [--context N] [--repo PATH]
"""

import csv
import re
import subprocess
import sys
import os
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Set, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from paths import PDAR_WORK, PDAR_RESULT, APACHE_PROJECTS, PT_PROJECTS_LIST  # noqa: E402


# ============== Configuration ==============

# JUnit5 pattern
JUNIT5_PT_PATTERN = re.compile(r'@ParameterizedTest')

# JUnit4 pattern
JUNIT4_PT_PATTERN = re.compile(r'@RunWith\s*\(\s*Parameterized')


# ============== Helper Functions ==============

def run_git_command(cmd: List[str], cwd: str, timeout: int = 300) -> Tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors='replace'
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'Timeout'
    except Exception as e:
        return -1, '', str(e)


def get_all_commits_with_info(project_path: str) -> List[Dict]:
    """Get all commits with author info"""
    cmd = ['git', 'log', '--all', '--format=%H|%an|%ae|%ad|%s', '--date=iso']
    code, stdout, stderr = run_git_command(cmd, project_path)
    if code != 0:
        return []
    
    commits = []
    for line in stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('|', 4)
        if len(parts) >= 5:
            commits.append({
                'commit_hash': parts[0],
                'author_name': parts[1],
                'author_email': parts[2],
                'date': parts[3],
                'subject': parts[4]
            })
    return commits


def get_commit_diff(project_path: str, commit: str, context: int = 3) -> str:
    """Get the diff of a commit (comparing to its parent).

    `context` = git 的上下文行数（-U）。默认 3 即 git 自身的默认值，也是论文
    报告数字所用的口径。Layer 1 只能看到 hunk 内的行，所以这个值直接决定
    它的召回率 —— 调大它会让更多「离注解较远但仍在同一 PT 内」的改动被看到。
    """
    cmd = ['git', 'diff-tree', '-p', f'-U{context}', commit]
    code, stdout, stderr = run_git_command(cmd, project_path, timeout=60)
    if code != 0:
        return ''
    return stdout


def get_modified_java_files_from_diff(diff: str) -> List[str]:
    """Extract list of modified .java files from diff"""
    files = []
    # Pattern: diff --git a/path/to/File.java b/path/to/File.java
    for line in diff.split('\n'):
        if line.startswith('diff --git'):
            # Extract b/ path (the new file path)
            match = re.search(r'b/(.+\.java)$', line)
            if match:
                files.append(match.group(1))
    return files


def check_touched_test(diff: str) -> bool:
    """
    Check if a commit touched test code.
    
    Criteria (any of the following):
    1. Path contains test-related patterns:
       - src/test/, /test/, tests/
       - Filename: *Test.java, *Tests.java, *TestCase.java, Test*.java
    2. Content contains test annotations:
       - @Test
       - import org.junit
       - import org.testng
    """
    lines = diff.split('\n')
    
    for line in lines:
        # Check file paths from diff headers
        if line.startswith('diff --git'):
            # Path-based check
            path_lower = line.lower()
            if '/test/' in path_lower or '/tests/' in path_lower or 'src/test/' in path_lower:
                return True
            # Filename-based check
            match = re.search(r'b/(.+\.java)$', line)
            if match:
                filename = match.group(1).split('/')[-1]
                if (filename.endswith('Test.java') or 
                    filename.endswith('Tests.java') or 
                    filename.endswith('TestCase.java') or
                    filename.startswith('Test')):
                    return True
        
        # Content-based check (only on actual lines, not diff headers)
        elif not line.startswith('+++') and not line.startswith('---'):
            if '@Test' in line:
                return True
            if 'import org.junit' in line or 'import org.testng' in line:
                return True
    
    return False


def check_junit5_in_diff(diff: str) -> bool:
    """
    Layer 1: Check if @ParameterizedTest appears in diff with modifications around it.
    
    Logic:
    - Find @ParameterizedTest in the diff
    - Check one line BEFORE (might have @MethodSource, @ValueSource etc. being modified)
    - Check lines AFTER until the next test method or hunk
    - Stop at: @Test, @ParameterizedTest (new test), @@ (new hunk), diff --git (new file)
    - Note: void is part of method signature, NOT a stop condition
    """
    lines = diff.split('\n')
    
    for i, line in enumerate(lines):
        # Skip diff header lines
        if line.startswith('+++') or line.startswith('---'):
            continue
            
        # Check if this line contains @ParameterizedTest
        if JUNIT5_PT_PATTERN.search(line):
            # Check one line BEFORE (might have @MethodSource, @ValueSource etc.)
            if i > 0:
                prev_line = lines[i - 1]
                # Skip diff headers
                if not prev_line.startswith('+++') and not prev_line.startswith('---'):
                    if prev_line.startswith('+') or prev_line.startswith('-'):
                        return True
            
            # Look for +/- lines AFTER until the next test method
            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                
                # Strip the +/- prefix for content checking
                content = next_line[1:] if next_line.startswith(('+', '-')) and not next_line.startswith(('+++', '---')) else next_line
                
                # New hunk or new file = end of current hunk
                if next_line.startswith('@@') or next_line.startswith('diff --git'):
                    break
                
                # Another test annotation = new test method starts
                # Only stop at @Test or @ParameterizedTest (not void, as it's part of method signature)
                if re.search(r'^\s*@(Test|ParameterizedTest)\b', content):
                    break
                
                # Found a modification within this PT method
                if next_line.startswith('+') and not next_line.startswith('+++'):
                    return True
                if next_line.startswith('-') and not next_line.startswith('---'):
                    return True
    
    return False


def get_file_content_at_commit(project_path: str, commit: str, filepath: str) -> Optional[str]:
    """Get file content at a specific commit using git show"""
    cmd = ['git', 'show', f'{commit}:{filepath}']
    code, stdout, stderr = run_git_command(cmd, project_path, timeout=30)
    if code != 0:
        # File might not exist at this commit (deleted or not yet created)
        # Try parent commit for deleted files
        cmd = ['git', 'show', f'{commit}^:{filepath}']
        code, stdout, stderr = run_git_command(cmd, project_path, timeout=30)
        if code != 0:
            return None
    return stdout


def check_junit4_in_diff(diff: str, project_path: str, commit: str) -> bool:
    """
    Layer 2: Check if any modified .java file is a JUnit4 parameterized test.
    
    Logic:
    - Get list of modified .java files from diff
    - For each file, check if it contains @RunWith(Parameterized
    """
    java_files = get_modified_java_files_from_diff(diff)
    
    for filepath in java_files:
        content = get_file_content_at_commit(project_path, commit, filepath)
        if content and JUNIT4_PT_PATTERN.search(content):
            return True
    
    return False


def get_pickaxe_commits(project_path: str) -> Set[str]:
    """
    Layer 3: Use git log -G to find commits that add/delete PT annotations.
    These are core developers.
    """
    commits = set()
    
    # JUnit5 - use longer timeout for large repos
    cmd = ['git', 'log', '--all', '-G', '@ParameterizedTest', '--format=%H']
    code, stdout, stderr = run_git_command(cmd, project_path, timeout=600)
    if code == 0:
        for line in stdout.strip().split('\n'):
            if line.strip():
                commits.add(line.strip())
    else:
        print(f"    [Warning] JUnit5 pickaxe failed or timed out: {stderr[:100]}")
    
    # JUnit4 - use longer timeout for large repos
    cmd = ['git', 'log', '--all', '-G', 'RunWith.*Parameterized', '--format=%H']
    code, stdout, stderr = run_git_command(cmd, project_path, timeout=600)
    if code == 0:
        for line in stdout.strip().split('\n'):
            if line.strip():
                commits.add(line.strip())
    else:
        print(f"    [Warning] JUnit4 pickaxe failed or timed out: {stderr[:100]}")
    
    return commits


def load_repo_mapping() -> Dict[str, Dict[str, str]]:
    """读 pdar_repo_map.csv：{项目显示名: {'repo':..., 'git_url':...}}。

    **这份 CSV 是 PDAR 的唯一仓库名来源。** 原先有两套互相冲突的来源：
      - `projects.txt`，用 `url.rstrip('.git')` 解析 —— 这是个 bug：`rstrip`
        剥的是**字符集合** {'.','g','i','t'} 而不是字面后缀，于是
        `ambari`→`ambar`、`pig`→`p`、`poi`→`po`、`thrift`→`thrif`，42 个项目的
        名字被剥坏。它只影响「定位仓库」这一步，定位失败直接退出，
        不会去分析错的仓库，所以已发表的数字未受污染 —— 但必须修。
      - `asf_domain_mapping.csv` 的 `matched_machine` 列，含明显错配
        （Commons-Chain / Commons-HttpClient / Commons-OGNL 三个不同项目
        全都映射到 `commons-weaver`），且对已退休项目给的是 `attic-*` 镜像名。
    本表取 `projects.txt` 的实际 clone URL（它给的是真正含 Java 代码的子仓库，
    如 `logging-log4j2`、`qpid-broker-j`、`uima-uimaj`），并补齐它缺的三项。
    """
    mapping: Dict[str, Dict[str, str]] = {}
    map_csv = Path(__file__).parent / 'pdar_repo_map.csv'
    if not map_csv.exists():
        return mapping
    with open(map_csv, newline='') as f:
        for row in csv.DictReader(f):
            mapping[row['project']] = {'repo': row['repo'], 'git_url': row['git_url']}
    return mapping


def resolve_repo(project_name: str, explicit: Optional[str] = None) -> str:
    """定位该项目的**全量**克隆。

    必须是全量克隆：`git log --all` 与 `git diff-tree` 在 `--depth 1` 的浅克隆上
    只能看到 1 个提交，PDAR 会算成 0。PT_SSD/apache-projects 里的就是浅克隆
    （本研究其余部分不需要历史），所以默认只在 PDAR_WORK 下找，
    并显式检查 shallow 标记后再继续。
    """
    if explicit:
        candidates = [explicit]
    else:
        entry = load_repo_mapping().get(project_name)
        repo_name = entry['repo'] if entry else project_name.lower()
        candidates = [os.path.join(PDAR_WORK, project_name),
                      os.path.join(PDAR_WORK, repo_name),
                      os.path.join(APACHE_PROJECTS, repo_name)]

    for path in candidates:
        if os.path.isdir(os.path.join(path, '.git')):
            if os.path.exists(os.path.join(path, '.git', 'shallow')):
                print(f"Error: {path} 是浅克隆（存在 .git/shallow）。")
                print("  PDAR 需要全量历史。请用 batch_pdar.sh，它会 clone 全量、分析、再删除。")
                sys.exit(2)
            return path

    print(f"Error: 找不到 {project_name} 的全量克隆。试过：")
    for c in candidates:
        print(f"  {c}")
    print(f"\n  用 PT_PDAR_WORK 指定工作区，或 --repo 直接给路径。")
    print(f"  batch_pdar.sh 会按 clone → 分析 → 删除 的方式自动处理整张清单。")
    sys.exit(2)


def main():
    import argparse
    ap = argparse.ArgumentParser(description='PDAR 的逐项目提交级检测（三层）')
    ap.add_argument('project_name')
    ap.add_argument('--context', type=int, default=3,
                    help='git diff 的上下文行数（-U）。默认 3 = git 默认值 = 论文口径。'
                         '调大可评估 Layer 1 的漏检，见 README 敏感性分析')
    ap.add_argument('--repo', default=None, help='直接指定全量克隆的路径')
    ap.add_argument('--out', default=None, help='输出目录，默认 PT_PDAR_RESULT')
    args = ap.parse_args()

    project_name = args.project_name
    context = args.context
    project_path = resolve_repo(project_name, args.repo)

    print(f"{'='*60}")
    print(f"PT Developer Finder - {project_name}")
    print(f"{'='*60}")
    print(f"Project path   : {project_path}")
    print(f"Diff context   : -U{context}" + ("  (论文口径)" if context == 3 else "  (非默认，敏感性分析)"))
    print()

    # 输出目录：非默认上下文单独放，避免覆盖论文口径的结果
    result_dir = Path(args.out) if args.out else Path(PDAR_RESULT)
    if context != 3:
        result_dir = result_dir.parent / f'{result_dir.name}_U{context}'
    result_dir.mkdir(parents=True, exist_ok=True)
    
    # ==================== Pre-compute Pickaxe commits ====================
    print("Pre-computing pickaxe commits (git log -G)...")
    pickaxe_commits = get_pickaxe_commits(project_path)
    print(f"  Found {len(pickaxe_commits)} pickaxe commits (core developers)")
    
    # ==================== Process all commits ====================
    print("\nProcessing all commits with 3-layer detection...")
    
    all_commits = get_all_commits_with_info(project_path)
    print(f"  Total commits: {len(all_commits)}")
    
    commit_data = []
    stats = {
        'layer1_junit5': 0,
        'layer2_junit4': 0,
        'layer3_pickaxe': 0,
        'not_pt': 0
    }
    
    for i, commit_info in enumerate(all_commits):
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1}/{len(all_commits)} commits...")
        
        commit_hash = commit_info['commit_hash']
        modified_pt = 0
        is_core = 0
        detection_layer = ''
        
        # Get diff for this commit
        diff = get_commit_diff(project_path, commit_hash, context)
        
        # Check if this commit touched test code
        touched_test = 1 if check_touched_test(diff) else 0
        
        # Layer 1: JUnit5 hunk detection
        if check_junit5_in_diff(diff):
            modified_pt = 1
            detection_layer = 'junit5_hunk'
            stats['layer1_junit5'] += 1
        
        # Layer 2: JUnit4 file detection
        elif check_junit4_in_diff(diff, project_path, commit_hash):
            modified_pt = 1
            detection_layer = 'junit4_file'
            stats['layer2_junit4'] += 1
        
        # Layer 3: Pickaxe detection
        elif commit_hash in pickaxe_commits:
            modified_pt = 1
            is_core = 1
            detection_layer = 'pickaxe'
            stats['layer3_pickaxe'] += 1
        
        else:
            stats['not_pt'] += 1
        
        # If detected by layer 1 or 2, check if also in pickaxe (core)
        if modified_pt == 1 and detection_layer != 'pickaxe':
            if commit_hash in pickaxe_commits:
                is_core = 1
        
        commit_data.append({
            'commit_hash': commit_hash,
            'author_name': commit_info['author_name'],
            'author_email': commit_info['author_email'],
            'date': commit_info['date'],
            'touched_test': touched_test,
            'modifiedPT': modified_pt,
            'is_core': is_core,
            'detection_layer': detection_layer
        })
    
    # ==================== Save commits CSV ====================
    commits_csv = result_dir / f'{project_name}_commits.csv'
    with open(commits_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['commit_hash', 'author_name', 'author_email', 'date',
                      'touched_test', 'modifiedPT', 'is_core', 'detection_layer']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(commit_data)
    
    print(f"\n  Detection statistics:")
    print(f"    Layer 1 (JUnit5 hunk): {stats['layer1_junit5']}")
    print(f"    Layer 2 (JUnit4 file): {stats['layer2_junit4']}")
    print(f"    Layer 3 (Pickaxe only): {stats['layer3_pickaxe']}")
    print(f"    Not PT related: {stats['not_pt']}")
    print(f"  Saved to: {commits_csv}")
    
    # ==================== Aggregate by Author ====================
    print("\nAggregating by author (email)...")
    
    developers = defaultdict(lambda: {
        'name': '',
        'pt_commits': 0,
        'core_commits': 0,
        'total_commits': 0,
        'first_pt_date': '',
        'last_pt_date': ''
    })
    
    for row in commit_data:
        email = row['author_email']
        developers[email]['name'] = row['author_name']
        developers[email]['total_commits'] += 1
        
        if row['modifiedPT'] == 1:
            developers[email]['pt_commits'] += 1
            
            # Track first/last PT date
            date = row['date']
            if not developers[email]['first_pt_date'] or date < developers[email]['first_pt_date']:
                developers[email]['first_pt_date'] = date
            if not developers[email]['last_pt_date'] or date > developers[email]['last_pt_date']:
                developers[email]['last_pt_date'] = date
        
        if row['is_core'] == 1:
            developers[email]['core_commits'] += 1
    
    # Filter to only PT participants
    pt_participants = {email: info for email, info in developers.items() if info['pt_commits'] > 0}
    core_developers = {email: info for email, info in developers.items() if info['core_commits'] > 0}
    
    # Save developer summary
    summary_data = []
    for email, info in sorted(pt_participants.items(), key=lambda x: -x[1]['pt_commits']):
        summary_data.append({
            'author_email': email,
            'author_name': info['name'],
            'pt_commits': info['pt_commits'],
            'core_commits': info['core_commits'],
            'total_commits': info['total_commits'],
            'is_core_developer': 1 if info['core_commits'] > 0 else 0,
            'first_pt_date': info['first_pt_date'],
            'last_pt_date': info['last_pt_date']
        })
    
    summary_csv = result_dir / f'{project_name}_developer_summary.csv'
    with open(summary_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['author_email', 'author_name', 'pt_commits', 'core_commits',
                      'total_commits', 'is_core_developer', 'first_pt_date', 'last_pt_date']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_data)
    
    print(f"  Saved to: {summary_csv}")
    
    # ==================== Summary ====================
    total_pt_commits = sum(1 for c in commit_data if c['modifiedPT'] == 1)
    
    print(f"\n{'='*60}")
    print(f"Summary for {project_name}")
    print(f"{'='*60}")
    print(f"  Total commits: {len(all_commits)}")
    print(f"  PT-related commits: {total_pt_commits}")
    print(f"  Total developers: {len(developers)}")
    print(f"  PT participants: {len(pt_participants)}")
    print(f"  Core developers (add/delete PT): {len(core_developers)}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
