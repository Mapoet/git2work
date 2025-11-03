# Git Work Log Generator with AI Summary

自动生成 Git 工作日志并使用 OpenAI API 生成智能总结的工具。

> **新特性**：现在支持自动检测 git pull 操作，将 pull 时间作为工作会话的开始时间，更准确地反映实际工作时间！

## 功能特性

- 📝 从 Git 提交记录生成详细的工作日志（Markdown 格式）
- 🤖 使用 OpenAI 或 DeepSeek API 自动生成中文工作总结
- 📊 统计代码变更（新增/删除行数、文件数）
- 🎯 支持自定义时间范围、作者过滤
- 🔧 支持自定义系统提示词
- ⏱️ **精细化时间分析**：自动识别工作会话、功能窗口、跨项目交叉时间，并在 AI 总结中生成时间分布图
- 🔄 **并行工作时间检测**：多项目模式下自动识别同时在不同项目上工作的时段，准确评估实际工作时间（避免重复累加）
- 🌐 **远程仓库支持**：支持 GitHub 和 Gitee 远程仓库的 commits 和 PRs（Pull Requests/MRs）查询，无需本地克隆仓库
- 📥 **Git Pull 记录支持**：自动检测 git pull/fetch 操作，将 pull 时间作为工作会话的开始时间，更准确地反映实际工作时间（如果一次会话没有 pull，则使用第一个 commit 时间作为开始时间）

## 安装依赖

```bash
# 基础依赖
pip install openai gitpython requests

# GitHub 支持（可选，如需要查询 GitHub 仓库）
pip install PyGithub
```

## 使用方法

### 方法 1: 使用便捷脚本（推荐）

```bash
# 生成今天的工作日志（带 AI 总结）
./gen_worklog.sh

# 生成指定日期的工作日志
./gen_worklog.sh 2025-10-28

# 生成指定日期的日志并保存到指定文件
./gen_worklog.sh 2025-10-28 worklog.md

#### 作者过滤与多仓
# 仅统计作者(名字或邮箱包含关键字)
AUTHOR="mapoet" ./gen_worklog.sh 2025-10-29

# 多仓库（逗号分隔），并按作者过滤
REPOS="/mnt/d/works/RayTracy,/path/to/another" \
AUTHOR="mapoet" \
./gen_worklog.sh 2025-10-29

```

### 方法 2: 直接使用 Python 脚本

#### 基本用法

```bash
# 生成今天的工作日志（不带 AI 总结）
./git2work.py --days 1 --output worklog_today.md

# 生成指定日期范围的工作日志
./git2work.py --since 2025-10-27 --until 2025-10-29 --output worklog_range.md

# 只生成最近 7 天的日志
./git2work.py --days 7 --output worklog_7days.md
```

#### 多项目与精细化时间分析

```bash
# 多项目：自动汇总“项目→日期→提交”，并在 AI 总结中按项目估算投入时间与主要产出
# 时间统计会自动识别工作会话（默认间隔120分钟，可通过--session-gap-minutes调整）
./git2work.py \
  --repos "/mnt/d/works/RayTracy,/path/to/another" \
  --since 2025-10-28 --until 2025-10-29 \
  --add-summary --provider deepseek --deepseek-model deepseek-chat \
  --session-gap-minutes 60 \
  --output worklog_multi.md --title "多项目工作日志"

./git2work.py --days 30 \
  --author mapoet --output worklog_today.md \
  --add-summary --system-prompt-file system_prompt.txt \
  --repos /mnt/d/works/RayTracy,/mnt/d/works/git2work,/mnt/d/works/vtec \
  --provider deepseek

# 查询 GitHub 仓库（需要 GitHub token）
./git2work.py --github owner/repo --github-token YOUR_TOKEN \
  --since 2025-10-01 --until 2025-10-31 --add-summary \
  --output worklog_github.md

# 查询 Gitee 仓库（需要 Gitee token）
./git2work.py --gitee owner/repo --gitee-token YOUR_TOKEN \
  --days 7 --add-summary --output worklog_gitee.md

# 混合查询本地和远程仓库
./git2work.py \
  --repo /mnt/d/works/RayTracy \
  --github owner/repo1 --gitee owner/repo2 \
  --days 30 --add-summary --output worklog_mixed.md

# 多仓库查询（支持混合本地和远程）
./git2work.py \
  --repos /mnt/d/works/RayTracy,/mnt/d/works/git2work \
  --github owner/repo1,owner/repo2 \
  --gitee owner/repo3 \
  --days 30 --add-summary --output worklog_all.md
```

