# Tushare 数据对接 Qlib 快速指南

## 📖 目录

1. [快速开始](#快速开始)
2. [核心功能](#核心功能)
3. [常用操作](#常用操作)
4. [数据验证](#数据验证)
5. [常见问题](#常见问题)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install tushare pandas numpy streamlit plotly jupyter
```

### 2. 获取 Tushare Token

1. 注册账号: https://tushare.pro/register
2. 获取 Token: https://tushare.pro/user/token
3. 设置环境变量:
```bash
export TUSHARE_TOKEN="your_token_here"
```

### 3. 一键运行

```bash
cd /path/to/qlib/scripts/data_collector/tushare

# 方式1: 使用快速脚本（推荐）
./quick_start.sh

# 方式2: 交互式Jupyter教程
jupyter notebook tushare_tutorial.ipynb

# 方式3: 手动运行（见下文）
```

---

## 💡 核心功能

### 1. 数据收集

支持获取:
- ✅ **行情数据**: OHLCV + 复权因子
- ✅ **财务数据**: PE、PB、PS、市值等
- ✅ **市值数据**: 总市值、流通市值
- ✅ **指数成分股**: 沪深300、中证500等

### 2. 复权处理

**重要**: 已修复复权计算公式！

```python
# 正确的复权公式（已实现）
后复权价格 = 原始价格 × (当日adj_factor / 最新adj_factor)
前复权价格 = 原始价格 × (当日adj_factor / 最新adj_factor)
```

数据包含三种价格:
- `open`, `close`, `high`, `low`: 原始价格（未复权）
- `open_qfq`, `close_qfq`, ...: 前复权价格
- `open_hfq`, `close_hfq`, ...: 后复权价格

### 3. 指数成分股

支持常用指数:
```python
# 获取沪深300成分股
python index_manager.py get --token YOUR_TOKEN --index_code hs300 --output hs300.txt

# 支持的指数简写
hs300   -> 沪深300
csi500  -> 中证500
sz50    -> 上证50
cyb     -> 创业板指
kc50    -> 科创50
```

### 4. 自动更新

```bash
# 每日自动更新（推荐用crontab）
python auto_update.py --token YOUR_TOKEN

# 添加到crontab（每天18:00执行）
0 18 * * * cd /path/to/qlib && python scripts/data_collector/tushare/auto_update.py --token YOUR_TOKEN
```

### 5. 数据可视化

```bash
# 启动Web界面
streamlit run data_viewer.py

# 浏览器访问: http://localhost:8501
```

---

## 🔧 常用操作

### 场景1: 首次收集全市场数据

```bash
# 收集所有股票（2020-01-01 至今）
python collector.py collect \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TOKEN \
    --start 2020-01-01 \
    --interval 1d

# 转换为Qlib格式
python ../../dump_bin.py dump_all \
    --data_path ~/.qlib/tushare_data/cn_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data \
    --include_fields open,close,high,low,volume,factor,close_qfq,close_hfq \
    --file_suffix .csv
```

### 场景2: 收集指定指数成分股

```bash
# 1. 获取沪深300成分股列表
python index_manager.py get --token YOUR_TOKEN --index_code hs300 --output hs300.txt

# 2. 收集成分股数据
python collector.py collect \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TOKEN \
    --start 2020-01-01 \
    --stock_list_file hs300.txt

# 3. 转换为Qlib格式
python ../../dump_bin.py dump_all \
    --data_path ~/.qlib/tushare_data/cn_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data \
    --include_fields open,close,high,low,volume,factor,close_qfq,close_hfq \
    --file_suffix .csv
```

### 场景3: 增量添加新指标

```bash
# 添加财务指标（不重新下载OHLCV）
python collector.py collect_extra_fields_only \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TOKEN \
    --extra_fields pe,pb,turnover_rate

# 转换新字段
python ../../dump_bin.py dump_all \
    --data_path ~/.qlib/tushare_data/cn_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data \
    --include_fields pe,pb,turnover_rate \
    --file_suffix .csv
```

### 场景4: 每日更新

```bash
# 手动更新到最新交易日
python auto_update.py --token YOUR_TOKEN

# 或使用旧版脚本
python update_scheduler.py daily_update \
    --csv_data_dir ~/.qlib/tushare_data/cn_data \
    --qlib_data_dir ~/.qlib/qlib_data/cn_data \
    --token YOUR_TOKEN
```

---

## ✅ 数据验证

### 1. 验证复权计算

```bash
# 验证后复权公式是否正确
python verify_adjustment.py YOUR_TOKEN 000001.SZ
```

### 2. 检查数据质量

```bash
python ../../check_data_health.py check_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data
```

### 3. 使用数据

```python
import qlib
from qlib.data import D

# 初始化
qlib.init(provider_uri='~/.qlib/qlib_data/cn_data', region='cn')

# 获取数据
data = D.features(
    ['SZ000001'], 
    ['$close', '$close_qfq', '$close_hfq', '$volume'],
    start_time='2024-01-01'
)
print(data.head())
```

### 4. Web可视化

```bash
# 启动可视化服务
streamlit run data_viewer.py

# 功能:
# - K线图
# - 复权对比
# - 多股票对比
# - 成交量分析
```

---

## ❓ 常见问题

### Q1: 如何只收集特定股票？

```bash
# 方式1: 命令行参数
python collector.py collect \
    --token YOUR_TOKEN \
    --stock_list "000001.SZ,600000.SH,600519.SH"

# 方式2: 文件（推荐）
echo "000001.SZ" > stocks.txt
echo "600000.SH" >> stocks.txt
python collector.py collect --token YOUR_TOKEN --stock_list_file stocks.txt

# 方式3: 指数成分股
python index_manager.py get --token YOUR_TOKEN --index_code hs300 --output stocks.txt
python collector.py collect --token YOUR_TOKEN --stock_list_file stocks.txt
```

### Q2: 添加新字段会影响已有数据吗？

不会！使用 `collect_extra_fields_only` 只添加新字段:

```bash
python collector.py collect_extra_fields_only \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TOKEN \
    --extra_fields pe,pb
```

### Q3: 如何验证复权数据是否正确？

```bash
# 运行验证脚本
python verify_adjustment.py YOUR_TOKEN 000001.SZ

# 输出会对比我们的计算结果和Tushare官方复权价格
```

### Q4: 数据更新失败怎么办？

原有数据不会受影响（使用追加模式）：

```bash
# 1. 检查token是否正确
# 2. 检查API积分是否足够
# 3. 重新运行更新即可
python auto_update.py --token YOUR_TOKEN
```

### Q5: 如何设置自动更新？

```bash
# 编辑crontab
crontab -e

# 添加定时任务（每天18:00）
0 18 * * * cd /path/to/qlib && /path/to/python scripts/data_collector/tushare/auto_update.py --token YOUR_TOKEN --log-dir ~/.qlib/logs
```

### Q6: 支持哪些额外指标？

```python
# 财务指标（daily_basic接口）
pe, pb, ps, dv_ttm, total_mv, circ_mv

# 基本面数据（daily_basic接口）
turnover_rate, volume_ratio, amount

# 资金流向（moneyflow接口）
buy_sm_amount, sell_sm_amount, net_mf_amount
```

### Q7: 分钟线数据如何收集？

```bash
# 注意: 分钟线需要5000+积分，数据量大，建议指定股票
python collector.py collect \
    --token YOUR_TOKEN \
    --interval 1min \
    --stock_list_file stocks.txt \
    --save_dir ~/.qlib/tushare_data/cn_data_1min

# 转换
python ../../dump_bin.py dump_all \
    --data_path ~/.qlib/tushare_data/cn_data_1min \
    --qlib_dir ~/.qlib/qlib_data/cn_data_1min \
    --freq 1min \
    --include_fields open,close,high,low,volume,factor \
    --file_suffix .csv
```

---

## 📚 完整工具列表

| 工具 | 功能 | 使用场景 |
|------|------|----------|
| `collector.py` | 数据收集 | 首次收集、增量更新 |
| `index_manager.py` | 指数管理 | 获取指数成分股 |
| `auto_update.py` | 自动更新 | 定时任务 |
| `update_scheduler.py` | 更新调度（旧版） | 兼容旧版本 |
| `data_viewer.py` | 数据可视化 | 验证数据质量 |
| `verify_adjustment.py` | 验证复权 | 检查复权计算 |
| `quick_start.sh` | 快速开始 | 一键运行 |
| `tushare_tutorial.ipynb` | 交互式教程 | 学习和测试 |

---

## 🔗 相关链接

- [Tushare Pro 文档](https://tushare.pro/document/2)
- [Qlib 官方文档](https://qlib.readthedocs.io/)
- [完整使用指南](./使用指南.md)（详细版本）

---

## 📝 快速命令参考

```bash
# 完整流程（首次）
./quick_start.sh

# 每日更新
python auto_update.py --token $TUSHARE_TOKEN

# 数据可视化
streamlit run data_viewer.py

# 获取指数成分股
python index_manager.py interactive --token $TUSHARE_TOKEN

# 验证复权
python verify_adjustment.py $TUSHARE_TOKEN 000001.SZ

# Jupyter教程
jupyter notebook tushare_tutorial.ipynb
```

---

**提示**: 推荐使用 `tushare_tutorial.ipynb` 进行交互式学习！
