#!/bin/bash

# Tushare 数据对接快速开始脚本
# 使用方法: ./quick_start.sh
# 注意: 运行前需要先激活 qlib conda 环境: conda activate qlib
#
# 功能说明:
# 1. 支持列出所有可用的指数
# 2. 支持交互式选择指数或指定指数代码
# 3. 自动获取指数成分股列表
# 4. 下载成分股数据并转换为 Qlib 格式
#
# 配置说明:
# - INDEX_CODE: 设置为 "interactive" 进行交互式选择，设置为指数代码（如 "hs300", "000300.SH"）直接使用，设置为空则下载所有股票

set -e

# 配置变量（请根据实际情况修改）
TUSHARE_TOKEN="${TUSHARE_TOKEN:-YOUR_TUSHARE_TOKEN}"  # 从环境变量读取，或替换为你的 token
START_DATE="2020-01-01"
END_DATE=$(date +%Y-%m-%d)
INTERVAL="1d"
CSV_DATA_DIR="$HOME/.qlib/tushare_data/cn_data"
QLIB_DATA_DIR="$HOME/.qlib/qlib_data/cn_data"
MAX_WORKERS=2

# 股票列表配置
# 方式1: 使用逗号分隔的字符串
# STOCK_LIST="000001.SZ,600000.SH,600519.SH"
# 方式2: 使用文件（每行一个股票代码）
# STOCK_LIST_FILE="stock_list.txt"
# 方式3: 使用指数成分股
#   - 设置为指数代码（如 "000300.SH"）或简写（如 "hs300", "csi500"）
#   - 设置为 "interactive" 以交互式选择指数
#   - 设置为空则收集所有股票
INDEX_CODE="interactive"  # 指数代码或 "interactive" 或空
STOCK_LIST=""
STOCK_LIST_FILE=""

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Tushare 数据对接快速开始${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查 Python 环境
if ! command -v python &> /dev/null; then
    echo "错误: 未找到 Python，请先安装 Python"
    exit 1
fi

# 检查 tushare 是否安装
if ! python -c "import tushare" 2>/dev/null; then
    echo -e "${YELLOW}正在安装 tushare...${NC}"
    pip install tushare pandas numpy
fi

# 进入脚本目录并切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../.." || exit 1

# 如果指定了指数代码，先获取成分股列表
if [ -n "$INDEX_CODE" ]; then
    echo -e "${GREEN}[0/5] 获取指数成分股列表...${NC}"
    
    if [ "$INDEX_CODE" = "interactive" ]; then
        # 交互式选择指数
        echo -e "${YELLOW}请选择指数:${NC}"
        INDEX_STOCK_FILE="$SCRIPT_DIR/index_stocks.txt"
        
        # 运行交互式选择，并将输出保存到临时文件
        python scripts/data_collector/tushare/index_manager.py interactive \
            --token "$TUSHARE_TOKEN" \
            --output "$INDEX_STOCK_FILE"
        
        # 检查是否成功生成股票列表文件
        if [ -f "$INDEX_STOCK_FILE" ] && [ -s "$INDEX_STOCK_FILE" ]; then
            STOCK_LIST_FILE="$INDEX_STOCK_FILE"
            echo "已获取指数成分股列表: $INDEX_STOCK_FILE"
        else
            echo -e "${YELLOW}警告: 未选择指数或获取失败，将收集所有股票数据${NC}"
            INDEX_CODE=""
        fi
    else
        # 使用指定的指数代码
        INDEX_STOCK_FILE="$SCRIPT_DIR/${INDEX_CODE//./_}_stocks.txt"
        python scripts/data_collector/tushare/index_manager.py get \
            --token "$TUSHARE_TOKEN" \
            --index_code "$INDEX_CODE" \
            --output "$INDEX_STOCK_FILE"
        
        if [ -f "$INDEX_STOCK_FILE" ] && [ -s "$INDEX_STOCK_FILE" ]; then
            STOCK_LIST_FILE="$INDEX_STOCK_FILE"
            echo "已获取指数 $INDEX_CODE 的成分股列表: $INDEX_STOCK_FILE"
        else
            echo -e "${YELLOW}警告: 未能获取指数 $INDEX_CODE 的股票列表，将收集所有股票数据${NC}"
            INDEX_CODE=""
        fi
    fi
fi

echo -e "${GREEN}[1/5] 收集数据...${NC}"

# 构建collect命令（从项目根目录运行）
COLLECT_CMD="python scripts/data_collector/tushare/collector.py collect \
    --save_dir \"$CSV_DATA_DIR\" \
    --token \"$TUSHARE_TOKEN\" \
    --start \"$START_DATE\" \
    --end \"$END_DATE\" \
    --interval \"$INTERVAL\" \
    --max_workers $MAX_WORKERS \
    --delay 0.5"

# 如果指定了股票列表文件
if [ -n "$STOCK_LIST_FILE" ] && [ -f "$STOCK_LIST_FILE" ]; then
    COLLECT_CMD="$COLLECT_CMD --stock_list_file \"$STOCK_LIST_FILE\""
    echo "使用股票列表文件: $STOCK_LIST_FILE"
# 如果指定了股票列表（逗号分隔）
elif [ -n "$STOCK_LIST" ]; then
    COLLECT_CMD="$COLLECT_CMD --stock_list \"$STOCK_LIST\""
    echo "使用指定股票列表: $STOCK_LIST"
else
    echo "收集所有股票数据"
fi

# 执行收集命令
eval $COLLECT_CMD

echo ""
echo -e "${GREEN}[2/5] 转换为 Qlib 格式...${NC}"
# 确保在项目根目录（已经在上面切换过了）
# 包含基础字段和复权价格字段（前复权和后复权）
python scripts/dump_bin.py dump_all \
    --data_path "$CSV_DATA_DIR" \
    --qlib_dir "$QLIB_DATA_DIR" \
    --include_fields open,close,high,low,volume,factor,open_qfq,high_qfq,low_qfq,close_qfq,open_hfq,high_hfq,low_hfq,close_hfq \
    --file_suffix .csv \
    --date_field_name date \
    --symbol_field_name symbol \
    --max_workers 16

echo ""
echo -e "${GREEN}[3/5] 验证数据...${NC}"
python scripts/check_data_health.py check_data \
    --qlib_dir "$QLIB_DATA_DIR"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}数据准备完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "数据位置:"
echo "  CSV 数据: $CSV_DATA_DIR"
echo "  Qlib 数据: $QLIB_DATA_DIR"
echo ""
echo "下一步:"
echo "  1. 初始化 Qlib:"
echo "     import qlib"
echo "     qlib.init(provider_uri='$QLIB_DATA_DIR', region='cn')"
echo ""
echo "  2. 测试数据访问:"
echo "     from qlib.data import D"
echo "     # 使用原始价格"
echo "     data = D.features(['SZ000001'], ['\$close'], start_time='2024-01-01')"
echo "     # 使用前复权价格"
echo "     data_qfq = D.features(['SZ000001'], ['\$close_qfq'], start_time='2024-01-01')"
echo "     # 使用后复权价格"
echo "     data_hfq = D.features(['SZ000001'], ['\$close_hfq'], start_time='2024-01-01')"
echo ""
echo "注意: 数据包含原始价格、前复权价格和后复权价格字段"
echo "      - 原始价格: open, close, high, low"
echo "      - 前复权价格: open_qfq, close_qfq, high_qfq, low_qfq"
echo "      - 后复权价格: open_hfq, close_hfq, high_hfq, low_hfq"
echo ""

