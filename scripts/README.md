# GitHub Activity Analyzer & Git Work Log Generator

本目录包含两个核心工具的详细使用文档：

1. **GitHub 活动分析工具（git_activity.py）**：数据收集与发现工具，用于分析 GitHub 上的代码活动
2. **Git Work Log Generator（git2work.py）**：工作日志生成工具，基于 Git 提交记录生成详细的工作日志和 AI 总结

---

## 工具一：GitHub 活动分析工具（git_activity.py）

`git_activity.py` 是一个基于 PyGithub 的 GitHub 活动抓取和汇总工具，支持多种查询模式，可以帮你分析 GitHub 上的代码活动。

### 安装依赖

```bash
pip install PyGithub python-dateutil
```

### 认证设置

```bash
# 设置 GitHub Personal Access Token（可选，但建议设置以提高 API 速率限制）
export GITHUB_TOKEN="your-github-token"

# 未设置 token 时，将按未授权调用（速率限制 60/h）
```

### 支持的查询模式

#### 1. cross-repos：不同仓库同一作者（提交明细）

查询指定作者在多个仓库中的提交记录。

```bash
python git_activity.py cross-repos \
  --author-login Mapoet \
  --since 2025-01-01 --until 2025-11-04 \
  --owner someuser \
  --repo-type all \
  --max-per-repo 1000 \
  --out cross_repos.csv
```

**参数说明**：
- `--author-login`：作者 GitHub 登录名
- `--author-email`：作者邮箱（更稳定，可选）
- `--since`：起始时间（ISO 或 YYYY-MM-DD 格式）
- `--until`：结束时间
- `--owner`：枚举此 owner 的仓库（用户或组织）。不填则默认枚举 author-login 的仓库
- `--repo-type`：仓库类型（`owner`/`member`/`all`/`public`/`private`，默认 `owner`）
- `--max-per-repo`：每个仓库最多查询的提交数（默认 1000）

**输出字段**：`repo`, `sha`, `date`, `author_login`, `author_name`, `author_email`, `committer_login`, `title`, `url`

#### 2. repo-authors：同一仓库不同作者（提交明细）

查询指定仓库中多个作者的提交记录。

```bash
python git_activity.py repo-authors \
  --repo-full owner/repo \
  --authors-login Mapoet User2 \
  --since 2025-01-01 --until 2025-11-04 \
  --max-per-author 1000 \
  --out repo_authors.csv
```

**参数说明**：
- `--repo-full`：仓库全名（格式：`owner/name`，必填）
- `--authors-login`：作者登录名列表（可选，不提供则返回时间窗内所有提交）
- `--authors-emails`：作者邮箱列表（可选）
- `--max-per-author`：每个作者最多查询的提交数（默认 1000）

#### 3. repos-by-author：同一作者在哪些仓库有活动（列表 + 提交数）

列出指定作者活跃的仓库及其提交数（按提交数降序）。

```bash
python git_activity.py repos-by-author \
  --author-login Mapoet \
  --since 2025-01-01 --until 2025-11-04 \
  --owner someuser \
  --repo-type all \
  --min-commits 3 \
  --out repos_by_author.csv
```

**参数说明**：
- `--min-commits`：最小提交数阈值（默认 1）
- 其他参数同 `cross-repos`

**输出字段**：`repo`, `commits`

#### 4. authors-by-repo：同一仓库哪些作者有活动（列表 + 提交数）

列出指定仓库中的活跃作者及其提交数（按提交数降序）。

```bash
python git_activity.py authors-by-repo \
  --repo-full owner/repo \
  --since 2025-01-01 --until 2025-11-04 \
  --prefer login \
  --min-commits 1 \
  --out authors_by_repo.csv
```

**参数说明**：
- `--prefer`：主显示字段偏好（`login`/`email`/`name`，默认 `login`）

**输出字段**：`repo`, `author_key`, `author_login`, `author_email`, `commits`

#### 5. search-repos：按关键词搜索项目列表

使用 GitHub Search API 搜索仓库，支持多种过滤条件。

```bash
python git_activity.py search-repos \
  --keyword "ray tracing" \
  --language C++ \
  --min-stars 100 \
  --pushed-since 2025-09-01 \
  --topic rendering \
  --owner NVIDIA \
  --sort updated \
  --order desc \
  --limit 200 \
  --out search_repos.csv
```

**参数说明**：
- `--keyword`：关键词（匹配 name/description/readme，必填）
- `--language`：语言限定（如 `Python`/`C++`/`TypeScript`）
- `--min-stars`：最小 Star 数
- `--pushed-since`：最近活跃起始时间（如 `2025-09-01`）
- `--topic`：限定某个 topic
- `--owner`：限定某个用户/组织的仓库
- `--sort`：排序方式（`updated`/`stars`/`forks`，默认 `updated`）
- `--order`：排序顺序（`desc`/`asc`，默认 `desc`）
- `--limit`：最多返回条数（默认 200，范围 1-2000）

