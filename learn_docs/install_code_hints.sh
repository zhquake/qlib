#!/bin/bash

# 安装 Jupyter 代码提示支持
# 此脚本会安装 JupyterLab 和 LSP 扩展以获得更好的代码提示体验

echo "=========================================="
echo "  安装 Jupyter 代码提示支持"
echo "=========================================="
echo ""

# 检查 Python 环境
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python，请先安装 Python"
    exit 1
fi

PYTHON_CMD="python3"
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "📦 检测到 Python: $($PYTHON_CMD --version)"
echo ""

# 1. 安装 JupyterLab
echo "1️⃣  安装 JupyterLab..."
pip install -q jupyterlab
if [ $? -eq 0 ]; then
    echo "   ✅ JupyterLab 安装完成"
else
    echo "   ❌ JupyterLab 安装失败"
    exit 1
fi
echo ""

# 2. 安装 LSP 扩展
echo "2️⃣  安装 LSP 扩展（代码提示核心）..."
pip install -q jupyterlab-lsp 'python-lsp-server[all]'
if [ $? -eq 0 ]; then
    echo "   ✅ LSP 扩展安装完成"
else
    echo "   ⚠️  LSP 扩展安装失败，但可以继续使用基础功能"
fi
echo ""

# 3. 安装类型检查支持（可选）
echo "3️⃣  安装类型检查支持（可选）..."
read -p "   是否安装类型检查支持？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install -q pylsp-mypy
    if [ $? -eq 0 ]; then
        echo "   ✅ 类型检查支持安装完成"
    else
        echo "   ⚠️  类型检查支持安装失败，但不影响基本使用"
    fi
fi
echo ""

# 4. 安装 IPython 增强功能
echo "4️⃣  安装 IPython 增强功能..."
pip install -q ipython
if [ $? -eq 0 ]; then
    echo "   ✅ IPython 安装完成"
fi
echo ""

echo "=========================================="
echo "  ✅ 安装完成！"
echo "=========================================="
echo ""
echo "📝 下一步："
echo "   1. 启动 JupyterLab："
echo "      cd learn_docs"
echo "      ./start_jupyterlab.sh"
echo ""
echo "   2. 或使用 VS Code 打开 notebook 文件"
echo ""
echo "💡 使用提示："
echo "   - 代码补全：输入时自动显示，按 Tab 确认"
echo "   - 参数提示：输入函数名后按 Shift+Tab"
echo "   - 类型提示：悬停变量/函数查看"
echo ""
echo "📚 详细配置请参考：learn_docs/配置代码提示.md"
echo ""

