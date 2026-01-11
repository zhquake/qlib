# Tushare Collector 改进总结

## 📋 完成的改进

### 1. ✅ 修复复权因子计算问题

**问题**: 原代码中的后复权计算公式错误
- 错误公式: `后复权价格 = 原始价格 × factor`
- 正确公式: `后复权价格 = 原始价格 × (当日factor / 最新factor)`

**解决方案**:
- 更新了 `collector.py` 中的复权计算逻辑
- 添加了详细的注释说明Tushare的adj_factor定义
- 创建了 `verify_adjustment.py` 脚本用于验证计算正确性

**文件变更**:
- `collector.py`: 第314-396行，修复复权计算
- `verify_adjustment.py`: 新增验证脚本

---

### 2. ✅ 完善指数成分股支持

**改进内容**:
- 扩展了常用指数映射，新增中证1000、创业板指、科创50等
- 添加了 `get_multiple_indices_constituents()` 方法，支持获取多指数并集/交集
- 优化了成分股文件输出格式，添加元数据注释
- 改进了日期查询逻辑，支持指定交易日期

**新增指数简写**:
```python
'zz1000': '000852.SH',    # 中证1000
'cybz': '399006.SZ',      # 创业板指
'cyb': '399006.SZ',       # 创业板指
'kc50': '000688.SH',      # 科创50
```

**文件变更**:
- `index_manager.py`: 新增方法和优化逻辑

---

### 3. ✅ 优化自动更新功能

**新增功能**:
- 创建了 `auto_update.py` 新版自动更新服务
- 支持自动判断交易日
- 支持配置文件方式运行
- 支持失败重试机制
- 支持日志记录
- 预留了通知接口（企业微信、钉钉、邮件）

**主要特性**:
```python
# 自动判断交易日
is_trading_day(date) -> bool

# 获取最近交易日
get_last_trading_day() -> str

# 带重试的更新
run_with_retry(trading_date) -> bool
```

**文件变更**:
- `auto_update.py`: 新增自动更新服务
- `config.example.yaml`: 配置文件示例

---

### 4. ✅ 创建数据可视化服务

**功能**:
- 基于 Streamlit + Plotly 的Web界面
- 支持K线图展示（含成交量）
- 支持复权对比（原始/前复权/后复权）
- 支持多股票对比（可归一化）
- 响应式交互界面

**使用方法**:
```bash
# 启动服务
streamlit run data_viewer.py

# 浏览器访问
http://localhost:8501
```

**主要功能模块**:
- `plot_candlestick()`: K线图 + 成交量
- `plot_price_comparison()`: 复权对比
- `plot_multiple_stocks()`: 多股票对比

**文件变更**:
- `data_viewer.py`: 新增可视化服务

---

### 5. ✅ 简化和整合文档

**改进内容**:
- 创建了简洁的 `README.md` 快速指南
- 创建了交互式 `tushare_tutorial.ipynb` Jupyter教程
- 保留了详细的 `使用指南.md` 作为完整文档

**文档结构**:
```
README.md                # 快速指南（推荐新手）
tushare_tutorial.ipynb   # 交互式教程（推荐学习）
使用指南.md              # 完整文档（详细参考）
```

**Jupyter教程章节**:
1. 环境准备
2. 获取指数成分股
3. 数据收集
4. 数据转换
5. 数据验证
6. 使用数据
7. 复权对比
8. 数据更新

**文件变更**:
- `README.md`: 全新快速指南
- `tushare_tutorial.ipynb`: 交互式教程
- `requirements.txt`: 更新依赖列表

---

## 📁 新增和修改的文件

### 新增文件 (7个)
1. `verify_adjustment.py` - 复权计算验证脚本
2. `auto_update.py` - 自动更新服务
3. `config.example.yaml` - 配置文件示例
4. `data_viewer.py` - 数据可视化Web服务
5. `README.md` - 快速指南（全新）
6. `tushare_tutorial.ipynb` - 交互式教程
7. `CHANGES.md` - 本文档

### 修改文件 (3个)
1. `collector.py` - 修复复权计算逻辑
2. `index_manager.py` - 增强指数管理功能
3. `requirements.txt` - 更新依赖列表

---

## 🎯 功能对照表

| 需求 | 状态 | 实现方式 |
|------|------|----------|
| 1. 获取行情/财务/市值数据，支持增量添加指标 | ✅ | `collector.py` + `collect_extra_fields_only()` |
| 2. 后复权数据正确性验证 | ✅ | 修复公式 + `verify_adjustment.py` |
| 3. 支持常用指数作为stock pool | ✅ | `index_manager.py` 增强 |
| 4. 支持每日自动更新 | ✅ | `auto_update.py` + crontab |
| 5. 数据可视化服务 | ✅ | `data_viewer.py` (Streamlit) |
| 6. 简化文档和交互式教程 | ✅ | `README.md` + `tushare_tutorial.ipynb` |