**输出字段**：`full_name`, `name`, `owner`, `description`, `language`, `stargazers_count`, `forks_count`, `archived`, `private`, `updated_at`, `pushed_at`, `html_url`

#### 6. org-repos：按组织获取项目列表

列出指定组织的所有仓库。

```bash
python git_activity.py org-repos \
  --org NVIDIA-RTX \
  --repo-type all \
  --include-archived \
  --sort updated \
  --limit 500 \
  --out org_repos.csv
```

**参数说明**：
- `--org`：组织名（必填）
- `--repo-type`：仓库类型（`all`/`public`/`private`/`forks`/`sources`/`member`，默认 `all`）
- `--include-archived`：包含 archived 仓库（默认不包含）
- `--sort`：排序方式（`updated`/`pushed`/`full_name`，默认 `updated`）
- `--limit`：最多返回条数（默认 500，范围 1-5000）

#### 7. user-repos：列出某用户拥有/Star 的项目列表（可合并）

列出指定用户拥有或 Star 的仓库列表，支持合并查询和多种过滤排序选项。

```bash
python git_activity.py user-repos \
  --login mapoet \
  --query-mode both \
  --include-private \
  --include-archived \
  --include-forks \
  --sort updated \
  --order desc \
  --limit 300 \
  --out user_repos.csv
```

**参数说明**：
- `--login`：GitHub 用户登录名（必填）
- `--query-mode`：查询模式（`owned`/`starred`/`both`，默认 `both`）
  - `owned`：仅查询用户拥有的仓库
  - `starred`：仅查询用户 Star 的仓库
  - `both`：合并查询 owned 和 starred，然后统一排序和限量
- `--include-private`：包含私有仓库（需 token 权限）
- `--include-archived`：包含 archived 仓库（默认不包含）
- `--include-forks`：包含 fork 仓库（默认不包含）
- `--sort`：排序方式（`updated`/`pushed`/`full_name`/`stars`，默认 `updated`）
- `--order`：排序顺序（`desc`/`asc`，默认 `desc`）
- `--limit`：最多返回条数（默认 500）

**输出字段**：`relation`（`owned` 或 `starred`）, `full_name`, `name`, `owner`, `description`, `language`, `stargazers_count`, `forks_count`, `archived`, `private`, `updated_at`, `pushed_at`, `html_url`

**性能优化**：
- 自动去重：如果同一个仓库同时出现在 owned 和 starred，保留 owned
- 提前退出：收集到足够数据后提前停止，避免处理过多仓库
- 速率限制保护：自动检测 API 速率限制并等待重置

### 使用技巧

1. **时间格式**：支持 ISO 格式（`2025-01-01T00:00:00Z`）或简单日期格式（`2025-01-01`）

2. **速率限制**：
   - 未设置 token：60 次/小时
   - 设置 token：5000 次/小时
   - 工具会自动检测速率限制并在需要时等待

3. **调试输出**：所有模式都会输出详细的进度信息到 stderr，方便跟踪执行过程

4. **错误处理**：单个仓库访问失败不会影响整体流程，会继续处理其他仓库

5. **性能建议**：
   - 对于大量仓库的查询，合理设置 `--limit` 参数
   - 使用时间范围过滤减少查询量
   - `user-repos` 模式在 `both` 模式下会自动优化，避免处理过多数据

### 示例场景

#### 场景 1：查询自己在某个组织的所有仓库中的活动

```bash
python git_activity.py repos-by-author \
  --author-login Mapoet \
  --since 2025-01-01 --until 2025-11-04 \
  --owner someorg \
  --repo-type all \
  --min-commits 5 \
  --out my_activity.csv
```

#### 场景 2：搜索特定技术栈的仓库

```bash
python git_activity.py search-repos \
  --keyword "vulkan ray tracing" \
  --language C++ \
  --min-stars 50 \
  --sort stars \
  --order desc \
  --limit 100 \
  --out vulkan_repos.csv
```

#### 场景 3：分析某个仓库的贡献者

```bash
python git_activity.py authors-by-repo \
  --repo-full owner/repo \
  --since 2025-01-01 --until 2025-11-04 \
  --min-commits 10 \
  --out contributors.csv
```

#### 场景 4：获取用户的所有项目（owned + starred）

```bash
python git_activity.py user-repos \
  --login mapoet \
  --query-mode both \
  --include-forks \
  --sort updated \
  --order desc \
  --limit 500 \
  --out all_repos.csv
```

