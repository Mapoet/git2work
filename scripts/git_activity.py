#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyGithub 活动抓取/汇总工具

支持四类需求：
1) cross-repos      : 不同仓库同一作者（跨仓提交明细）
2) repo-authors     : 同一仓库不同作者（单仓提交明细）
3) repos-by-author  : 同一作者在哪些仓库有活动（列表 + 提交数）
4) authors-by-repo  : 同一仓库哪些作者有活动（列表 + 提交数）

依赖:
  pip install PyGithub python-dateutil

认证:
  export GITHUB_TOKEN=xxxx
"""

import os
import sys
import csv
import time
import argparse
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple, DefaultDict
from collections import defaultdict, Counter

from github import Auth, Github, GithubException, RateLimitExceededException
from dateutil import parser as dateparser


# --------- 通用工具 ---------
def gh_client() -> Github:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return Github(per_page=100)
    # 使用新的 Auth API 避免弃用警告
    auth = Auth.Token(token)
    return Github(auth=auth, per_page=100)

def parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    dt = dateparser.parse(s)
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def rate_limit_guard(g: Github, min_core_remaining: int = 5, sleep_sec: int = 10):
    """
    简易速率限制保护: core 剩余过少时 sleep，直到 reset。
    """
    try:
        rl = g.get_rate_limit()
        core_rem = rl.core.remaining
        if core_rem <= min_core_remaining:
            reset = rl.core.reset.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            wait = max((reset - now).total_seconds(), sleep_sec)
            print(f"[rate-limit] core 剩余 {core_rem}，休眠 {int(wait)} 秒...", file=sys.stderr)
            time.sleep(wait)
    except Exception:
        pass

def write_csv(rows: List[Dict[str, Any]], out_path: str, keys: Optional[List[str]] = None):
    if not rows:
        print(f"[info] 无数据，未生成 {out_path}")
        return
    if keys is None:
        # 默认取第一条的键
        keys = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    print(f"[ok] 导出 {len(rows)} 条记录到 {out_path}")


# --------- 1) 跨仓：不同仓库同一作者（明细） ----------
def fetch_user_activity_across_repos(
    g: Github,
    author_login: Optional[str],
    author_email: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
    owner: Optional[str],
    repo_type: str = "owner",   # owner | member | all | public | private
    max_per_repo: int = 1000
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    # 仓库来源
    if owner:
        try:
            user_or_org = g.get_user(owner)
        except GithubException:
            user_or_org = g.get_organization(owner)
        repos = user_or_org.get_repos(type=repo_type, sort="updated")
    else:
        if not author_login:
            raise ValueError("未提供 owner 时，必须提供 author_login 才能枚举其仓库。")
        user = g.get_user(author_login)
        repos = user.get_repos(type=repo_type, sort="updated")

    for repo in repos:
        rate_limit_guard(g)
        full = repo.full_name
        try:
            if author_login:
                commits = repo.get_commits(author=author_login, since=since, until=until)
            else:
                commits = repo.get_commits(since=since, until=until)

            cnt = 0
            for c in commits:
                # email 二次过滤（如果指定）
                if author_email:
                    a = getattr(c.commit, "author", None)
                    em = getattr(a, "email", None) if a else None
                    if not em or em.lower() != author_email.lower():
                        continue

                rows.append({
                    "repo": full,
                    "sha": c.sha,
                    "date": getattr(c.commit.author, "date", ""),
                    "author_login": c.author.login if c.author else "",
                    "author_name": getattr(getattr(c.commit, "author", None), "name", ""),
                    "author_email": getattr(getattr(c.commit, "author", None), "email", ""),
                    "committer_login": c.committer.login if c.committer else "",
                    "title": (c.commit.message or "").splitlines()[0],
                    "url": c.html_url,
                })
                cnt += 1
                if cnt >= max_per_repo:
                    break

        except RateLimitExceededException:
            rate_limit_guard(g, min_core_remaining=100, sleep_sec=30)
            continue
        except GithubException as e:
            print(f"[warn] 跳过 {full}: {e}", file=sys.stderr)
            continue
    return rows


# --------- 2) 单仓：同一仓库不同作者（明细） ----------
def fetch_repo_activity_across_authors(
    g: Github,
    repo_full: str,               # "owner/name"
    authors_login: Optional[List[str]] = None,
    authors_emails: Optional[List[str]] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    max_per_author: int = 1000
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    repo = g.get_repo(repo_full)

    authors_login = list({a for a in (authors_login or []) if a})
    authors_emails = [e.lower() for e in (authors_emails or []) if e]

    # 无作者清单 = 拉时间窗内所有提交（可能较多）
    if not authors_login and not authors_emails:
        commits = repo.get_commits(since=since, until=until)
        for c in commits:
            rows.append({
                "repo": repo_full,
                "sha": c.sha,
                "date": getattr(c.commit.author, "date", ""),
                "author_login": c.author.login if c.author else "",
                "author_name": getattr(getattr(c.commit, "author", None), "name", ""),
                "author_email": getattr(getattr(c.commit, "author", None), "email", ""),
                "committer_login": c.committer.login if c.committer else "",
                "title": (c.commit.message or "").splitlines()[0],
                "url": c.html_url,
            })
        return rows

    # 1) 先按 login 拉
    for login in (authors_login or []):
        rate_limit_guard(g)
        try:
            commits = repo.get_commits(author=login, since=since, until=until)
            cnt = 0
            for c in commits:
                # 若提供邮箱集合，再二次过滤
                if authors_emails:
                    a = getattr(c.commit, "author", None)
                    em = getattr(a, "email", None) if a else None
                    if not em or (em.lower() not in authors_emails):
                        continue

                rows.append({
                    "repo": repo_full,
                    "sha": c.sha,
                    "date": getattr(c.commit.author, "date", ""),
                    "author_login": c.author.login if c.author else "",
                    "author_name": getattr(getattr(c.commit, "author", None), "name", ""),
                    "author_email": getattr(getattr(c.commit, "author", None), "email", ""),
                    "committer_login": c.committer.login if c.committer else "",
                    "title": (c.commit.message or "").splitlines()[0],
                    "url": c.html_url,
                })
                cnt += 1
                if cnt >= max_per_author:
                    break
        except GithubException as e:
            print(f"[warn] login {login}: {e}", file=sys.stderr)

    # 2) 仅邮箱（补漏）
    if authors_emails:
        try:
            commits = repo.get_commits(since=since, until=until)
            cnt = 0
            for c in commits:
                a = getattr(c.commit, "author", None)
                em = getattr(a, "email", None) if a else None
                if not em or (em.lower() not in authors_emails):
                    continue
                rows.append({
                    "repo": repo_full,
                    "sha": c.sha,
                    "date": getattr(c.commit, "date", ""),
                    "author_login": c.author.login if c.author else "",
                    "author_name": getattr(a, "name", ""),
                    "author_email": em,
                    "committer_login": c.committer.login if c.committer else "",
                    "title": (c.commit.message or "").splitlines()[0],
                    "url": c.html_url,
                })
                cnt += 1
                if cnt >= max_per_author:
                    break
        except GithubException as e:
            print(f"[warn] email pass: {e}", file=sys.stderr)

    return rows


# --------- 3) 新增：同一作者在哪些仓库（列表） ----------
def list_repos_for_author(
    g: Github,
    author_login: Optional[str],
    author_email: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
    owner: Optional[str],
    repo_type: str = "owner",   # owner | member | all | public | private
    min_commits: int = 1
) -> List[Dict[str, Any]]:
    """
    输出：有该作者提交活动的仓库列表 + 提交数（按降序）。
    """
    results: List[Dict[str, Any]] = []
    counts: Dict[str, int] = defaultdict(int)

    # 仓库来源
    if owner:
        try:
            user_or_org = g.get_user(owner)
            print(f"[info] 找到用户: {owner}", file=sys.stderr)
        except GithubException:
            try:
                user_or_org = g.get_organization(owner)
                print(f"[info] 找到组织: {owner}", file=sys.stderr)
            except GithubException as e:
                print(f"[error] 无法找到用户或组织 '{owner}': {e}", file=sys.stderr)
                return []
        repos = user_or_org.get_repos(type=repo_type, sort="updated")
        repo_list = list(repos)
        print(f"[info] 找到 {len(repo_list)} 个仓库（类型: {repo_type}）", file=sys.stderr)
    else:
        if not author_login:
            raise ValueError("未提供 owner 时，必须提供 author_login 才能枚举其仓库。")
        user = g.get_user(author_login)
        repos = user.get_repos(type=repo_type, sort="updated")
        repo_list = list(repos)
        print(f"[info] 从作者 {author_login} 找到 {len(repo_list)} 个仓库", file=sys.stderr)

    checked_count = 0
    for repo in repo_list:
        rate_limit_guard(g)
        full = repo.full_name
        checked_count += 1
        try:
            if author_login:
                commits = repo.get_commits(author=author_login, since=since, until=until)
            else:
                commits = repo.get_commits(since=since, until=until)

            repo_count = 0
            for c in commits:
                if author_email:
                    a = getattr(c.commit, "author", None)
                    em = getattr(a, "email", None) if a else None
                    if not em or em.lower() != author_email.lower():
                        continue
                repo_count += 1

            if repo_count > 0:
                print(f"[info] {full}: 找到 {repo_count} 个提交（阈值: {min_commits}）", file=sys.stderr)
            
            if repo_count >= min_commits:
                counts[full] += repo_count

        except RateLimitExceededException:
            rate_limit_guard(g, min_core_remaining=100, sleep_sec=30)
            continue
        except GithubException as e:
            print(f"[warn] 跳过 {full}: {e}", file=sys.stderr)
            continue
    
    print(f"[info] 检查了 {checked_count} 个仓库，找到 {len(counts)} 个符合条件的仓库", file=sys.stderr)

    for repo_full, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        results.append({"repo": repo_full, "commits": cnt})
    return results


# --------- 4) 新增：同一仓库不同作者（作者列表） ----------
def list_authors_for_repo(
    g: Github,
    repo_full: str,
    since: Optional[datetime],
    until: Optional[datetime],
    prefer: str = "login",           # "login" | "email" | "name"（作为主显示字段）
    min_commits: int = 1
) -> List[Dict[str, Any]]:
    """
    输出：该仓库在时间窗内的作者列表 + 提交数（按降序）。
    prefer 决定 primary 字段（login/email/name）。
    """
    repo = g.get_repo(repo_full)
    counter: Counter[str] = Counter()
    meta: Dict[str, Tuple[str, str]] = {}  # key -> (login, email) 便于同时输出

    commits = repo.get_commits(since=since, until=until)
    for c in commits:
        login = c.author.login if c.author else ""
        name  = getattr(getattr(c.commit, "author", None), "name", "") or ""
        email = getattr(getattr(c.commit, "author", None), "email", "") or ""

        # 选择主键
        if prefer == "email" and email:
            key = email.lower()
        elif prefer == "name" and name:
            key = name
        else:
            key = login or email.lower() or name or "(unknown)"

        counter[key] += 1
        meta.setdefault(key, (login, email))

    rows: List[Dict[str, Any]] = []
    for key, cnt in counter.most_common():
        login, email = meta.get(key, ("", ""))
        rows.append({
            "repo": repo_full,
            "author_key": key,
            "author_login": login,
            "author_email": email,
            "commits": cnt
        })

    # 过滤 min_commits
    rows = [r for r in rows if r["commits"] >= min_commits]
    return rows

# --------- 5) 新增：按关键词搜索项目 ----------
def search_repos_by_keyword(
    g: Github,
    keyword: str,
    language: Optional[str] = None,
    min_stars: Optional[int] = None,
    pushed_since: Optional[datetime] = None,
    topic: Optional[str] = None,
    owner: Optional[str] = None,
    sort: str = "updated",          # "stars" | "forks" | "updated"
    order: str = "desc",
    limit: int = 200
) -> List[Dict[str, Any]]:
    """
    使用 Search API 搜索仓库。keyword 会匹配 name/description/readme。
    可叠加 language、stars、pushed:>=、topic、owner 限制。
    """
    # 组装 GitHub 搜索语句
    q = [keyword, "in:name,description,readme"]
    if language:
        q.append(f"language:{language}")
    if min_stars is not None:
        q.append(f"stars:>={min_stars}")
    if pushed_since:
        q.append(f"pushed:>={pushed_since.date().isoformat()}")
    if topic:
        q.append(f"topic:{topic}")
    if owner:
        q.append(f"user:{owner}")   # 对用户；若是组织也可以，用 org: 则写 org:{owner}
    query = " ".join(q)

    rows: List[Dict[str, Any]] = []
    try:
        results = g.search_repositories(query=query, sort=sort, order=order)
        for i, repo in enumerate(results):
            if i >= limit:
                break
            rate_limit_guard(g)
            rows.append({
                "full_name": repo.full_name,
                "name": repo.name,
                "owner": repo.owner.login if repo.owner else "",
                "description": repo.description or "",
                "language": repo.language or "",
                "stargazers_count": repo.stargazers_count,
                "forks_count": repo.forks_count,
                "archived": repo.archived,
                "private": repo.private,
                "updated_at": getattr(repo, "updated_at", ""),
                "pushed_at": getattr(repo, "pushed_at", ""),
                "html_url": repo.html_url,
            })
    except GithubException as e:
        print(f"[warn] search error: {e}", file=sys.stderr)

    return rows


# --------- 6) 新增：按组织获取项目列表 ----------
def list_repos_for_org(
    g: Github,
    org: str,
    repo_type: str = "all",          # "all" | "public" | "private" | "forks" | "sources" | "member"
    include_archived: bool = True,
    sort: str = "updated",           # PyGithub 的 get_repos 支持 sort="updated"/"pushed"/"full_name"（行为以 GitHub 为准）
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    列出组织的仓库。若 include_archived=False 将过滤 archived 仓库。
    """
    rows: List[Dict[str, Any]] = []
    try:
        org_obj = g.get_organization(org)
        repos = org_obj.get_repos(type=repo_type, sort=sort)
        for i, repo in enumerate(repos):
            if i >= limit:
                break
            rate_limit_guard(g)
            if (not include_archived) and repo.archived:
                continue
            rows.append({
                "full_name": repo.full_name,
                "name": repo.name,
                "description": repo.description or "",
                "language": repo.language or "",
                "stargazers_count": repo.stargazers_count,
                "forks_count": repo.forks_count,
                "archived": repo.archived,
                "private": repo.private,
                "updated_at": getattr(repo, "updated_at", ""),
                "pushed_at": getattr(repo, "pushed_at", ""),
                "html_url": repo.html_url,
            })
    except GithubException as e:
        print(f"[warn] org list error: {e}", file=sys.stderr)

    return rows


