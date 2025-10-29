# Git Work Log Generator

自动生成 Git 工作日志并使用 AI（OpenAI/DeepSeek）生成智能总结的工具。

## 功能特性

- 📝 从 Git 提交记录生成详细的工作日志（Markdown 格式）
- 🤖 使用 OpenAI 或 DeepSeek API 自动生成中文工作总结
- 📊 统计代码变更（新增/删除行数、文件数）
- 🎯 支持自定义时间范围、作者过滤
- 🔧 支持自定义系统提示词
- 🔄 支持多 LLM 提供商（OpenAI / DeepSeek）

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
pip install openai gitpython requests
```

### 2. 设置 API Key

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-key"

# DeepSeek
export DEEPSEEK_API_KEY="your-deepseek-key"
```

### 3. 生成工作日志

```bash
# 生成今天的工作日志（使用默认 LLM）
cd scripts
./gen_worklog.sh

# 使用 DeepSeek
PROVIDER=deepseek ./gen_worklog.sh

# 使用 OpenAI
PROVIDER=openai OPENAI_MODEL=gpt-4o-mini ./gen_worklog.sh

# 生成指定日期
./gen_worklog.sh 2025-10-29
```

## 详细文档

查看 [scripts/README.md](scripts/README.md) 获取完整的使用说明。

## 许可证

MIT License

