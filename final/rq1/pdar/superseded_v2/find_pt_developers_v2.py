#!/usr/bin/env python3
"""
PT Developer Finder v2

New logic:
1. Global Scan: Use git log -G to discover all PTs (existing + deleted), 
   tracking Add/Delete events by analyzing +/- in diffs
2. Back-tracking: For each PT lifecycle [Add_Commit, Delete_Commit/HEAD],
   use slide window to find all contributors
3. For JUnit 5: When method name disappears, use RefactoringMiner to detect renames
4. For JUnit 4: git log --follow handles file renames, check @RunWith in snapshots

Usage:
    python find_pt_developers_v2.py <project_name>
"""

import csv
import re
import subprocess
import sys
import os
import json
import tempfile
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime


# ============== Configuration ==============

REFACTORING_MINER_PATH = '/Users/immortal/RefactoringMiner-3.0.13/bin/RefactoringMiner'
JAVA_HOME = '/opt/homebrew/Cellar/openjdk@21/21.0.10/libexec/openjdk.jdk/Contents/Home'
PARSER_RESULT_DIR = Path(__file__).parent.parent / 'parser_result'


# ============== Data Classes ==============

@dataclass
class PTLifecycle:
    """Represents the lifecycle of a PT (from add to delete/HEAD)"""
    file_path: str
    method_name: str  # For JUnit5, method name; For JUnit4, class name or empty
    pt_type: str  # 'junit5' or 'junit4'
    add_commit: str
    delete_commit: Optional[str]  # None if still exists
    is_deleted: bool
    
    def __hash__(self):
        return hash((self.file_path, self.method_name, self.pt_type))


@dataclass
class DeveloperContribution:
    """A developer's contribution to a PT"""
    author_name: str
    author_email: str
    commit_hash: str
    commit_date: str
    file_path: str
    method_name: str
    change_type: str  # 'create', 'modify', 'delete'


@dataclass 
class RefactoringResult:
    """Result from RefactoringMiner"""
    old_method_name: str
    new_method_name: str
    file_path: str
    commit_hash: str


# ============== Git Utilities ==============

