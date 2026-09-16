#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"
MIN_PYTHON_MINOR=8

# 1. 检查 Python 版本
PYTHON_BIN=""
for bin in python3 python; do
    if command -v "$bin" &>/dev/null; then
        version=$("$bin" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo "0")
        major=$("$bin" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo "0")
        if [ "$major" -eq 3 ] && [ "$version" -ge "$MIN_PYTHON_MINOR" ]; then
            PYTHON_BIN="$bin"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[-] 需要 Python 3.${MIN_PYTHON_MINOR}+，请先安装。"
    exit 1
fi

echo "[*] 使用 Python: $($PYTHON_BIN --version)"

# 2. 创建虚拟环境（如不存在）
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] 创建虚拟环境 $VENV_DIR ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# 3. 激活虚拟环境并安装依赖
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "[*] 安装/更新依赖..."
pip install -q -r requirements.txt

# 4. 初始化 .env（首次运行引导）
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo ""
        echo "[!] 已生成 .env 文件，请先填写必填项 OCI_INSTANCE_ID："
        echo "    文件路径: $(pwd)/$ENV_FILE"
        echo ""
        # 尝试用编辑器打开，失败则等待用户手动编辑后按回车继续
        if command -v "${EDITOR:-vi}" &>/dev/null; then
            "${EDITOR:-vi}" "$ENV_FILE"
        else
            echo "[*] 请编辑 $ENV_FILE 填写 OCI_INSTANCE_ID，完成后按回车继续..."
            read -r
        fi
    else
        echo "[-] 缺少 .env.example，无法初始化配置。"
        exit 1
    fi
fi

# 5. 执行主程序（透传所有参数，如 --dry-run）
echo "[*] 启动 oracle-change-ip..."
python main.py "$@"
