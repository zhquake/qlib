#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
指数管理工具
功能：
1. 列出所有可用的指数
2. 根据指数代码获取成分股列表
3. 下载指定指数的成分股数据

使用方法:
    # 列出所有指数
    python index_manager.py list --token YOUR_TOKEN
    
    # 获取指定指数的成分股
    python index_manager.py get --token YOUR_TOKEN --index_code 000300.SH --output stocks.txt
    
    # 交互式选择指数并获取成分股
    python index_manager.py interactive --token YOUR_TOKEN
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import pandas as pd
import tushare as ts
from loguru import logger


class IndexManager:
    """指数管理器"""
    
    # 常用指数代码映射（用于快速访问）
    COMMON_INDICES = {
        'hs300': '000300.SH',      # 沪深300
        'csi300': '000300.SH',     # 沪深300
        'hs500': '000905.SH',      # 中证500
        'csi500': '000905.SH',     # 中证500
        'zz500': '000905.SH',      # 中证500
        'hs100': '000903.SH',      # 中证100
        'csi100': '000903.SH',     # 中证100
        'sz50': '000016.SH',       # 上证50
        'sh50': '000016.SH',       # 上证50
        'zz1000': '000852.SH',     # 中证1000
        'csi1000': '000852.SH',    # 中证1000
        'cybz': '399006.SZ',       # 创业板指
        'cyb': '399006.SZ',        # 创业板指
        'kc50': '000688.SH',       # 科创50
    }
    
    def __init__(self, token: str):
        """
        初始化指数管理器
        
        Parameters
        ----------
        token: str
            Tushare API token
        """
        self.token = token
        self.pro = ts.pro_api(token)
    
    def list_indices(self, market: str = 'MSCI', limit: int = 100) -> pd.DataFrame:
        """
        列出所有可用的指数
        
        Parameters
        ----------
        market: str
            市场类型，可选值：MSCI（MSCI指数）、CSI（中证指数）、SSE（上交所）、SZSE（深交所）
        limit: int
            返回数量限制
        
        Returns
        -------
        pd.DataFrame
            指数列表，包含指数代码、名称等信息
        """
        try:
            logger.info(f"正在获取指数列表（市场: {market}）...")
            
            # 使用 index_basic 接口获取指数基本信息
            df = self.pro.index_basic(
                market=market,
                fields='ts_code,name,market,publisher,index_type,category,base_date,base_point,list_date,weight_rule,desc,exp_date'
            )
            
            if df is None or df.empty:
                logger.warning(f"未获取到 {market} 市场的指数数据，尝试其他市场...")
                # 尝试获取所有市场
                all_dfs = []
                for mkt in ['MSCI', 'CSI', 'SSE', 'SZSE']:
                    try:
                        df_mkt = self.pro.index_basic(market=mkt)
                        if df_mkt is not None and not df_mkt.empty:
                            all_dfs.append(df_mkt)
                    except:
                        continue
                
                if all_dfs:
                    df = pd.concat(all_dfs, ignore_index=True)
                else:
                    raise ValueError("未能获取到任何指数数据")
            
            # 按指数代码排序
            df = df.sort_values('ts_code').reset_index(drop=True)
            
            logger.info(f"成功获取 {len(df)} 个指数")
            return df
            
        except Exception as e:
            logger.error(f"获取指数列表失败: {e}")
            raise
    
    def get_index_constituents(self, index_code: str, output_file: Optional[str] = None, 
                              trade_date: Optional[str] = None) -> List[str]:
        """
        获取指定指数的成分股列表
        
        Parameters
        ----------
        index_code: str
            指数代码，如 '000300.SH'（沪深300）
            也支持简写，如 'hs300', 'csi300' 等
        output_file: str, optional
            输出文件路径，如果指定则保存到文件
        trade_date: str, optional
            指定交易日期(YYYYMMDD格式)，如果不指定则使用最近交易日
        
        Returns
        -------
        List[str]
            股票代码列表，格式：['000001.SZ', '600000.SH', ...]
        """
        # 检查是否是简写代码
        original_code = index_code
        if index_code.lower() in self.COMMON_INDICES:
            index_code = self.COMMON_INDICES[index_code.lower()]
            logger.info(f"使用指数代码映射: {original_code} -> {index_code}")
        
        logger.info(f"正在获取指数 {index_code} 的成分股列表...")
        
        df = None
        
        # 方法1: 尝试使用 index_weight 接口（需要日期）
        if trade_date:
            check_dates = [trade_date]
        else:
            # 尝试最近30个交易日（因为可能是非交易日）
            check_dates = [(datetime.now() - timedelta(days=i)).strftime('%Y%m%d') 
                          for i in range(0, 30)]
        
        logger.info(f"尝试使用 index_weight 接口...")
        
        for i, check_date in enumerate(check_dates):
            try:
                df = self.pro.index_weight(
                    index_code=index_code,
                    trade_date=check_date
                )
                if df is not None and not df.empty:
                    logger.info(f"成功获取日期 {check_date} 的成分股数据，共 {len(df)} 条")
                    break
            except Exception as e:
                if i == 0:
                    logger.debug(f"日期 {check_date} 获取失败: {e}")
                continue
        
        # 方法2: 如果 index_weight 失败，尝试使用 index_cons 接口
        if df is None or df.empty:
            try:
                logger.info("尝试使用 index_cons 接口...")
                df = self.pro.index_cons(index_code=index_code)
                if df is not None and not df.empty:
                    logger.info(f"使用 index_cons 接口成功获取成分股，共 {len(df)} 条")
            except Exception as e:
                logger.warning(f"index_cons 接口也失败: {e}")
        
        if df is None or df.empty:
            raise ValueError(f"未能获取到指数 {index_code} 的成分股数据，请检查指数代码和API权限")
        
        # 提取股票代码
        # index_weight 接口返回的字段可能是 'con_code' 或 'ts_code'
        # index_cons 接口返回的字段是 'ts_code'
        if 'con_code' in df.columns:
            stock_list = df['con_code'].unique().tolist()
        elif 'ts_code' in df.columns:
            stock_list = df['ts_code'].unique().tolist()
        else:
            raise ValueError(f"无法识别股票代码字段，可用字段: {df.columns.tolist()}")
        
        stock_list = sorted(stock_list)
        logger.info(f"成功获取 {len(stock_list)} 只成分股")
        
        # 保存到文件
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                # 添加文件头注释
                f.write(f"# 指数成分股列表: {index_code} ({original_code})\n")
                f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 股票数量: {len(stock_list)}\n")
                f.write("#\n")
                for stock in stock_list:
                    f.write(f"{stock}\n")
            logger.info(f"股票列表已保存到: {output_path}")
        
        return stock_list
    
    def get_multiple_indices_constituents(self, index_codes: List[str], 
                                         output_file: Optional[str] = None,
                                         union: bool = True) -> List[str]:
        """
        获取多个指数的成分股列表
        
        Parameters
        ----------
        index_codes: List[str]
            指数代码列表，如 ['000300.SH', '000905.SH']
        output_file: str, optional
            输出文件路径
        union: bool, default True
            True: 返回所有指数的并集
            False: 返回所有指数的交集
        
        Returns
        -------
        List[str]
            股票代码列表
        """
        logger.info(f"正在获取多个指数的成分股: {index_codes}")
        logger.info(f"合并方式: {'并集' if union else '交集'}")
        
        all_stocks = []
        for idx_code in index_codes:
            try:
                stocks = self.get_index_constituents(idx_code)
                all_stocks.append(set(stocks))
                logger.info(f"  {idx_code}: {len(stocks)} 只股票")
            except Exception as e:
                logger.error(f"获取指数 {idx_code} 失败: {e}")
                continue
        
        if not all_stocks:
            raise ValueError("未能获取任何指数的成分股数据")
        
        # 计算并集或交集
        if union:
            result_set = set().union(*all_stocks)
        else:
            result_set = set.intersection(*all_stocks)
        
        result_list = sorted(list(result_set))
        logger.info(f"最终结果: {len(result_list)} 只股票")
        
        # 保存到文件
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# 多指数成分股{'并集' if union else '交集'}: {', '.join(index_codes)}\n")
                f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 股票数量: {len(result_list)}\n")
                f.write("#\n")
                for stock in result_list:
                    f.write(f"{stock}\n")
            logger.info(f"股票列表已保存到: {output_path}")
        
        return result_list
    
    def interactive_select(self) -> Optional[str]:
        """
        交互式选择指数
        
        Returns
        -------
        str or None
            选择的指数代码，如果取消则返回 None
        """
        try:
            # 获取所有指数
            print("\n正在获取指数列表...")
            df = self.list_indices()
            
            # 显示常用指数
            print("\n" + "="*80)
            print("常用指数（可直接输入简写代码）:")
            print("-"*80)
            for key, code in self.COMMON_INDICES.items():
                # 查找指数名称
                index_info = df[df['ts_code'] == code]
                if not index_info.empty:
                    name = index_info.iloc[0].get('name', '未知')
                    print(f"  {key:10s} -> {code:12s} ({name})")
            
            # 显示部分指数列表
            print("\n" + "="*80)
            print("指数列表（前50个）:")
            print("-"*80)
            print(f"{'序号':<6} {'指数代码':<15} {'指数名称':<30} {'市场':<10}")
            print("-"*80)
            
            for idx, row in df.head(50).iterrows():
                ts_code = row.get('ts_code', '')
                name = row.get('name', '未知')
                market = row.get('market', '未知')
                print(f"{idx+1:<6} {ts_code:<15} {name[:28]:<30} {market:<10}")
            
            if len(df) > 50:
                print(f"\n... 还有 {len(df) - 50} 个指数未显示")
                print("提示: 可以输入完整的指数代码（如 000300.SH）")
            
            print("\n" + "="*80)
            print("请选择指数:")
            print("  1. 输入简写代码（如: hs300, csi500）")
            print("  2. 输入完整指数代码（如: 000300.SH）")
            print("  3. 输入序号（1-50）")
            print("  4. 输入 'q' 退出")
            
            choice = input("\n请输入选择: ").strip()
            
            if choice.lower() == 'q':
                return None
            
            # 检查是否是简写代码
            if choice.lower() in self.COMMON_INDICES:
                return self.COMMON_INDICES[choice.lower()]
            
            # 检查是否是完整指数代码
            if '.' in choice and len(choice) > 5:
                # 验证代码是否存在
                if choice in df['ts_code'].values:
                    return choice
                else:
                    print(f"错误: 指数代码 {choice} 不存在")
                    return None
            
            # 检查是否是序号
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(df):
                    return df.iloc[idx]['ts_code']
                else:
                    print(f"错误: 序号 {choice} 超出范围")
                    return None
            except ValueError:
                print(f"错误: 无法识别输入 '{choice}'")
                return None
                
        except Exception as e:
            logger.error(f"交互式选择失败: {e}")
            return None


