#!/bin/bash
# Tushare Collector 安装和测试脚本

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Tushare Collector 安装和测试${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# 1. 检查Python环境
echo -e "${YELLOW}[1/5] 检查Python环境...${NC}"
if ! command -v python &> /dev/null; then
    echo -e "${RED}错误: 未找到Python，请先安装Python 3.7+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python版本: $PYTHON_VERSION${NC}"

# 2. 安装依赖
echo ""
echo -e "${YELLOW}[2/5] 安装依赖包...${NC}"
pip install -r requirements.txt -q
echo -e "${GREEN}✓ 依赖安装完成${NC}"

# 3. 检查Tushare Token
echo ""
echo -e "${YELLOW}[3/5] 检查Tushare Token...${NC}"
if [ -z "$TUSHARE_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  未设置TUSHARE_TOKEN环境变量${NC}"
    echo ""
    echo "请执行以下步骤:"
    echo "1. 访问 https://tushare.pro/register 注册账号"
    echo "2. 访问 https://tushare.pro/user/token 获取Token"
    echo "3. 设置环境变量: export TUSHARE_TOKEN='your_token'"
    echo ""
    read -p "是否现在输入Token? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "请输入Token: " TUSHARE_TOKEN
        export TUSHARE_TOKEN
        echo -e "${GREEN}✓ Token已设置${NC}"
    else
        echo -e "${RED}退出安装${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Token已配置: ${TUSHARE_TOKEN:0:10}...${NC}"
fi

# 4. 运行测试
echo ""
echo -e "${YELLOW}[4/5] 运行测试...${NC}"
echo ""

# 测试Tushare连接
echo "测试1: Tushare API连接..."
python -c "
import tushare as ts
ts.set_token('$TUSHARE_TOKEN')
pro = ts.pro_api()
df = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
print(f'✓ 连接成功，获取到 {len(df)} 只股票')
" || {
    echo -e "${RED}✗ Tushare连接失败${NC}"
    exit 1
}

echo ""
echo "测试2: 指数管理器..."
python index_manager.py get --token "$TUSHARE_TOKEN" --index_code hs300 --output test_stocks.txt > /dev/null 2>&1 && {
    STOCK_COUNT=$(wc -l < test_stocks.txt | tr -d ' ')
    # 减去注释行
    STOCK_COUNT=$((STOCK_COUNT - 4))
    echo -e "✓ 指数管理器正常，获取到沪深300成分股 $STOCK_COUNT 只"
    rm test_stocks.txt
} || {
    echo -e "${RED}✗ 指数管理器测试失败${NC}"
}

echo ""
echo "测试3: 数据收集器导入..."
python -c "
from collector import TushareCollector
print('✓ 数据收集器导入成功')
" || {
    echo -e "${RED}✗ 数据收集器导入失败${NC}"
    exit 1
}

echo ""
echo "测试4: 自动更新服务..."
python auto_update.py --help > /dev/null 2>&1 && {
    echo "✓ 自动更新服务正常"
} || {
    echo -e "${YELLOW}⚠️  自动更新服务测试失败（可能需要额外依赖）${NC}"
}

# 5. 显示下一步
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✓ 安装和测试完成！${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "下一步操作:"
echo ""
echo "1. 📚 阅读快速指南:"
echo "   cat README.md"
echo ""
echo "2. 🎓 运行交互式教程:"
echo "   jupyter notebook tushare_tutorial.ipynb"
echo ""
echo "3. 🚀 快速开始（收集数据）:"
echo "   ./quick_start.sh"
echo ""
echo "4. 📊 启动数据可视化:"
echo "   streamlit run data_viewer.py"
echo ""
echo "5. 🔄 设置每日自动更新:"
echo "   crontab -e"
echo "   # 添加: 0 18 * * * cd $(pwd) && python auto_update.py --token $TUSHARE_TOKEN"
echo ""
echo "更多信息请查看:"
echo "  - README.md (快速指南)"
echo "  - 使用指南.md (完整文档)"
echo "  - CHANGES.md (改进总结)"
echo ""
