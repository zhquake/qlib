# Tushare 数据收集器

使用 Tushare Pro API 收集中国股票市场数据，并转换为 Qlib 格式。

## 功能特性

- ✅ **多时间粒度支持**：日线(1d)、分钟线(1min, 5min, 15min, 30min, 60min)
- ✅ **多种指标数据**：OHLCV、复权因子、财务指标等
- ✅ **本地缓存机制**：自动缓存已下载的数据，避免重复请求
- ✅ **增量更新**：支持增量更新数据，只下载新增部分
- ✅ **数据验证**：使用 Qlib 的数据验证工具检查数据质量
- ✅ **定时更新**：支持定时任务自动更新数据
- ✅ **灵活扩展**：支持添加更多指标（财务指标、基本面数据等），**不需要重新下载已有数据**

## 安装依赖

```bash
pip install tushare pandas numpy
```

## 使用方法

### 1. 基本使用

#### 收集日线数据

**收集所有股票**：

```bash
python collector.py collect \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TUSHARE_TOKEN \
    --start 2020-01-01 \
    --end 2024-12-31 \
    --interval 1d
```

**收集指定股票（方式1：命令行参数）**：

```bash
python collector.py collect \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TUSHARE_TOKEN \
    --start 2020-01-01 \
    --end 2024-12-31 \
    --interval 1d \
    --stock_list "000001.SZ,600000.SH,600519.SH"
```

**收集指定股票（方式2：从文件读取）**：

创建 `stock_list.txt` 文件（每行一个股票代码）：
```
000001.SZ
600000.SH
600519.SH
```

然后运行：
```bash
python collector.py collect \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TUSHARE_TOKEN \
    --start 2020-01-01 \
    --end 2024-12-31 \
    --interval 1d \
    --stock_list_file stock_list.txt
```

#### 收集分钟线数据

```bash
python collector.py collect \
    --save_dir ~/.qlib/tushare_data/cn_data_1min \
    --token YOUR_TUSHARE_TOKEN \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --interval 1min
```

### 2. 参数说明

- `save_dir`: 数据保存目录
- `token`: Tushare Pro API token（必需）
- `start`: 开始日期，格式：YYYY-MM-DD
- `end`: 结束日期，格式：YYYY-MM-DD
- `interval`: 时间粒度，可选值：1d, 1min, 5min, 15min, 30min, 60min
- `max_workers`: 最大并发数（默认：4）
- `delay`: 请求间隔秒数（默认：0.1，避免触发频率限制）
- `limit_nums`: 限制收集的股票数量（用于调试）
- `stock_list`: 指定股票列表（可选），可以是：
  - 逗号分隔的字符串：`"000001.SZ,600000.SH,600519.SH"`
  - 列表：`['000001.SZ', '600000.SH']`
- `stock_list_file`: 股票列表文件路径（可选），每行一个股票代码
- `use_cache`: 是否使用本地缓存（默认：True）

### 3. 增量更新数据

```bash
# 更新到今天
python collector.py collect \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TUSHARE_TOKEN \
    --interval 1d \
    update_data
```

### 4. 转换为 Qlib 格式

收集完 CSV 数据后，需要转换为 Qlib 的二进制格式：

```bash
python ../../dump_bin.py dump_all \
    --data_path ~/.qlib/tushare_data/cn_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data \
    --include_fields open,close,high,low,volume,factor \
    --file_suffix .csv
```

### 5. 数据验证

```bash
python ../../check_data_health.py check_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data
```

## 完整工作流程

### 首次收集数据

```bash
# 1. 收集日线数据
python collector.py collect \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TUSHARE_TOKEN \
    --start 2020-01-01 \
    --end 2024-12-31 \
    --interval 1d

# 2. 转换为 Qlib 格式
python ../../dump_bin.py dump_all \
    --data_path ~/.qlib/tushare_data/cn_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data \
    --include_fields open,close,high,low,volume,factor \
    --file_suffix .csv

# 3. 验证数据
python ../../check_data_health.py check_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data
```

### 定时更新（使用 crontab）

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每个交易日收盘后更新）
0 18 * * 1-5 cd /path/to/qlib/scripts/data_collector/tushare && \
    python collector.py collect \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TUSHARE_TOKEN \
    --interval 1d \
    update_data && \
    python ../../dump_bin.py dump_update \
    --data_path ~/.qlib/tushare_data/cn_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data \
    --include_fields open,close,high,low,volume,factor \
    --file_suffix .csv