def list_indices_cmd(args):
    """列出所有指数命令"""
    manager = IndexManager(args.token)
    df = manager.list_indices()
    
    print("\n" + "="*80)
    print(f"指数列表（共 {len(df)} 个）:")
    print("="*80)
    print(f"{'指数代码':<15} {'指数名称':<40} {'市场':<10} {'发布日期':<12}")
    print("-"*80)
    
    for _, row in df.iterrows():
        ts_code = row.get('ts_code', '')
        name = row.get('name', '未知')
        market = row.get('market', '未知')
        list_date = row.get('list_date', '')
        print(f"{ts_code:<15} {name[:38]:<40} {market:<10} {list_date:<12}")


def get_constituents_cmd(args):
    """获取成分股命令"""
    manager = IndexManager(args.token)
    
    try:
        stock_list = manager.get_index_constituents(args.index_code, args.output)
        
        print(f"\n成功获取 {len(stock_list)} 只成分股")
        if args.output:
            print(f"股票列表已保存到: {args.output}")
        print(f"\n前10只股票示例:")
        for stock in stock_list[:10]:
            print(f"  {stock}")
        if len(stock_list) > 10:
            print(f"  ... 还有 {len(stock_list) - 10} 只股票")
    except Exception as e:
        logger.error(f"获取成分股失败: {e}")
        sys.exit(1)


