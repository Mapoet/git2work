# Git Work Log Generator

> ⚠️ **项目状态说明**
> 
> **本项目已停止研发**，后续功能将移植到 [autoGit-MCP](https://github.com/Mapoet/autoGit-MCP) 项目中进行持续更新。
> 
> 请关注新项目：[https://github.com/Mapoet/autoGit-MCP](https://github.com/Mapoet/autoGit-MCP)

自动生成 Git 工作日志并使用 AI（OpenAI/DeepSeek）生成智能总结的工具。

## 功能特性

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
- 📥 **Git Pull 记录支持**：自动检测 git pull/fetch 操作，将 pull 时间作为工作会话的开始时间，更准确地反映实际工作时间（如果一次会话没有 pull，则使用第一个 commit 时间作为开始时间）

## 项目结构

```
git2work/
├── scripts/
│   ├── git2work.py          # 核心 Python 脚本
│   ├── gen_worklog.sh       # 便捷生成脚本
│   ├── system_prompt.txt    # 系统提示词模板
│   └── README.md            # 详细使用文档
├── .gitignore
└── README.md                # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
# 基础依赖
pip install openai gitpython requests

# GitHub 支持（可选，如需要查询 GitHub 仓库）
pip install PyGithub
```

### 2. 设置 API Key

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-key"

# DeepSeek
export DEEPSEEK_API_KEY="your-deepseek-key"

# GitHub（如需查询 GitHub 仓库）
export GITHUB_TOKEN="your-github-token"

# Gitee（如需查询 Gitee 仓库）
export GITEE_TOKEN="your-gitee-token"
```

### 3. 生成工作日志

```bash
# 生成今天的工作日志（使用默认 LLM）
cd scripts
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

## 核心功能说明

### Git Pull 记录支持

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

- **技术实现**：
  - 使用 `git reflog` 获取操作历史，解析 pull/fetch/merge 操作时间
  - 自动识别相关操作（pull、fetch、merge），过滤无关操作（checkout、commit 等）
  - 为每个会话查找第一个 commit 之前 2 小时内的 pull 操作
  - 如果找到合适的 pull，使用 pull 时间；否则使用第一个 commit 时间
  - 支持多项目模式，每个本地仓库独立处理 pull 记录

## 详细文档

查看 [scripts/README.md](scripts/README.md) 获取完整的使用说明。

## License

MIT License（见 `LICENSE`）