**Git Pull 记录说明**：
- **自动检测**：脚本会自动检测本地仓库的 git pull/fetch/merge 操作
- **会话开始时间**：如果会话的第一个 commit 之前有 pull 操作（2 小时内），会使用 pull 时间作为会话开始时间
- **示例场景**：
  - 场景 1：09:00 pull 项目 → 09:05 开始 commit → 会话开始时间：09:00（使用 pull 时间）
  - 场景 2：09:05 直接 commit（没有 pull）→ 会话开始时间：09:05（使用第一个 commit 时间）
  - 场景 3：07:00 pull 项目 → 09:05 commit（超过 2 小时）→ 会话开始时间：09:05（pull 时间超过有效范围，使用 commit 时间）
- **优势**：更准确地反映实际工作时间，特别是在协作开发场景中，pull 操作通常标志着工作开始

**时间分析功能说明**：
- **工作会话**：
  - 根据 commit 时间戳自动识别连续工作时段（相邻提交间隔小于指定分钟数视为同一会话）
  - **Git Pull 记录支持**：自动检测 git pull/fetch 操作，作为会话开始时间参考
    - 如果会话的第一个 commit 之前有 pull 操作（且在 2 小时内），使用 pull 时间作为会话开始时间
    - 如果没有找到合适的 pull 记录，使用第一个 commit 时间作为会话开始时间
    - 这样可以更准确地反映实际工作时间，因为协作开发时通常先 pull 项目再开始工作
- **功能窗口**：按 commit message 类型（feat/fix/docs/build/refactor等）统计各功能的起止时间
- **跨项目并行工作时间检测**：
  - 多项目模式下，自动检测不同项目在时间上重叠的工作时段
  - 识别同时在不同项目上工作的并行时段，标注涉及的多个项目
  - 统计并行时段的起止时间与重叠时长
  - **重要**：并行工作时间不应简单累加，实际投入时间以重叠时段的最大值为准
- **跨项目分析**：自动统计项目间切换的时间点，识别项目上下文切换模式
- **时间分布图**：AI 总结会自动生成包含会话时间轴、提交分布、并行工作标注的可视化图表（Markdown/Mermaid 格式）

#### 使用 AI 总结

```bash
# 需要先设置 OpenAI API Key
export OPENAI_API_KEY="your-api-key"

# 生成带 AI 总结的工作日志
./git2work.py --days 1 --output worklog_today.md --add-summary --title "今日工作日志"

# 使用自定义系统提示词
./git2work.py --days 1 --output worklog_today.md --add-summary --system-prompt-file system_prompt.txt

# 指定 OpenAI 模型
./git2work.py --days 1 --output worklog_today.md --add-summary --openai-model "gpt-4o-mini"
```

#### 命令行参数说明

```bash
./git2work.py --help
```

主要参数：
- `--repo`: Git 仓库路径（单仓库，默认：/mnt/d/works/RayTracy）
- `--repos`: 多仓库路径（逗号分隔，如 "/path/repo1,/path/repo2"）
- `--github`: GitHub 仓库（格式：OWNER/REPO，多个用逗号分隔，如 "owner1/repo1,owner2/repo2"）
- `--gitee`: Gitee 仓库（格式：OWNER/REPO，多个用逗号分隔，如 "owner1/repo1,owner2/repo2"）
- `--github-token`: GitHub Personal Access Token（或使用环境变量 GITHUB_TOKEN）
- `--gitee-token`: Gitee Personal Access Token（或使用环境变量 GITEE_TOKEN）
- `--since`: 开始日期（ISO 或 YYYY-MM-DD 格式）
- `--until`: 结束日期（ISO 或 YYYY-MM-DD 格式）
- `--days`: 最近 N 天的提交
- `--author`: 按作者过滤（作者名或邮箱包含关键字）
- `--output`: 输出文件路径
- `--title`: 日志标题
- `--add-summary`: 添加 AI 生成的总结（包含时间分布图）
- `--session-gap-minutes`: 工作会话识别间隔（默认60分钟，超过此间隔视为新会话）
- `--openai-key`: OpenAI API Key（或使用环境变量 OPENAI_API_KEY）
- `--openai-model`: OpenAI 模型（默认：gpt-4o-mini）
- `--provider`: LLM 提供方（openai 或 deepseek，默认 openai）
- `--deepseek-key`: DeepSeek API Key（或使用环境变量 DEEPSEEK_API_KEY）
- `--deepseek-model`: DeepSeek 模型（默认：deepseek-chat）
- `--system-prompt-file`: 自定义系统提示词文件路径

## 自定义系统提示词

编辑 `system_prompt.txt` 文件来自定义 AI 总结的生成方式。

示例：

```
你是一个专业的技术文档撰写助手。根据提供的 git commit 记录，生成一份结构化的中文工作总结。

要求：
1. 使用 Markdown 格式
2. 总结主要包括：
   - 今日工作概述（3-5句）
   - 主要完成内容（按模块分类）
   - 统计数据（提交数、代码变更、涉及文件等）
   - 技术亮点或重要改进
3. 语言简洁专业，避免过于冗长
4. 重点关注代码改进、功能增强、问题修复等技术性内容
```

