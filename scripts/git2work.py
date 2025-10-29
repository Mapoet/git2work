#! /usr/bin/env python3

import os
import sys
import subprocess
import argparse
import re
import json
import requests
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from git import Repo
from datetime import datetime, timedelta
# API Keys - 仅从环境变量读取，不提供默认值以确保安全
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai package not installed. Please run: pip install openai")


# 默认系统提示词
default_system_prompt = """你是一个专业的技术文档撰写助手。根据提供的 git commit 记录，生成一份结构化的中文工作总结。

要求：
1. 使用 Markdown 格式
2. 总结主要包括：
   - 今日工作概述（3-5句）
   - 主要完成内容（按模块分类）
   - 统计数据（提交数、代码变更、涉及文件等）
   - 技术亮点或重要改进
3. 语言简洁专业，避免过于冗长
4. 重点关注代码改进、功能增强、问题修复等技术性内容

【工作会话时间图要求】
如果提供的 commit 记录中包含工作会话统计信息（如"工作会话: X 个，总时长约 Y 分钟"），请基于这些会话信息绘制一个简洁的工作内容时间分布图。图应包含：
1. 各工作会话的起止时间范围
2. 每个会话涉及的提交数量或主要功能模块
3. 会话之间的时间间隔（便于识别工作节奏）
4. 如有跨项目提交，标注项目切换的时间点
5. **特别注意并行工作时间**：如果存在"跨项目并行工作时间段"标识，请在时间图中清晰标注同时在不同项目上工作的时段，这有助于准确评估实际投入时间（并行工作不应简单累加）

时间图可使用 Markdown 表格及 Mermaid 10分钟级甘特图形式呈现。

请根据提供的 commit 信息生成工作总结。"""

def parse_git_log(raw):
    # 我们使用 git log 输出以 \x1e（record sep）分割 commit，以 \x1f 字段分割
    commits = []
    if not raw:
        return commits
    for entry in raw.strip("\x1e").split("\x1e"):
        parts = entry.split("\x1f")
        if len(parts) < 5:
            continue
        # 支持两种格式：5字段(旧) 或 6字段(含 %at epoch)
        if len(parts) >= 6:
            sha, author_name, author_email, date_str, epoch_str, message = [p.strip() for p in parts[:6]]
            date_epoch = int(epoch_str) if epoch_str.isdigit() else None
        else:
            sha, author_name, author_email, date_str, message = [p.strip() for p in parts[:5]]
            date_epoch = None
        # date_str 示例: 2025-10-20 12:34:56 +0800 （取决于 --date=iso）
        commits.append({
            "sha": sha,
            "author_name": author_name,
            "author_email": author_email,
            "date": date_str,
            "date_epoch": date_epoch,
            "message": message,
        })
    return commits

def get_commits_between(repo_path, since_dt, until_dt, max_count=None):
    """
    since_dt / until_dt: python datetime（最好带时区或者是本地时间）
    返回 commit 对象列表（可以转换为 dict）
    """
    repo = Repo(repo_path)
    # gitpython 没有直接参数用来筛选日期，所以使用 git directly via repo.git.log 更方便：
    since = since_dt.isoformat(sep=' ')
    until = until_dt.isoformat(sep=' ')
    # 增加 %at（author epoch 秒）便于稳定时间统计
    raw = repo.git.log(
        f'--since={since}',
        f'--until={until}',
        '--pretty=format:%H%x1f%an%x1f%ae%x1f%ad%x1f%at%x1f%s%x1e',
        date='iso'
    )
    # 复用上面 parse 函数
    return parse_git_log(raw)

