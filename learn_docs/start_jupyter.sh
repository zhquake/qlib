#!/bin/bash

# Qlib 学习环境 Jupyter 启动脚本
# 用于交互式学习和实验

echo "=========================================="
echo "  启动 Qlib 学习环境 Jupyter 服务"
echo "=========================================="

# 检查是否安装了 jupyter
if ! command -v jupyter &> /dev/null; then
    echo "❌ 未检测到 Jupyter，正在安装..."
    pip install jupyter ipykernel
fi

# 获取当前脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# 切换到项目根目录
cd "$PROJECT_ROOT"

echo "📁 工作目录: $PROJECT_ROOT"
echo ""
echo "🚀 启动 Jupyter Notebook..."
echo "   访问地址: http://localhost:8888"
echo ""
echo "💡 提示:"
echo "   - 按 Ctrl+C 停止服务"
echo "   - 学习用的 notebook 位于: learn_docs/qlib_学习.ipynb"
echo "   - 示例 notebook 位于: examples/ 目录下"
echo ""
echo "⚠️  注意：传统 Jupyter Notebook 的代码提示功能有限"
echo "   推荐使用 JupyterLab 以获得更好的代码提示体验："
echo "   ./learn_docs/start_jupyterlab.sh"
echo ""

# 启动 Jupyter Notebook
jupyter notebook \
    --notebook-dir="$PROJECT_ROOT" \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root