## 配置

### 环境变量

- `OPENAI_API_KEY`: OpenAI API Key
- `DEEPSEEK_API_KEY`: DeepSeek API Key
- `GITHUB_TOKEN`: GitHub Personal Access Token（用于查询 GitHub 仓库）
- `GITEE_TOKEN`: Gitee Personal Access Token（用于查询 Gitee 仓库）
- `GIT_REPO`: 默认 Git 仓库路径（单仓库模式）
- `REPOS`: 多个仓库路径（逗号分隔，多仓库模式）
- `PROVIDER`: LLM 提供方（openai 或 deepseek）
- `GAP_MINUTES`: 工作会话识别间隔分钟数（默认1440=24小时，脚本中使用）
- `SCRIPT_OUTPUT_DIR`: 脚本输出目录
- `AUTHOR`: 作者过滤关键字（通过 `gen_worklog.sh` 使用时）

### 示例

```bash
export OPENAI_API_KEY="sk-xxxxx"
export GITHUB_TOKEN="ghp_xxxxx"
export GITEE_TOKEN="your-gitee-token"
export GIT_REPO="/path/to/your/repo"
export SCRIPT_OUTPUT_DIR="/path/to/output"
```

## 输出格式

生成的工作日志包含：

1. **标题和摘要**：总提交数统计、项目数（多项目模式）
2. **时间统计信息**（多项目模式或启用时间分析时）：
   - **跨项目并行工作时间统计**（多项目模式）：
     - 自动检测并列出并行工作时段的数量与总重叠时长
     - 每个并行时段的起止时间、重叠时长、涉及的多个项目
     - 重要提示：并行工作时间不应简单累加
   - **各项目时间统计**：
     - 工作会话统计：会话数量、总时长、每个会话的起止时间与提交数
     - **会话开始时间优化**：
       - 自动检测 git pull/fetch 操作，作为会话开始时间参考
       - 如果会话的第一个 commit 之前有 pull 操作（且在 2 小时内），使用 pull 时间作为会话开始时间
       - 如果没有找到合适的 pull，使用第一个 commit 时间作为会话开始时间
       - 这样可以更准确地反映实际工作时间，因为协作开发时通常先 pull 项目再开始工作
     - 并行会话标记：标注哪些会话属于并行工作时段
   - **功能窗口统计**：按类型（feat/fix/docs等）统计各功能的起止时间与提交数
3. **按日期分组的提交记录**：
   - 提交 SHA、时间、信息
   - 代码统计（新增/删除行数）
     - 本地仓库：完整的文件变更统计
     - 远程仓库：无法获取 numstat，显示为 0（但会标注为 PR 或 commit）
   - 修改的文件列表（仅本地仓库）
   - 完整的 commit message（本地仓库）或 PR 标题（远程仓库）
   - 远程仓库的 PR 会以 `PR#123` 格式显示 SHA
4. **AI 总结**（启用 `--add-summary` 时）：
   - 工作概述（含作者标注，如有过滤）
   - 主要完成内容（按模块分类）
   - 统计数据（提交数、代码变更、涉及文件等）
   - **工作内容时间分布图**（基于会话信息自动生成，Markdown/Mermaid 格式）：
     - 包含各工作会话的起止时间范围
     - 标注并行工作时段（多项目模式）
     - 展示会话之间的时间间隔与工作节奏
     - 项目切换时间点（如有）
   - 技术亮点或重要改进
   - 多项目模式下：
     - 按项目分别估算投入时间与主要产出
     - **特别注意并行工作时间**：在评估总投入时间时，会将并行时段考虑在内，避免重复计算

## 核心功能详解

### Git Pull 记录支持

工具支持自动检测 git pull/fetch 操作，并将其作为工作会话的开始时间，更准确地反映实际工作时间。

#### 工作原理

1. **Pull 记录获取**：
   - 使用 `git reflog` 获取指定时间范围内的操作历史
   - 识别 pull/fetch/merge 等操作（过滤掉 checkout、commit、reset 等无关操作）
   - 解析操作时间戳，筛选在查询时间范围内的记录

2. **会话开始时间计算**：
   - 为每个工作会话查找第一个 commit 之前最近的 pull 操作
   - 如果 pull 在 commit 之前且在 **2 小时内**，使用 pull 时间作为会话开始时间
   - 如果 pull 时间超过 2 小时或没有找到 pull，使用第一个 commit 时间作为开始时间

3. **时间范围**：
   - Pull 记录有效范围：2 小时内的 pull 视为有效（可在代码中调整）
   - 超过 2 小时的 pull 视为不相关（可能是前一天的操作）

#### 适用场景与示例

