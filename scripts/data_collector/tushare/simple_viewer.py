#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的数据可视化脚本（不需要Streamlit）

使用matplotlib直接展示K线图和复权对比
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import qlib
from qlib.constant import REG_CN
from qlib.data import D


def plot_stock_data(qlib_dir: str = "~/.qlib/qlib_data/test_data"):
    """绘制股票数据"""
    
    # 初始化Qlib
    qlib_dir = Path(qlib_dir).expanduser()
    qlib.init(provider_uri=str(qlib_dir), region=REG_CN)
    
    print("📊 正在加载数据...")
    
    # 获取股票列表
    instruments = D.instruments(market='all')
    stock_list = D.list_instruments(instruments=instruments, as_list=True)
    
    if not stock_list:
        print("❌ 未找到股票数据")
        return
    
    symbol = stock_list[0]
    print(f"📈 分析股票: {symbol}")
    
    # 获取数据
    data = D.features(
        [symbol],
        ['$open', '$close', '$high', '$low', '$volume', 
         '$close_qfq', '$close_hfq'],
        start_time='2022-01-01',
        end_time='2025-01-11',
        freq='day'
    )
    
    if data.empty:
        print("❌ 数据为空")
        return
    
    # 提取单只股票数据
    stock_data = data.loc[symbol].copy()
    stock_data = stock_data.reset_index()
    
    print(f"📅 数据范围: {stock_data['datetime'].min()} 至 {stock_data['datetime'].max()}")
    print(f"📊 数据条数: {len(stock_data)}")
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建图表
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    fig.suptitle(f'{symbol} 股票数据可视化 (2022-2025)', fontsize=16, fontweight='bold')
    
    # 1. K线图
    ax1 = axes[0]
    ax1.plot(stock_data['datetime'], stock_data['$close'], linewidth=2, color='blue')
    ax1.set_title('收盘价走势', fontsize=12)
    ax1.set_ylabel('价格', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    # 2. 成交量
    ax2 = axes[1]
    colors = ['red' if close >= open_ else 'green' 
             for close, open_ in zip(stock_data['$close'], stock_data['$open'])]
    ax2.bar(stock_data['datetime'], stock_data['$volume'], color=colors, alpha=0.6, width=1)
    ax2.set_title('成交量', fontsize=12)
    ax2.set_ylabel('成交量', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    # 3. 复权对比
    ax3 = axes[2]
    ax3.plot(stock_data['datetime'], stock_data['$close'], label='原始价格', linewidth=2)
    if '$close_qfq' in stock_data.columns:
        ax3.plot(stock_data['datetime'], stock_data['$close_qfq'], 
                label='前复权', linewidth=2, alpha=0.7)
    if '$close_hfq' in stock_data.columns:
        ax3.plot(stock_data['datetime'], stock_data['$close_hfq'], 
                label='后复权', linewidth=2, alpha=0.7)
    ax3.set_title('复权价格对比', fontsize=12)
    ax3.set_xlabel('日期', fontsize=10)
    ax3.set_ylabel('价格', fontsize=10)
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    # 自动旋转日期标签
    for ax in axes:
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    # 保存图片
    output_file = Path.home() / 'Desktop' / f'{symbol}_analysis.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存到: {output_file}")
    
    # 不显示图表（避免阻塞）
    # plt.show()
    plt.close()
    
    # 打印统计信息
    print("\n📊 数据统计:")
    print(f"  平均收盘价: {stock_data['$close'].mean():.2f}")
    print(f"  最高价: {stock_data['$high'].max():.2f}")
    print(f"  最低价: {stock_data['$low'].min():.2f}")
    print(f"  平均成交量: {stock_data['$volume'].mean():.0f}")
    
    # 计算收益率
    returns = stock_data['$close'].pct_change()
    print(f"  平均日收益率: {returns.mean()*100:.4f}%")
    print(f"  收益率波动率: {returns.std()*100:.4f}%")
    
    # 最近价格
    print(f"\n📈 最新数据 ({stock_data['datetime'].iloc[-1].strftime('%Y-%m-%d')}):")
    print(f"  原始价格: {stock_data['$close'].iloc[-1]:.2f}")
    if '$close_qfq' in stock_data.columns:
        print(f"  前复权: {stock_data['$close_qfq'].iloc[-1]:.2f}")
    if '$close_hfq' in stock_data.columns:
        print(f"  后复权: {stock_data['$close_hfq'].iloc[-1]:.2f}")


if __name__ == "__main__":
    qlib_dir = sys.argv[1] if len(sys.argv) > 1 else "~/.qlib/qlib_data/test_data"
    plot_stock_data(qlib_dir)
