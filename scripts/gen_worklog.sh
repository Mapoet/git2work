#!/bin/bash
# Git Work Log Generator with AI Summary
# Usage: ./gen_worklog.sh [DATE] [OUTPUT_FILE]

set -e

# 默认配置与 LLM 提供方
REPO="${GIT_REPO:-/mnt/d/works/RayTracy}"
# 可选：多仓库，逗号分隔，如 REPOS="/path/repo1,/path/repo2"
REPOS="${REPOS:-/mnt/d/works/RayTracy,/mnt/d/works/git2work,/mnt/d/works/vtec,/mnt/d/works/taskflow}"
# GitHub 仓库，逗号分隔，格式: OWNER/REPO
GITHUB_REPOS="${GITHUB_REPOS:-Mapoet/.github,Mapoet/sp3exPhs,Mapoet/RayTracy}"
# Gitee 仓库，逗号分隔，格式: OWNER/REPO
GITEE_REPOS="${GITEE_REPOS:-}"
# GitHub/Gitee token
GITHUB_TOKEN_ENV="${GITHUB_TOKEN:-}"
GITEE_TOKEN_ENV="${GITEE_TOKEN:-}"
OUTPUT_DIR="${SCRIPT_OUTPUT_DIR:-$(dirname "$0")}"
PROVIDER="${PROVIDER:-deepseek}"            # openai | deepseek
OPENAI_MODEL="${OPENAI_MODEL:-gpt-4o-mini}"
DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"
OPENAI_KEY_ENV="${OPENAI_API_KEY:-}"
DEEPSEEK_KEY_ENV="${DEEPSEEK_API_KEY:-}"
AUTHOR_FILTER="${AUTHOR:-}"
GAP_MINUTES="${GAP_MINUTES:-300}" # 1440 minutes = 24 hours    
# 解析参数
if [ "$1" = "--test" ]; then
    TEST_MODE=1
    shift || true
else
    TEST_MODE=0
fi

DATE="${1:-$(date +%Y-%m-%d)}"
OUTPUT="${2:-${OUTPUT_DIR}/worklog_${DATE}.md}"
TITLE="工作日志 ${DATE}"

echo "========================================="
echo "Git Work Log Generator with AI Summary"
echo "========================================="
if [ -n "$REPOS" ]; then
    echo "本地仓库(多): $REPOS"
elif [ -n "$REPO" ]; then
    echo "本地仓库: $REPO"
fi
if [ -n "$GITHUB_REPOS" ]; then
    echo "GitHub 仓库: $GITHUB_REPOS"
fi
if [ -n "$GITEE_REPOS" ]; then
    echo "Gitee 仓库: $GITEE_REPOS"
fi
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

# 基础命令
BASE_CMD=(python3 "$(dirname "$0")/git2work.py" --since "$DATE" --until "$DATE" --output "$OUTPUT" --title "$TITLE" --session-gap-minutes "$GAP_MINUTES")
if [ -n "$REPOS" ]; then
    BASE_CMD+=(--repos "$REPOS")
elif [ -n "$REPO" ]; then
    BASE_CMD+=(--repo "$REPO")
fi
if [ -n "$GITHUB_REPOS" ]; then
    BASE_CMD+=(--github "$GITHUB_REPOS")
    if [ -n "$GITHUB_TOKEN_ENV" ]; then
        BASE_CMD+=(--github-token "$GITHUB_TOKEN_ENV")
        echo "已检测到 GITHUB_TOKEN（环境变量），将查询 GitHub 仓库"
    else
        echo "提示: 未检测到 GITHUB_TOKEN，如需查询 GitHub 仓库请设置该环境变量"
    fi
fi
if [ -n "$GITEE_REPOS" ]; then
    BASE_CMD+=(--gitee "$GITEE_REPOS")
    if [ -n "$GITEE_TOKEN_ENV" ]; then
        BASE_CMD+=(--gitee-token "$GITEE_TOKEN_ENV")
        echo "已检测到 GITEE_TOKEN（环境变量），将查询 Gitee 仓库"
    else
        echo "提示: 未检测到 GITEE_TOKEN，如需查询 Gitee 仓库请设置该环境变量"
    fi
