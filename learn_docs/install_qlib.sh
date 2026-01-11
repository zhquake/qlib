#!/bin/bash

# =============================================================================
# Qlib 完整安装脚本
# =============================================================================
# 此脚本将完成以下任务：
# 1. 创建 conda 环境
# 2. 安装基础依赖（numpy, cython）
# 3. 从源码安装 Qlib
# 4. 安装常用依赖包（lightgbm, pytorch等）
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量（可根据需要修改）
ENV_NAME="qlib"
PYTHON_VERSION="3.10"
QLIB_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Qlib 安装脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# =============================================================================
# 步骤 1: 检查 conda 是否安装
# =============================================================================
echo -e "${YELLOW}[1/6] 检查 conda 环境...${NC}"
if ! command -v conda &> /dev/null; then
    echo -e "${RED}错误: 未找到 conda 命令${NC}"
    echo "请先安装 Anaconda 或 Miniconda:"
    echo "  - Anaconda: https://www.anaconda.com/products/distribution"
    echo "  - Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi
echo -e "${GREEN}✓ conda 已安装${NC}"
echo ""

# =============================================================================
# 步骤 2: 创建 conda 环境
# =============================================================================
echo -e "${YELLOW}[2/6] 创建 conda 环境: ${ENV_NAME} (Python ${PYTHON_VERSION})...${NC}"

# 检查环境是否已存在
if conda env list | grep -q "^${ENV_NAME} "; then
    echo -e "${YELLOW}警告: 环境 ${ENV_NAME} 已存在${NC}"
    read -p "是否删除并重新创建? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "删除现有环境..."
        conda env remove -n ${ENV_NAME} -y
        echo "创建新环境..."
        conda create -n ${ENV_NAME} python=${PYTHON_VERSION} -y
    else
        echo "使用现有环境..."
    fi
else
    echo "创建新环境..."
    conda create -n ${ENV_NAME} python=${PYTHON_VERSION} -y
fi
echo -e "${GREEN}✓ conda 环境创建完成${NC}"
echo ""

# =============================================================================
# 步骤 3: 激活环境并安装基础依赖
# =============================================================================
echo -e "${YELLOW}[3/6] 安装基础依赖 (numpy, cython)...${NC}"

# 注意: 在脚本中激活 conda 环境需要使用 conda activate
# 但由于脚本执行环境限制，我们需要使用 conda run
conda run -n ${ENV_NAME} pip install --upgrade pip
conda run -n ${ENV_NAME} pip install numpy
conda run -n ${ENV_NAME} pip install --upgrade cython

echo -e "${GREEN}✓ 基础依赖安装完成${NC}"
echo ""

# =============================================================================
# 步骤 4: 从源码安装 Qlib
# =============================================================================
echo -e "${YELLOW}[4/6] 从源码安装 Qlib...${NC}"
echo "安装目录: ${QLIB_DIR}"

# 检查是否在正确的目录
if [ ! -f "${QLIB_DIR}/setup.py" ] || [ ! -f "${QLIB_DIR}/pyproject.toml" ]; then
    echo -e "${RED}错误: 未找到 Qlib 源码文件 (setup.py 或 pyproject.toml)${NC}"
    echo "当前目录: ${QLIB_DIR}"
    exit 1
fi

# 安装 Qlib（开发模式，便于修改代码）
conda run -n ${ENV_NAME} bash -c "cd ${QLIB_DIR} && pip install -e ."

echo -e "${GREEN}✓ Qlib 安装完成${NC}"
echo ""

# =============================================================================
# 步骤 5: 安装常用依赖包
# =============================================================================
echo -e "${YELLOW}[5/6] 安装常用依赖包...${NC}"

# LightGBM (用于基础示例)
echo "安装 LightGBM..."
conda run -n ${ENV_NAME} pip install lightgbm

# PyTorch (用于深度学习模型，可选)
echo "安装 PyTorch..."
# 根据系统自动选择 PyTorch 版本
# macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    conda run -n ${ENV_NAME} pip install torch torchvision torchaudio
# Linux/Windows
else
    conda run -n ${ENV_NAME} pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# 其他常用包
echo "安装其他常用包..."
conda run -n ${ENV_NAME} pip install \
    scikit-learn \
    matplotlib \
    seaborn \
    jupyter \
    ipykernel \
    plotly \
    statsmodels

echo -e "${GREEN}✓ 常用依赖包安装完成${NC}"
echo ""

# =============================================================================
# 步骤 6: 验证安装
# =============================================================================
echo -e "${YELLOW}[6/6] 验证安装...${NC}"

# 验证 Qlib 安装
VERSION=$(conda run -n ${ENV_NAME} python -c "import qlib; print(qlib.__version__)" 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Qlib 安装成功，版本: ${VERSION}${NC}"
else
    echo -e "${RED}✗ Qlib 安装验证失败${NC}"
    exit 1
fi

# 验证 LightGBM
if conda run -n ${ENV_NAME} python -c "import lightgbm; print('LightGBM version:', lightgbm.__version__)" 2>/dev/null; then
    echo -e "${GREEN}✓ LightGBM 安装成功${NC}"
else
    echo -e "${YELLOW}⚠ LightGBM 验证失败（可能不影响基础使用）${NC}"
fi

# 验证 PyTorch
if conda run -n ${ENV_NAME} python -c "import torch; print('PyTorch version:', torch.__version__)" 2>/dev/null; then
    echo -e "${GREEN}✓ PyTorch 安装成功${NC}"
else
    echo -e "${YELLOW}⚠ PyTorch 验证失败（如果不需要深度学习模型可忽略）${NC}"
fi

echo ""

# =============================================================================
# 完成
# =============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}安装完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "下一步操作："
echo "1. 激活 conda 环境:"
echo -e "   ${YELLOW}conda activate ${ENV_NAME}${NC}"
echo ""
echo "2. 验证安装:"
echo -e "   ${YELLOW}python -c \"import qlib; print(qlib.__version__)\"${NC}"
echo ""
echo "3. 下载数据:"
echo -e "   ${YELLOW}python -m qlib.cli.data qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn${NC}"
echo ""
echo "4. 运行第一个示例:"
echo -e "   ${YELLOW}cd examples${NC}"
echo -e "   ${YELLOW}qrun benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml${NC}"
echo ""

