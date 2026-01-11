#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证Tushare复权因子计算的正确性

功能:
1. 获取测试股票的原始数据和复权因子
2. 验证后复权价格计算公式
3. 对比我们的计算结果与Tushare pro_bar接口返回的复权价格
"""

import os
import pandas as pd
import tushare as ts
from loguru import logger


def verify_adjustment(token: str, ts_code: str = "000001.SZ", 
                     start_date: str = "20240101", end_date: str = "20241231"):
    """
    验证复权计算的正确性
    
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
    
    logger.info(f"正在验证股票 {ts_code} 的复权计算...")
    
    # 1. 获取未复权的原始数据
    logger.info("1. 获取未复权的原始数据...")
    df_daily = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    df_daily['trade_date'] = pd.to_datetime(df_daily['trade_date'], format='%Y%m%d')
    df_daily = df_daily.sort_values('trade_date').reset_index(drop=True)
    
    # 2. 获取复权因子
    logger.info("2. 获取复权因子...")
    df_adj = pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
    df_adj['trade_date'] = pd.to_datetime(df_adj['trade_date'], format='%Y%m%d')
    
    # 3. 合并数据
    df = pd.merge(df_daily, df_adj[['trade_date', 'adj_factor']], 
                  on='trade_date', how='left')
    df['adj_factor'] = df['adj_factor'].fillna(method='ffill').fillna(method='bfill').fillna(1.0)
    
    # 4. 获取Tushare提供的后复权数据（用于对比验证）
    logger.info("3. 获取Tushare的后复权数据（用于对比）...")
    df_hfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, 
                        adj='hfq', factors=['tor', 'vr'])
    if df_hfq is not None and not df_hfq.empty:
        df_hfq['trade_date'] = pd.to_datetime(df_hfq['trade_date'], format='%Y%m%d')
        df_hfq = df_hfq.sort_values('trade_date').reset_index(drop=True)
        df_hfq = df_hfq.rename(columns={'close': 'close_hfq_tushare'})
        df = pd.merge(df, df_hfq[['trade_date', 'close_hfq_tushare']], 
                     on='trade_date', how='left')
    
    # 5. 计算后复权价格
    logger.info("4. 计算后复权价格...")
    factor_latest = df['adj_factor'].iloc[-1]
    logger.info(f"   最新复权因子: {factor_latest}")
    
    # 根据Tushare官方定义：后复权价格 = 原始价格 × (当日adj_factor / 最新adj_factor)
    df['close_hfq_calculated'] = df['close'] * (df['adj_factor'] / factor_latest)
    
    # 6. 对比结果
    logger.info("\n5. 验证结果:")
    logger.info("="*80)
    
    # 选择部分数据展示
    display_df = df[['trade_date', 'close', 'adj_factor', 'close_hfq_calculated']].copy()
    if 'close_hfq_tushare' in df.columns:
        display_df['close_hfq_tushare'] = df['close_hfq_tushare']
        display_df['diff'] = (display_df['close_hfq_calculated'] - 
                              display_df['close_hfq_tushare']).abs()
        display_df['diff_pct'] = (display_df['diff'] / 
                                  display_df['close_hfq_tushare'] * 100)
    
    # 显示前5条和后5条数据
    logger.info("\n前5个交易日:")
    logger.info(display_df.head().to_string())
    
    logger.info("\n后5个交易日:")
    logger.info(display_df.tail().to_string())
    
    # 统计差异
    if 'diff' in display_df.columns:
        max_diff = display_df['diff'].max()
        mean_diff = display_df['diff'].mean()
        max_diff_pct = display_df['diff_pct'].max()
        
        logger.info("\n差异统计:")
        logger.info(f"  最大绝对差异: {max_diff:.6f}")
        logger.info(f"  平均绝对差异: {mean_diff:.6f}")
        logger.info(f"  最大相对差异: {max_diff_pct:.4f}%")
        
        if max_diff_pct < 0.01:  # 差异小于0.01%
            logger.info("\n✅ 验证通过！计算结果与Tushare提供的后复权价格一致！")
        else:
            logger.warning(f"\n⚠️  存在较大差异（{max_diff_pct:.4f}%），请检查计算逻辑！")
    else:
        logger.warning("\n⚠️  无法获取Tushare的后复权数据进行对比")
    
    logger.info("="*80)
    
    # 7. 说明复权公式
    logger.info("\n复权计算公式说明:")
    logger.info("-"*80)
    logger.info("后复权价格 = 原始价格 × (当日adj_factor / 最新adj_factor)")
    logger.info("  - 作用: 将历史价格调整到最新价格水平")
    logger.info("  - 特点: 保持历史价格的连续性，最新价格可能远大于原始价格")
    logger.info("")
    logger.info("前复权价格 = 原始价格 × (当日adj_factor / 最新adj_factor)")
    logger.info("  - 作用: 保持最新价格不变，调整历史价格")
    logger.info("  - 特点: 最新价格等于原始价格，历史价格被调整")
    logger.info("")
    logger.info("注意: 在Tushare的adj_factor定义下，前复权和后复权的计算公式相同！")
    logger.info("      区别在于选择不同的基准日期来确定factor_latest的值")
    logger.info("-"*80)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python verify_adjustment.py YOUR_TUSHARE_TOKEN [股票代码]")
        print("示例: python verify_adjustment.py your_token 000001.SZ")
        sys.exit(1)
    
    token = sys.argv[1]
    ts_code = sys.argv[2] if len(sys.argv) > 2 else "000001.SZ"
    
    verify_adjustment(token, ts_code)