def get_commit_numstat(repo_path: str, sha: str) -> Tuple[List[str], int, int]:
    """
    返回 (files, insertions, deletions)
    通过 `git show --numstat` 解析每个 commit 修改的文件与增删行数。
    """
    repo = Repo(repo_path)
    # --pretty=tformat: 只输出文件变更（避免重复元信息）
    output = repo.git.show(sha, '--numstat', '--pretty=tformat:')
    files: List[str] = []
    insertions_total = 0
    deletions_total = 0
    for line in output.splitlines():
        parts = line.split('\t')
        if len(parts) == 3:
            add_str, del_str, path = parts
            # 二进制文件会显示 '-'，此时计为 0
            try:
                add = int(add_str) if add_str.isdigit() else 0
            except ValueError:
                add = 0
            try:
                dele = int(del_str) if del_str.isdigit() else 0
            except ValueError:
                dele = 0
            insertions_total += add
            deletions_total += dele
            files.append(path)
    return files, insertions_total, deletions_total

def get_commit_body(repo_path: str, sha: str) -> str:
    """
    获取完整 commit message（含主题与正文）。
    """
    repo = Repo(repo_path)
    body = repo.git.show(sha, '-s', '--format=%B')
    return body.strip('\n')

def group_commits_by_date(commits: List[Dict]) -> Dict[str, List[Dict]]:
    groups: Dict[str, List[Dict]] = defaultdict(list)
    for c in commits:
        # date 字符串形如 "2025-10-20 12:34:56 +0800"
        date_part = c['date'].split(' ')[0]
        groups[date_part].append(c)
    # 对每组按时间排序（从早到晚）
    for k in groups:
        groups[k].sort(key=lambda x: x['date'])
    return dict(sorted(groups.items(), key=lambda x: x[0]))