```

## 数据格式

收集的 CSV 文件格式：

```csv
symbol,date,open,high,low,close,volume,factor
SZ000001,2020-01-02,10.5,10.8,10.3,10.6,12345678,1.0
SZ000001,2020-01-03,10.6,10.9,10.4,10.7,12345679,1.0
```

字段说明：
- `symbol`: 股票代码（qlib格式：SZ000001, SH600000）
- `date`: 交易日期
- `open`: 开盘价（前复权）
- `high`: 最高价（前复权）
- `low`: 最低价（前复权）
- `close`: 收盘价（前复权）
- `volume`: 成交量
- `factor`: 复权因子

## 注意事项

1. **Tushare Pro 权限**：
   - 日线数据需要积分：2000+
   - 分钟线数据需要积分：5000+
   - 请确保你的账户有足够的积分

2. **API 频率限制**：
   - 免费用户：每分钟 120 次
   - 建议设置 `delay=0.1` 避免触发限制

3. **数据缓存**：
   - 缓存文件保存在 `save_dir/.cache/` 目录
   - 可以手动删除缓存强制重新下载

4. **股票代码格式**：
   - Tushare 格式：`000001.SZ`, `600000.SH`
   - Qlib 格式：`SZ000001`, `SH600000`
   - 收集器会自动转换格式

## 故障排查

### 问题1：API 调用失败

**原因**：Token 无效或积分不足

**解决**：
1. 检查 Token 是否正确
2. 登录 Tushare 官网检查积分
3. 确认数据权限是否足够

### 问题2：数据为空

**原因**：股票代码格式错误或数据不存在

**解决**：
1. 检查股票代码格式
2. 确认时间范围内是否有交易数据
3. 检查股票是否已退市

### 问题3：转换失败

**原因**：CSV 格式不符合要求

**解决**：
1. 检查 CSV 文件是否包含必需字段
2. 检查日期格式是否正确
3. 检查是否有缺失值

## 扩展功能：添加更多指标

### 支持添加的指标类型

- **财务指标**：PE、PB、PS、股息率、市值等
- **基本面数据**：换手率、量比、成交额等
- **资金流向**：大单、中单、小单资金流向
- **自定义指标**：可以基于已有数据计算自定义指标

### 增量添加指标（推荐）

**重要**：添加新指标时，**不需要重新下载已有数据**！

```bash
# 使用收集器，只收集额外字段（增量添加）
python collector.py collect_extra_fields_only \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TOKEN \
    --start 2020-01-01 \
    --end 2024-12-31 \
    --interval 1d \
    --extra_fields pe,pb,ps,turnover_rate,volume_ratio

# 转换新字段到Qlib格式
python ../../dump_bin.py dump_all \
    --data_path ~/.qlib/tushare_data/cn_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data \
    --include_fields pe,pb,ps,turnover_rate,volume_ratio \
    --file_suffix .csv
```

### 指标存储方式

Qlib 使用**字段级别的存储**，每个指标存储为独立的二进制文件：

```
~/.qlib/qlib_data/cn_data/features/sz000001/
├── open.day.bin          # 开盘价
├── close.day.bin        # 收盘价
├── volume.day.bin       # 成交量
├── pe.day.bin           # 市盈率（新增）
├── pb.day.bin           # 市净率（新增）
└── turnover_rate.day.bin # 换手率（新增）
```

**关键优势**：
- ✅ 每个字段独立存储，互不影响
- ✅ 添加新字段时，只需要转换新字段
- ✅ 不需要重新下载基础数据（OHLCV）

详细说明请参考：[指标扩展说明.md](指标扩展说明.md)

## 增量更新

### 更新更多日期的数据

**重要**：更新时，**不需要修改原有的 bin 文件**，只需要追加新数据即可！

```bash
# 1. 更新 CSV 数据（只收集新日期）
python collector.py collect \
    --save_dir ~/.qlib/tushare_data/cn_data \
    --token YOUR_TOKEN \
    --start 2025-01-01 \
    --end 2025-01-31

# 2. 增量转换为 Qlib 格式（追加模式）
python ../../dump_bin.py dump_update \
    --data_path ~/.qlib/tushare_data/cn_data \
    --qlib_dir ~/.qlib/qlib_data/cn_data \
    --include_fields open,close,high,low,volume,factor \
    --file_suffix .csv
```

**工作原理**：
- `dump_update` 使用**追加（append）模式**
- 新数据直接追加到 bin 文件末尾
- **不会修改已有数据**，安全可靠

详细说明请参考：[增量更新说明.md](增量更新说明.md)

## 完整文档

**推荐阅读**：[使用指南.md](使用指南.md) - 完整的使用指南，包含所有功能说明

## 相关文档

- [Tushare Pro 文档](https://tushare.pro/document/2)
- [Qlib 数据格式文档](https://qlib.readthedocs.io/en/latest/component/data.html)
- [Qlib dump_bin 使用说明](../../../docs/component/data.rst)