**场景 1：协作开发（有 pull 记录）**
```
09:00 - git pull（拉取最新代码）
09:05 - commit: feat: 添加新功能
09:30 - commit: fix: 修复 bug
10:00 - commit: docs: 更新文档

会话开始时间：09:00（使用 pull 时间）
会话结束时间：10:00
会话时长：60 分钟
```

**场景 2：单机开发（无 pull 记录）**
```
09:05 - commit: feat: 添加新功能
09:30 - commit: fix: 修复 bug

会话开始时间：09:05（使用第一个 commit 时间）
会话结束时间：09:30
会话时长：25 分钟
```

**场景 3：Pull 时间过久（超过 2 小时）**
```
07:00 - git pull（早上拉取代码）
09:30 - commit: feat: 添加新功能（2.5 小时后）

会话开始时间：09:30（pull 超过有效范围，使用 commit 时间）
```

#### 技术细节

- **Pull 操作识别**：
  - 通过 `git reflog` 解析操作历史，识别包含以下关键词的操作：`pull`、`fetch`、`merge`、`update`、`rebase`
  - 自动过滤掉无关操作（如 `checkout`、`commit`、`reset`、`branch`、`switch` 等）
  - 支持多种 pull 场景：`pull: Fast-forward`、`pull: Merge`、`fetch`、`merge` 等

- **时间匹配算法**：
  - 为每个工作会话的第一个 commit 查找之前的 pull 操作
  - 使用倒序遍历（从最近到最早），找到第一个在 commit 之前的 pull
  - 时间有效性检查：pull 必须在 commit 之前，且时间差不超过 2 小时
  - 如果多个会话，每个会话独立查找对应的 pull 记录

- **性能优化**：
  - Pull 记录获取失败不会影响主流程（静默失败，返回空列表）
  - 如果仓库没有 reflog 或查询时间范围内没有 pull，不影响 commit 处理和会话计算
  - Pull 记录只在本地仓库处理，远程仓库直接跳过

#### 注意事项

- **仅本地仓库支持**：GitHub/Gitee 等远程仓库无法获取 pull 记录（仅查询 commits 和 PRs）
- **依赖 reflog**：如果仓库没有 reflog 或 reflog 已过期，会静默跳过，不影响主流程
- **有效时间范围**：Pull 在第一个 commit 之前 2 小时内才被视为有效（可根据需要调整）
- **自动处理**：所有处理都是自动的，无需额外配置
- **多项目支持**：多项目模式下，每个本地仓库独立获取和处理 pull 记录

## 示例

```bash
# 生成今天的工作日志（自动使用 pull 记录优化会话时间）
./gen_worklog.sh

# 生成指定日期的工作日志
./gen_worklog.sh 2025-10-28

# 生成带自定义提示词的日志
./git2work.py --days 1 --output worklog.md --add-summary --system-prompt-file custom_prompt.txt

# 查询 GitHub 仓库并生成工作日志（远程仓库无法获取 pull 记录）
./git2work.py --github owner/repo --github-token YOUR_TOKEN \
  --days 7 --add-summary --output worklog_github.md

# 混合查询本地和远程仓库（本地仓库会自动使用 pull 记录）
./git2work.py \
  --repo /mnt/d/works/RayTracy \
  --github owner/repo1 --gitee owner/repo2 \
  --days 30 --add-summary --output worklog_mixed.md
```

## 注意事项

1. 确保已安装必要的 Python 包（`openai`, `gitpython`, `requests`）
2. 如需查询 GitHub 仓库，需要安装 `PyGithub`：`pip install PyGithub`
3. 需要有效的 OpenAI/DeepSeek API Key（如使用 AI 总结功能）
4. 查询远程仓库需要对应的 token：
   - GitHub：需要 Personal Access Token（可在 GitHub Settings > Developer settings > Personal access tokens 创建）
   - Gitee：需要 Personal Access Token（可在 Gitee 设置 > 安全设置 > 私人令牌 创建）
5. 远程仓库查询限制：
   - 无法获取文件变更统计（numstat），这些字段会显示为 0
   - 某些情况下无法获取完整的 commit body
   - PRs 按 `updated_at` 时间筛选，而不是创建时间
6. **Git Pull 记录检测**：
   - 仅对本地仓库有效（通过 `git reflog` 获取）
   - 远程仓库（GitHub/Gitee）无法检测 pull 操作
   - Pull 记录有效范围：如果 pull 在第一个 commit 之前且在 2 小时内，会使用 pull 时间作为会话开始时间
   - 如果仓库没有 reflog 或 reflog 已过期，会静默跳过，不影响主流程
   - Pull 操作识别关键词：`pull`、`fetch`、`merge`、`update`、`rebase`
7. API 调用会产生费用（OpenAI/DeepSeek）
8. 建议使用 `gpt-4o-mini` 或 `deepseek-chat` 模型以节省成本