---

## 工具二：Git Work Log Generator（git2work.py）

自动生成 Git 工作日志并使用 OpenAI API 生成智能总结的工具。

> **新特性**：现在支持自动检测 git pull 操作，将 pull 时间作为工作会话的开始时间，更准确地反映实际工作时间！

### 功能特性

- 📝 从 Git 提交记录生成详细的工作日志（Markdown 格式）
- 🤖 使用 OpenAI 或 DeepSeek API 自动生成中文工作总结
- 📊 统计代码变更（新增/删除行数、文件数）
- 🎯 支持自定义时间范围、作者过滤
- 🔧 支持自定义系统提示词
- ⏱️ **精细化时间分析**：自动识别工作会话、功能窗口、跨项目交叉时间，并在 AI 总结中生成时间分布图
- 🔄 **并行工作时间检测**：多项目模式下自动识别同时在不同项目上工作的时段，准确评估实际工作时间（避免重复累加）
- 🌐 **远程仓库支持**：支持 GitHub 和 Gitee 远程仓库的 commits 和 PRs（Pull Requests/MRs）查询，无需本地克隆仓库
- 📥 **Git Pull 记录支持**：自动检测 git pull/fetch 操作，将 pull 时间作为工作会话的开始时间，更准确地反映实际工作时间（如果一次会话没有 pull，则使用第一个 commit 时间作为开始时间）

### 安装依赖

```bash
# 基础依赖
pip install openai gitpython requests

# GitHub 支持（可选，如需要查询 GitHub 仓库）
pip install PyGithub python-dateutil
```

### 使用方法

#### 方法 1: 使用便捷脚本（推荐）

```bash
# 生成今天的工作日志（带 AI 总结）
./gen_worklog.sh

# 生成指定日期的工作日志
./gen_worklog.sh 2025-10-28

# 生成指定日期的日志并保存到指定文件
./gen_worklog.sh 2025-10-28 worklog.md

# 仅统计作者(名字或邮箱包含关键字)
AUTHOR="mapoet" ./gen_worklog.sh 2025-10-29

# 多仓库（逗号分隔），并按作者过滤
REPOS="/mnt/d/works/RayTracy,/path/to/another" \
AUTHOR="mapoet" \
./gen_worklog.sh 2025-10-29
```

#### 方法 2: 直接使用 Python 脚本

##### 基本用法

```bash
# 生成今天的工作日志（不带 AI 总结）
./git2work.py --days 1 --output worklog_today.md

# 生成指定日期范围的工作日志
./git2work.py --since 2025-10-27 --until 2025-10-29 --output worklog_range.md

# 只生成最近 7 天的日志
./git2work.py --days 7 --output worklog_7days.md
```

##### 多项目与精细化时间分析

```bash
# 多项目：自动汇总"项目→日期→提交"，并在 AI 总结中按项目估算投入时间与主要产出
# 时间统计会自动识别工作会话（默认间隔120分钟，可通过--session-gap-minutes调整）
./git2work.py \
  --repos "/mnt/d/works/RayTracy,/path/to/another" \
  --since 2025-10-28 --until 2025-10-29 \
  --add-summary --provider deepseek --deepseek-model deepseek-chat \
  --session-gap-minutes 60 \
  --output worklog_multi.md --title "多项目工作日志"

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

##### 使用 AI 总结

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

##### 命令行参数说明

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

### 自定义系统提示词

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

### 配置

#### 环境变量

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

#### 示例

```bash
export OPENAI_API_KEY="sk-xxxxx"
export GITHUB_TOKEN="ghp_xxxxx"
export GITEE_TOKEN="your-gitee-token"
export GIT_REPO="/path/to/your/repo"
export SCRIPT_OUTPUT_DIR="/path/to/output"
```

### 输出格式

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

### 核心功能详解

#### Git Pull 记录支持

工具支持自动检测 git pull/fetch 操作，并将其作为工作会话的开始时间，更准确地反映实际工作时间。

##### 工作原理

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

##### 适用场景与示例

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

##### 技术细节

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

##### 注意事项

- **仅本地仓库支持**：GitHub/Gitee 等远程仓库无法获取 pull 记录（仅查询 commits 和 PRs）
- **依赖 reflog**：如果仓库没有 reflog 或 reflog 已过期，会静默跳过，不影响主流程
- **有效时间范围**：Pull 在第一个 commit 之前 2 小时内才被视为有效（可根据需要调整）
- **自动处理**：所有处理都是自动的，无需额外配置
- **多项目支持**：多项目模式下，每个本地仓库独立获取和处理 pull 记录

### 示例

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

### 注意事项

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
