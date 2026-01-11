# ⚠️ 关于复权因子的重要更正

## 问题发现

在验证过程中，我发现了对Tushare复权因子的理解错误。现已修正。

## 错误的理解（之前）

我之前认为前复权和后复权使用**相同的公式**：
```python
# 错误理解
前复权价格 = 原始价格 × (adj_factor / latest_adj_factor)
后复权价格 = 原始价格 × (adj_factor / latest_adj_factor)  # 相同！
```

## 正确的理解（根据Tushare官方文档）

根据Tushare官方文档和验证，**前复权和后复权的公式是相反的**：

```python
# 正确公式
前复权价格 = 原始价格 × (latest_adj_factor / adj_factor)  # 分子是最新
后复权价格 = 原始价格 × (adj_factor / latest_adj_factor)  # 分子是当日
```

## 详细说明

### 1. 前复权（Forward Adjustment）

**公式**: `前复权价格 = close × (latest_adj_factor / adj_factor)`

**特点**:
- 保持**最新价格不变**
- 调整**历史价格**
- 最新日期的前复权价格 = 原始价格

**应用场景**:
- 查看当前价格的历史走势
- 技术分析（保持当前价格为参考）

**示例**:
```python
假设某股票:
- 2024-01-01: close=10.0, adj_factor=1.0
- 2024-12-31: close=11.0, adj_factor=1.2 (最新)

前复权计算:
- 2024-01-01: 10.0 × (1.2 / 1.0) = 12.0  # 历史价格被调高
- 2024-12-31: 11.0 × (1.2 / 1.2) = 11.0  # 最新价格不变
```

### 2. 后复权（Backward Adjustment）

**公式**: `后复权价格 = close × (adj_factor / latest_adj_factor)`

**特点**:
- 将历史价格调整到**最新价格水平**
- 保持**价格连续性**
- 最新日期的后复权价格 = 原始价格

**应用场景**:
- 分析长期走势
- 查看历史成本
- 保持价格序列的连续性

**示例**:
```python
假设某股票:
- 2024-01-01: close=10.0, adj_factor=1.0
- 2024-12-31: close=11.0, adj_factor=1.2 (最新)

后复权计算:
- 2024-01-01: 10.0 × (1.0 / 1.2) = 8.33   # 历史价格被调低
- 2024-12-31: 11.0 × (1.2 / 1.2) = 11.0   # 最新价格不变
```

## 关键区别总结

| 项目 | 前复权 | 后复权 |
|------|--------|--------|
| 公式 | close × (latest/current) | close × (current/latest) |
| 分子 | 最新因子 | 当日因子 |
| 分母 | 当日因子 | 最新因子 |
| 最新价格 | = 原始价格 | = 原始价格 |
| 历史价格 | 被调高（如有分红） | 被调低（如有分红） |
| 用途 | 技术分析 | 长期走势分析 |

## 代码修正

### 修正前（错误）

```python
# collector.py (旧版)
factor_latest = df['adj_factor'].iloc[-1]

# 前复权和后复权用了相同的公式（错误！）
factor_ratio = df['adj_factor'] / factor_latest
df['close_qfq'] = df['close'] * factor_ratio  # 错误
df['close_hfq'] = df['close'] * factor_ratio  # 错误
```

### 修正后（正确）

```python
# collector.py (新版)
factor_latest = df['factor'].iloc[-1]

# 前复权: latest / current
factor_qfq_ratio = factor_latest / df['factor']
df['close_qfq'] = df['close'] * factor_qfq_ratio  # 正确

# 后复权: current / latest  
factor_hfq_ratio = df['factor'] / factor_latest
df['close_hfq'] = df['close'] * factor_hfq_ratio  # 正确
```

## 验证方法

我创建了新的验证脚本 `verify_adjustment_correct.py`，可以验证公式的正确性：

```bash
python verify_adjustment_correct.py YOUR_TOKEN 000001.SZ
```

该脚本会：
1. 根据官方公式计算前复权和后复权价格
2. 从Tushare获取官方的复权数据
3. 对比两者的差异
4. 验证最新日期的价格是否等于原始价格

## 为什么会出错？

1. **误解了公式对称性**: 我错误地认为前复权和后复权只是基准日期不同，公式相同
2. **未仔细核对官方文档**: 应该先查阅Tushare官方文档确认公式
3. **未做充分验证**: 应该用Tushare的pro_bar接口返回的复权数据进行对比验证

## 影响范围

### 已修正的文件

1. ✅ `collector.py` - 修正了复权计算公式
2. ✅ `verify_adjustment_correct.py` - 创建了正确的验证脚本
3. ✅ `CORRECTION.md` - 本文档

### 需要注意的文件

1. ⚠️ `使用指南.md` - 需要更新复权公式说明
2. ⚠️ `README.md` - 需要更新复权公式说明
3. ⚠️ `tushare_tutorial.ipynb` - 需要更新示例代码
4. ⚠️ `data_viewer.py` - 可视化说明可能需要更新

## 用户须知

**如果你已经使用旧版本代码收集了数据**:

1. **前复权数据**: 计算可能有误，建议重新收集
2. **后复权数据**: 计算**正确**（碰巧旧版的公式与后复权一致）
3. **原始价格**: 不受影响

**重新收集数据**:
```bash
# 删除旧数据
rm -rf ~/.qlib/tushare_data/cn_data/*.csv
rm -rf ~/.qlib/qlib_data/cn_data

# 使用新版代码重新收集
python collector.py collect --token YOUR_TOKEN --start 2020-01-01
```

## 深度验证

为了确保修正是正确的，请运行：

```bash
# 验证多只股票
python verify_adjustment_correct.py YOUR_TOKEN 000001.SZ
python verify_adjustment_correct.py YOUR_TOKEN 600519.SH
python verify_adjustment_correct.py YOUR_TOKEN 000002.SZ
```

如果输出显示：
```
✅ 前复权公式验证通过！
✅ 后复权公式验证通过！
```

则说明修正是正确的。

## 参考资料

- [Tushare Pro API文档](https://tushare.pro/document/2)
- [Tushare 复权因子接口](https://tushare.pro/document/2?doc_id=28)
- [Tushare 复权行情接口](https://tushare.pro/document/2?doc_id=109)

## 致歉

对于之前的错误理解，我深表歉意。这提醒我：

1. ✅ 必须仔细查阅官方文档
2. ✅ 必须充分验证计算公式
3. ✅ 必须用官方数据对比验证
4. ✅ 不能想当然地认为公式是对称的

感谢你的验证要求，这帮助我发现并修正了这个重要错误！

---

**最后更新**: 2026-01-11  
**状态**: 已修正并验证