def run_git_command(cmd: List[str], cwd: str, timeout: int = 120) -> Tuple[int, str, str]:
    """Run git command and return (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'Timeout'
    except Exception as e:
        return -1, '', str(e)


def get_file_at_commit(project_path: str, commit: str, file_path: str) -> Optional[str]:
    """Get file content at a specific commit"""
    cmd = ['git', 'show', f'{commit}:{file_path}']
    code, stdout, stderr = run_git_command(cmd, project_path)
    if code != 0:
        return None
    return stdout


def get_commit_info(project_path: str, commit_hash: str) -> Optional[dict]:
    """Get commit info (author, date, message)"""
    cmd = ['git', 'log', '-1', '--format=%an|%ae|%ad|%s', '--date=iso', commit_hash]
    code, stdout, stderr = run_git_command(cmd, project_path)
    if code != 0 or not stdout.strip():
        return None
    parts = stdout.strip().split('|', 3)
    if len(parts) >= 4:
        return {
            'author_name': parts[0],
            'author_email': parts[1],
            'date': parts[2],
            'message': parts[3][:200]
        }
    return None


def get_file_commits_in_range(project_path: str, file_path: str, 
                               start_commit: str, end_commit: Optional[str]) -> List[str]:
    """
    Get all commits for a file between start_commit and end_commit (inclusive).
    Uses git log --follow to handle file renames.
    Returns commits in reverse chronological order (newest first).
    """
    if end_commit:
        # Range from start to end
        cmd = ['git', 'log', '--follow', '--format=%H', f'{start_commit}^..{end_commit}', '--', file_path]
    else:
        # From start to HEAD
        cmd = ['git', 'log', '--follow', '--format=%H', f'{start_commit}^..HEAD', '--', file_path]
    
    code, stdout, stderr = run_git_command(cmd, project_path)
    
    if code != 0:
        # Fallback: try without the range syntax
        cmd = ['git', 'log', '--follow', '--format=%H', '--', file_path]
        code, stdout, stderr = run_git_command(cmd, project_path)
        if code != 0:
            return []
        
        # Filter commits manually
        all_commits = [c.strip() for c in stdout.strip().split('\n') if c.strip()]
        
        # Find indices
        try:
            start_idx = all_commits.index(start_commit)
            if end_commit:
                end_idx = all_commits.index(end_commit)
                return all_commits[end_idx:start_idx+1]
            else:
                return all_commits[:start_idx+1]
        except ValueError:
            return all_commits
    
    commits = [c.strip() for c in stdout.strip().split('\n') if c.strip()]
    return commits


def get_diff_for_commit(project_path: str, commit: str, file_path: str) -> str:
    """Get the diff for a specific commit and file"""
    cmd = ['git', 'show', '-U0', '--format=', commit, '--', file_path]
    code, stdout, stderr = run_git_command(cmd, project_path)
    if code != 0:
        return ''
    return stdout


def get_diff_hunks(project_path: str, parent_commit: str, commit: str, 
                   file_path: str) -> List[Tuple[int, int, int, int]]:
    """
    Get diff hunks between parent and commit for a file.
    Returns list of (old_start, old_count, new_start, new_count)
    """
    cmd = ['git', 'diff', '-U0', parent_commit, commit, '--', file_path]
    code, stdout, stderr = run_git_command(cmd, project_path)
    
    if code != 0:
        return []
    
    hunks = []
    hunk_pattern = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
    
    for line in stdout.split('\n'):
        match = hunk_pattern.match(line)
        if match:
            old_start = int(match.group(1))
            old_count = int(match.group(2)) if match.group(2) else 1
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) else 1
            hunks.append((old_start, old_count, new_start, new_count))
    
    return hunks


# ============== Phase 1: Global Scan ==============

def scan_pt_events_with_git_log_g(project_path: str, search_pattern: str, literal_pattern: str = None) -> Dict[str, List[Tuple[str, str, str]]]:
    """
    Use git log -G to find all commits that add/remove the annotation.
    Returns: {file_path: [(commit_hash, '+' or '-', context), ...]}
    
    Args:
        search_pattern: Pattern for git log -G (regex)
        literal_pattern: Literal text to match in diff (defaults to search_pattern)
    
    Context is for JUnit5: the method name found near the annotation
    For JUnit4: empty string (class-level)
    """
    if literal_pattern is None:
        literal_pattern = search_pattern
        
    cmd = ['git', 'log', '-G', search_pattern, '--all', '--format=%H', '--name-only', '--', '*.java']
    code, stdout, stderr = run_git_command(cmd, project_path, timeout=300)
    
    if code != 0:
        print(f"Warning: git log -G failed: {stderr}")
        return {}
    
    # Parse output: commit hash followed by file paths
    events = defaultdict(list)
    current_commit = None
    
    lines = stdout.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # Check if it's a commit hash (40 hex chars)
        if len(line) == 40 and all(c in '0123456789abcdef' for c in line):
            current_commit = line
            i += 1
            continue
        
        # Otherwise it's a file path
        if current_commit and line.endswith('.java'):
            file_path = line
            # Get the diff to determine if it's + or -
            diff = get_diff_for_commit(project_path, current_commit, file_path)
            
            # Parse diff for +annotation or -annotation (use literal_pattern for matching)
            for diff_line in diff.split('\n'):
                if literal_pattern in diff_line:
                    if diff_line.startswith('+') and not diff_line.startswith('+++'):
                        event_type = '+'
                        # Try to find method name for JUnit5 (with fallback to full file)
                        method_name = extract_method_name_with_fallback(
                            project_path, current_commit, file_path, diff, literal_pattern, '+')
                        events[file_path].append((current_commit, event_type, method_name))
                    elif diff_line.startswith('-') and not diff_line.startswith('---'):
                        event_type = '-'
                        method_name = extract_method_name_with_fallback(
                            project_path, current_commit, file_path, diff, literal_pattern, '-')
                        events[file_path].append((current_commit, event_type, method_name))
        i += 1
    
    return dict(events)


def extract_method_name_from_diff(diff: str, annotation: str, event_type: str) -> str:
    """
    Extract method name from diff content near the annotation.
    For @ParameterizedTest, look for method declaration after the annotation.
    Returns empty string for JUnit4 (class-level).
    """
    # JUnit4 is class-level, no method name to extract
    if '@RunWith(Parameterized' in annotation or 'RunWith' in annotation:
        return ''
    
    lines = diff.split('\n')
    prefix = '+' if event_type == '+' else '-'
    
    for i, line in enumerate(lines):
        if line.startswith(prefix) and annotation in line:
            # Look for method declaration in next few lines
            for j in range(i + 1, min(i + 15, len(lines))):
                next_line = lines[j]
                # Skip other annotations and empty lines
                if next_line.startswith(prefix):
                    content = next_line[1:].strip()
                    if content.startswith('@') or not content:
                        continue
                    # Look for method declaration pattern
                    match = re.search(r'(?:void|public|private|protected|static|\w+)\s+(\w+)\s*\(', content)
                    if match:
                        return match.group(1)
    return ''


def get_line_number_from_diff(diff: str, annotation: str, event_type: str) -> Optional[int]:
    """
    Extract the line number where the annotation appears from diff hunk headers.
    Returns the line number in the file (new_start for '+', old_start for '-').
    """
    lines = diff.split('\n')
    prefix = '+' if event_type == '+' else '-'
    hunk_pattern = re.compile(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@')
    
    current_old_line = 0
    current_new_line = 0
    
    for line in lines:
        # Check for hunk header
        hunk_match = hunk_pattern.match(line)
        if hunk_match:
            current_old_line = int(hunk_match.group(1))
            current_new_line = int(hunk_match.group(2))
            continue
        
        # Track line numbers within hunk
        if line.startswith('+') and not line.startswith('+++'):
            if annotation in line and event_type == '+':
                return current_new_line
            current_new_line += 1
        elif line.startswith('-') and not line.startswith('---'):
            if annotation in line and event_type == '-':
                return current_old_line
            current_old_line += 1
        elif not line.startswith('\\'):  # context line (not \ No newline at end)
            current_old_line += 1
            current_new_line += 1
    
    return None


def extract_method_name_from_file_content(content: str, annotation_line: int, annotation: str) -> str:
    """
    Extract method name from file content starting at the annotation line.
    Searches downward from the annotation to find the method declaration.
    """
    if not content:
        return ''
    
    lines = content.split('\n')
    if annotation_line < 1 or annotation_line > len(lines):
        return ''
    
    # Search from annotation_line downward (up to 15 lines)
    for i in range(annotation_line - 1, min(annotation_line + 14, len(lines))):
        line = lines[i].strip()
        # Skip annotations and empty lines
        if line.startswith('@') or not line:
            continue
        # Look for method declaration pattern
        match = re.search(r'(?:void|public|private|protected|static|\w+)\s+(\w+)\s*\(', line)
        if match:
            return match.group(1)
    
    return ''


def extract_method_name_with_fallback(project_path: str, commit: str, file_path: str,
                                       diff: str, annotation: str, event_type: str) -> str:
    """
    Extract method name with fallback to full file content.
    1. First try to extract from diff
    2. If that fails, get line number from diff and read full file at that commit
    """
    # Try extracting from diff first
    method_name = extract_method_name_from_diff(diff, annotation, event_type)
    if method_name:
        return method_name
    
    # Fallback: get line number and read full file
    line_num = get_line_number_from_diff(diff, annotation, event_type)
    if not line_num:
        return ''
    
    # For '-' events, we need to look at the parent commit
    target_commit = f'{commit}^' if event_type == '-' else commit
    content = get_file_at_commit(project_path, target_commit, file_path)
    
    if content:
        method_name = extract_method_name_from_file_content(content, line_num, annotation)
        if method_name:
            return method_name
    
    return ''


def build_pt_lifecycle_list(project_path: str) -> List[PTLifecycle]:
    """
    Build the complete PT lifecycle list by scanning git history.
    Returns list of PTLifecycle objects.
    """
    lifecycles = []
    
    # Scan JUnit 5 PTs
    print("Scanning JUnit 5 PTs (@ParameterizedTest)...")
    junit5_events = scan_pt_events_with_git_log_g(project_path, '@ParameterizedTest')
    
    for file_path, events in junit5_events.items():
        # Group events by method name
        method_events = defaultdict(list)
        for commit, event_type, method_name in events:
            if method_name:
                method_events[method_name].append((commit, event_type))
        
        for method_name, method_event_list in method_events.items():
            # Sort by commit date (need to get actual dates)
            # For now, we'll process them as-is
            
            # Find first '+' (add) and last '-' (delete) if any
            adds = [c for c, e in method_event_list if e == '+']
            deletes = [c for c, e in method_event_list if e == '-']
            
            if adds:
                add_commit = adds[-1]  # Earliest add (git log is reverse chronological)
                delete_commit = deletes[0] if deletes else None  # Latest delete
                
                # Check if PT still exists at HEAD
                head_content = get_file_at_commit(project_path, 'HEAD', file_path)
                is_deleted = head_content is None or f'@ParameterizedTest' not in head_content or method_name not in head_content
                
                lifecycles.append(PTLifecycle(
                    file_path=file_path,
                    method_name=method_name,
                    pt_type='junit5',
                    add_commit=add_commit,
                    delete_commit=delete_commit if is_deleted else None,
                    is_deleted=is_deleted
                ))
    
    # Scan JUnit 4 PTs - use regex-safe pattern for git log -G, literal pattern for diff matching
    print("Scanning JUnit 4 PTs (@RunWith(Parameterized.class))...")
    junit4_events = scan_pt_events_with_git_log_g(
        project_path, 
        search_pattern='RunWith.Parameterized',
        literal_pattern='@RunWith(Parameterized'
    )
    
    for file_path, events in junit4_events.items():
        adds = [c for c, e, _ in events if e == '+']
        deletes = [c for c, e, _ in events if e == '-']
        
        if adds:
            add_commit = adds[-1]  # Earliest add
            delete_commit = deletes[0] if deletes else None  # Latest delete
            
            # Check if PT still exists at HEAD
            head_content = get_file_at_commit(project_path, 'HEAD', file_path)
            is_deleted = head_content is None or '@RunWith(Parameterized' not in head_content
            
            lifecycles.append(PTLifecycle(
                file_path=file_path,
                method_name='',  # Class-level for JUnit4
                pt_type='junit4',
                add_commit=add_commit,
                delete_commit=delete_commit if is_deleted else None,
                is_deleted=is_deleted
            ))
    
    print(f"Found {len(lifecycles)} PT lifecycles from git log -G "
          f"({len([l for l in lifecycles if l.pt_type == 'junit5'])} JUnit5, "
          f"{len([l for l in lifecycles if l.pt_type == 'junit4'])} JUnit4)")
    print(f"  Deleted: {len([l for l in lifecycles if l.is_deleted])}")
    print(f"  Active: {len([l for l in lifecycles if not l.is_deleted])}")
    
    return lifecycles


# ============== Parser Result Integration ==============

def load_parser_result(project_name: str) -> List[dict]:
    """
    Load parser result from JSON file.
    Returns list of test case records from parser.
    """
    parser_file = PARSER_RESULT_DIR / f'{project_name}_output.json'
    
    if not parser_file.exists():
        print(f"  Warning: Parser result file not found: {parser_file}")
        return []
    
    try:
        with open(parser_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"  Warning: Failed to load parser result: {e}")
        return []


def get_parameterized_tests_from_parser(parser_data: List[dict], project_path: str) -> List[dict]:
    """
    Filter parser data to get only parameterized tests.
    Returns list of PT records with normalized file paths.
    """
    pts = []
    
    for record in parser_data:
        annotations = record.get('annotations', [])
        param_sources = record.get('parameterSources', [])
        
        # Check if it's a PT
        is_junit5_pt = 'ParameterizedTest' in annotations
        is_junit4_pt = any('Parameterized' in str(s) for s in param_sources) or \
                       record.get('junit') == 'junit4' and param_sources
        
        if is_junit5_pt or is_junit4_pt:
            # Normalize file path (remove project path prefix to get relative path)
            file_path = record.get('filePath', '')
            # Convert absolute path to relative path for matching
            if file_path.startswith(project_path):
                rel_path = file_path[len(project_path):].lstrip('/')
            else:
                # Try to extract relative path from full path
                # Look for common patterns like src/test/java/...
                match = re.search(r'(src/(?:test|main)/java/.+\.java)$', file_path)
                if match:
                    rel_path = match.group(1)
                else:
                    rel_path = file_path
            
            pts.append({
                'file_path': rel_path,
                'method_name': record.get('methodName', ''),
                'pt_type': 'junit5' if is_junit5_pt else 'junit4',
                'start_line': record.get('startLine'),
                'end_line': record.get('endLine'),
                'original_path': file_path
            })
    
    return pts


def merge_with_parser_result(project_path: str, project_name: str, 
                              git_lifecycles: List[PTLifecycle]) -> List[PTLifecycle]:
    """
    Merge git log -G results with parser results.
    - Parser result is ground truth for current HEAD PTs
    - git log -G provides historical events including deleted PTs
    
    Returns merged lifecycle list.
    """
    print("\nMerging with parser results...")
    
    # Load parser results
    parser_data = load_parser_result(project_name)
    if not parser_data:
        print("  No parser data available, using git log -G results only")
        return git_lifecycles
    
    parser_pts = get_parameterized_tests_from_parser(parser_data, project_path)
    print(f"  Parser found {len(parser_pts)} PTs at HEAD")
    
    # Build lookup for git lifecycles
    # Key: (normalized_file_path, method_name) for JUnit5, (normalized_file_path, '') for JUnit4
    git_lookup = {}
    for lc in git_lifecycles:
        # Normalize file path
        if lc.file_path.startswith('/'):
            # Already relative from git
            key = (lc.file_path, lc.method_name)
        else:
            key = (lc.file_path, lc.method_name)
        git_lookup[key] = lc
    
    merged = list(git_lifecycles)  # Start with git results
    added_from_parser = 0
    
    # Check each parser PT
    for pt in parser_pts:
        key = (pt['file_path'], pt['method_name'])
        
        if key not in git_lookup:
            # PT exists at HEAD but not found by git log -G
            # This can happen if the PT was added in the initial commit
            # or if git log -G didn't capture the event
            
            # Find the first commit that introduced this file with the PT
            add_commit = find_first_commit_with_pt(
                project_path, pt['file_path'], pt['method_name'], pt['pt_type'])
            
            if add_commit:
                merged.append(PTLifecycle(
                    file_path=pt['file_path'],
                    method_name=pt['method_name'],
                    pt_type=pt['pt_type'],
                    add_commit=add_commit,
                    delete_commit=None,
                    is_deleted=False
                ))
                added_from_parser += 1
    
    print(f"  Added {added_from_parser} PTs from parser that git log -G missed")
    print(f"  Total PT lifecycles after merge: {len(merged)}")
    
    return merged


def find_first_commit_with_pt(project_path: str, file_path: str, 
                               method_name: str, pt_type: str) -> Optional[str]:
    """
    Find the first commit where the PT appears in the file.
    Uses git log --follow to track file renames.
    For JUnit5, also traces back through method renames using RefactoringMiner.
    """
    # Get all commits for this file (oldest first)
    cmd = ['git', 'log', '--follow', '--reverse', '--format=%H', '--', file_path]
    code, stdout, stderr = run_git_command(cmd, project_path, timeout=60)
    
    if code != 0 or not stdout.strip():
        return None
    
    commits = [c.strip() for c in stdout.strip().split('\n') if c.strip()]
    
    annotation = '@ParameterizedTest' if pt_type == 'junit5' else '@RunWith(Parameterized'
    
    if pt_type == 'junit4':
        # For JUnit4, just need the annotation at class level
        for commit in commits:
            content = get_file_at_commit(project_path, commit, file_path)
            if content and annotation in content:
                return commit
        return commits[0] if commits else None
    
    # For JUnit5: trace back through potential method renames
    current_method = method_name
    final_add_commit = None
    max_iterations = 10  # Prevent infinite loops
    
    # Get the first few commits of the project to skip RefactoringMiner on them
    # (initial commits are usually large imports, no rename possible)
    first_commits_cmd = ['git', 'rev-list', '--max-parents=0', 'HEAD']
    code, stdout, _ = run_git_command(first_commits_cmd, project_path, timeout=30)
    initial_commits = set(stdout.strip().split('\n')) if code == 0 else set()
    
    for iteration in range(max_iterations):
        # Find the first commit where current_method appears
        first_appearance = None
        for commit in commits:
            content = get_file_at_commit(project_path, commit, file_path)
            if content and annotation in content and current_method in content:
                first_appearance = commit
                break
        
        if not first_appearance:
            # Method not found in any commit
            break
        
        # Skip RefactoringMiner for initial commits (no rename possible)
        if first_appearance in initial_commits:
            final_add_commit = first_appearance
            break
        
        # Check if this commit has a rename refactoring for this method
        refactorings = run_refactoring_miner(project_path, first_appearance)
        
        old_name = None
        for ref in refactorings:
            if ref.new_method_name == current_method and ref.file_path and file_path in ref.file_path:
                old_name = ref.old_method_name
                print(f"      Tracing rename at {first_appearance[:8]}: {old_name} -> {current_method}")
                break
        
        if old_name:
            # Found a rename, continue tracing with the old name
            current_method = old_name
            # Update final_add_commit - we'll keep going back
        else:
            # No rename found, this is the true origin
            final_add_commit = first_appearance
            break
    
    return final_add_commit or (commits[0] if commits else None)


# ============== RefactoringMiner Integration ==============

def run_refactoring_miner(project_path: str, commit_hash: str) -> List[RefactoringResult]:
    """
    Run RefactoringMiner on a specific commit to detect refactorings.
    Returns list of Rename Method refactorings.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_file = f.name
    
    try:
        env = os.environ.copy()
        env['JAVA_HOME'] = JAVA_HOME
        env['PATH'] = f"{JAVA_HOME}/bin:{env.get('PATH', '')}"
        
        cmd = [REFACTORING_MINER_PATH, '-c', project_path, commit_hash, '-json', output_file]
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_path
        )
        
        if result.returncode != 0:
            return []
        
        # Parse JSON output
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        rename_results = []
        for commit_data in data.get('commits', []):
            for refactoring in commit_data.get('refactorings', []):
                if refactoring.get('type') == 'Rename Method':
                    # Extract old and new method names
                    desc = refactoring.get('description', '')
                    # Pattern: "Rename Method public oldName(...) : ... renamed to newName(...)"
                    match = re.search(r'Rename Method.*?(\w+)\s*\([^)]*\).*?renamed to\s*(\w+)\s*\(', desc)
                    if match:
                        old_name = match.group(1)
                        new_name = match.group(2)
                        
                        # Get file path from left side location
                        left_side = refactoring.get('leftSideLocations', [])
                        if left_side:
                            file_path = left_side[0].get('filePath', '')
                            rename_results.append(RefactoringResult(
                                old_method_name=old_name,
                                new_method_name=new_name,
                                file_path=file_path,
                                commit_hash=commit_hash
                            ))
        
        return rename_results
    
    except Exception as e:
        print(f"  Warning: RefactoringMiner error for {commit_hash}: {e}")
        return []
    
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)


