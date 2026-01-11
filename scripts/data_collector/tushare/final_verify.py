#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终验证脚本 - 确认所有复权公式都正确

这个脚本会：
1. 测试后复权公式: close × adj_factor
2. 测试前复权公式: close × (current_factor / latest_factor)
3. 与Tushare官方数据对比
4. 输出详细的验证报告
"""

import sys
import pandas as pd
import tushare as ts
from loguru import logger


def final_verify(token: str, ts_code: str = "000001.SZ"):
    """最终验证"""
    
    ts.set_token(token)
    pro = ts.pro_api()
    
    logger.info("="*80)
    logger.info(f"最终验证: {ts_code}")
    logger.info("="*80)
    
    start_date = "20240101"
    end_date = "20241231"
    
    # 1. 获取原始数据
    df_raw = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    df_raw['trade_date'] = pd.to_datetime(df_raw['trade_date'], format='%Y%m%d')
    df_raw = df_raw.sort_values('trade_date').reset_index(drop=True)
    
    # 2. 获取adj_factor
    df_adj = pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
    df_adj['trade_date'] = pd.to_datetime(df_adj['trade_date'], format='%Y%m%d')
    
    # 3. 获取Tushare的复权数据
    df_qfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq')
    df_qfq['trade_date'] = pd.to_datetime(df_qfq['trade_date'], format='%Y%m%d')
    df_qfq = df_qfq.sort_values('trade_date').reset_index(drop=True)
    
    df_hfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='hfq')
    df_hfq['trade_date'] = pd.to_datetime(df_hfq['trade_date'], format='%Y%m%d')
    df_hfq = df_hfq.sort_values('trade_date').reset_index(drop=True)
    
    # 4. 合并数据
    df = df_raw[['trade_date', 'close']].copy()
    df = df.merge(df_adj[['trade_date', 'adj_factor']], on='trade_date', how='left')
    df = df.merge(df_qfq[['trade_date', 'close']].rename(columns={'close': 'close_qfq_tushare'}), 
                  on='trade_date', how='left')
    df = df.merge(df_hfq[['trade_date', 'close']].rename(columns={'close': 'close_hfq_tushare'}), 
                  on='trade_date', how='left')
    
    df['adj_factor'] = df['adj_factor'].ffill().bfill().fillna(1.0)
    
    # 5. 使用最终正确的公式计算
    factor_latest = df['adj_factor'].iloc[-1]
    
    # 后复权: close × adj_factor
    df['close_hfq_calc'] = df['close'] * df['adj_factor']
    
    # 前复权: close × (current_factor / latest_factor)
    df['close_qfq_calc'] = df['close'] * (df['adj_factor'] / factor_latest)
    
    # 6. 计算差异
    df['hfq_diff'] = (df['close_hfq_calc'] - df['close_hfq_tushare']).abs()
    df['hfq_diff_pct'] = (df['hfq_diff'] / df['close_hfq_tushare'] * 100).abs()
    
    df['qfq_diff'] = (df['close_qfq_calc'] - df['close_qfq_tushare']).abs()
    df['qfq_diff_pct'] = (df['qfq_diff'] / df['close_qfq_tushare'] * 100).abs()
    
    # 7. 输出结果
    logger.info("\n【数据样本】")
    logger.info("-"*80)
    display_cols = ['trade_date', 'close', 'adj_factor', 
                    'close_qfq_calc', 'close_qfq_tushare', 'qfq_diff_pct',
                    'close_hfq_calc', 'close_hfq_tushare', 'hfq_diff_pct']
    logger.info("\n" + df[display_cols].head(5).to_string(index=False))
    
    logger.info("\n【最新数据】")
    logger.info("-"*80)
    logger.info("\n" + df[display_cols].tail(5).to_string(index=False))
    
    # 8. 统计结果
    logger.info("\n" + "="*80)
    logger.info("【验证结果】")
    logger.info("="*80)
    
    # 后复权验证
    max_hfq_diff = df['hfq_diff'].max()
    mean_hfq_diff = df['hfq_diff'].mean()
    max_hfq_diff_pct = df['hfq_diff_pct'].max()
    
    logger.info("\n后复权验证:")
    logger.info(f"  公式: close × adj_factor")
    logger.info(f"  最大绝对差异: {max_hfq_diff:.6f}")
    logger.info(f"  平均绝对差异: {mean_hfq_diff:.6f}")
    logger.info(f"  最大相对差异: {max_hfq_diff_pct:.4f}%")
    
    if max_hfq_diff_pct < 0.01:
        logger.info(f"  结果: ✅ 完全正确！")
    elif max_hfq_diff_pct < 0.1:
        logger.info(f"  结果: ✅ 可接受（浮点精度误差）")
    else:
        logger.warning(f"  结果: ⚠️  存在差异")
    
    # 前复权验证
    max_qfq_diff = df['qfq_diff'].max()
    mean_qfq_diff = df['qfq_diff'].mean()
    max_qfq_diff_pct = df['qfq_diff_pct'].max()
    
    logger.info("\n前复权验证:")
    logger.info(f"  公式: close × (current_factor / latest_factor)")
    logger.info(f"  最大绝对差异: {max_qfq_diff:.6f}")
    logger.info(f"  平均绝对差异: {mean_qfq_diff:.6f}")
    logger.info(f"  最大相对差异: {max_qfq_diff_pct:.4f}%")
    
    if max_qfq_diff_pct < 0.01:
        logger.info(f"  结果: ✅ 完全正确！")
    elif max_qfq_diff_pct < 0.1:
        logger.info(f"  结果: ✅ 可接受（浮点精度误差）")
    else:
        logger.warning(f"  结果: ⚠️  存在差异")
    
    # 9. 验证最新日期
    logger.info("\n" + "="*80)
    logger.info("【最新日期验证】")
    logger.info("="*80)
    
    last_row = df.iloc[-1]
    logger.info(f"\n日期: {last_row['trade_date'].strftime('%Y-%m-%d')}")
    logger.info(f"原始价格: {last_row['close']:.4f}")
    logger.info(f"前复权价格: {last_row['close_qfq_calc']:.4f}")
    logger.info(f"后复权价格: {last_row['close_hfq_calc']:.4f}")
    
    if abs(last_row['close'] - last_row['close_qfq_calc']) < 0.01:
        logger.info("✅ 前复权: 最新价格 = 原始价格 (正确！)")
    else:
        logger.warning(f"⚠️  前复权: 最新价格与原始价格不一致")
    
    # 10. 最终结论
    logger.info("\n" + "="*80)
    logger.info("【最终结论】")
    logger.info("="*80)
    
    # 0.1%以内的差异都是可接受的（浮点精度+数据四舍五入）
    if max_hfq_diff_pct < 0.1 and max_qfq_diff_pct < 0.1:
        logger.info("\n🎉 所有公式验证通过！")
        logger.info("\n正确的公式:")
        logger.info("  后复权价格 = 原始价格 × adj_factor")
        logger.info("  前复权价格 = 原始价格 × (当日adj_factor / 最新adj_factor)")
        logger.info("\n代码已修正，可以放心使用！")
        logger.info("\n说明: 微小差异(< 0.1%)是由于浮点数精度和Tushare数据四舍五入导致的，完全正常。")
    else:
        logger.error("\n❌ 验证未通过，请检查公式！")
    
    logger.info("="*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python final_verify.py YOUR_TOKEN [股票代码]")
        print("示例: python final_verify.py your_token 000001.SZ")
        sys.exit(1)
    
    token = sys.argv[1]
    ts_code = sys.argv[2] if len(sys.argv) > 2 else "000001.SZ"
    
    final_verify(token, ts_code)
