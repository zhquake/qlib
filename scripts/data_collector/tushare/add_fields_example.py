#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例：如何添加新字段到已有数据

这个脚本演示了如何：
1. 读取现有CSV数据
2. 添加新的财务指标字段
3. 保存并转换到Qlib格式
"""

import os
import sys
from pathlib import Path
import pandas as pd
from loguru import logger

# 添加路径
CUR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CUR_DIR.parent.parent.parent))

from collector import TushareCollector


def add_financial_indicators_example():
    """
    示例：添加财务指标到已有数据
    """
    # 配置
    csv_data_dir = Path.home() / ".qlib" / "tushare_data" / "cn_data"
    token = os.getenv("TUSHARE_TOKEN", "YOUR_TUSHARE_TOKEN")  # 从环境变量读取，或替换为你的 token
    
    # 要添加的字段
    extra_fields = ['pe', 'pb', 'ps', 'turnover_rate', 'volume_ratio', 'total_mv', 'circ_mv']
    
    logger.info(f"开始添加财务指标: {extra_fields}")
    
    # 创建收集器（支持额外字段）
    collector = TushareCollector(
        save_dir=str(csv_data_dir),
        token=token,
        start='2020-01-01',
        end='2024-12-31',
        interval='1d',
        extra_fields=extra_fields,
        max_workers=4,
        delay=0.1,
    )
    
    # 增量收集（只下载新字段，合并到现有CSV）
    collector.collect_extra_fields_only()
    
    logger.info("财务指标添加完成！")
    logger.info("下一步：使用 dump_bin.py 转换新字段到 Qlib 格式")


def add_custom_field_example():
    """
    示例：添加自定义计算的字段
    """
    csv_data_dir = Path.home() / ".qlib" / "tushare_data" / "cn_data"
    
    logger.info("开始添加自定义字段...")
    
    # 遍历所有CSV文件
    csv_files = list(csv_data_dir.glob("*.csv"))
    
    for csv_file in csv_files:
        try:
            # 读取现有数据
            df = pd.read_csv(csv_file)
            df['date'] = pd.to_datetime(df['date'])
            
            # 计算自定义指标
            # 示例1：价格变化率
            if 'close' in df.columns:
                df['price_change_pct'] = df['close'].pct_change() * 100
            
            # 示例2：成交量变化率
            if 'volume' in df.columns:
                df['volume_change_pct'] = df['volume'].pct_change() * 100
            
            # 示例3：价格/成交量比率
            if 'close' in df.columns and 'volume' in df.columns:
                df['price_volume_ratio'] = df['close'] / df['volume']
            
            # 保存
            df.to_csv(csv_file, index=False)
            logger.info(f"✓ {csv_file.name}: 已添加自定义字段")
            
        except Exception as e:
            logger.error(f"✗ {csv_file.name}: {e}")
    
    logger.info("自定义字段添加完成！")
    logger.info("下一步：使用 dump_bin.py 转换新字段到 Qlib 格式")


if __name__ == "__main__":
    import fire
    fire.Fire({
        "add_financial": add_financial_indicators_example,
        "add_custom": add_custom_field_example,
    })