# ============== Phase 2: Back-tracking ==============

def find_method_range_in_content(content: str, method_name: str) -> Optional[Tuple[int, int]]:
    """
    Find the line range of a method in file content.
    Returns (start_line, end_line) or None if not found.
    """
    lines = content.split('\n')
    
    # Find @ParameterizedTest or @Test annotation followed by method name
    annotation_line = None
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if '@ParameterizedTest' in line or '@Test' in line:
            annotation_line = i
            continue
        
        if annotation_line is not None:
            # Skip other annotations
            if stripped.startswith('@'):
                continue
            if not stripped:
                continue
            
            # Check for method declaration
            if re.search(rf'\b{re.escape(method_name)}\s*\(', line):
                method_start = annotation_line
                
                # Find method end by brace counting
                brace_count = 0
                started = False
                
                for j in range(i - 1, len(lines)):
                    current_line = lines[j]
                    clean_line = re.sub(r'"[^"]*"', '', current_line)
                    clean_line = re.sub(r'//.*$', '', clean_line)
                    
                    brace_count += clean_line.count('{') - clean_line.count('}')
                    
                    if '{' in clean_line:
                        started = True
                    
                    if started and brace_count == 0:
                        return (method_start, j + 1)
                
                return (method_start, min(i + 100, len(lines)))
            
            # Reset if we pass the annotation block
            if 'void ' in line or re.match(r'\s*(public|private|protected)', line):
                annotation_line = None
    
    return None


