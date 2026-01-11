#!/bin/bash

# Qlib 学习环境 JupyterLab 启动脚本（带代码提示支持）
# 推荐使用此脚本以获得更好的代码提示体验

echo "=========================================="
echo "  启动 Qlib 学习环境 JupyterLab 服务"
echo "  （支持代码自动补全和参数提示）"
echo "=========================================="

# 获取当前脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 检查是否安装了 jupyterlab
if ! command -v jupyter-lab &> /dev/null && ! command -v jupyter lab &> /dev/null; then
    echo "❌ 未检测到 JupyterLab，正在安装..."
    pip install jupyterlab
fi

# 检查是否安装了 LSP 扩展（可选，但推荐）
if ! python -c "import jupyterlab_lsp" 2>/dev/null; then
    echo "💡 检测到未安装 LSP 扩展，建议安装以获得更好的代码提示："
    echo "   pip install jupyterlab-lsp 'python-lsp-server[all]'"
    echo ""
    read -p "是否现在安装？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在安装 LSP 扩展..."
        pip install jupyterlab-lsp 'python-lsp-server[all]'
        echo "✅ LSP 扩展安装完成"
    fi
fi

echo "📁 工作目录: $PROJECT_ROOT"
echo ""
echo "🚀 启动 JupyterLab..."
echo "   访问地址: http://localhost:8888"
echo ""
echo "💡 提示:"
echo "   - 按 Ctrl+C 停止服务"
echo "   - 学习用的 notebook 位于: learn_docs/qlib_学习.ipynb"
echo "   - 代码提示：输入时自动显示，按 Tab 补全"
echo "   - 参数提示：输入函数名后按 Shift+Tab 查看"
echo "   - 类型提示：悬停变量/函数查看类型信息"
echo ""

# 启动 JupyterLab
if command -v jupyter-lab &> /dev/null; then
    jupyter-lab \
        --notebook-dir="$PROJECT_ROOT" \
        --ip=0.0.0.0 \
        --port=8888 \
        --no-browser \
        --allow-root
else
    jupyter lab \
        --notebook-dir="$PROJECT_ROOT" \
        --ip=0.0.0.0 \
        --port=8888 \
        --no-browser \
        --allow-root
fi