fi
if [ -n "$AUTHOR_FILTER" ]; then
    BASE_CMD+=(--author "$AUTHOR_FILTER")
    echo "作者过滤: $AUTHOR_FILTER"
fi

if [ "$TEST_MODE" = "1" ]; then
    echo "进入测试模式：将执行以下测试用例"
    echo "1) 单仓库，无总结"
    TMP_OUT1="${OUTPUT_DIR}/worklog_test_single.md"
    "${BASE_CMD[@]}" --output "$TMP_OUT1"
    echo "✅ 生成：$TMP_OUT1"

    echo "2) 单仓库，启用总结（根据 PROVIDER 与密钥可用性自动尝试）"
    TMP_OUT2="${OUTPUT_DIR}/worklog_test_single_summary.md"
    if [ "$PROVIDER" = "deepseek" ]; then
        "${BASE_CMD[@]}" --output "$TMP_OUT2" --add-summary --provider deepseek --deepseek-model "$DEEPSEEK_MODEL" ${LLM_ARGS[@]}
    else
        "${BASE_CMD[@]}" --output "$TMP_OUT2" --add-summary --provider openai --openai-model "$OPENAI_MODEL" ${LLM_ARGS[@]}
    fi
    echo "✅ 生成：$TMP_OUT2"

    if [ -n "$REPOS" ] || [ -n "$GITHUB_REPOS" ] || [ -n "$GITEE_REPOS" ]; then
        echo "3) 多仓库，启用总结"
        TMP_OUT3="${OUTPUT_DIR}/worklog_test_multi_summary.md"
        TEST_CMD=(python3 "$(dirname "$0")/git2work.py" --since "$DATE" --until "$DATE" --output "$TMP_OUT3" --title "多项目工作日志 ${DATE}" --add-summary --session-gap-minutes "$GAP_MINUTES")
        if [ -n "$REPOS" ]; then
            TEST_CMD+=(--repos "$REPOS")
        elif [ -n "$REPO" ]; then
            TEST_CMD+=(--repo "$REPO")
        fi
        if [ -n "$GITHUB_REPOS" ]; then
            TEST_CMD+=(--github "$GITHUB_REPOS")
            [ -n "$GITHUB_TOKEN_ENV" ] && TEST_CMD+=(--github-token "$GITHUB_TOKEN_ENV")
        fi
        if [ -n "$GITEE_REPOS" ]; then
            TEST_CMD+=(--gitee "$GITEE_REPOS")
            [ -n "$GITEE_TOKEN_ENV" ] && TEST_CMD+=(--gitee-token "$GITEE_TOKEN_ENV")
        fi
        if [ -n "$AUTHOR_FILTER" ]; then
            TEST_CMD+=(--author "$AUTHOR_FILTER")
        fi
        if [ "$PROVIDER" = "deepseek" ]; then
            TEST_CMD+=(--provider deepseek --deepseek-model "$DEEPSEEK_MODEL" ${LLM_ARGS[@]})
        else
            TEST_CMD+=(--provider openai --openai-model "$OPENAI_MODEL" ${LLM_ARGS[@]})
        fi
        "${TEST_CMD[@]}"
        echo "✅ 生成：$TMP_OUT3"
    fi
else
    # 正常执行
    if [ "$PROVIDER" = "deepseek" ]; then
        "${BASE_CMD[@]}" --add-summary --provider deepseek --deepseek-model "$DEEPSEEK_MODEL" ${LLM_ARGS[@]}
    else
        "${BASE_CMD[@]}" --add-summary --provider openai --openai-model "$OPENAI_MODEL" ${LLM_ARGS[@]}
    fi
fi

echo ""
echo "========================================="
echo "完成！日志已保存至: $OUTPUT"
echo "========================================="