def interactive_cmd(args):
    """交互式命令"""
    manager = IndexManager(args.token)
    
    index_code = manager.interactive_select()
    
    if index_code is None:
        print("已取消选择")
        return
    
    print(f"\n已选择指数: {index_code}")
    
    # 获取成分股
    output_file = args.output or f"{index_code.replace('.', '_')}_stocks.txt"
    try:
        stock_list = manager.get_index_constituents(index_code, output_file)
        
        print(f"\n成功获取 {len(stock_list)} 只成分股")
        print(f"股票列表已保存到: {output_file}")
        print(f"\n前10只股票示例:")
        for stock in stock_list[:10]:
            print(f"  {stock}")
        if len(stock_list) > 10:
            print(f"  ... 还有 {len(stock_list) - 10} 只股票")
    except Exception as e:
        logger.error(f"获取成分股失败: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='指数管理工具 - 列出指数、获取成分股',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有指数
  python index_manager.py list --token YOUR_TOKEN
  
  # 获取沪深300成分股
  python index_manager.py get --token YOUR_TOKEN --index_code 000300.SH --output hs300_stocks.txt
  
  # 使用简写代码
  python index_manager.py get --token YOUR_TOKEN --index_code hs300 --output hs300_stocks.txt
  
  # 交互式选择
  python index_manager.py interactive --token YOUR_TOKEN
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令', required=True)
    
    # list 命令
    parser_list = subparsers.add_parser('list', help='列出所有可用的指数')
    parser_list.add_argument('--token', type=str, required=True, help='Tushare API token')
    
    # get 命令
    parser_get = subparsers.add_parser('get', help='获取指定指数的成分股列表')
    parser_get.add_argument('--token', type=str, required=True, help='Tushare API token')
    parser_get.add_argument('--index_code', type=str, required=True,
                           help='指数代码（如 000300.SH）或简写（如 hs300, csi500）')
    parser_get.add_argument('--output', type=str, default=None,
                           help='输出文件路径（可选）')
    
    # interactive 命令
    parser_interactive = subparsers.add_parser('interactive', help='交互式选择指数并获取成分股')
    parser_interactive.add_argument('--token', type=str, required=True, help='Tushare API token')
    parser_interactive.add_argument('--output', type=str, default=None,
                                   help='输出文件路径（可选，默认使用指数代码命名）')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_indices_cmd(args)
    elif args.command == 'get':
        get_constituents_cmd(args)
    elif args.command == 'interactive':
        interactive_cmd(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

