# Git Work Log Generator with AI Summary

自动生成 Git 工作日志并使用 OpenAI API 生成智能总结的工具。

## 功能特性

- 📝 从 Git 提交记录生成详细的工作日志（Markdown 格式）
- 🤖 使用 OpenAI API 自动生成中文工作总结
- 📊 统计代码变更（新增/删除行数、文件数）
- 🎯 支持自定义时间范围、作者过滤
- 🔧 支持自定义系统提示词

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
- `--repo`: Git 仓库路径（默认：/mnt/d/works/RayTracy）
- `--since`: 开始日期（ISO 或 YYYY-MM-DD 格式）
- `--until`: 结束日期（ISO 或 YYYY-MM-DD 格式）
- `--days`: 最近 N 天的提交
- `--author`: 按作者过滤
- `--output`: 输出文件路径
- `--title`: 日志标题
- `--add-summary`: 添加 AI 生成的总结
- `--openai-key`: OpenAI API Key（或使用环境变量 OPENAI_API_KEY）
- `--openai-model`: OpenAI 模型（默认：gpt-4o-mini）
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
- `GIT_REPO`: 默认 Git 仓库路径
- `SCRIPT_OUTPUT_DIR`: 脚本输出目录

### 示例

```bash
export OPENAI_API_KEY="sk-xxxxx"
export GIT_REPO="/path/to/your/repo"
export SCRIPT_OUTPUT_DIR="/path/to/output"
```

## 输出格式

生成的工作日志包含：

1. **标题和摘要**：总提交数统计
2. **按日期分组的提交记录**：
   - 提交 SHA、时间、信息
   - 代码统计（新增/删除行数）
   - 修改的文件列表
   - 完整的 commit message
3. **AI 总结**（可选）：
   - 工作概述
   - 主要完成内容
   - 统计数据
   - 技术亮点

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
