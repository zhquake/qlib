#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
深度验证Tushare复权因子的定义

根据Tushare官方文档：
- 前复权: close × latest_adj_factor / adj_factor  (保持最新价格不变)
- 后复权: close × adj_factor / latest_adj_factor  (保持历史价格连续)

本脚本将验证这两个公式，并与Tushare的pro_bar接口返回的复权价格对比
"""

import os
import sys
import pandas as pd
import tushare as ts
from loguru import logger
import numpy as np


def verify_adjustment_formulas(token: str, ts_code: str = "000001.SZ", 
                               start_date: str = "20240101", end_date: str = "20241231"):
    """
    全面验证复权公式
    
    Parameters
    ----------
    token: str
        Tushare API token
    ts_code: str
        测试股票代码
    start_date: str
        开始日期 YYYYMMDD
    end_date: str
        结束日期 YYYYMMDD
    """
    ts.set_token(token)
    pro = ts.pro_api()
    
    logger.info(f"="*80)
    logger.info(f"验证股票 {ts_code} 的复权计算公式")
    logger.info(f"="*80)
    
    # 1. 获取未复权的原始数据
    logger.info("\n[步骤1] 获取未复权的原始数据...")
    df_daily = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    df_daily['trade_date'] = pd.to_datetime(df_daily['trade_date'], format='%Y%m%d')
    df_daily = df_daily.sort_values('trade_date').reset_index(drop=True)
    logger.info(f"  获取到 {len(df_daily)} 条记录")
    
    # 2. 获取复权因子
    logger.info("\n[步骤2] 获取复权因子...")
    df_adj = pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
    df_adj['trade_date'] = pd.to_datetime(df_adj['trade_date'], format='%Y%m%d')
    
    # 3. 合并数据
    df = pd.merge(df_daily, df_adj[['trade_date', 'adj_factor']], 
                  on='trade_date', how='left')
    df['adj_factor'] = df['adj_factor'].fillna(method='ffill').fillna(method='bfill').fillna(1.0)
    
    # 获取最新的adj_factor
    factor_latest = df['adj_factor'].iloc[-1]
    logger.info(f"  最新复权因子: {factor_latest:.6f}")
    logger.info(f"  最早复权因子: {df['adj_factor'].iloc[0]:.6f}")
    
    # 4. 根据官方文档计算复权价格
    logger.info("\n[步骤3] 根据官方公式计算复权价格...")
    
    # 前复权公式: close × latest_adj_factor / adj_factor
    df['close_qfq_calc'] = df['close'] * (factor_latest / df['adj_factor'])
    logger.info("  前复权公式: close × (latest_adj_factor / adj_factor)")
    
    # 后复权公式: close × adj_factor / latest_adj_factor  
    df['close_hfq_calc'] = df['close'] * (df['adj_factor'] / factor_latest)
    logger.info("  后复权公式: close × (adj_factor / latest_adj_factor)")
    
    # 5. 获取Tushare的复权数据进行对比
    logger.info("\n[步骤4] 获取Tushare官方的复权数据用于对比...")
    
    # 获取前复权数据
    df_qfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, 
                        adj='qfq', factors=['tor', 'vr'])
    if df_qfq is not None and not df_qfq.empty:
        df_qfq['trade_date'] = pd.to_datetime(df_qfq['trade_date'], format='%Y%m%d')
        df_qfq = df_qfq.sort_values('trade_date').reset_index(drop=True)
        df_qfq = df_qfq.rename(columns={'close': 'close_qfq_tushare'})
        df = pd.merge(df, df_qfq[['trade_date', 'close_qfq_tushare']], 
                     on='trade_date', how='left')
        logger.info("  ✓ 已获取前复权数据")
    
    # 获取后复权数据
    df_hfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, 
                        adj='hfq', factors=['tor', 'vr'])
    if df_hfq is not None and not df_hfq.empty:
        df_hfq['trade_date'] = pd.to_datetime(df_hfq['trade_date'], format='%Y%m%d')
        df_hfq = df_hfq.sort_values('trade_date').reset_index(drop=True)
        df_hfq = df_hfq.rename(columns={'close': 'close_hfq_tushare'})
        df = pd.merge(df, df_hfq[['trade_date', 'close_hfq_tushare']], 
                     on='trade_date', how='left')
        logger.info("  ✓ 已获取后复权数据")
    
    # 6. 对比验证
    logger.info("\n" + "="*80)
    logger.info("【验证结果】")
    logger.info("="*80)
    
    # 显示数据样本
    display_cols = ['trade_date', 'close', 'adj_factor']
    if 'close_qfq_calc' in df.columns:
        display_cols.append('close_qfq_calc')
    if 'close_qfq_tushare' in df.columns:
        display_cols.append('close_qfq_tushare')
    if 'close_hfq_calc' in df.columns:
        display_cols.append('close_hfq_calc')
    if 'close_hfq_tushare' in df.columns:
        display_cols.append('close_hfq_tushare')
    
    logger.info("\n前5个交易日数据:")
    logger.info("\n" + df[display_cols].head().to_string(index=False))
    
    logger.info("\n后5个交易日数据:")
    logger.info("\n" + df[display_cols].tail().to_string(index=False))
    
    # 前复权验证
    if 'close_qfq_tushare' in df.columns:
        df['qfq_diff'] = (df['close_qfq_calc'] - df['close_qfq_tushare']).abs()
        df['qfq_diff_pct'] = (df['qfq_diff'] / df['close_qfq_tushare'] * 100).abs()
        
        max_diff_qfq = df['qfq_diff'].max()
        mean_diff_qfq = df['qfq_diff'].mean()
        max_diff_pct_qfq = df['qfq_diff_pct'].max()
        
        logger.info("\n" + "-"*80)
        logger.info("【前复权验证】")
        logger.info("-"*80)
        logger.info(f"最大绝对差异: {max_diff_qfq:.6f}")
        logger.info(f"平均绝对差异: {mean_diff_qfq:.6f}")
        logger.info(f"最大相对差异: {max_diff_pct_qfq:.4f}%")
        
        if max_diff_pct_qfq < 0.01:
            logger.info("✅ 前复权公式验证通过！")
        else:
            logger.warning(f"⚠️  前复权存在差异 ({max_diff_pct_qfq:.4f}%)")
    
    # 后复权验证
    if 'close_hfq_tushare' in df.columns:
        df['hfq_diff'] = (df['close_hfq_calc'] - df['close_hfq_tushare']).abs()
        df['hfq_diff_pct'] = (df['hfq_diff'] / df['close_hfq_tushare'] * 100).abs()
        
        max_diff_hfq = df['hfq_diff'].max()
        mean_diff_hfq = df['hfq_diff'].mean()
        max_diff_pct_hfq = df['hfq_diff_pct'].max()
        
        logger.info("\n" + "-"*80)
        logger.info("【后复权验证】")
        logger.info("-"*80)
        logger.info(f"最大绝对差异: {max_diff_hfq:.6f}")
        logger.info(f"平均绝对差异: {mean_diff_hfq:.6f}")
        logger.info(f"最大相对差异: {max_diff_pct_hfq:.4f}%")
        
        if max_diff_pct_hfq < 0.01:
            logger.info("✅ 后复权公式验证通过！")
        else:
            logger.warning(f"⚠️  后复权存在差异 ({max_diff_pct_hfq:.4f}%)")
    
    # 7. 总结
    logger.info("\n" + "="*80)
    logger.info("【公式总结】")
    logger.info("="*80)
    logger.info("\n根据Tushare官方文档：")
    logger.info("  前复权: close × (latest_adj_factor / adj_factor)")
    logger.info("         作用: 保持最新价格不变，调整历史价格")
    logger.info("         特点: 最新价格 = 原始价格")
    logger.info("")
    logger.info("  后复权: close × (adj_factor / latest_adj_factor)")
    logger.info("         作用: 将历史价格调整到最新价格水平")
    logger.info("         特点: 保持价格连续性")
    logger.info("")
    logger.info("注意: 前复权和后复权的公式是相反的！")
    logger.info("     前复权: 除以当日因子，乘以最新因子")
    logger.info("     后复权: 乘以当日因子，除以最新因子")
    logger.info("="*80)
    
    # 8. 特别验证：检查最新日期的价格
    logger.info("\n" + "="*80)
    logger.info("【特别验证：最新日期的价格】")
    logger.info("="*80)
    latest_row = df.iloc[-1]
    logger.info(f"最新交易日: {latest_row['trade_date'].strftime('%Y-%m-%d')}")
    logger.info(f"原始收盘价: {latest_row['close']:.4f}")
    if 'close_qfq_calc' in df.columns:
        logger.info(f"前复权价格: {latest_row['close_qfq_calc']:.4f}")
        if abs(latest_row['close_qfq_calc'] - latest_row['close']) < 0.01:
            logger.info("✅ 前复权：最新价格 = 原始价格（验证通过）")
        else:
            logger.warning(f"⚠️  前复权：最新价格与原始价格不一致（差异: {abs(latest_row['close_qfq_calc'] - latest_row['close']):.4f}）")
    
    if 'close_hfq_calc' in df.columns:
        logger.info(f"后复权价格: {latest_row['close_hfq_calc']:.4f}")
        # 后复权的最新价格应该也等于原始价格（因为除以和乘以的是同一个值）
        if abs(latest_row['close_hfq_calc'] - latest_row['close']) < 0.01:
            logger.info("✅ 后复权：最新价格 = 原始价格（验证通过）")
        else:
            logger.info(f"ℹ️  后复权：最新价格与原始价格的差异: {abs(latest_row['close_hfq_calc'] - latest_row['close']):.4f}")
    
    logger.info("="*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python verify_adjustment_correct.py YOUR_TUSHARE_TOKEN [股票代码]")
        print("示例: python verify_adjustment_correct.py your_token 000001.SZ")
        sys.exit(1)
    
    token = sys.argv[1]
    ts_code = sys.argv[2] if len(sys.argv) > 2 else "000001.SZ"
    
    verify_adjustment_formulas(token, ts_code)
