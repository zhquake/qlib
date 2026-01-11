#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tushare 数据自动更新服务

功能:
1. 每日自动更新股票数据
2. 自动检测是否为交易日
3. 支持更新失败重试
4. 记录更新日志
5. 发送更新通知（可选）

使用方法:
    # 直接运行（更新到昨天）
    python auto_update.py --token YOUR_TOKEN
    
    # 作为定时任务（添加到 crontab）
    0 18 * * * cd /path/to/qlib && python scripts/data_collector/tushare/auto_update.py --token YOUR_TOKEN
    
    # 配置文件方式
    python auto_update.py --config config.yaml
"""

import os
import sys
import time
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict
import argparse

from loguru import logger
import pandas as pd
import tushare as ts

# 添加路径
CUR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CUR_DIR.parent.parent.parent))

from scripts.data_collector.tushare.collector import TushareCollector
from scripts.dump_bin import DumpDataUpdate


class AutoUpdateService:
    """自动更新服务"""
    
    def __init__(
        self,
        token: str,
        csv_data_dir: str = "~/.qlib/tushare_data/cn_data",
        qlib_data_dir: str = "~/.qlib/qlib_data/cn_data",
        interval: str = "1d",
        max_workers: int = 4,
        max_retries: int = 3,
        retry_delay: int = 300,  # 5分钟
        log_dir: Optional[str] = None,
        enable_notification: bool = False,
        notification_config: Optional[Dict] = None,
    ):
        """
        初始化自动更新服务
        
        Parameters
        ----------
        token: str
            Tushare API token
        csv_data_dir: str
            CSV数据目录
        qlib_data_dir: str
            Qlib数据目录
        interval: str
            时间粒度
        max_workers: int
            最大并发数
        max_retries: int
            最大重试次数
        retry_delay: int
            重试延迟（秒）
        log_dir: str, optional
            日志目录
        enable_notification: bool
            是否启用通知
        notification_config: dict, optional
            通知配置
        """
        self.token = token
        self.csv_data_dir = Path(csv_data_dir).expanduser()
        self.qlib_data_dir = Path(qlib_data_dir).expanduser()
        self.interval = interval
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_notification = enable_notification
        self.notification_config = notification_config or {}
        
        # 设置日志
        if log_dir:
            log_path = Path(log_dir).expanduser()
            log_path.mkdir(parents=True, exist_ok=True)
            log_file = log_path / f"update_{datetime.now().strftime('%Y%m%d')}.log"
            logger.add(log_file, rotation="1 day", retention="30 days")
        
        # 初始化 Tushare
        ts.set_token(token)
        self.pro = ts.pro_api()
    
    def is_trading_day(self, date: str) -> bool:
        """
        判断是否为交易日
        
        Parameters
        ----------
        date: str
            日期，格式：YYYY-MM-DD
        
        Returns
        -------
        bool
            是否为交易日
        """
        try:
            date_str = pd.to_datetime(date).strftime('%Y%m%d')
            df = self.pro.trade_cal(
                exchange='SSE',
                start_date=date_str,
                end_date=date_str
            )
            if df is not None and not df.empty:
                return df.iloc[0]['is_open'] == 1
            return False
        except Exception as e:
            logger.warning(f"检查交易日失败: {e}，假设为交易日")
            return True
    
    def get_last_trading_day(self, from_date: Optional[str] = None) -> str:
        """
        获取最近的交易日
        
        Parameters
        ----------
        from_date: str, optional
            起始日期，默认为今天
        
        Returns
        -------
        str
            最近交易日，格式：YYYY-MM-DD
        """
        if from_date is None:
            from_date = datetime.now().strftime('%Y-%m-%d')
        
        # 往前查找最多30天
        for i in range(30):
            check_date = (pd.to_datetime(from_date) - timedelta(days=i)).strftime('%Y-%m-%d')
            if self.is_trading_day(check_date):
                return check_date
        
        raise ValueError(f"未能在 {from_date} 前30天内找到交易日")
    
    def update_data(self, trading_date: Optional[str] = None) -> bool:
        """
        更新数据
        
        Parameters
        ----------
        trading_date: str, optional
            交易日期，如果为None则自动获取最近交易日
        
        Returns
        -------
        bool
            是否更新成功
        """
        try:
            # 确定更新日期
            if trading_date is None:
                trading_date = self.get_last_trading_day()
            
            logger.info("="*80)
            logger.info(f"开始更新数据到 {trading_date}")
            logger.info("="*80)
            
            # 检查是否为交易日
            if not self.is_trading_day(trading_date):
                logger.info(f"{trading_date} 不是交易日，跳过更新")
                return True
            
            # 1. 更新CSV数据
            logger.info("步骤 1/2: 更新CSV数据...")
            collector = TushareCollector(
                save_dir=str(self.csv_data_dir),
                token=self.token,
                interval=self.interval,
                max_workers=self.max_workers,
                use_cache=True,
            )
            collector.update_data(trading_date=trading_date)
            
            # 2. 转换为Qlib格式
            logger.info("步骤 2/2: 转换为Qlib格式...")
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
            
            logger.info("="*80)
            logger.info(f"数据更新完成: {trading_date}")
            logger.info("="*80)
            
            # 发送成功通知
            if self.enable_notification:
                self._send_notification(
                    f"数据更新成功: {trading_date}",
                    f"CSV目录: {self.csv_data_dir}\nQlib目录: {self.qlib_data_dir}"
                )
            
            return True
            
        except Exception as e:
            error_msg = f"数据更新失败: {e}"
            logger.error(error_msg)
            
            # 发送失败通知
            if self.enable_notification:
                self._send_notification(
                    f"数据更新失败: {trading_date}",
                    str(e),
                    level="error"
                )
            
            return False
    
    def run_with_retry(self, trading_date: Optional[str] = None) -> bool:
        """
        带重试的更新
        
        Parameters
        ----------
        trading_date: str, optional
            交易日期
        
        Returns
        -------
        bool
            是否更新成功
        """
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"更新尝试 {attempt}/{self.max_retries}")
            
            success = self.update_data(trading_date)
            
            if success:
                return True
            
            if attempt < self.max_retries:
                logger.warning(f"更新失败，{self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)
        
        logger.error(f"更新失败，已达到最大重试次数: {self.max_retries}")
        return False
    
    def _send_notification(self, title: str, message: str, level: str = "info"):
        """
        发送通知
        
        Parameters
        ----------
        title: str
            通知标题
        message: str
            通知内容
        level: str
            通知级别: info, warning, error
        """
        # TODO: 实现通知功能（企业微信、钉钉、邮件等）
        logger.info(f"[通知] {title}: {message}")
    
    @classmethod
    def from_config(cls, config_file: str) -> 'AutoUpdateService':
        """
        从配置文件创建服务实例
        
        Parameters
        ----------
        config_file: str
            配置文件路径
        
        Returns
        -------
        AutoUpdateService
            服务实例
        """
        config_path = Path(config_file).expanduser()
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return cls(**config)


def main():
    parser = argparse.ArgumentParser(
        description='Tushare 数据自动更新服务',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--token', type=str, help='Tushare API token')
    parser.add_argument('--csv-data-dir', type=str, 
                       default='~/.qlib/tushare_data/cn_data',
                       help='CSV数据目录')
    parser.add_argument('--qlib-data-dir', type=str,
                       default='~/.qlib/qlib_data/cn_data',
                       help='Qlib数据目录')
    parser.add_argument('--trading-date', type=str, default=None,
                       help='交易日期(YYYY-MM-DD)，默认为最近交易日')
    parser.add_argument('--interval', type=str, default='1d',
                       help='时间粒度')
    parser.add_argument('--max-workers', type=int, default=4,
                       help='最大并发数')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='最大重试次数')
    parser.add_argument('--retry-delay', type=int, default=300,
                       help='重试延迟（秒）')
    parser.add_argument('--log-dir', type=str, default=None,
                       help='日志目录')
    parser.add_argument('--config', type=str, default=None,
                       help='配置文件路径')
    
    args = parser.parse_args()
    
    # 从配置文件创建服务
    if args.config:
        service = AutoUpdateService.from_config(args.config)
    else:
        # 检查token
        if not args.token:
            token = os.environ.get('TUSHARE_TOKEN')
            if not token:
                parser.error("必须提供 --token 参数或设置 TUSHARE_TOKEN 环境变量")
            args.token = token
        
        # 创建服务
        service = AutoUpdateService(
            token=args.token,
            csv_data_dir=args.csv_data_dir,
            qlib_data_dir=args.qlib_data_dir,
            interval=args.interval,
            max_workers=args.max_workers,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            log_dir=args.log_dir,
        )
    
    # 执行更新
    success = service.run_with_retry(args.trading_date)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
