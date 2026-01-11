#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tushare 数据定时更新脚本
支持定时自动更新数据到最新日期
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import fire
from loguru import logger

# 添加路径
CUR_DIR = Path(__file__).resolve().parent
sys.path.append(str(CUR_DIR.parent.parent.parent))

import sys
from pathlib import Path

# 添加路径
CUR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CUR_DIR.parent.parent.parent))

from data_collector.tushare.collector import TushareCollector
from dump_bin import DumpDataUpdate


class TushareUpdateScheduler:
    """
    Tushare 数据更新调度器
    """
    
    def __init__(
        self,
        csv_data_dir: str,
        qlib_data_dir: str,
        token: str,
        interval: str = "1d",
        max_workers: int = 4,
    ):
        """
        初始化调度器
        
        Parameters
        ----------
        csv_data_dir: str
            CSV 数据目录
        qlib_data_dir: str
            Qlib 数据目录
        token: str
            Tushare token
        interval: str
            时间粒度
        max_workers: int
            最大并发数
        """
        self.csv_data_dir = Path(csv_data_dir).expanduser()
        self.qlib_data_dir = Path(qlib_data_dir).expanduser()
        self.token = token
        self.interval = interval
        self.max_workers = max_workers
    
    def update_to_bin(self, trading_date: str = None):
        """
        更新数据并转换为 Qlib 格式
        
        Parameters
        ----------
        trading_date: str, optional
            交易日期，格式：YYYY-MM-DD，如果为None则更新到今天
        """
        if trading_date is None:
            trading_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"开始更新数据到 {trading_date}")
        
        # 1. 更新 CSV 数据
        logger.info("步骤 1/2: 更新 CSV 数据...")
        collector = TushareCollector(
            save_dir=str(self.csv_data_dir),
            token=self.token,
            interval=self.interval,
            max_workers=self.max_workers,
            use_cache=True,
        )
        collector.update_data(trading_date=trading_date)
        
        # 2. 转换为 Qlib 格式
        logger.info("步骤 2/2: 转换为 Qlib 格式...")
        # 包含基础字段和复权价格字段（前复权和后复权）
        dump_update = DumpDataUpdate(
            data_path=str(self.csv_data_dir),
            qlib_dir=str(self.qlib_data_dir),
            freq="day" if self.interval == "1d" else "1min",
            max_workers=self.max_workers,
            date_field_name="date",
            file_suffix=".csv",
            symbol_field_name="symbol",
            include_fields="open,close,high,low,volume,factor,open_qfq,high_qfq,low_qfq,close_qfq,open_hfq,high_hfq,low_hfq,close_hfq",
        )
        dump_update.dump()
        
        logger.info("数据更新完成！")
    
    def daily_update(self):
        """
        每日更新（更新到昨天）
        """
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.update_to_bin(trading_date=yesterday)


if __name__ == "__main__":
    fire.Fire(TushareUpdateScheduler)

