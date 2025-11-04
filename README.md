# GitHub Activity Analyzer & Git Work Log Generator

> ⚠️ **项目状态说明**
> 
> **本项目已停止研发**，后续功能将移植到 [autoGit-MCP](https://github.com/Mapoet/autoGit-MCP) 项目中进行持续更新。
> 
> 请关注新项目：[https://github.com/Mapoet/autoGit-MCP](https://github.com/Mapoet/autoGit-MCP)

本项目包含两个核心工具，用于 GitHub/Git 活动分析和工作日志生成：

1. **GitHub 活动分析工具（git_activity.py）**：数据收集与发现工具，用于发现和分析 GitHub 仓库活动
2. **Git Work Log Generator（git2work.py）**：工作日志生成工具，基于 Git 提交记录生成详细的工作日志和 AI 总结

## 工具关系

两个工具可以独立使用，也可以配合使用：

- **独立使用**：`git_activity.py` 用于 GitHub 仓库分析，`git2work.py` 用于本地或远程仓库的工作日志生成
- **配合使用**：先用 `git_activity.py` 发现和分析相关仓库，再用 `git2work.py` 生成这些仓库的工作日志

## 项目结构

```
git2work/
├── scripts/
│   ├── git_activity.py      # GitHub 活动抓取/汇总工具（数据收集）
│   ├── git2work.py          # 工作日志生成工具（数据分析与报告）
│   ├── gen_worklog.sh       # 便捷生成脚本
│   ├── system_prompt.txt    # 系统提示词模板
│   └── README.md            # 详细使用文档
├── .gitignore
└── README.md                # 项目说明
```

## 安装与配置

### 1. 安装依赖

```bash
# 基础依赖（git2work.py 必需）
pip install openai gitpython requests

# GitHub 支持（git_activity.py 和 git2work.py 的 GitHub 功能）
pip install PyGithub python-dateutil
```

### 2. 设置 API Key

```bash
# OpenAI（用于 AI 总结）
export OPENAI_API_KEY="your-openai-key"

# DeepSeek（用于 AI 总结）
export DEEPSEEK_API_KEY="your-deepseek-key"

# GitHub（用于查询 GitHub 仓库）
export GITHUB_TOKEN="your-github-token"

# Gitee（用于查询 Gitee 仓库）
export GITEE_TOKEN="your-gitee-token"
```

---

## 工具一：GitHub 活动分析工具（git_activity.py）

**用途**：数据收集与发现工具，用于分析 GitHub 上的代码活动，发现相关仓库。

### 功能特性

- 📊 **跨仓库活动分析**：查询指定作者在多个仓库中的提交记录
- 📈 **仓库活动统计**：统计同一仓库中不同作者的活动情况
- 🔍 **作者活跃仓库列表**：列出指定作者活跃的仓库及其提交数
- 👥 **仓库作者列表**：列出指定仓库中的活跃作者及其提交数
- 🔎 **仓库搜索**：按关键词、语言、Star 数等条件搜索仓库
- 🏢 **组织仓库列表**：列出指定组织的所有仓库
- ⭐ **用户仓库列表**：列出用户拥有或 Star 的项目（支持合并查询）

### 快速开始

```bash
cd scripts

# 查询指定作者在哪些仓库有活动
python git_activity.py repos-by-author \
  --author-login Mapoet \
  --since 2025-01-01 --until 2025-11-04 \
  --min-commits 3 \
  --out repos_by_author.csv

# 查询用户拥有或 Star 的仓库
python git_activity.py user-repos \
  --login mapoet \
  --query-mode both \
  --include-forks \
  --sort updated --order desc \
  --limit 300 \
  --out user_repos.csv

# 按关键词搜索仓库
python git_activity.py search-repos \
  --keyword "ray tracing" \
  --language C++ \
  --min-stars 100 \
  --limit 200 \
  --out search_repos.csv
```

### 支持的查询模式

1. **cross-repos**：不同仓库同一作者（提交明细）
2. **repo-authors**：同一仓库不同作者（提交明细）
3. **repos-by-author**：同一作者在哪些仓库有活动（列表 + 提交数）
4. **authors-by-repo**：同一仓库哪些作者有活动（列表 + 提交数）
5. **search-repos**：按关键词搜索项目列表
6. **org-repos**：按组织获取项目列表
7. **user-repos**：列出某用户拥有/Star 的项目列表（可合并）

**详细使用说明**：查看 [scripts/README.md](scripts/README.md#github-活动分析工具-git_activitypy)

---

## 工具二：Git Work Log Generator（git2work.py）

**用途**：工作日志生成工具，基于 Git 提交记录生成详细的工作日志和 AI 总结。

### 功能特性

- 📝 从 Git 提交记录生成详细的工作日志（Markdown 格式）
- 🤖 使用 OpenAI 或 DeepSeek API 自动生成中文工作总结
- 📊 统计代码变更（新增/删除行数、文件数）
- 🎯 支持自定义时间范围、作者过滤
- 🔧 支持自定义系统提示词
- 🔄 支持多 LLM 提供商（OpenAI / DeepSeek）
- 🧩 多项目分析：支持 `--repos` 多仓库输入，输出按"项目→日期→提交"归档
- 👤 作者过滤：通过 `--author` 或脚本环境变量 `AUTHOR` 仅统计指定作者/邮箱
- ⏱️ 精细化时间分析：基于 commit 时间戳统计工作会话、功能窗口、跨项目交叉时间，并在 AI 总结中绘制工作内容时间分布图
- 🔄 并行工作时间检测：多项目模式下自动识别同时在不同项目上工作的时段，避免重复计算实际工作时间
- 🌐 **远程仓库支持**：支持 GitHub 和 Gitee 远程仓库的 commits 和 PRs（Pull Requests/MRs）查询，无需本地克隆仓库
- 📥 **Git Pull 记录支持**：自动检测 git pull/fetch 操作，将 pull 时间作为工作会话的开始时间，更准确地反映实际工作时间

### 快速开始

```bash
cd scripts

# 生成今天的工作日志（使用默认 LLM）
./gen_worklog.sh

# 使用 DeepSeek（环境变量控制 LLM 提供方）
PROVIDER=deepseek ./gen_worklog.sh

# 使用 OpenAI（并指定模型）
PROVIDER=openai OPENAI_MODEL=gpt-4o-mini ./gen_worklog.sh

# 生成指定日期（并按作者过滤）
AUTHOR="mapoet" ./gen_worklog.sh 2025-10-29

# 多仓库输入（逗号分隔）
REPOS="/mnt/d/works/RayTracy,/path/to/another" ./gen_worklog.sh 2025-10-29

# 查询 GitHub 仓库（需要设置 GITHUB_TOKEN 环境变量）
python git2work.py --github owner/repo --github-token YOUR_TOKEN --days 7

# 查询 Gitee 仓库（需要设置 GITEE_TOKEN 环境变量）
python git2work.py --gitee owner/repo --gitee-token YOUR_TOKEN --days 7

# 混合查询本地和远程仓库
python git2work.py --repo /path/to/local/repo --github owner/repo --days 7

# 多仓库查询（支持混合本地和远程）
python git2work.py --github owner/repo1,owner/repo2 --gitee owner/repo3 --days 30

# 自定义会话间隔（默认1440分钟=24小时，可通过GAP_MINUTES环境变量调整）
GAP_MINUTES=60 ./gen_worklog.sh 2025-10-29
```

### 核心功能说明

#### Git Pull 记录支持

工具支持自动检测 git pull/fetch 操作，并将其作为工作会话的开始时间，更准确地反映实际工作时间：

- **工作原理**：
  - 使用 `git reflog` 获取指定时间范围内的 pull/fetch/merge 操作记录
  - 为每个工作会话查找第一个 commit 之前最近的 pull 操作
  - 如果 pull 在 commit 之前且在 2 小时内，使用 pull 时间作为会话开始时间
  - 如果没有找到合适的 pull，使用第一个 commit 时间作为会话开始时间

- **适用场景**：
  - 协作开发：每日开始工作时先 pull 项目，pull 时间更准确地反映工作开始
  - 单机开发：如果没有 pull 记录，仍使用 commit 时间作为开始时间
  - 远程仓库：GitHub/Gitee 仓库无法获取 pull 记录（仅本地仓库支持）

- **示例**：
  ```
  09:00 - git pull（拉取最新代码）
  09:05 - 第一次 commit
  09:30 - 第二次 commit
  
  会话开始时间：09:00（使用 pull 时间）
  会话结束时间：09:30
  会话时长：60 分钟（从 pull 到最后一个 commit）
  ```

**详细使用说明**：查看 [scripts/README.md](scripts/README.md)

---

## 使用场景示例

### 场景 1：发现和分析 GitHub 仓库活动

```bash
# 步骤 1：使用 git_activity.py 发现相关仓库
python git_activity.py repos-by-author \
  --author-login Mapoet \
  --since 2025-01-01 --until 2025-11-04 \
  --min-commits 3 \
  --out repos_by_author.csv

# 步骤 2：从结果中选择仓库，使用 git2work.py 生成工作日志
python git2work.py \
  --github owner/repo1,owner/repo2 \
  --days 30 \
  --add-summary \
  --output worklog.md
```

### 场景 2：搜索特定技术栈的仓库并生成日志

```bash
# 步骤 1：搜索相关仓库
python git_activity.py search-repos \
  --keyword "vulkan ray tracing" \
  --language C++ \
  --min-stars 50 \
  --limit 10 \
  --out relevant_repos.csv

# 步骤 2：为感兴趣的仓库生成工作日志
python git2work.py \
  --github owner/repo1 \
  --days 7 \
  --add-summary \
  --output worklog.md
```

### 场景 3：分析本地项目并生成工作日志

```bash
# 直接使用 git2work.py 分析本地仓库
./gen_worklog.sh 2025-10-29
```

---

## 详细文档

- **完整使用说明**：查看 [scripts/README.md](scripts/README.md)
- **GitHub 活动分析工具详细文档**：查看 [scripts/README.md#github-活动分析工具-git_activity.py](scripts/README.md#github-活动分析工具-git_activitypy)

## License

MIT License（见 `LICENSE`）
