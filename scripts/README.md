# Git Work Log Generator with AI Summary

自动生成 Git 工作日志并使用 OpenAI API 生成智能总结的工具。

## 功能特性

- 📝 从 Git 提交记录生成详细的工作日志（Markdown 格式）
- 🤖 使用 OpenAI 或 DeepSeek API 自动生成中文工作总结
- 📊 统计代码变更（新增/删除行数、文件数）
- 🎯 支持自定义时间范围、作者过滤
- 🔧 支持自定义系统提示词
- ⏱️ **精细化时间分析**：自动识别工作会话、功能窗口、跨项目交叉时间，并在 AI 总结中生成时间分布图
- 🔄 **并行工作时间检测**：多项目模式下自动识别同时在不同项目上工作的时段，准确评估实际工作时间（避免重复累加）

## 安装依赖

```bash
pip install openai gitpython
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
```

**时间分析功能说明**：
- **工作会话**：根据 commit 时间戳自动识别连续工作时段（相邻提交间隔小于指定分钟数视为同一会话）
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
- `GIT_REPO`: 默认 Git 仓库路径（单仓库模式）
- `REPOS`: 多个仓库路径（逗号分隔，多仓库模式）
- `PROVIDER`: LLM 提供方（openai 或 deepseek）
- `GAP_MINUTES`: 工作会话识别间隔分钟数（默认1440=24小时，脚本中使用）
- `SCRIPT_OUTPUT_DIR`: 脚本输出目录
- `AUTHOR`: 作者过滤关键字（通过 `gen_worklog.sh` 使用时）

### 示例

```bash
export OPENAI_API_KEY="sk-xxxxx"
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
     - 并行会话标记：标注哪些会话属于并行工作时段
   - **功能窗口统计**：按类型（feat/fix/docs等）统计各功能的起止时间与提交数
3. **按日期分组的提交记录**：
   - 提交 SHA、时间、信息
   - 代码统计（新增/删除行数）
   - 修改的文件列表
   - 完整的 commit message
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

## 示例

```bash
# 生成今天的工作日志
./gen_worklog.sh

# 生成指定日期的工作日志
./gen_worklog.sh 2025-10-28

# 生成带自定义提示词的日志
./git2work.py --days 1 --output worklog.md --add-summary --system-prompt-file custom_prompt.txt
```

## 注意事项

1. 确保已安装必要的 Python 包（`openai`, `gitpython`）
2. 需要有效的 OpenAI API Key
3. API 调用会产生费用
4. 建议使用 `gpt-4o-mini` 模型以节省成本
