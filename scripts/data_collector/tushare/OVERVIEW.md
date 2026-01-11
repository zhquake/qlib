# Tushare数据对接Qlib - 项目概览

## 📦 项目结构

```
tushare/
├── 📚 文档
│   ├── README.md                  # 快速指南（推荐新手阅读）
│   ├── tushare_tutorial.ipynb    # 交互式教程（推荐学习）
│   ├── 使用指南.md                # 完整文档（详细参考）
│   ├── 开发指南.md                # 开发者文档
│   └── CHANGES.md                # 改进总结
│
├── 🔧 核心工具
│   ├── collector.py              # 数据收集器（核心）
│   ├── index_manager.py          # 指数管理器
│   ├── auto_update.py            # 自动更新服务
│   └── update_scheduler.py       # 更新调度器（旧版）
│
├── 🛠️ 辅助工具
│   ├── verify_adjustment.py      # 复权验证脚本
│   ├── data_viewer.py            # 数据可视化Web服务
│   ├── add_fields_example.py     # 添加字段示例
│   └── install.sh                # 安装和测试脚本
│
├── 🚀 快速启动
│   ├── quick_start.sh            # 一键启动脚本
│   └── config.example.yaml       # 配置文件示例
│
└── 📝 其他
    ├── requirements.txt          # Python依赖
    └── stock_list_example.txt    # 股票列表示例
```

## ✨ 核心功能

### 1. 数据收集 (collector.py)

**功能**:
- ✅ 获取OHLCV行情数据
- ✅ 获取财务数据（PE、PB、PS等）
- ✅ 获取市值数据（总市值、流通市值）
- ✅ 支持增量添加新指标
- ✅ 三种复权价格（原始/前复权/后复权）
- ✅ 自动缓存和增量更新

**使用**:
```bash
# 收集所有股票
python collector.py collect --token YOUR_TOKEN

# 收集指定股票
python collector.py collect --token YOUR_TOKEN --stock_list_file stocks.txt

# 增量添加指标
python collector.py collect_extra_fields_only --token YOUR_TOKEN --extra_fields pe,pb
```

### 2. 指数管理 (index_manager.py)

**功能**:
- ✅ 获取常用指数成分股（沪深300、中证500等）
- ✅ 支持简写代码（hs300、csi500等）
- ✅ 支持多指数合并（并集/交集）
- ✅ 交互式选择指数

**支持的指数**:
- `hs300` / `csi300`: 沪深300
- `csi500` / `zz500`: 中证500
- `sz50` / `sh50`: 上证50
- `csi1000` / `zz1000`: 中证1000
- `cyb` / `cybz`: 创业板指
- `kc50`: 科创50

**使用**:
```bash
# 获取沪深300成分股
python index_manager.py get --token YOUR_TOKEN --index_code hs300 --output hs300.txt

# 交互式选择
python index_manager.py interactive --token YOUR_TOKEN
```

### 3. 自动更新 (auto_update.py)

**功能**:
- ✅ 自动判断交易日
- ✅ 失败重试机制
- ✅ 日志记录
- ✅ 配置文件支持
- ✅ 预留通知接口

**使用**:
```bash
# 手动更新
python auto_update.py --token YOUR_TOKEN

# 使用配置文件
python auto_update.py --config config.yaml

# 定时任务（crontab）
0 18 * * * cd /path/to/qlib && python scripts/data_collector/tushare/auto_update.py --token YOUR_TOKEN
```

### 4. 数据可视化 (data_viewer.py)

**功能**:
- ✅ K线图 + 成交量
- ✅ 复权对比
- ✅ 多股票对比
- ✅ 响应式Web界面

**使用**:
```bash
streamlit run data_viewer.py
# 浏览器访问: http://localhost:8501
```

### 5. 复权验证 (verify_adjustment.py)

**功能**:
- ✅ 验证复权计算公式
- ✅ 对比Tushare官方数据
- ✅ 输出详细对比结果

**使用**:
```bash
python verify_adjustment.py YOUR_TOKEN 000001.SZ
```

## 🎯 主要改进

### 1. 修复复权计算错误 ⚠️

**问题**: 原代码使用错误的公式计算后复权价格

**修复**:
```python
# 错误（旧版）
后复权价格 = 原始价格 × factor

# 正确（新版）
后复权价格 = 原始价格 × (当日factor / 最新factor)
```

**验证**: 使用 `verify_adjustment.py` 对比Tushare官方数据

### 2. 增强指数支持

- 新增更多常用指数简写
- 支持多指数合并（并集/交集）
- 优化成分股获取逻辑

### 3. 完善自动更新

- 新增 `auto_update.py` 服务
- 自动判断交易日
- 支持配置文件
- 失败重试机制

### 4. 数据可视化

- 基于Streamlit的Web界面
- K线图、成交量、复权对比
- 多股票对比分析

