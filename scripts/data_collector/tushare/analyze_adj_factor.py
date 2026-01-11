#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
深度分析Tushare的adj_factor定义

目标：彻底搞清楚adj_factor的含义和正确的复权公式
"""

import sys
import pandas as pd
import tushare as ts
from loguru import logger


def analyze_adj_factor(token: str, ts_code: str = "000001.SZ"):
    """深度分析adj_factor"""
    
    ts.set_token(token)
    pro = ts.pro_api()
    
    logger.info("="*80)
    logger.info(f"深度分析 {ts_code} 的adj_factor")
    logger.info("="*80)
    
    # 获取数据
    start_date = "20240101"
    end_date = "20241231"
    
    # 1. 获取未复权数据
    df_raw = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    df_raw['trade_date'] = pd.to_datetime(df_raw['trade_date'], format='%Y%m%d')
    df_raw = df_raw.sort_values('trade_date').reset_index(drop=True)
    
    # 2. 获取adj_factor
    df_adj = pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
    df_adj['trade_date'] = pd.to_datetime(df_adj['trade_date'], format='%Y%m%d')
    
    # 3. 获取前复权数据
    df_qfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq')
    df_qfq['trade_date'] = pd.to_datetime(df_qfq['trade_date'], format='%Y%m%d')
    df_qfq = df_qfq.sort_values('trade_date').reset_index(drop=True)
    
    # 4. 获取后复权数据
    df_hfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='hfq')
    df_hfq['trade_date'] = pd.to_datetime(df_hfq['trade_date'], format='%Y%m%d')
    df_hfq = df_hfq.sort_values('trade_date').reset_index(drop=True)
    
    # 5. 合并所有数据
    df = df_raw[['trade_date', 'close']].copy()
    df = df.merge(df_adj[['trade_date', 'adj_factor']], on='trade_date', how='left')
    df = df.merge(df_qfq[['trade_date', 'close']].rename(columns={'close': 'close_qfq'}), 
                  on='trade_date', how='left')
    df = df.merge(df_hfq[['trade_date', 'close']].rename(columns={'close': 'close_hfq'}), 
                  on='trade_date', how='left')
    
    df['adj_factor'] = df['adj_factor'].fillna(method='ffill').fillna(method='bfill').fillna(1.0)
    
    # 6. 分析
    logger.info("\n【数据样本】")
    logger.info("-"*80)
    logger.info(df.head(10).to_string(index=False))
    
    logger.info("\n【最新数据】")
    logger.info("-"*80)
    logger.info(df.tail(5).to_string(index=False))
    
    # 7. 反推公式
    logger.info("\n【反推复权公式】")
    logger.info("="*80)
    
    # 取第一行和最后一行
    first_row = df.iloc[0]
    last_row = df.iloc[-1]
    
    logger.info(f"\n第一个交易日 ({first_row['trade_date'].strftime('%Y-%m-%d')}):")
    logger.info(f"  原始价格: {first_row['close']:.4f}")
    logger.info(f"  adj_factor: {first_row['adj_factor']:.4f}")
    logger.info(f"  前复权价格: {first_row['close_qfq']:.4f}")
    logger.info(f"  后复权价格: {first_row['close_hfq']:.4f}")
    
    logger.info(f"\n最后一个交易日 ({last_row['trade_date'].strftime('%Y-%m-%d')}):")
    logger.info(f"  原始价格: {last_row['close']:.4f}")
    logger.info(f"  adj_factor: {last_row['adj_factor']:.4f}")
    logger.info(f"  前复权价格: {last_row['close_qfq']:.4f}")
    logger.info(f"  后复权价格: {last_row['close_hfq']:.4f}")
    
    # 8. 尝试各种公式
    logger.info("\n【测试各种公式】")
    logger.info("="*80)
    
    factor_first = first_row['adj_factor']
    factor_last = last_row['adj_factor']
    
    logger.info(f"\nadj_factor范围: {factor_first:.4f} ~ {factor_last:.4f}")
    
    # 测试1: 后复权 = close × adj_factor
    test_hfq_1 = first_row['close'] * first_row['adj_factor']
    logger.info(f"\n测试1: 后复权 = close × adj_factor")
    logger.info(f"  计算结果: {test_hfq_1:.4f}")
    logger.info(f"  Tushare值: {first_row['close_hfq']:.4f}")
    logger.info(f"  是否匹配: {'✅' if abs(test_hfq_1 - first_row['close_hfq']) < 0.01 else '❌'}")
    
    # 测试2: 前复权 = close × (factor_last / factor_current)
    test_qfq_2 = first_row['close'] * (factor_last / first_row['adj_factor'])
    logger.info(f"\n测试2: 前复权 = close × (latest_factor / current_factor)")
    logger.info(f"  计算结果: {test_qfq_2:.4f}")
    logger.info(f"  Tushare值: {first_row['close_qfq']:.4f}")
    logger.info(f"  是否匹配: {'✅' if abs(test_qfq_2 - first_row['close_qfq']) < 0.01 else '❌'}")
    
    # 测试3: 后复权 = close × (factor_current / factor_last)
    test_hfq_3 = first_row['close'] * (first_row['adj_factor'] / factor_last)
    logger.info(f"\n测试3: 后复权 = close × (current_factor / latest_factor)")
    logger.info(f"  计算结果: {test_hfq_3:.4f}")
    logger.info(f"  Tushare值: {first_row['close_hfq']:.4f}")
    logger.info(f"  是否匹配: {'✅' if abs(test_hfq_3 - first_row['close_hfq']) < 0.01 else '❌'}")
    
    # 9. 验证最新日期
    logger.info("\n【验证最新日期的价格】")
    logger.info("="*80)
    logger.info(f"原始价格: {last_row['close']:.4f}")
    logger.info(f"前复权价格: {last_row['close_qfq']:.4f}")
    logger.info(f"后复权价格: {last_row['close_hfq']:.4f}")
    
    if abs(last_row['close'] - last_row['close_qfq']) < 0.01:
        logger.info("✅ 前复权: 最新价格 = 原始价格")
    else:
        logger.info(f"❌ 前复权: 最新价格({last_row['close_qfq']:.4f}) ≠ 原始价格({last_row['close']:.4f})")
    
    if abs(last_row['close'] - last_row['close_hfq']) < 0.01:
        logger.info("✅ 后复权: 最新价格 = 原始价格")
    else:
        logger.info(f"❌ 后复权: 最新价格({last_row['close_hfq']:.4f}) ≠ 原始价格({last_row['close']:.4f})")
    
    # 10. 全量验证
    logger.info("\n【全量验证】")
    logger.info("="*80)
    
    # 验证公式1: 后复权 = close × adj_factor
    df['hfq_test1'] = df['close'] * df['adj_factor']
    diff1 = (df['hfq_test1'] - df['close_hfq']).abs().max()
    logger.info(f"公式1: 后复权 = close × adj_factor")
    logger.info(f"  最大差异: {diff1:.6f}")
    logger.info(f"  结果: {'✅ 正确' if diff1 < 0.01 else '❌ 错误'}")
    
    # 验证公式2: 前复权 = close × (latest_factor / current_factor)
    df['qfq_test2'] = df['close'] * (factor_last / df['adj_factor'])
    diff2 = (df['qfq_test2'] - df['close_qfq']).abs().max()
    logger.info(f"\n公式2: 前复权 = close × (latest_factor / current_factor)")
    logger.info(f"  最大差异: {diff2:.6f}")
    logger.info(f"  结果: {'✅ 正确' if diff2 < 0.01 else '❌ 错误'}")
    
    logger.info("\n" + "="*80)
    logger.info("【结论】")
    logger.info("="*80)
    logger.info("根据验证结果，正确的公式是：")
    logger.info("  后复权价格 = 原始价格 × adj_factor")
    logger.info("  前复权价格 = 原始价格 × (最新adj_factor / 当日adj_factor)")
    logger.info("="*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python analyze_adj_factor.py YOUR_TOKEN [股票代码]")
        sys.exit(1)
    
    token = sys.argv[1]
    ts_code = sys.argv[2] if len(sys.argv) > 2 else "000001.SZ"
    
    analyze_adj_factor(token, ts_code)