# --------- 7) 新增：同一作者拥有/Star 的项目列表（合并/可过滤/可排序） ----------
def list_user_repos(
    g: Github,
    login: str,
    mode: str = "both",                 # "owned" | "starred" | "both"
    include_private: bool = False,      # 需要 token 权限且可访问
    include_archived: bool = True,
    include_forks: bool = True,
    sort: str = "updated",              # "updated" | "pushed" | "full_name" | "stars"
    order: str = "desc",
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    列出指定用户的 owned / starred 仓库列表。
    统一输出字段，并用 relation 标记来源（"owned"|"starred"）。
    """
    rows: List[Dict[str, Any]] = []
    u = g.get_user(login)

    def add_repo(repo, relation: str):
        if (not include_archived) and repo.archived:
            return False
        if (not include_forks) and getattr(repo, "fork", False):
            return False
        if (not include_private) and repo.private:
            return False
        rows.append({
            "relation": relation,  # "owned" or "starred"
            "full_name": repo.full_name,
            "name": repo.name,
            "owner": repo.owner.login if repo.owner else "",
            "description": repo.description or "",
            "language": repo.language or "",
            "stargazers_count": repo.stargazers_count,
            "forks_count": repo.forks_count,
            "archived": repo.archived,
            "private": repo.private,
            "updated_at": getattr(repo, "updated_at", ""),
            "pushed_at": getattr(repo, "pushed_at", ""),
            "html_url": repo.html_url,
        })
        return True

    # owned
    if mode in ("owned", "both"):
        print(f"[info] 开始获取用户 {login} 的 owned 仓库...", file=sys.stderr)
        try:
            count = 0
            owned_count = 0
            # 更激进的提前退出：只需要 limit + 一些缓冲即可
            max_collect = limit + 50 if mode == "both" else limit
            repos=u.get_repos(type="owner", sort="updated")
            for repo in repos:
                # 每10次检查一次速率限制，减少检查频率
                if count % 10 == 0:
                    pass #rate_limit_guard(g)
                count += 1
                try:
                    if add_repo(repo, "owned"):
                        owned_count += 1
                    # 减少打印频率，每100个打印一次
                    if count % 100 == 0:
                        print(f"[info] 已处理 {count} 个 owned 仓库，已添加 {owned_count} 个到结果", file=sys.stderr)
                except Exception as e:
                    print(f"[warn] 跳过仓库 {getattr(repo, 'full_name', 'unknown')}: {e}", file=sys.stderr)
                    continue
                # 提前退出：如果已经收集足够多，立即停止
                if len(rows) >= max_collect:
                    print(f"[info] 已收集 {len(rows)} 个仓库（目标: {limit}），提前停止 owned 收集", file=sys.stderr)
                    break
            print(f"[info] owned 仓库处理完成，共处理 {count} 个，添加 {owned_count} 个", file=sys.stderr)
        except Exception as e:
            print(f"[error] 获取 owned 仓库时出错: {e}", file=sys.stderr)

    # starred
    if mode in ("starred", "both"):
        print(f"[info] 开始获取用户 {login} 的 starred 仓库...", file=sys.stderr)
        try:
            count = 0
            starred_count = 0
            # 更激进的提前退出：只需要 limit + 一些缓冲即可
            max_collect = limit + 50 if mode == "both" else limit
            # 设置最大处理数量，避免处理过多（如果用户 star 了上千个）
            max_process = min(limit * 3, 2000) if mode == "both" else limit * 2
            
            # get_starred() 服务端没有 stars 排序；我们在本地统一排序
            repos=u.get_starred()
            for repo in repos:
                # 每10次检查一次速率限制
                if count % 10 == 0:
                    pass #rate_limit_guard(g)
                count += 1
                try:
                    if add_repo(repo, "starred"):
                        starred_count += 1
                    # 减少打印频率，每200个打印一次
                    if count % 200 == 0:
                        print(f"[info] 已处理 {count} 个 starred 仓库，已添加 {starred_count} 个到结果", file=sys.stderr)
                except Exception as e:
                    print(f"[warn] 跳过仓库 {getattr(repo, 'full_name', 'unknown')}: {e}", file=sys.stderr)
                    continue
                # 提前退出：如果已经收集足够多或处理太多，立即停止
                if len(rows) >= max_collect:
                    print(f"[info] 已收集 {len(rows)} 个仓库（目标: {limit}），提前停止 starred 收集", file=sys.stderr)
                    break
                if count >= max_process:
                    print(f"[info] 已处理 {count} 个仓库（达到上限 {max_process}），提前停止 starred 收集", file=sys.stderr)
                    break
            print(f"[info] starred 仓库处理完成，共处理 {count} 个，添加 {starred_count} 个", file=sys.stderr)
        except Exception as e:
            print(f"[error] 获取 starred 仓库时出错: {e}", file=sys.stderr)

    print(f"[info] 开始排序和去重，当前有 {len(rows)} 条记录", file=sys.stderr)
    
    # 去重（如果同一个仓库同时出现在 owned 和 starred，保留 owned）
    # 使用字典记录索引，避免 index() 查找
    seen = {}
    unique_rows = []
    for r in rows:
        full_name = r["full_name"]
        if full_name not in seen:
            seen[full_name] = len(unique_rows)  # 记录索引位置
            unique_rows.append(r)
        elif unique_rows[seen[full_name]]["relation"] == "starred" and r["relation"] == "owned":
            # 如果已存在的是 starred，新的是 owned，替换
            unique_rows[seen[full_name]] = r
    
    rows = unique_rows
    print(f"[info] 去重后剩余 {len(rows)} 条记录", file=sys.stderr)

    # 本地排序
    key_map = {
        "updated":    lambda r: r["updated_at"] or "",
        "pushed":     lambda r: r["pushed_at"] or "",
        "full_name":  lambda r: r["full_name"] or "",
        "stars":      lambda r: r["stargazers_count"] or 0,
    }
    keyfunc = key_map.get(sort, key_map["updated"])
    rows.sort(key=keyfunc, reverse=(order == "desc"))

    # 限量（both 模式下合并后再截断）
    if len(rows) > limit:
        rows = rows[:limit]
        print(f"[info] 截断到 {limit} 条记录", file=sys.stderr)
    
    print(f"[info] 最终返回 {len(rows)} 条记录", file=sys.stderr)
    return rows


# --------- CLI ---------
def main():
    ap = argparse.ArgumentParser(description="GitHub 活动抓取/汇总（PyGithub）")
    sub = ap.add_subparsers(dest="mode", required=True)

    # 1) 跨仓：不同仓库同一作者（明细）
    s1 = sub.add_parser("cross-repos", help="不同仓库同一作者（提交明细）")
    s1.add_argument("--author-login", help="作者 GitHub 登录名")
    s1.add_argument("--author-email", help="作者邮箱（更稳定）")
    s1.add_argument("--since", help="起始时间，如 2025-01-01 或 2025-01-01T00:00:00Z")
    s1.add_argument("--until", help="结束时间，如 2025-11-04 或 2025-11-04T23:59:59Z")
    s1.add_argument("--owner", help="枚举此 owner 的仓库（用户或组织）。不填则默认枚举 author-login 的仓库")
    s1.add_argument("--repo-type", default="owner", choices=["all","owner","member","public","private"])
    s1.add_argument("--max-per-repo", type=int, default=1000)
    s1.add_argument("--out", default="cross_repos.csv")

    # 2) 单仓：同一仓库不同作者（明细）
    s2 = sub.add_parser("repo-authors", help="同一仓库不同作者（提交明细）")
    s2.add_argument("--repo-full", required=True, help="仓库全名 owner/name")
    s2.add_argument("--authors-login", nargs="*", help="作者登录名列表")
    s2.add_argument("--authors-emails", nargs="*", help="作者邮箱列表")
    s2.add_argument("--since", help="起始时间")
    s2.add_argument("--until", help="结束时间")
    s2.add_argument("--max-per-author", type=int, default=1000)
    s2.add_argument("--out", default="repo_authors.csv")

    # 3) 新增：同一作者在哪些仓库（列表）
    s3 = sub.add_parser("repos-by-author", help="同一作者活跃的仓库名列表（含提交数）")
    s3.add_argument("--author-login", help="作者 GitHub 登录名")
    s3.add_argument("--author-email", help="作者邮箱（更稳定）")
    s3.add_argument("--since", help="起始时间")
    s3.add_argument("--until", help="结束时间")
    s3.add_argument("--owner", help="枚举此 owner 的仓库（用户或组织）。不填则默认枚举 author-login 的仓库")
    s3.add_argument("--repo-type", default="owner", choices=["all","owner","member","public","private"])
    s3.add_argument("--min-commits", type=int, default=1, help="最小提交数阈值")
    s3.add_argument("--out", default="repos_by_author.csv")

    # 4) 新增：同一仓库不同作者（作者列表）
    s4 = sub.add_parser("authors-by-repo", help="同一仓库活跃的作者列表（含提交数）")
    s4.add_argument("--repo-full", required=True, help="仓库全名 owner/name")
    s4.add_argument("--since", help="起始时间")
    s4.add_argument("--until", help="结束时间")
    s4.add_argument("--prefer", choices=["login","email","name"], default="login", help="主显示字段偏好")
    s4.add_argument("--min-commits", type=int, default=1, help="最小提交数阈值")
    s4.add_argument("--out", default="authors_by_repo.csv")    
    
    # 5) search-repos：按关键词搜索
    s5 = sub.add_parser("search-repos", help="按关键词搜索项目列表")
    s5.add_argument("--keyword", required=True, help="关键词（匹配 name/description/readme）")
    s5.add_argument("--language", help="语言限定，如 Python/C++/TypeScript")
    s5.add_argument("--min-stars", type=int, help="最小 Star 数，如 50")
    s5.add_argument("--pushed-since", help="最近活跃起始，如 2025-09-01")
    s5.add_argument("--topic", help="限定某个 topic")
    s5.add_argument("--owner", help="限定某个用户/组织的仓库（搜索域缩小）")
    s5.add_argument("--sort", choices=["updated","stars","forks"], default="updated")
    s5.add_argument("--order", choices=["desc","asc"], default="desc")
    s5.add_argument("--limit", type=int, default=200, help="最多返回条数")
    s5.add_argument("--out", default="search_repos.csv")

    # 6) org-repos：按组织列出项目
    s6 = sub.add_parser("org-repos", help="按组织获取项目列表")
    s6.add_argument("--org", required=True, help="组织名")
    s6.add_argument("--repo-type", default="all",
                    choices=["all","public","private","forks","sources","member"])
    s6.add_argument("--include-archived", action="store_true", help="包含 archived 仓库")
    s6.add_argument("--sort", choices=["updated","pushed","full_name"], default="updated")
    s6.add_argument("--limit", type=int, default=500)
    s6.add_argument("--out", default="org_repos.csv")
    
    # 7) user-repos：列出用户 owned/starred/both 仓库
    s7 = sub.add_parser("user-repos", help="列出某用户拥有/Star 的项目列表（可合并）")
    s7.add_argument("--login", required=True, help="GitHub 用户登录名")
    s7.add_argument("--query-mode", dest="query_mode",
                    choices=["owned","starred","both"], default="both", help="查询模式")
    s7.add_argument("--include-private", action="store_true", help="包含私有仓库（需 token 权限）")
    s7.add_argument("--include-archived", action="store_true", help="包含 archived 仓库")
    s7.add_argument("--include-forks", action="store_true", help="包含 fork 仓库")
    s7.add_argument("--sort", choices=["updated","pushed","full_name","stars"], default="updated")
    s7.add_argument("--order", choices=["desc","asc"], default="desc")
    s7.add_argument("--limit", type=int, default=500)
    s7.add_argument("--out", default="user_repos.csv")

    args = ap.parse_args()

    g = gh_client()
    since = parse_dt(args.since) if hasattr(args, "since") else None
    until = parse_dt(args.until) if hasattr(args, "until") else None

    if args.mode == "cross-repos":
        rows = fetch_user_activity_across_repos(
            g=g,
            author_login=args.author_login,
            author_email=args.author_email,
            since=since, until=until,
            owner=args.owner,
            repo_type=args.repo_type,
            max_per_repo=args.max_per_repo,
        )
        keys = ["repo","sha","date","author_login","author_name","author_email","committer_login","title","url"]
        write_csv(rows, args.out, keys)

    elif args.mode == "repo-authors":
        rows = fetch_repo_activity_across_authors(
            g=g,
            repo_full=args.repo_full,
            authors_login=args.authors_login,
            authors_emails=args.authors_emails,
            since=since, until=until,
            max_per_author=args.max_per_author,
        )
        keys = ["repo","sha","date","author_login","author_name","author_email","committer_login","title","url"]
        write_csv(rows, args.out, keys)

    elif args.mode == "repos-by-author":
        rows = list_repos_for_author(
            g=g,
            author_login=args.author_login,
            author_email=args.author_email,
            since=since, until=until,
            owner=args.owner,
            repo_type=args.repo_type,
            min_commits=args.min_commits
        )
        keys = ["repo","commits"]
        write_csv(rows, args.out, keys)

    elif args.mode == "authors-by-repo":
        rows = list_authors_for_repo(
            g=g,
            repo_full=args.repo_full,
            since=since, until=until,
            prefer=args.prefer,
            min_commits=args.min_commits
        )
        keys = ["repo","author_key","author_login","author_email","commits"]
        write_csv(rows, args.out, keys)    
    elif args.mode == "search-repos":
        ps = parse_dt(args.pushed_since)
        rows = search_repos_by_keyword(
            g=g,
            keyword=args.keyword,
            language=args.language,
            min_stars=args.min_stars,
            pushed_since=ps,
            topic=args.topic,
            owner=args.owner,
            sort=args.sort,
            order=args.order,
            limit=args.limit
        )
        keys = ["full_name","name","owner","description","language","stargazers_count",
                "forks_count","archived","private","updated_at","pushed_at","html_url"]
        write_csv(rows, args.out, keys)

    elif args.mode == "org-repos":
        rows = list_repos_for_org(
            g=g,
            org=args.org,
            repo_type=args.repo_type,
            include_archived=args.include_archived,
            sort=args.sort,
            limit=args.limit
        )
        keys = ["full_name","name","description","language","stargazers_count",
                "forks_count","archived","private","updated_at","pushed_at","html_url"]
        write_csv(rows, args.out, keys)    
        
    elif args.mode == "user-repos":
        rows = list_user_repos(
            g=g,
            login=args.login,
            mode=args.query_mode,
            include_private=args.include_private,
            include_archived=args.include_archived,
            include_forks=args.include_forks,
            sort=args.sort,
            order=args.order,
            limit=args.limit
        )
        keys = ["relation","full_name","name","owner","description","language",
                "stargazers_count","forks_count","archived","private","updated_at","pushed_at","html_url"]
        write_csv(rows, args.out, keys)



if __name__ == "__main__":
    main()
