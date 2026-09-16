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
        echo "[!] 已生成 .env 文件，请填写以下必填项后重新运行："
        echo "    OCI_INSTANCE_ID=<你的实例 OCID>"
        echo ""
        exit 0
    else
        echo "[-] 缺少 .env.example，无法初始化配置。"
        exit 1
    fi
fi

# 5. 执行主程序（透传所有参数，如 --dry-run）
echo "[*] 启动 oracle-change-ip..."
python main.py "$@"
