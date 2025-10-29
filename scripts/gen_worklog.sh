#!/bin/bash
# Git Work Log Generator with AI Summary
# Usage: ./gen_worklog.sh [DATE] [OUTPUT_FILE]

set -e

# 默认配置与 LLM 提供方
REPO="${GIT_REPO:-/mnt/d/works/RayTracy}"
OUTPUT_DIR="${SCRIPT_OUTPUT_DIR:-$(dirname "$0")}"
PROVIDER="${PROVIDER:-deepseek}"            # openai | deepseek
OPENAI_MODEL="${OPENAI_MODEL:-gpt-4o-mini}"
DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"
OPENAI_KEY_ENV="${OPENAI_API_KEY:-}"
DEEPSEEK_KEY_ENV="${DEEPSEEK_API_KEY:-}"

# 解析参数
DATE="${1:-$(date +%Y-%m-%d)}"
OUTPUT="${2:-${OUTPUT_DIR}/worklog_${DATE}.md}"
TITLE="工作日志 ${DATE}"

echo "========================================="
echo "Git Work Log Generator with AI Summary"
echo "========================================="
echo "仓库: $REPO"
echo "日期: $DATE"
echo "输出: $OUTPUT"
echo "LLM 提供方: $PROVIDER"
echo "========================================="
echo ""

# 组装 AI 总结参数
ADD_SUMMARY=""
LLM_ARGS=()
if [ "$PROVIDER" = "deepseek" ]; then
    ADD_SUMMARY="--add-summary --provider deepseek --deepseek-model \"$DEEPSEEK_MODEL\""
    if [ -n "$DEEPSEEK_KEY_ENV" ]; then
        LLM_ARGS+=(--deepseek-key "$DEEPSEEK_KEY_ENV")
        echo "已检测到 DEEPSEEK_API_KEY（环境变量），将使用 DeepSeek 生成总结"
    else
        echo "提示: 未检测到 DEEPSEEK_API_KEY，若需生成总结请设置该环境变量或在 Python 脚本参数中传入 --deepseek-key"
    fi
else
    # openai 提供方需要 openai 包
    if python3 -c "import openai" 2>/dev/null; then
        ADD_SUMMARY="--add-summary --provider openai --openai-model \"$OPENAI_MODEL\""
        if [ -n "$OPENAI_KEY_ENV" ]; then
            LLM_ARGS+=(--openai-key "$OPENAI_KEY_ENV")
            echo "已检测到 OPENAI_API_KEY（环境变量），将使用 OpenAI 生成总结"
        else
            echo "提示: 未检测到 OPENAI_API_KEY，若需生成总结请设置该环境变量或在 Python 脚本参数中传入 --openai-key"
        fi
    else
        echo "警告: 未安装 openai 包，无法使用 OpenAI 生成总结（可切换 PROVIDER=deepseek）"
    fi
fi

echo ""
echo "正在生成工作日志..."

# 运行 git2work.py
python3 "$(dirname "$0")/git2work.py" \
    --repo "$REPO" \
    --since "$DATE" \
    --until "$DATE" \
    --output "$OUTPUT" \
    --title "$TITLE" \
    $ADD_SUMMARY \
    ${LLM_ARGS[@]}

echo ""
echo "========================================="
echo "完成！日志已保存至: $OUTPUT"
echo "========================================="
