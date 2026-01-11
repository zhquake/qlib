# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Tushare 数据收集器
支持多时间粒度、多种指标的数据收集，并提供本地缓存和定时更新功能
"""

import os
import sys
import time
import datetime
import functools
from pathlib import Path
from typing import List, Optional, Dict, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

import fire
import pandas as pd
import numpy as np
from loguru import logger
import tushare as ts

# 添加父目录到路径
CUR_DIR = Path(__file__).resolve().parent
# 添加 scripts 目录到路径（data_collector 在 scripts 下）
sys.path.insert(0, str(CUR_DIR.parent.parent))

from data_collector.base import BaseCollector, BaseNormalize, Normalize

# 实现 deco_retry 装饰器（避免依赖 yahooquery）
def deco_retry(retry: int = 5, retry_sleep: int = 3):
    """
    重试装饰器
    """
    def deco_func(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _retry = 5 if callable(retry) else retry
            _result = None
            for _i in range(1, _retry + 1):
                try:
                    _result = func(*args, **kwargs)
                    break
                except Exception as e:
                    logger.warning(f"{func.__name__}: {_i} :{e}")
                    if _i == _retry:
                        raise
                    time.sleep(retry_sleep)
            return _result
        return wrapper
    return deco_func(retry) if callable(retry) else deco_func


class TushareCollector(BaseCollector):
    """
    Tushare 数据收集器
    
    支持的功能：
    - 多时间粒度：日线(1d)、分钟线(1min, 5min, 15min, 30min, 60min)
    - 多种指标：OHLCV、财务指标、基本面数据等
    - 本地缓存：自动缓存已下载的数据
    - 增量更新：支持增量更新数据
    """
    
    INTERVAL_1d = "1d"
    INTERVAL_1min = "1min"
    INTERVAL_5min = "5min"
    INTERVAL_15min = "15min"
    INTERVAL_30min = "30min"
    INTERVAL_60min = "60min"
    
    SUPPORTED_INTERVALS = [INTERVAL_1d, INTERVAL_1min, INTERVAL_5min, 
                           INTERVAL_15min, INTERVAL_30min, INTERVAL_60min]
    
    def __init__(
        self,
        save_dir: Union[str, Path],
        token: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
        max_workers: int = 4,
        delay: float = 0.1,
        check_data_length: Optional[int] = None,
        limit_nums: Optional[int] = None,
        stock_list: Optional[Union[List[str], str]] = None,
        stock_list_file: Optional[str] = None,
        use_cache: bool = True,
        extra_fields: Optional[List[str]] = None,
    ):
        """
        初始化 Tushare 收集器
        
        Parameters
        ----------
        save_dir: str or Path
            数据保存目录
        token: str
            Tushare API token
        start: str, optional
            开始日期，格式：YYYY-MM-DD
        end: str, optional
            结束日期，格式：YYYY-MM-DD
        interval: str, default "1d"
            时间粒度，支持：1d, 1min, 5min, 15min, 30min, 60min
        max_workers: int, default 4
            最大并发数
        delay: float, default 0.1
            请求间隔（秒），避免触发频率限制
        check_data_length: int, optional
            检查数据长度
        limit_nums: int, optional
            限制收集的股票数量（用于调试）
        stock_list: list or str, optional
            指定股票列表，可以是：
            - 列表：['000001.SZ', '600000.SH', ...]
            - 字符串（逗号分隔）：'000001.SZ,600000.SH,600519.SH'
            如果为None则收集所有股票
        stock_list_file: str, optional
            股票列表文件路径（每行一个股票代码，格式：000001.SZ）
            如果指定，会从文件读取股票列表
        use_cache: bool, default True
            是否使用本地缓存
        """
        # 先设置一些基础属性，避免 BaseCollector.__init__ 调用 get_instrument_list 时出错
        self.token = token
        self.use_cache = use_cache
        self.cache_dir = Path(save_dir) / ".cache"
        
        # 临时设置 instrument_list 为空，避免 BaseCollector.__init__ 出错
        self.instrument_list = []
        
        super().__init__(
            save_dir=save_dir,
            start=start,
            end=end,
            interval=interval,
            max_workers=max_workers,
            delay=delay,
            check_data_length=check_data_length,
            limit_nums=limit_nums,
        )
        
        # 设置 Tushare token
        ts.set_token(token)
        self.pro = ts.pro_api()
        
        # 缓存设置
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 验证时间粒度
        if interval not in self.SUPPORTED_INTERVALS:
            raise ValueError(f"不支持的interval: {interval}，支持的值: {self.SUPPORTED_INTERVALS}")
        
        # 初始化时间
        self.init_datetime()
        
        # 获取股票列表
        if stock_list_file:
            # 从文件读取股票列表
            self.stock_list = self._load_stock_list_from_file(stock_list_file)
        elif stock_list is not None:
            # 处理股票列表参数
            if isinstance(stock_list, str):
                # 如果是字符串，按逗号分割
                self.stock_list = [s.strip() for s in stock_list.split(',') if s.strip()]
            else:
                # 如果是列表，直接使用
                self.stock_list = stock_list
        else:
            # 获取所有股票
            self.stock_list = self._get_stock_list()
        
        if limit_nums:
            self.stock_list = self.stock_list[:limit_nums]
        
        # 设置 instrument_list（BaseCollector 需要）
        self.instrument_list = [self.normalize_symbol(code) for code in self.stock_list]
        
        # 额外字段支持
        self.extra_fields = extra_fields or []
        
        # 支持的额外指标类型
        self.INDICATOR_TYPES = {
            'financial': ['pe', 'pb', 'ps', 'dv_ttm', 'total_mv', 'circ_mv'],
            'basic': ['turnover_rate', 'volume_ratio', 'amount'],
            'moneyflow': ['buy_sm_amount', 'sell_sm_amount', 'net_mf_amount'],
        }
        
        if self.extra_fields:
            logger.info(f"初始化完成，共 {len(self.stock_list)} 只股票，额外字段: {self.extra_fields}")
        else:
            logger.info(f"初始化完成，共 {len(self.stock_list)} 只股票，时间范围: {self.start_datetime} 到 {self.end_datetime}")
    
    def init_datetime(self):
        """初始化时间范围"""
        if self.start_datetime is None:
            # 默认从2020-01-01开始
            self.start_datetime = pd.Timestamp("2020-01-01")
        else:
            self.start_datetime = pd.Timestamp(self.start_datetime)
        
        if self.end_datetime is None:
            # 默认到今天
            self.end_datetime = pd.Timestamp.now()
        else:
            self.end_datetime = pd.Timestamp(self.end_datetime)
    
    def _get_stock_list(self) -> List[str]:
        """
        获取股票列表
        
        Returns
        -------
        List[str]
            股票代码列表，格式：['000001.SZ', '600000.SH', ...]
        """
        logger.info("正在获取股票列表...")
        try:
            # 获取所有A股股票列表
            stock_basic = self.pro.stock_basic(
                exchange='',
                list_status='L',  # L-上市，D-退市，P-暂停上市
                fields='ts_code,symbol,name,area,industry,list_date'
            )
            
            # 转换为标准格式：ts_code (如 000001.SZ)
            stock_list = stock_basic['ts_code'].tolist()
            logger.info(f"获取到 {len(stock_list)} 只股票")
            return stock_list
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            # 返回一些示例股票
            return ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '600519.SH']
    
    def _load_stock_list_from_file(self, file_path: Union[str, Path]) -> List[str]:
        """
        从文件读取股票列表
        
        Parameters
        ----------
        file_path: str or Path
            股票列表文件路径，每行一个股票代码
        
        Returns
        -------
        List[str]
            股票代码列表
        """
        file_path = Path(file_path).expanduser()
        if not file_path.exists():
            raise FileNotFoundError(f"股票列表文件不存在: {file_path}")
        
        stock_list = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释行
                if line and not line.startswith('#'):
                    stock_list.append(line)
        
        logger.info(f"从文件读取到 {len(stock_list)} 只股票: {file_path}")
        return stock_list
    
    @deco_retry
    def _get_daily_data(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取日线数据
        
        Parameters
        ----------
        ts_code: str
            股票代码，格式：000001.SZ
        start_date: str
            开始日期，格式：YYYYMMDD
        end_date: str
            结束日期，格式：YYYYMMDD
        
        Returns
        -------
        pd.DataFrame or None
            日线数据
        """
        try:
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            # 每次 API 调用后添加延迟，避免频率限制
            if self.delay > 0:
                time.sleep(self.delay)
            
            if df is None or df.empty:
                return None
            
            # 重命名列以匹配qlib格式
            df = df.rename(columns={
                'trade_date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
            })
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            
            # 存储原始价格（未复权）+ 复权因子，提供最大灵活性
            # 策略：
            #   1. 存储原始价格（daily() API 返回的未复权价格）
            #   2. 获取 Tushare 的 adj_factor（累积复权因子）
            #   3. 计算前复权价格和后复权价格作为额外字段，方便查阅
            #   4. factor 字段存储 Tushare 的 adj_factor（累积复权因子）
            #
            # 计算方式：
            #   - 后复权价格 = 原始价格 × adj_factor
            #   - 前复权价格 = 原始价格 × (adj_factor / adj_factor_latest)
            #   - 其中 adj_factor_latest 是最近一个交易日的 adj_factor
            try:
                # 获取 Tushare 的累积复权因子（adj_factor）
                adj_factor_df = self.pro.adj_factor(
                    ts_code=ts_code,
                    trade_date='',  # 空字符串表示不指定日期
                    start_date=start_date,
                    end_date=end_date
                )
                
                # 每次 API 调用后添加延迟，避免频率限制
                if self.delay > 0:
                    time.sleep(self.delay)
                
                if adj_factor_df is not None and not adj_factor_df.empty:
                    # 转换日期格式并合并
                    adj_factor_df['trade_date'] = pd.to_datetime(adj_factor_df['trade_date'], format='%Y%m%d')
                    adj_factor_df = adj_factor_df.rename(columns={'trade_date': 'date', 'adj_factor': 'factor'})
                    df = df.merge(adj_factor_df[['date', 'factor']], on='date', how='left')
                    df['factor'] = df['factor'].fillna(1.0)
                    
                    # 获取最新日期的 factor（用于计算前复权）
                    # 按日期排序，取最后一个非空的 factor
                    df_sorted = df.sort_values('date')
                    factor_latest = df_sorted['factor'].iloc[-1] if not df_sorted.empty else 1.0
                    
                    # 计算后复权价格（后复权 = 原始价格 × factor）
                    df['close_hfq'] = df['close'] * df['factor']  # 后复权收盘价
                    df['open_hfq'] = df['open'] * df['factor']   # 后复权开盘价
                    df['high_hfq'] = df['high'] * df['factor']   # 后复权最高价
                    df['low_hfq'] = df['low'] * df['factor']     # 后复权最低价
                    
                    # 计算前复权价格（前复权 = 原始价格 × (factor / factor_latest)）
                    # 前复权保持最新价格不变，调整历史价格
                    if factor_latest > 0:
                        factor_qfq = df['factor'] / factor_latest
                        df['close_qfq'] = df['close'] * factor_qfq  # 前复权收盘价
                        df['open_qfq'] = df['open'] * factor_qfq   # 前复权开盘价
                        df['high_qfq'] = df['high'] * factor_qfq   # 前复权最高价
                        df['low_qfq'] = df['low'] * factor_qfq     # 前复权最低价
                    else:
                        # 如果 factor_latest 为 0，使用原始价格
                        df['close_qfq'] = df['close']
                        df['open_qfq'] = df['open']
                        df['high_qfq'] = df['high']
                        df['low_qfq'] = df['low']
                else:
                    # 如果无法获取复权因子，使用默认值
                    logger.warning(f"无法获取复权因子 {ts_code}，使用默认值1.0")
                    df['factor'] = 1.0
                    # 复权价格等于原始价格
                    df['close_hfq'] = df['close']
                    df['open_hfq'] = df['open']
                    df['high_hfq'] = df['high']
                    df['low_hfq'] = df['low']
                    df['close_qfq'] = df['close']
                    df['open_qfq'] = df['open']
                    df['high_qfq'] = df['high']
                    df['low_qfq'] = df['low']
            except Exception as e:
                # 如果获取复权因子失败，使用默认值
                logger.warning(f"获取复权因子失败 {ts_code}: {e}，使用默认值1.0")
                df['factor'] = 1.0
                # 复权价格等于原始价格
                df['close_hfq'] = df['close']
                df['open_hfq'] = df['open']
                df['high_hfq'] = df['high']
                df['low_hfq'] = df['low']
                df['close_qfq'] = df['close']
                df['open_qfq'] = df['open']
                df['high_qfq'] = df['high']
                df['low_qfq'] = df['low']
            
            # 添加股票代码
            df['symbol'] = ts_code
            
            # 选择基础列（保留其他可能存在的列，以便后续扩展）
            # 基础列：原始价格 + factor
            # 额外列：前复权价格（_qfq）和后复权价格（_hfq），方便查阅
            base_columns = [
                'symbol', 'date', 
                'open', 'high', 'low', 'close', 'volume',  # 原始价格（未复权）
                'factor',  # 累积复权因子
                'open_qfq', 'high_qfq', 'low_qfq', 'close_qfq',  # 前复权价格
                'open_hfq', 'high_hfq', 'low_hfq', 'close_hfq',  # 后复权价格
            ]
            # 保留基础列，同时保留其他已存在的列（用于扩展字段）
            all_columns = base_columns + [col for col in df.columns if col not in base_columns]
            df = df[[col for col in all_columns if col in df.columns]]
            
            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.warning(f"获取日线数据失败 {ts_code}: {e}")
            return None
    
    @deco_retry
    def _get_minute_data(self, ts_code: str, start_date: str, end_date: str, freq: str = "1min") -> Optional[pd.DataFrame]:
        """
        获取分钟线数据
        
        Parameters
        ----------
        ts_code: str
            股票代码
        start_date: str
            开始日期，格式：YYYYMMDD
        end_date: str
            结束日期，格式：YYYYMMDD
        freq: str
            频率：1min, 5min, 15min, 30min, 60min
        
        Returns
        -------
        pd.DataFrame or None
            分钟线数据
        """
        try:
            # Tushare的分钟线数据接口
            # 注意：分钟线数据需要tushare pro权限
            df = ts.pro_bar(
                ts_code=ts_code,
                freq=freq,
                start_date=start_date,
                end_date=end_date,
                adj='qfq'  # 前复权
            )
            
            # 每次 API 调用后添加延迟，避免频率限制
            if self.delay > 0:
                time.sleep(self.delay)
            
            if df is None or df.empty:
                return None
            
            # 重命名列
            df = df.rename(columns={
                'trade_time': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
            })
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])
            
            # 添加复权因子（分钟线数据已经是复权的，因子设为1）
            df['factor'] = 1.0
            
            # 添加股票代码
            df['symbol'] = ts_code
            
            # 选择基础列（保留其他可能存在的列）
            base_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'factor']
            all_columns = base_columns + [col for col in df.columns if col not in base_columns]
            df = df[[col for col in all_columns if col in df.columns]]
            
            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.warning(f"获取分钟线数据失败 {ts_code} {freq}: {e}")
            return None
    
    @deco_retry
    def _get_financial_indicators(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取财务指标数据
        
        Parameters
        ----------
        ts_code: str
            股票代码
        start_date: str
            开始日期 YYYYMMDD
        end_date: str
            结束日期 YYYYMMDD
        
        Returns
        -------
        pd.DataFrame or None
        """
        try:
            # 获取每日基本面数据（包含PE、PB等）
            df = self.pro.daily_basic(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                fields='ts_code,trade_date,turnover_rate,volume_ratio,pe,pb,ps,dv_ttm,total_mv,circ_mv'
            )
            
            # 每次 API 调用后添加延迟，避免频率限制
            if self.delay > 0:
                time.sleep(self.delay)
            
            if df is None or df.empty:
                return None
            
            # 转换日期格式
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df = df.rename(columns={'trade_date': 'date'})
            
            # 选择需要的字段
            available_fields = ['date']
            for field in self.extra_fields:
                if field in df.columns:
                    available_fields.append(field)
            
            df = df[available_fields]
            return df
            
        except Exception as e:
            logger.warning(f"获取财务指标失败 {ts_code}: {e}")
            return None
    
    @deco_retry
    def _get_moneyflow_data(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取资金流向数据
        
        Parameters
        ----------
        ts_code: str
            股票代码
        start_date: str
            开始日期 YYYYMMDD
        end_date: str
            结束日期 YYYYMMDD
        
        Returns
        -------
        pd.DataFrame or None
        """
        try:
            # 获取资金流向数据
            df = self.pro.moneyflow(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            # 每次 API 调用后添加延迟，避免频率限制
            if self.delay > 0:
                time.sleep(self.delay)
            
            if df is None or df.empty:
                return None
            
            # 转换日期格式
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df = df.rename(columns={'trade_date': 'date'})
            
            # 选择需要的字段
            available_fields = ['date']
            for field in self.extra_fields:
                if field in df.columns:
                    available_fields.append(field)
            
            df = df[available_fields]
            return df
            
        except Exception as e:
            logger.warning(f"获取资金流向数据失败 {ts_code}: {e}")
            return None
    
    def _get_extra_data(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取额外指标数据
        
        Parameters
        ----------
        ts_code: str
            股票代码
        start_date: str
            开始日期 YYYYMMDD
        end_date: str
            结束日期 YYYYMMDD
        
        Returns
        -------
        pd.DataFrame or None
        """
        if not self.extra_fields:
            return None
        
        # 判断需要哪些类型的数据
        financial_fields = [f for f in self.extra_fields if f in self.INDICATOR_TYPES['financial']]
        basic_fields = [f for f in self.extra_fields if f in self.INDICATOR_TYPES['basic']]
        moneyflow_fields = [f for f in self.extra_fields if f in self.INDICATOR_TYPES['moneyflow']]
        
        result_dfs = []
        original_extra_fields = self.extra_fields.copy()
        
        # 获取财务指标
        if financial_fields or basic_fields:
            self.extra_fields = financial_fields + basic_fields
            df_financial = self._get_financial_indicators(ts_code, start_date, end_date)
            if df_financial is not None and not df_financial.empty:
                result_dfs.append(df_financial)
        
        # 获取资金流向
        if moneyflow_fields:
            self.extra_fields = moneyflow_fields
            df_moneyflow = self._get_moneyflow_data(ts_code, start_date, end_date)
            if df_moneyflow is not None and not df_moneyflow.empty:
                result_dfs.append(df_moneyflow)
        
        # 恢复原始字段列表
        self.extra_fields = original_extra_fields
        
        # 合并所有数据
        if not result_dfs:
            return None
        
        # 按日期合并
        result = result_dfs[0]
        for df in result_dfs[1:]:
            result = result.merge(df, on='date', how='outer')
        
        return result.sort_values('date').reset_index(drop=True)
    
    def _get_cached_data(self, ts_code: str) -> Optional[pd.DataFrame]:
        """
        从缓存读取数据
        
        Parameters
        ----------
        ts_code: str
            股票代码
        
        Returns
        -------
        pd.DataFrame or None
        """
        if not self.use_cache:
            return None
        
        cache_file = self.cache_dir / f"{ts_code}_{self.interval}.csv"
        if cache_file.exists():
            try:
                df = pd.read_csv(cache_file)
                df['date'] = pd.to_datetime(df['date'])
                return df
            except Exception as e:
                logger.warning(f"读取缓存失败 {cache_file}: {e}")
                return None
        return None
    
    def _save_cached_data(self, ts_code: str, df: pd.DataFrame):
        """
        保存数据到缓存
        
        Parameters
        ----------
        ts_code: str
            股票代码
        df: pd.DataFrame
            数据
        """
        if not self.use_cache or df is None or df.empty:
            return
        
        cache_file = self.cache_dir / f"{ts_code}_{self.interval}.csv"
        try:
            df.to_csv(cache_file, index=False)
        except Exception as e:
            logger.warning(f"保存缓存失败 {cache_file}: {e}")
    
    def _collect_single_stock(self, ts_code: str) -> Optional[pd.DataFrame]:
        """
        收集单只股票的数据（包括额外字段）
        
        Parameters
        ----------
        ts_code: str
            股票代码
        
        Returns
        -------
        pd.DataFrame or None
            如果数据已存在且完整，返回 None（跳过）
            如果需要更新或新数据，返回 DataFrame
        """
        # 转换日期格式
        start_date = self.start_datetime.strftime('%Y%m%d')
        end_date = self.end_datetime.strftime('%Y%m%d')
        
        # 检查 CSV 文件是否已存在且完整
        save_dir = Path(self.save_dir)
        normalized_code = self.normalize_symbol(ts_code)
        csv_file = save_dir / f"{normalized_code}.csv"
        
        if csv_file.exists():
            try:
                existing_df = pd.read_csv(csv_file)
                existing_df['date'] = pd.to_datetime(existing_df['date'])
                existing_start = existing_df['date'].min()
                existing_end = existing_df['date'].max()
                
                # 检查日期范围是否满足要求
                if (existing_start <= self.start_datetime and 
                    existing_end >= self.end_datetime):
                    # 检查是否有额外字段需求
                    if self.extra_fields:
                        missing_fields = [f for f in self.extra_fields 
                                         if f not in existing_df.columns]
                        if missing_fields:
                            # CSV 缺少字段，需要获取
                            logger.debug(f"CSV 缺少字段 {missing_fields}，需要获取: {ts_code}")
                        else:
                            # CSV 数据完整，无需更新
                            logger.info(f"⏭ {ts_code} -> {normalized_code}: 数据已存在且完整，跳过更新")
                            return None  # 返回 None 表示跳过
                    else:
                        # CSV 数据完整，无需更新
                        logger.info(f"⏭ {ts_code} -> {normalized_code}: 数据已存在且完整，跳过更新")
                        return None  # 返回 None 表示跳过
            except Exception as e:
                logger.warning(f"读取现有 CSV 文件失败 {csv_file}: {e}，将重新下载")
        
        # 检查缓存
        if self.use_cache:
            cached_df = self._get_cached_data(ts_code)
            if cached_df is not None:
                # 检查是否需要更新
                cached_end = cached_df['date'].max()
                if cached_end >= self.end_datetime:
                    # 如果有额外字段需求，需要检查缓存是否包含这些字段
                    if self.extra_fields:
                        missing_fields = [f for f in self.extra_fields if f not in cached_df.columns]
                        if missing_fields:
                            # 缓存缺少字段，需要获取
                            logger.debug(f"缓存缺少字段 {missing_fields}，需要获取: {ts_code}")
                        else:
                            # 缓存数据完整，但 CSV 可能不存在，返回缓存数据
                            logger.debug(f"使用缓存数据: {ts_code}")
                            return cached_df
                    else:
                        # 缓存数据完整，但 CSV 可能不存在，返回缓存数据
                        logger.debug(f"使用缓存数据: {ts_code}")
                        return cached_df
                else:
                    # 增量更新
                    start_date = (cached_end + pd.Timedelta(days=1)).strftime('%Y%m%d')
                    # 保存缓存数据，以便后续合并
                    cached_df_for_merge = cached_df.copy()
            else:
                cached_df_for_merge = None
        else:
            cached_df_for_merge = None
        
        # 获取基础数据（OHLCV）
        if self.interval == self.INTERVAL_1d:
            df = self._get_daily_data(ts_code, start_date, end_date)
        else:
            df = self._get_minute_data(ts_code, start_date, end_date, freq=self.interval)
        
        # 如果新数据为空，但有缓存数据，返回缓存数据
        if (df is None or df.empty) and cached_df_for_merge is not None:
            logger.debug(f"新数据为空，返回缓存数据: {ts_code}")
            return cached_df_for_merge
        
        if df is None or df.empty:
            return None
        
        # 获取额外指标数据
        if self.extra_fields:
            extra_df = self._get_extra_data(ts_code, start_date, end_date)
            if extra_df is not None and not extra_df.empty:
                # 合并数据
                df = df.merge(extra_df, on='date', how='left')
        
        # 如果有缓存数据需要合并（增量更新场景）
        if cached_df_for_merge is not None and not cached_df_for_merge.empty:
            # 合并数据，去重
            df = pd.concat([cached_df_for_merge, df], ignore_index=True)
            df = df.drop_duplicates(subset=['date'], keep='last')
            df = df.sort_values('date').reset_index(drop=True)
        elif self.use_cache:
            # 检查是否有其他缓存数据需要合并（非增量更新场景）
            cached_df = self._get_cached_data(ts_code)
            if cached_df is not None and not cached_df.empty:
                # 合并数据，去重
                df = pd.concat([cached_df, df], ignore_index=True)
                df = df.drop_duplicates(subset=['date'], keep='last')
                df = df.sort_values('date').reset_index(drop=True)
        
        # 保存缓存
        self._save_cached_data(ts_code, df)
        
        # 注意：延迟已经在每次 API 调用后添加，这里不再需要额外延迟
        # 这样可以避免重复延迟，提高效率
        
        return df
    
    def _collect_single_stock_incremental(self, ts_code: str) -> Optional[pd.DataFrame]:
        """
        增量收集：只获取额外字段，合并到现有CSV
        用于增量添加新指标，不需要重新下载基础数据
        """
        save_dir = Path(self.save_dir)
        normalized_code = self.normalize_symbol(ts_code)
        csv_file = save_dir / f"{normalized_code}.csv"
        
        # 读取现有数据
        if csv_file.exists():
            existing_df = pd.read_csv(csv_file)
            existing_df['date'] = pd.to_datetime(existing_df['date'])
        else:
            logger.warning(f"文件不存在，无法增量更新: {csv_file}")
            return None
        
        # 获取额外字段数据
        start_date = self.start_datetime.strftime('%Y%m%d')
        end_date = self.end_datetime.strftime('%Y%m%d')
        extra_df = self._get_extra_data(ts_code, start_date, end_date)
        
        if extra_df is None or extra_df.empty:
            logger.warning(f"未获取到额外数据: {ts_code}")
            return existing_df
        
        # 合并：保留现有字段，添加新字段
        result_df = existing_df.merge(extra_df, on='date', how='left')
        
        return result_df
    
    def collect_extra_fields_only(self):
        """
        只收集额外字段，合并到现有CSV文件
        用于增量添加新指标，不需要重新下载基础数据
        """
        if not self.extra_fields:
            logger.warning("未指定额外字段，请使用 --extra_fields 参数")
            return
        
        logger.info(f"开始增量收集额外字段: {self.extra_fields}")
        
        save_dir = Path(self.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        fail_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._collect_single_stock_incremental, ts_code): ts_code 
                      for ts_code in self.stock_list}
            
            for future in as_completed(futures):
                ts_code = futures[future]
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        normalized_code = self.normalize_symbol(ts_code)
                        csv_file = save_dir / f"{normalized_code}.csv"
                        df.to_csv(csv_file, index=False)
                        success_count += 1
                        logger.info(f"✓ {ts_code} -> {normalized_code} (已添加字段: {self.extra_fields})")
                    else:
                        fail_count += 1
                        logger.warning(f"✗ {ts_code}: 无数据")
                except Exception as e:
                    fail_count += 1
                    logger.error(f"✗ {ts_code}: {e}")
        
        logger.info(f"增量收集完成: 成功 {success_count}, 失败 {fail_count}")
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码格式
        Tushare格式：000001.SZ -> qlib格式：SZ000001
        
        Parameters
        ----------
        symbol: str
            股票代码
        
        Returns
        -------
        str
            标准化后的代码
        """
        if '.' in symbol:
            code, market = symbol.split('.')
            # 转换市场代码：SZ -> SZ, SH -> SH
            if market == 'SZ':
                return f"SZ{code}"
            elif market == 'SH':
                return f"SH{code}"
        return symbol
    
    def get_data(
        self, symbol: str, interval: str, start_datetime: pd.Timestamp, end_datetime: pd.Timestamp
    ) -> pd.DataFrame:
        """
        获取数据（BaseCollector 要求的抽象方法）
        
        Parameters
        ----------
        symbol: str
            股票代码（Tushare格式：000001.SZ）
        interval: str
            时间粒度
        start_datetime: pd.Timestamp
            开始时间
        end_datetime: pd.Timestamp
            结束时间
        
        Returns
        -------
        pd.DataFrame
            包含 symbol 和 date 列的数据
        """
        # 转换日期格式
        start_date = start_datetime.strftime('%Y%m%d')
        end_date = end_datetime.strftime('%Y%m%d')
        
        # 获取数据
        if interval == self.INTERVAL_1d:
            df = self._get_daily_data(symbol, start_date, end_date)
        else:
            df = self._get_minute_data(symbol, start_date, end_date, freq=interval)
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 确保包含 symbol 和 date 列
        if 'symbol' not in df.columns:
            df['symbol'] = symbol
        if 'date' not in df.columns:
            raise ValueError("数据必须包含 date 列")
        
        return df
    
    def get_instrument_list(self):
        """
        获取股票列表（BaseCollector 需要的方法）
        """
        # 如果 instrument_list 还没有初始化，先初始化
        if not hasattr(self, 'instrument_list') or self.instrument_list is None:
            # 获取股票列表
            if hasattr(self, 'stock_list') and self.stock_list:
                self.instrument_list = [self.normalize_symbol(code) for code in self.stock_list]
            else:
                # 如果 stock_list 也没有，返回空列表（会在后续初始化）
                return []
        return self.instrument_list
    
    def collect(self):
        """
        收集所有股票的数据
        """
        logger.info(f"开始收集数据，共 {len(self.stock_list)} 只股票")
        
        save_dir = Path(self.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        fail_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._collect_single_stock, ts_code): ts_code 
                      for ts_code in self.stock_list}
            
            for future in as_completed(futures):
                ts_code = futures[future]
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        # 标准化股票代码
                        normalized_code = self.normalize_symbol(ts_code)
                        # 保存为CSV文件
                        csv_file = save_dir / f"{normalized_code}.csv"
                        df.to_csv(csv_file, index=False)
                        success_count += 1
                        logger.info(f"✓ {ts_code} -> {normalized_code} ({len(df)} 条记录)")
                    elif df is None:
                        # None 表示数据已存在且完整，跳过更新
                        # 这种情况已经在 _collect_single_stock 中记录了日志（⏭ 跳过）
                        # 不增加成功或失败计数，因为这是正常的跳过行为
                        pass
                    else:
                        # df 是空 DataFrame，表示无数据
                        fail_count += 1
                        logger.warning(f"✗ {ts_code}: 无数据")
                except Exception as e:
                    fail_count += 1
                    logger.error(f"✗ {ts_code}: {e}")
        
        logger.info(f"收集完成: 成功 {success_count}, 失败 {fail_count}")
    
    def update_data(self, trading_date: Optional[str] = None):
        """
        更新数据到指定日期
        
        Parameters
        ----------
        trading_date: str, optional
            交易日期，格式：YYYY-MM-DD，如果为None则更新到今天
        """
        if trading_date is None:
            trading_date = pd.Timestamp.now().strftime('%Y-%m-%d')
        
        logger.info(f"开始更新数据到 {trading_date}")
        
        # 更新结束时间
        self.end_datetime = pd.Timestamp(trading_date)
        
        # 重新收集数据（会自动增量更新）
        self.collect()


class TushareNormalize(BaseNormalize):
    """
    Tushare 数据标准化
    """
    
    def normalize(self):
        """标准化数据"""
        normalize = Normalize(
            source_dir=self.source_dir,
            target_dir=self.target_dir,
            calendar_path=self.calendar_path,
            qlib_config=self.qlib_config,
        )
        normalize.normalize()


if __name__ == "__main__":
    # 使用 fire 创建命令行接口
    # 方式1: 直接调用 collect 方法
    class CollectorCLI:
        def collect(self, **kwargs):
            """收集所有股票的数据"""
            collector = TushareCollector(**kwargs)
            collector.collect()
        
        def collect_extra_fields_only(self, **kwargs):
            """只收集额外字段，合并到现有CSV文件"""
            collector = TushareCollector(**kwargs)
            collector.collect_extra_fields_only()
        
        def normalize(self, **kwargs):
            """标准化数据"""
            normalizer = TushareNormalize(**kwargs)
            normalizer.normalize()
    
    fire.Fire(CollectorCLI)

