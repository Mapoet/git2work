# Git Work Log Generator

自动生成 Git 工作日志并使用 AI（OpenAI/DeepSeek）生成智能总结的工具。

## 功能特性

- 📝 从 Git 提交记录生成详细的工作日志（Markdown 格式）
- 🤖 使用 OpenAI 或 DeepSeek API 自动生成中文工作总结
- 📊 统计代码变更（新增/删除行数、文件数）
- 🎯 支持自定义时间范围、作者过滤
- 🔧 支持自定义系统提示词
- 🔄 支持多 LLM 提供商（OpenAI / DeepSeek）
- 🧩 多项目分析：支持 `--repos` 多仓库输入，输出按“项目→日期→提交”归档
- 👤 作者过滤：通过 `--author` 或脚本环境变量 `AUTHOR` 仅统计指定作者/邮箱
- ⏱️ 精细化时间分析：基于 commit 时间戳统计工作会话、功能窗口、跨项目交叉时间，并在 AI 总结中绘制工作内容时间分布图

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

# 使用 DeepSeek（环境变量控制 LLM 提供方）
PROVIDER=deepseek ./gen_worklog.sh

# 使用 OpenAI（并指定模型）
PROVIDER=openai OPENAI_MODEL=gpt-4o-mini ./gen_worklog.sh

# 生成指定日期（并按作者过滤）
AUTHOR="mapoet" ./gen_worklog.sh 2025-10-29

# 多仓库输入（逗号分隔）
REPOS="/mnt/d/works/RayTracy,/path/to/another" ./gen_worklog.sh 2025-10-29

# 自定义会话间隔（默认1440分钟=24小时，可通过GAP_MINUTES环境变量调整）
GAP_MINUTES=60 ./gen_worklog.sh 2025-10-29
```

## 详细文档

查看 [scripts/README.md](scripts/README.md) 获取完整的使用说明。

## License

MIT License（见 `LICENSE`）

## 许可证

MIT License