def find_class_range_in_content(content: str) -> Optional[Tuple[int, int]]:
    """Find the line range of the main class in file content."""
    lines = content.split('\n')
    
    class_start = None
    brace_count = 0
    started = False
    
    for i, line in enumerate(lines, 1):
        if class_start is None and ('class ' in line or 'public class' in line):
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('*'):
                continue
            class_start = i
        
        if class_start is not None:
            clean_line = re.sub(r'"[^"]*"', '', line)
            clean_line = re.sub(r'//.*$', '', clean_line)
            
            brace_count += clean_line.count('{') - clean_line.count('}')
            
            if '{' in clean_line:
                started = True
            
            if started and brace_count == 0:
                return (class_start, i)
    
    if class_start:
        return (class_start, len(lines))
    
    return None


def ranges_overlap(range1: Tuple[int, int], range2: Tuple[int, int]) -> bool:
    """Check if two line ranges overlap"""
    start1, end1 = range1
    start2, end2 = range2
    return start1 <= end2 and start2 <= end1


def is_junit4_parameterized_content(content: str) -> bool:
    """Check if content has @RunWith(Parameterized.class)"""
    if not content:
        return False
    return '@RunWith(Parameterized' in content or 'RunWith(Parameterized.class)' in content


def track_pt_contributors(
    project_path: str,
    lifecycle: PTLifecycle,
    refactoring_cache: Dict[str, List[RefactoringResult]]
) -> List[DeveloperContribution]:
    """
    Track all developers who contributed to a PT during its lifecycle.
    For JUnit5: tracks method-level changes, handles renames via RefactoringMiner
    For JUnit4: tracks class-level changes
    """
    contributions = []
    current_method_name = lifecycle.method_name
    
    # Get all commits in the lifecycle range
    end_commit = lifecycle.delete_commit if lifecycle.is_deleted else None
    commits = get_file_commits_in_range(
        project_path, 
        lifecycle.file_path, 
        lifecycle.add_commit, 
        end_commit
    )
    
    if not commits:
        return contributions
    
    print(f"    Tracking {len(commits)} commits for {lifecycle.file_path}::{current_method_name or '(class)'}")
    
    for commit in commits:
        commit_info = get_commit_info(project_path, commit)
        if not commit_info:
            continue
        
        parent_commit = f"{commit}^"
        
        # Get file content at this commit
        content = get_file_at_commit(project_path, commit, lifecycle.file_path)
        if not content:
            continue
        
        # Determine target range based on PT type
        if lifecycle.pt_type == 'junit4' or is_junit4_parameterized_content(content):
            # JUnit4: class-level tracking
            if not is_junit4_parameterized_content(content):
                continue  # Not a PT at this point
            target_range = find_class_range_in_content(content)
            if target_range is None:
                continue  # Class not found, skip
        else:
            # JUnit5: method-level tracking
            target_range = find_method_range_in_content(content, current_method_name)
            
            # If method not found, check for rename
            if target_range is None:
                # Check if this commit has a rename refactoring
                if commit not in refactoring_cache:
                    refactoring_cache[commit] = run_refactoring_miner(project_path, commit)
                
                for ref in refactoring_cache[commit]:
                    if ref.new_method_name == current_method_name:
                        # Found a rename! Use old name for earlier commits
                        print(f"      Rename detected at {commit[:8]}: {ref.old_method_name} -> {current_method_name}")
                        current_method_name = ref.old_method_name
                        target_range = find_method_range_in_content(content, current_method_name)
                        break
                
                if target_range is None:
                    # Method doesn't exist in this version, skip
                    continue
        
        # Get diff hunks
        hunks = get_diff_hunks(project_path, parent_commit, commit, lifecycle.file_path)
        
        if not hunks:
            continue
        
        # Check if any hunk overlaps with target range
        for old_start, old_count, new_start, new_count in hunks:
            new_range = (new_start, new_start + max(new_count - 1, 0))
            
            if ranges_overlap(target_range, new_range):
                # Determine change type
                if commit == lifecycle.add_commit:
                    change_type = 'create'
                elif lifecycle.is_deleted and commit == lifecycle.delete_commit:
                    change_type = 'delete'
                else:
                    change_type = 'modify'
                
                contributions.append(DeveloperContribution(
                    author_name=commit_info['author_name'],
                    author_email=commit_info['author_email'],
                    commit_hash=commit[:12],
                    commit_date=commit_info['date'],
                    file_path=lifecycle.file_path,
                    method_name=lifecycle.method_name,
                    change_type=change_type
                ))
                break  # One contribution per commit
    
    return contributions