def commit_time_dt(c: Dict) -> datetime:
    if c.get('date_epoch'):
        try:
            return datetime.fromtimestamp(int(c['date_epoch']))
        except Exception:
            pass
    # Fallback parse from string
    ds = c.get('date', '')
    try:
        return datetime.strptime(ds, "%Y-%m-%d %H:%M:%S %z").astimezone().replace(tzinfo=None)
    except Exception:
        try:
            return datetime.strptime(ds, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.fromisoformat(ds.replace(' ', 'T').split(' +')[0])

def compute_work_sessions(commits: List[Dict], gap_minutes: int = 60) -> List[Dict]:
    if not commits:
        return []
    items = sorted(commits, key=lambda c: commit_time_dt(c))
    sessions: List[Dict] = []
    gap = timedelta(minutes=gap_minutes)
    current = {
        'start': commit_time_dt(items[0]),
        'end': commit_time_dt(items[0]),
        'commits': [items[0]],
    }
    for c in items[1:]:
        t = commit_time_dt(c)
        if t - commit_time_dt(current['commits'][-1]) <= gap:
            current['end'] = t
            current['commits'].append(c)
        else:
            current['duration_minutes'] = max(1, int((current['end'] - current['start']).total_seconds() // 60))
            sessions.append(current)
            current = {'start': t, 'end': t, 'commits': [c]}
    current['duration_minutes'] = max(1, int((current['end'] - current['start']).total_seconds() // 60))
    sessions.append(current)
    return sessions

def compute_feature_windows(commits: List[Dict]) -> Dict[str, Dict]:
    # Group by leading token of commit message (e.g., feat, fix, docs, build, refactor)
    windows: Dict[str, Dict] = {}
    for c in commits:
        msg = c.get('message', '').strip()
        token = msg.split(':', 1)[0].lower().split(' ')[0]
        key = token if token in ['feat', 'fix', 'docs', 'build', 'refactor', 'chore', 'perf', 'test'] else 'other'
        t = commit_time_dt(c)
        w = windows.get(key)
        if not w:
            windows[key] = {'start': t, 'end': t, 'count': 1}
        else:
            if t < w['start']:
                w['start'] = t
            if t > w['end']:
                w['end'] = t
            w['count'] += 1
    return windows

def detect_parallel_sessions(repo_to_sessions: Dict[str, List[Dict]]) -> List[Dict]:
    """
    检测跨项目的并行工作时段。
    返回重叠的时间段及其涉及的项目列表。
    """
    if len(repo_to_sessions) < 2:
        return []  # 单项目不需要检测并行
    
    all_periods: List[Dict] = []
    for repo, sessions in repo_to_sessions.items():
        for s in sessions:
            all_periods.append({
                'start': s['start'],
                'end': s['end'],
                'repo': repo,
                'session': s
            })
    
    if not all_periods:
        return []
    
    # 合并重叠时段算法：按时间线扫描，合并连续或重叠的时段
    all_periods.sort(key=lambda x: (x['start'], x['end']))
    merged_overlaps: List[Dict] = []
    
    current_overlaps = []  # 当前正在重叠的时段组
    
    for period in all_periods:
        if not current_overlaps:
            current_overlaps = [period]
            continue
        
        # 检查当前时段是否与已有重叠组有时间重叠
        can_merge = False
        for existing in current_overlaps:
            if not (period['end'] < existing['start'] or period['start'] > existing['end']):
                can_merge = True
                break
        
        if can_merge:
            current_overlaps.append(period)
        else:
            # 结束当前重叠组，开始新的
            if len(set(p['repo'] for p in current_overlaps)) > 1:
                overlap_start = min(p['start'] for p in current_overlaps)
                overlap_end = max(p['end'] for p in current_overlaps)
                overlap_repos = sorted(set(p['repo'] for p in current_overlaps))
                merged_overlaps.append({
                    'start': overlap_start,
                    'end': overlap_end,
                    'repos': overlap_repos,
                    'duration_minutes': int((overlap_end - overlap_start).total_seconds() // 60)
                })
            current_overlaps = [period]
    
    # 处理最后一组
    if len(set(p['repo'] for p in current_overlaps)) > 1:
        overlap_start = min(p['start'] for p in current_overlaps)
        overlap_end = max(p['end'] for p in current_overlaps)
        overlap_repos = sorted(set(p['repo'] for p in current_overlaps))
        merged_overlaps.append({
            'start': overlap_start,
            'end': overlap_end,
            'repos': overlap_repos,
            'duration_minutes': int((overlap_end - overlap_start).total_seconds() // 60)
        })
    
    # 再次合并可能连续或部分重叠的时段
    if not merged_overlaps:
        return []
    
    final_merged: List[Dict] = []
    merged_overlaps.sort(key=lambda x: (x['start'], x['end']))
    
    current = merged_overlaps[0]
    for next_period in merged_overlaps[1:]:
        # 如果时间有重叠或连续（间隔小于5分钟视为连续），且涉及相同项目，则合并
        gap = (next_period['start'] - current['end']).total_seconds() / 60
        if gap <= 5 or not (next_period['end'] < current['start'] or next_period['start'] > current['end']):
            # 合并
            current['start'] = min(current['start'], next_period['start'])
            current['end'] = max(current['end'], next_period['end'])
            current['repos'] = sorted(set(current['repos']) | set(next_period['repos']))
            current['duration_minutes'] = int((current['end'] - current['start']).total_seconds() // 60)
        else:
            final_merged.append(current)
            current = next_period
    final_merged.append(current)
    
    return final_merged

def build_commit_context_by_project(repo_to_grouped: Dict[str, Dict[str, List[Dict]]], repo_to_details: Dict[str, Dict[str, Tuple[List[str], int, int, str]]], gap_minutes: int = 60) -> str:
    lines: List[str] = []
    
    # 先计算所有项目的会话，用于检测并行工作
    repo_to_sessions: Dict[str, List[Dict]] = {}
    for repo_name, grouped in repo_to_grouped.items():
        flat_commits: List[Dict] = []
        for items in grouped.values():
            flat_commits.extend(items)
        sessions = compute_work_sessions(flat_commits, gap_minutes)
        repo_to_sessions[repo_name] = sessions
    
    # 检测跨项目并行工作时间
    parallel_periods = detect_parallel_sessions(repo_to_sessions)
    if parallel_periods:
        lines.append("# 跨项目并行工作时间段")
        total_parallel_minutes = sum(p['duration_minutes'] for p in parallel_periods)
        lines.append(f"检测到 {len(parallel_periods)} 个并行工作时段，总重叠时长约 {total_parallel_minutes} 分钟")
        for idx, p in enumerate(parallel_periods, 1):
            repos_str = ', '.join(p['repos'])
            lines.append(f"- 并行时段{idx}: {p['start']} ~ {p['end']} ({p['duration_minutes']} 分钟, 涉及项目: {repos_str})")
        lines.append("")
    
    # 各项目详细统计
    for repo_name, grouped in repo_to_grouped.items():
        lines.append(f"\n# 项目：{repo_name}")
        sessions = repo_to_sessions[repo_name]
        if sessions:
            total_minutes = sum(s['duration_minutes'] for s in sessions)
            lines.append(f"工作会话: {len(sessions)} 个，总时长约 {total_minutes} 分钟")
            for idx, s in enumerate(sessions, 1):
                # 标记是否为并行时段
                is_parallel = any(
                    not (s['end'] < pp['start'] or s['start'] > pp['end'])
                    for pp in parallel_periods
                    if repo_name in pp['repos']
                )
                parallel_marker = " [并行]" if is_parallel else ""
                lines.append(f"- 会话{idx}: {s['start']} ~ {s['end']} ({s['duration_minutes']} 分钟, {len(s['commits'])} 次提交){parallel_marker}")
        # Feature windows
        flat_commits: List[Dict] = []
        for items in grouped.values():
            flat_commits.extend(items)
        fw = compute_feature_windows(flat_commits)
        if fw:
            lines.append("功能窗口:")
            for k, v in fw.items():
                duration = int((v['end'] - v['start']).total_seconds() // 60)
                lines.append(f"- {k}: {v['start']} ~ {v['end']} ({duration} 分钟, {v['count']} 次提交)")
        for day, items in grouped.items():
            lines.append(f"\n## {day} ({len(items)} commits)")
            for c in items:
                sha = c['sha']
                files, ins, dels, body = repo_to_details[repo_name].get(sha, ([], 0, 0, ""))
                short_sha = sha[:8]
                time_part = ' '.join(c['date'].split(' ')[1:3]) if ' ' in c['date'] else c['date']
                lines.append(f"\n- [{short_sha}] {time_part}")
                lines.append(f"  提交信息: {c['message']}")
                lines.append(f"  统计: {ins} 行新增, {dels} 行删除, {len(files)} 个文件")
                if body and body.strip() != c['message']:
                    lines.append(f"  详细内容:\n{body}")
                if files:
                    lines.append(f"  修改的文件: {', '.join(files[:20])}{' ...' if len(files) > 20 else ''}")
    return "\n".join(lines)

def generate_summary_with_openai(
    grouped: Dict[str, List[Dict]], 
    details: Dict[str, Tuple[List[str], int, int, str]],
    system_prompt: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    author: Optional[str] = None,
    gap_minutes: int = 60
) -> str:
    """
    使用 OpenAI API 生成工作总结。
    如果没有提供 API key，会尝试从环境变量 OPENAI_API_KEY 获取。
    """
    if not OPENAI_AVAILABLE:
        return "错误：未安装 openai 包。请运行: pip install openai"
    
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "错误：未提供 OpenAI API key。请设置环境变量 OPENAI_API_KEY 或使用 --openai-key 参数"
    
    client = OpenAI(api_key=api_key)
    
    # 兼容单项目或多项目上下文
    if isinstance(grouped, dict) and grouped and all(isinstance(v, dict) for v in grouped.values()):
        # 多项目：grouped: repo -> {day -> commits}
        repo_to_grouped = grouped  # type: ignore
        repo_to_details = details  # type: ignore
        commit_context = build_commit_context_by_project(repo_to_grouped, repo_to_details, gap_minutes)  # type: ignore
    else:
        context_lines = []
        for day, items in grouped.items():
            context_lines.append(f"\n## {day} ({len(items)} commits)")
            for c in items:
                sha = c['sha']
                files, ins, dels, body = details.get(sha, ([], 0, 0, ""))
                short_sha = sha[:8]
                time_part = ' '.join(c['date'].split(' ')[1:3]) if ' ' in c['date'] else c['date']
                context_lines.append(f"\n- [{short_sha}] {time_part}")
                context_lines.append(f"  提交信息: {c['message']}")
                context_lines.append(f"  统计: {ins} 行新增, {dels} 行删除, {len(files)} 个文件")
                if body and body.strip() != c['message']:
                    context_lines.append(f"  详细内容:\n{body}")
                if files:
                    context_lines.append(f"  修改的文件: {', '.join(files[:20])}{' ...' if len(files) > 20 else ''}")
        commit_context = "\n".join(context_lines)

    system_msg = system_prompt or default_system_prompt + "\n此外，请按项目分别估算投入时间（根据提交时间密度与连续性），并给出每个项目的主要产出。"
    if author:
        system_msg += f"\n此外，请基于作者姓名或邮箱包含“{author}”的提交进行工作总结，并在摘要开头显式标注：作者：{author}。"
    user_msg = f"请根据以下 commit 记录生成工作总结：\n\n{commit_context}"
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"错误：调用 OpenAI API 失败: {str(e)}"

def generate_summary_with_deepseek(
    grouped: Dict[str, List[Dict]],
    details: Dict[str, Tuple[List[str], int, int, str]],
    system_prompt: Optional[str] = None,
    deepseek_api_key: Optional[str] = None,
    model: str = "deepseek-chat",
    author: Optional[str] = None,
    gap_minutes: int = 60
) -> str:
    """
    使用 DeepSeek API 生成工作总结（OpenAI 兼容的 Chat Completions 格式）。
    """
    final_key = deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
    if not final_key:
        return "错误：未提供 DeepSeek API key。请设置环境变量 DEEPSEEK_API_KEY 或使用 --deepseek-key 参数"

    # 构建上下文（支持多项目）
    if isinstance(grouped, dict) and grouped and all(isinstance(v, dict) for v in grouped.values()):
        commit_context = build_commit_context_by_project(grouped, details, gap_minutes)  # type: ignore
    else:
        context_lines = []
        for day, items in grouped.items():
            context_lines.append(f"\n## {day} ({len(items)} commits)")
            for c in items:
                sha = c['sha']
                files, ins, dels, body = details.get(sha, ([], 0, 0, ""))
                short_sha = sha[:8]
                time_part = ' '.join(c['date'].split(' ')[1:3]) if ' ' in c['date'] else c['date']
                context_lines.append(f"\n- [{short_sha}] {time_part}")
                context_lines.append(f"  提交信息: {c['message']}")
                context_lines.append(f"  统计: {ins} 行新增, {dels} 行删除, {len(files)} 个文件")
                if body and body.strip() != c['message']:
                    context_lines.append(f"  详细内容:\n{body}")
                if files:
                    context_lines.append(f"  修改的文件: {', '.join(files[:20])}{' ...' if len(files) > 20 else ''}")
        commit_context = "\n".join(context_lines)
        
    system_msg = system_prompt or default_system_prompt + "\n此外，请按项目分别估算投入时间（根据提交时间密度与连续性），并给出每个项目的主要产出。"
    if author:
        system_msg += f"\n此外，请基于作者姓名或邮箱包含“{author}”的提交进行工作总结，并在摘要开头显式标注：作者：{author}。"
    user_msg = f"请根据以下 commit 记录生成工作总结：\n\n{commit_context}"

    # 映射模型名称（DeepSeek 的正确模型名称）
    model_map = {
        "deepseek-chat": "deepseek-chat",
        "deepseek-reasoner": "deepseek-reasoner",
        "chat": "deepseek-chat"  # 默认
    }
    actual_model = model_map.get(model.lower(), "deepseek-chat")

    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {final_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": actual_model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.3
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError as e:
        error_detail = ""
        try:
            error_detail = f" - {resp.text}"
        except:
            pass
        return f"错误：调用 DeepSeek API 失败: {str(e)}{error_detail}"
    except Exception as e:
        return f"错误：调用 DeepSeek API 失败: {str(e)}"

def render_markdown_worklog(
    title: str, 
    grouped: Dict[str, List[Dict]], 
    details: Dict[str, Tuple[List[str], int, int, str]],
    add_summary: bool = False,
    summary_text: Optional[str] = None
) -> str:
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    total_commits = sum(len(v) for v in grouped.values())
    lines.append(f"总计 {total_commits} 个提交")
    lines.append("")
    for day, items in grouped.items():
        lines.append(f"## {day} ({len(items)} commits)")
        lines.append("")
        for c in items:
            sha = c['sha']
            short_sha = sha[:8]
            files, ins, dels, body = details.get(sha, ([], 0, 0, ""))
            time_part = ' '.join(c['date'].split(' ')[1:3]) if ' ' in c['date'] else c['date']
            lines.append(f"- [{short_sha}] {time_part} | {c['message']} ({ins}+/{dels}-; {len(files)} files)")
            if files:
                lines.append(f"  - files: {', '.join(files[:10])}{' ...' if len(files) > 10 else ''}")
            if body:
                lines.append("  - message:")
                lines.append("```")
                lines.extend(body.splitlines())
                lines.append("```")
        lines.append("")
    
    # 添加总结
    if add_summary and summary_text:
        lines.append(summary_text)
    
    return "\n".join(lines)

def render_multi_project_worklog(title: str, repo_to_grouped: Dict[str, Dict[str, List[Dict]]], repo_to_details: Dict[str, Dict[str, Tuple[List[str], int, int, str]]], add_summary: bool = False, summary_text: Optional[str] = None, gap_minutes: int = 60) -> str:
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    total_commits = sum(sum(len(v) for v in grouped.values()) for grouped in repo_to_grouped.values())
    lines.append(f"总计 {total_commits} 个提交，项目数 {len(repo_to_grouped)}")
    lines.append("")
    
    # 计算并行工作时间
    repo_to_sessions: Dict[str, List[Dict]] = {}
    for repo_name, grouped in repo_to_grouped.items():
        flat_commits: List[Dict] = []
        for items in grouped.values():
            flat_commits.extend(items)
        sessions = compute_work_sessions(flat_commits, gap_minutes)
        repo_to_sessions[repo_name] = sessions
    
    parallel_periods = detect_parallel_sessions(repo_to_sessions)
    if parallel_periods:
        lines.append("## 跨项目并行工作时间统计")
        total_parallel_minutes = sum(p['duration_minutes'] for p in parallel_periods)
        lines.append(f"检测到 **{len(parallel_periods)} 个并行工作时段**，总重叠时长约 **{total_parallel_minutes} 分钟**")
        lines.append("")
        for idx, p in enumerate(parallel_periods, 1):
            repos_str = ', '.join(p['repos'])
            lines.append(f"- **并行时段 {idx}**：{p['start'].strftime('%Y-%m-%d %H:%M')} ~ {p['end'].strftime('%Y-%m-%d %H:%M')} ({p['duration_minutes']} 分钟)")
            lines.append(f"  - 涉及项目：{repos_str}")
        lines.append("")
        lines.append("> 注意：并行工作时间不应简单累加，实际投入时间以重叠时段的最大值为准。")
        lines.append("")
    
    # 各项目时间统计
    lines.append("## 各项目时间统计")
    for repo_name, grouped in repo_to_grouped.items():
        sessions = repo_to_sessions[repo_name]
        if sessions:
            total_minutes = sum(s['duration_minutes'] for s in sessions)
            lines.append(f"### {repo_name}")
            lines.append(f"- 工作会话：{len(sessions)} 个，总时长约 {total_minutes} 分钟")
            for idx, s in enumerate(sessions, 1):
                is_parallel = any(
                    not (s['end'] < pp['start'] or s['start'] > pp['end'])
                    for pp in parallel_periods
                    if repo_name in pp['repos']
                )
                parallel_marker = " **[并行]**" if is_parallel else ""
                lines.append(f"  - 会话{idx}：{s['start'].strftime('%H:%M')} ~ {s['end'].strftime('%H:%M')} ({s['duration_minutes']} 分钟, {len(s['commits'])} 次提交){parallel_marker}")
    lines.append("")
    for repo_name, grouped in repo_to_grouped.items():
        lines.append(f"# 项目：{repo_name}")
        lines.append("")
        for day, items in grouped.items():
            lines.append(f"## {day} ({len(items)} commits)")
            lines.append("")
            for c in items:
                sha = c['sha']
                short_sha = sha[:8]
                files, ins, dels, body = repo_to_details[repo_name].get(sha, ([], 0, 0, ""))
                time_part = ' '.join(c['date'].split(' ')[1:3]) if ' ' in c['date'] else c['date']
                lines.append(f"- [{short_sha}] {time_part} | {c['message']} ({ins}+/{dels}-; {len(files)} files)")
                if files:
                    lines.append(f"  - files: {', '.join(files[:10])}{' ...' if len(files) > 10 else ''}")
                if body:
                    lines.append("  - message:")
                    lines.append("```")
                    lines.extend(body.splitlines())
                    lines.append("```")
            lines.append("")
        lines.append("")
    if add_summary and summary_text:
        lines.append(summary_text)
    return "\n".join(lines)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate work log from git commits")
    parser.add_argument('--repo', type=str, default=None, help='Path to git repository (single)')
    parser.add_argument('--repos', type=str, default=None, help='Multiple repositories, comma-separated')
    parser.add_argument('--since', type=str, default=None, help='Start datetime (ISO or YYYY-MM-DD)')
    parser.add_argument('--until', type=str, default=None, help='End datetime (ISO or YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=None, help='If set, use last N days ending today')
    parser.add_argument('--session-gap-minutes', type=int, default=60, help='Gap minutes to split work sessions')
    parser.add_argument('--author', type=str, default=None, help='Filter by author name or email (optional)')
    parser.add_argument('--output', type=str, default=None, help='Output file path (.md). If not set, print to stdout')
    parser.add_argument('--title', type=str, default=None, help='Title for the work log document')
    parser.add_argument('--add-summary', action='store_true', help='Add AI-generated Chinese summary at the end')
    parser.add_argument('--openai-key', type=str, default=None, help='OpenAI API key (or set OPENAI_API_KEY env var)')
    parser.add_argument('--openai-model', type=str, default='gpt-4o-mini', help='OpenAI model to use (default: gpt-4o-mini)')
    parser.add_argument('--system-prompt-file', type=str, default=None, help='Path to custom system prompt file')
    # DeepSeek 支持
    parser.add_argument('--provider', type=str, default='openai', choices=['openai', 'deepseek'], help='LLM provider')
    parser.add_argument('--deepseek-key', type=str, default=None, help='DeepSeek API key (or set DEEPSEEK_API_KEY env var)')
    parser.add_argument('--deepseek-model', type=str, default='deepseek-chat', help='DeepSeek model (e.g., deepseek-chat, deepseek-reasoner)')
    return parser.parse_args()

def parse_date_input(value: Optional[str], default_dt: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return default_dt
    # try ISO then YYYY-MM-DD
    try:
        return datetime.fromisoformat(value)
    except Exception:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except Exception:
            raise ValueError(f"无法解析日期: {value}")

def git2work():
    args = parse_args()
    repo_paths: List[str] = []
    if args.repos:
        repo_paths = [p.strip() for p in args.repos.split(',') if p.strip()]
    elif args.repo:
        repo_paths = [args.repo]
    else:
        # fallback to default single repo if none provided
        repo_paths = ["/mnt/d/works/RayTracy"]

    now = datetime.now()
    if args.days is not None and args.days > 0:
        start = (now - timedelta(days=args.days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    else:
        start = parse_date_input(args.since, now.replace(hour=0, minute=0, second=0, microsecond=0))
        end = parse_date_input(args.until, now.replace(hour=23, minute=59, second=59, microsecond=0))
        if start is not None:
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        if end is not None:
            end = end.replace(hour=23, minute=59, second=59, microsecond=0)

    multi_project = len(repo_paths) > 1

    if not multi_project:
        repo = repo_paths[0]
        commits = get_commits_between(repo, start, end)
        if args.author:
            author_lower = args.author.lower()
            commits = [c for c in commits if author_lower in c['author_name'].lower() or author_lower in c['author_email'].lower()]
        details: Dict[str, Tuple[List[str], int, int, str]] = {}
        for c in commits:
            files, ins, dels = get_commit_numstat(repo, c['sha'])
            body = get_commit_body(repo, c['sha'])
            details[c['sha']] = (files, ins, dels, body)
        grouped = group_commits_by_date(commits)
    else:
        repo_to_commits: Dict[str, List[Dict]] = {}
        repo_to_details: Dict[str, Dict[str, Tuple[List[str], int, int, str]]] = {}
        repo_to_grouped: Dict[str, Dict[str, List[Dict]]] = {}
        for repo in repo_paths:
            commits = get_commits_between(repo, start, end)
            if args.author:
                author_lower = args.author.lower()
                commits = [c for c in commits if author_lower in c['author_name'].lower() or author_lower in c['author_email'].lower()]
            repo_to_commits[repo] = commits
            details_map: Dict[str, Tuple[List[str], int, int, str]] = {}
            for c in commits:
                files, ins, dels = get_commit_numstat(repo, c['sha'])
                body = get_commit_body(repo, c['sha'])
                details_map[c['sha']] = (files, ins, dels, body)
            repo_to_details[repo] = details_map
            repo_to_grouped[repo] = group_commits_by_date(commits)
        grouped = repo_to_grouped  # type: ignore
        details = repo_to_details  # type: ignore

    title = args.title or (f"Work Log: {start.date()} to {end.date()}" if start and end else "Work Log")
    
    # 生成总结（如果需要）
    summary_text = None
    if args.add_summary:
        print("正在生成 AI 总结...")
        # 读取自定义提示词（如果有）
        system_prompt = None
        if args.system_prompt_file and os.path.exists(args.system_prompt_file):
            with open(args.system_prompt_file, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        
        if getattr(args, 'provider', 'openai') == 'deepseek':
            summary_text = generate_summary_with_deepseek(
                grouped,  # type: ignore
                details,  # type: ignore
                system_prompt=system_prompt,
                deepseek_api_key=args.deepseek_key,
                model=args.deepseek_model,
                author=args.author,
                gap_minutes=args.session_gap_minutes
            )
        else:
            summary_text = generate_summary_with_openai(
                grouped,  # type: ignore
                details,  # type: ignore
                system_prompt=system_prompt,
                openai_api_key=args.openai_key,
                model=args.openai_model,
                author=args.author,
                gap_minutes=args.session_gap_minutes
            )
        print("AI 总结生成完成")
    
    if not multi_project:
        md = render_markdown_worklog(title, grouped, details, add_summary=args.add_summary, summary_text=summary_text)  # type: ignore
    else:
        md = render_multi_project_worklog(title, grouped, details, add_summary=args.add_summary, summary_text=summary_text, gap_minutes=args.session_gap_minutes)  # type: ignore

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True) if os.path.dirname(args.output) else None
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(md)
        print(f"已写入: {args.output}")
    else:
        print(md)

if __name__ == "__main__":
    git2work()