---

## 🚀 快速开始

### 方式1: 使用快速脚本（推荐）
```bash
cd /path/to/qlib/scripts/data_collector/tushare
./quick_start.sh
```

### 方式2: Jupyter教程（推荐学习）
```bash
jupyter notebook tushare_tutorial.ipynb
```

### 方式3: 手动运行
```bash
# 1. 获取指数成分股
python index_manager.py get --token YOUR_TOKEN --index_code hs300 --output hs300.txt

# 2. 收集数据
python collector.py collect --token YOUR_TOKEN --stock_list_file hs300.txt

# 3. 转换格式
python ../../dump_bin.py dump_all --data_path ~/.qlib/tushare_data/cn_data --qlib_dir ~/.qlib/qlib_data/cn_data --include_fields open,close,high,low,volume,factor,close_qfq,close_hfq --file_suffix .csv

# 4. 验证数据
python verify_adjustment.py YOUR_TOKEN 000001.SZ

# 5. 可视化
streamlit run data_viewer.py
```

---

## 📝 使用示例

### 示例1: 收集沪深300数据
```bash
# 获取成分股
python index_manager.py get --token $TOKEN --index_code hs300 -o hs300.txt

# 收集数据
python collector.py collect --token $TOKEN --stock_list_file hs300.txt --start 2020-01-01

# 转换
python ../../dump_bin.py dump_all --data_path ~/.qlib/tushare_data/cn_data --qlib_dir ~/.qlib/qlib_data/cn_data --include_fields open,close,high,low,volume,factor,close_qfq,close_hfq --file_suffix .csv
```

### 示例2: 每日自动更新
```bash
# 手动更新
python auto_update.py --token $TOKEN

# 或者添加到crontab
0 18 * * * cd /path/to/qlib && python scripts/data_collector/tushare/auto_update.py --token YOUR_TOKEN
```

### 示例3: 数据可视化
```bash
streamlit run data_viewer.py
# 在浏览器打开 http://localhost:8501
```

### 示例4: 增量添加指标
```bash
# 添加PE、PB指标（不重新下载OHLCV）
python collector.py collect_extra_fields_only \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token $TOKEN \
    --extra_fields pe,pb,turnover_rate

# 转换新字段
python ../../dump_bin.py dump_all \
    --data_path ~/.qlib/tushare_data/cn_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data \
    --include_fields pe,pb,turnover_rate \
    --file_suffix .csv
```

---

## 🔍 技术细节

### 复权计算公式

**Tushare adj_factor 定义**:
- adj_factor 是累积复权因子
- 用于将原始价格调整为复权价格

**正确的计算方式**:
```python
# 后复权（将历史价格调整到最新价格水平）
后复权价格 = 原始价格 × (当日adj_factor / 最新adj_factor)

# 前复权（保持最新价格不变，调整历史价格）
前复权价格 = 原始价格 × (当日adj_factor / 最新adj_factor)

# 注意: Tushare定义下，两个公式相同！
# 区别在于选择不同的基准日期
```

### 数据存储策略

存储三种价格，提供最大灵活性:
1. **原始价格**: `open`, `close`, `high`, `low`（未复权）
2. **前复权**: `open_qfq`, `close_qfq`, `high_qfq`, `low_qfq`
3. **后复权**: `open_hfq`, `close_hfq`, `high_hfq`, `low_hfq`
4. **复权因子**: `factor`（Tushare的adj_factor）

---

## 📚 相关文档

- [README.md](./README.md) - 快速指南
- [tushare_tutorial.ipynb](./tushare_tutorial.ipynb) - 交互式教程
- [使用指南.md](./使用指南.md) - 完整文档
- [Tushare Pro 文档](https://tushare.pro/document/2)
- [Qlib 文档](https://qlib.readthedocs.io/)

---

## 🎉 总结

本次改进全面提升了Tushare数据收集器的功能和易用性:

1. **数据正确性**: 修复了复权计算错误，确保数据准确
2. **功能完整性**: 支持指数成分股、自动更新、增量添加指标
3. **易用性**: 提供Web可视化、交互式教程、简化文档
4. **可维护性**: 代码结构清晰，注释详细，易于扩展

**推荐使用流程**:
1. 阅读 `README.md` 了解基本概念
2. 运行 `tushare_tutorial.ipynb` 进行交互式学习
3. 使用 `quick_start.sh` 快速开始
4. 使用 `data_viewer.py` 验证数据质量
5. 设置 `auto_update.py` 实现每日自动更新

---

**祝你使用愉快！** 🚀