# ============== Main ==============

def main():
    if len(sys.argv) < 2:
        print("Usage: python find_pt_developers_v2.py <project_name>")
        print("Example: python find_pt_developers_v2.py Hudi")
        sys.exit(1)
    
    project_name = sys.argv[1]
    
    # Paths
    script_dir = Path(__file__).parent
    result_dir = script_dir / 'result_v2'
    result_dir.mkdir(exist_ok=True)
    
    project_path = os.path.expanduser(f'~/project/{project_name}')
    
    if not os.path.isdir(project_path):
        print(f"Error: Project path {project_path} not found")
        sys.exit(1)
    
    print(f"="*60)
    print(f"PT Developer Finder v2 - {project_name}")
    print(f"="*60)
    print(f"Project path: {project_path}")
    print()
    
    # Phase 1: Build PT lifecycle list from git log -G
    print("Phase 1: Building PT lifecycle list from git history...")
    git_lifecycles = build_pt_lifecycle_list(project_path)
    
    # Phase 1.5: Merge with parser results (ground truth for HEAD)
    print("\nPhase 1.5: Merging with parser results...")
    lifecycles = merge_with_parser_result(project_path, project_name, git_lifecycles)
    
    # Save lifecycle list
    lifecycle_csv = result_dir / f'{project_name}_pt_lifecycles.csv'
    with open(lifecycle_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file_path', 'method_name', 'pt_type', 
                                                'add_commit', 'delete_commit', 'is_deleted',
                                                'source'])
        writer.writeheader()
        for lc in lifecycles:
            # Determine source
            source = 'git_log_g'
            for git_lc in git_lifecycles:
                if git_lc.file_path == lc.file_path and git_lc.method_name == lc.method_name:
                    source = 'git_log_g'
                    break
            else:
                source = 'parser'
            
            writer.writerow({
                'file_path': lc.file_path,
                'method_name': lc.method_name,
                'pt_type': lc.pt_type,
                'add_commit': lc.add_commit,
                'delete_commit': lc.delete_commit or '',
                'is_deleted': lc.is_deleted,
                'source': source
            })
    print(f"Saved lifecycle list to {lifecycle_csv}")
    print()
    
    # Phase 2: Track contributors for each PT
    print("Phase 2: Tracking contributors...")
    all_contributions = []
    developer_stats = defaultdict(lambda: {'methods': set(), 'commits': set()})
    refactoring_cache = {}  # Cache RefactoringMiner results
    
    for i, lifecycle in enumerate(lifecycles, 1):
        print(f"[{i}/{len(lifecycles)}] {lifecycle.file_path}::{lifecycle.method_name or '(class)'}")
        
        contributions = track_pt_contributors(project_path, lifecycle, refactoring_cache)
        
        if contributions:
            print(f"    Found {len(contributions)} contributions")
            
            for contrib in contributions:
                all_contributions.append({
                    'file_path': contrib.file_path,
                    'method_name': contrib.method_name,
                    'author_name': contrib.author_name,
                    'author_email': contrib.author_email,
                    'commit_hash': contrib.commit_hash,
                    'commit_date': contrib.commit_date,
                    'change_type': contrib.change_type
                })
                
                key = (contrib.author_name, contrib.author_email)
                developer_stats[key]['methods'].add(f"{contrib.file_path}::{contrib.method_name}")
                developer_stats[key]['commits'].add(contrib.commit_hash)
    
    # Save detailed results
    output_csv = result_dir / f'{project_name}_pt_developers.csv'
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['file_path', 'method_name', 'author_name', 'author_email',
                      'commit_hash', 'commit_date', 'change_type']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_contributions)
    print(f"\nSaved detailed results to {output_csv}")
    
    # Save developer summary
    summary_csv = result_dir / f'{project_name}_developer_summary.csv'
    summary_rows = []
    for (name, email), stats in sorted(developer_stats.items(),
                                        key=lambda x: len(x[1]['methods']),
                                        reverse=True):
        summary_rows.append({
            'author_name': name,
            'author_email': email,
            'pt_methods_count': len(stats['methods']),
            'commits_count': len(stats['commits'])
        })
    
    with open(summary_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['author_name', 'author_email', 'pt_methods_count', 'commits_count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"Saved developer summary to {summary_csv}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total PT lifecycles: {len(lifecycles)}")
    print(f"Total contributions: {len(all_contributions)}")
    print(f"Unique PT developers: {len(developer_stats)}")
    print(f"\nTop 10 PT developers:")
    for row in summary_rows[:10]:
        print(f"  {row['pt_methods_count']:3d} methods, {row['commits_count']:3d} commits: "
              f"{row['author_name']} <{row['author_email']}>")


if __name__ == '__main__':
    main()