### 5. 简化文档

- 创建简洁的README快速指南
- 创建交互式Jupyter教程
- 保留完整的使用指南

## 📖 使用流程

### 新手快速开始

```bash
# 1. 安装和测试
./install.sh

# 2. 交互式学习
jupyter notebook tushare_tutorial.ipynb

# 3. 快速收集数据
./quick_start.sh

# 4. 数据可视化
streamlit run data_viewer.py
```

### 进阶使用

```bash
# 1. 获取指数成分股
python index_manager.py get --token $TOKEN --index_code hs300 -o hs300.txt

# 2. 收集数据
python collector.py collect --token $TOKEN --stock_list_file hs300.txt --start 2020-01-01

# 3. 转换为Qlib格式
python ../../dump_bin.py dump_all \
    --data_path ~/.qlib/tushare_data/cn_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data \
    --include_fields open,close,high,low,volume,factor,close_qfq,close_hfq \
    --file_suffix .csv

# 4. 验证复权
python verify_adjustment.py $TOKEN 000001.SZ

# 5. 设置自动更新
crontab -e
# 添加: 0 18 * * * cd /path/to/qlib && python scripts/data_collector/tushare/auto_update.py --token YOUR_TOKEN
```

## 🔍 数据说明

### 复权价格

存储三种价格，提供最大灵活性:

1. **原始价格**: `open`, `close`, `high`, `low`
   - 未复权的实际交易价格
   - 适合需要精确价格的场景

2. **前复权**: `open_qfq`, `close_qfq`, `high_qfq`, `low_qfq`
   - 保持最新价格不变，调整历史价格
   - 适合分析当前价格的历史走势

3. **后复权**: `open_hfq`, `close_hfq`, `high_hfq`, `low_hfq`
   - 将历史价格调整到最新价格水平
   - 适合分析长期走势的连续性

4. **复权因子**: `factor`
   - Tushare的adj_factor（累积复权因子）
   - 用于计算复权价格

### 额外指标

**财务指标**（daily_basic接口）:
- `pe`: 市盈率
- `pb`: 市净率
- `ps`: 市销率
- `dv_ttm`: 股息率TTM
- `total_mv`: 总市值
- `circ_mv`: 流通市值

**基本面数据**（daily_basic接口）:
- `turnover_rate`: 换手率
- `volume_ratio`: 量比
- `amount`: 成交额

**资金流向**（moneyflow接口）:
- `buy_sm_amount`: 小单买入金额
- `sell_sm_amount`: 小单卖出金额
- `net_mf_amount`: 净流入金额

## 🛡️ 数据安全

- ✅ 使用追加模式更新，不修改已有数据
- ✅ 增量添加指标不影响已下载数据
- ✅ 支持本地缓存，避免重复下载
- ✅ 自动去重，确保数据一致性

## 🔗 相关链接

- [Tushare Pro 文档](https://tushare.pro/document/2)
- [Qlib 官方文档](https://qlib.readthedocs.io/)
- [Qlib GitHub](https://github.com/microsoft/qlib)

## 💡 常见问题

### Q: 如何验证复权数据是否正确？

```bash
python verify_adjustment.py YOUR_TOKEN 000001.SZ
```

### Q: 如何只收集指数成分股？

```bash
# 1. 获取成分股列表
python index_manager.py get --token YOUR_TOKEN --index_code hs300 -o hs300.txt

# 2. 收集数据
python collector.py collect --token YOUR_TOKEN --stock_list_file hs300.txt
```

### Q: 如何增量添加新指标？

```bash
# 使用 collect_extra_fields_only，不会重新下载OHLCV
python collector.py collect_extra_fields_only \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TOKEN \
    --extra_fields pe,pb,turnover_rate
```

### Q: 如何设置自动更新？

```bash
# 方式1: crontab
crontab -e
# 添加: 0 18 * * * cd /path/to/qlib && python scripts/data_collector/tushare/auto_update.py --token YOUR_TOKEN

# 方式2: 配置文件
cp config.example.yaml config.yaml
# 编辑config.yaml，设置token等参数
python auto_update.py --config config.yaml
```

## 📊 性能参考

- **首次收集**: 约1-2小时（全市场5000只股票，5年数据）
- **每日更新**: 约5-10分钟（全市场）
- **指数成分股**: 约10-20分钟（300-500只股票，5年数据）
- **存储空间**: 约100MB/年（全市场日线）

## 🙏 致谢

感谢以下项目:
- [Qlib](https://github.com/microsoft/qlib) - Microsoft开源的量化投资平台
- [Tushare](https://tushare.pro/) - 财经数据接口
- [Streamlit](https://streamlit.io/) - 数据应用框架
- [Plotly](https://plotly.com/) - 交互式图表库

---

**祝你使用愉快！** 🚀

如有问题或建议，欢迎反馈。
