#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qlib数据可视化服务

功能:
1. 展示股票价格走势图（K线图）
2. 展示成交量走势图
3. 对比原始价格、前复权和后复权价格
4. 支持多股票对比
5. 提供Web界面访问

依赖:
    pip install streamlit plotly

使用方法:
    # 启动服务
    streamlit run data_viewer.py -- --qlib-dir ~/.qlib/qlib_data/cn_data
    
    # 或者使用默认配置
    streamlit run data_viewer.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 添加路径
CUR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CUR_DIR.parent.parent.parent))

import qlib
from qlib.constant import REG_CN
from qlib.data import D


class DataViewer:
    """数据查看器"""
    
    def __init__(self, qlib_dir: str):
        """
        初始化数据查看器
        
        Parameters
        ----------
        qlib_dir: str
            Qlib数据目录
        """
        self.qlib_dir = Path(qlib_dir).expanduser()
        
        # 初始化Qlib
        if not hasattr(qlib, '_inited') or not qlib._inited:
            qlib.init(provider_uri=str(self.qlib_dir), region=REG_CN)
    
    def get_stock_list(self) -> List[str]:
        """
        获取股票列表
        
        Returns
        -------
        List[str]
            股票代码列表
        """
        try:
            instruments = D.instruments(market='all')
            stock_list = D.list_instruments(instruments=instruments, as_list=True)
            return sorted(stock_list)
        except Exception as e:
            st.error(f"获取股票列表失败: {e}")
            return []
    
    def get_stock_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        fields: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取股票数据
        
        Parameters
        ----------
        symbols: List[str]
            股票代码列表
        start_date: str
            开始日期
        end_date: str
            结束日期
        fields: List[str], optional
            字段列表
        
        Returns
        -------
        pd.DataFrame
            股票数据
        """
        if fields is None:
            fields = [
                '$open', '$close', '$high', '$low', '$volume',
                '$factor', '$open_qfq', '$close_qfq', '$high_qfq', '$low_qfq',
                '$open_hfq', '$close_hfq', '$high_hfq', '$low_hfq'
            ]
        
        try:
            data = D.features(
                symbols,
                fields,
                start_time=start_date,
                end_time=end_date,
                freq='day'
            )
            return data
        except Exception as e:
            st.error(f"获取股票数据失败: {e}")
            return pd.DataFrame()
    
    def plot_candlestick(
        self,
        symbol: str,
        data: pd.DataFrame,
        price_type: str = "原始价格"
    ) -> go.Figure:
        """
        绘制K线图
        
        Parameters
        ----------
        symbol: str
            股票代码
        data: pd.DataFrame
            股票数据
        price_type: str
            价格类型: 原始价格, 前复权, 后复权
        
        Returns
        -------
        go.Figure
            图表对象
        """
        # 选择价格字段
        if price_type == "前复权":
            open_col, high_col, low_col, close_col = '$open_qfq', '$high_qfq', '$low_qfq', '$close_qfq'
        elif price_type == "后复权":
            open_col, high_col, low_col, close_col = '$open_hfq', '$high_hfq', '$low_hfq', '$close_hfq'
        else:  # 原始价格
            open_col, high_col, low_col, close_col = '$open', '$high', '$low', '$close'
        
        # 提取单只股票数据
        if symbol in data.index.get_level_values(0):
            stock_data = data.loc[symbol].copy()
        else:
            st.warning(f"未找到股票 {symbol} 的数据")
            return go.Figure()
        
        # 重置索引，确保日期列可用
        stock_data = stock_data.reset_index()
        
        # 创建子图：K线图 + 成交量
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f'{symbol} - {price_type}', '成交量')
        )
        
        # K线图
        fig.add_trace(
            go.Candlestick(
                x=stock_data['datetime'],
                open=stock_data[open_col],
                high=stock_data[high_col],
                low=stock_data[low_col],
                close=stock_data[close_col],
                name='K线'
            ),
            row=1, col=1
        )
        
        # 成交量
        colors = ['red' if close >= open else 'green' 
                 for close, open in zip(stock_data[close_col], stock_data[open_col])]
        
        fig.add_trace(
            go.Bar(
                x=stock_data['datetime'],
                y=stock_data['$volume'],
                name='成交量',
                marker_color=colors,
                showlegend=False
            ),
            row=2, col=1
        )
        
        # 更新布局
        fig.update_layout(
            title=f'{symbol} 价格走势 ({price_type})',
            xaxis_rangeslider_visible=False,
            height=600,
            hovermode='x unified'
        )
        
        fig.update_xaxes(title_text="日期", row=2, col=1)
        fig.update_yaxes(title_text="价格", row=1, col=1)
        fig.update_yaxes(title_text="成交量", row=2, col=1)
        
        return fig
    
    def plot_price_comparison(
        self,
        symbol: str,
        data: pd.DataFrame
    ) -> go.Figure:
        """
        对比不同复权方式的价格
        
        Parameters
        ----------
        symbol: str
            股票代码
        data: pd.DataFrame
            股票数据
        
        Returns
        -------
        go.Figure
            图表对象
        """
        # 提取单只股票数据
        if symbol in data.index.get_level_values(0):
            stock_data = data.loc[symbol].copy()
        else:
            st.warning(f"未找到股票 {symbol} 的数据")
            return go.Figure()
        
        stock_data = stock_data.reset_index()
        
        # 创建图表
        fig = go.Figure()
        
        # 原始价格
        fig.add_trace(go.Scatter(
            x=stock_data['datetime'],
            y=stock_data['$close'],
            mode='lines',
            name='原始价格',
            line=dict(color='blue')
        ))
        
        # 前复权价格
        if '$close_qfq' in stock_data.columns:
            fig.add_trace(go.Scatter(
                x=stock_data['datetime'],
                y=stock_data['$close_qfq'],
                mode='lines',
                name='前复权',
                line=dict(color='green')
            ))
        
        # 后复权价格
        if '$close_hfq' in stock_data.columns:
            fig.add_trace(go.Scatter(
                x=stock_data['datetime'],
                y=stock_data['$close_hfq'],
                mode='lines',
                name='后复权',
                line=dict(color='red')
            ))
        
        fig.update_layout(
            title=f'{symbol} 不同复权方式对比',
            xaxis_title='日期',
            yaxis_title='价格',
            hovermode='x unified',
            height=500
        )
        
        return fig
    
    def plot_multiple_stocks(
        self,
        symbols: List[str],
        data: pd.DataFrame,
        price_type: str = "原始价格",
        normalize: bool = True
    ) -> go.Figure:
        """
        对比多只股票
        
        Parameters
        ----------
        symbols: List[str]
            股票代码列表
        data: pd.DataFrame
            股票数据
        price_type: str
            价格类型
        normalize: bool
            是否归一化（以第一天价格为基准）
        
        Returns
        -------
        go.Figure
            图表对象
        """
        # 选择价格字段
        if price_type == "前复权":
            close_col = '$close_qfq'
        elif price_type == "后复权":
            close_col = '$close_hfq'
        else:
            close_col = '$close'
        
        fig = go.Figure()
        
        for symbol in symbols:
            if symbol in data.index.get_level_values(0):
                stock_data = data.loc[symbol].copy()
                stock_data = stock_data.reset_index()
                
                prices = stock_data[close_col]
                
                # 归一化
                if normalize and len(prices) > 0:
                    prices = (prices / prices.iloc[0] - 1) * 100  # 转换为百分比涨跌幅
                
                fig.add_trace(go.Scatter(
                    x=stock_data['datetime'],
                    y=prices,
                    mode='lines',
                    name=symbol
                ))
        
        y_title = '涨跌幅 (%)' if normalize else '价格'
        
        fig.update_layout(
            title=f'多股票对比 ({price_type})',
            xaxis_title='日期',
            yaxis_title=y_title,
            hovermode='x unified',
            height=500
        )
        
        return fig


def main():
    """主函数"""
    st.set_page_config(
        page_title="Qlib 数据查看器",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 Qlib 数据查看器")
    st.markdown("---")
    
    # 侧边栏配置
    st.sidebar.header("配置")
    
    # Qlib数据目录
    default_qlib_dir = "~/.qlib/qlib_data/cn_data"
    qlib_dir = st.sidebar.text_input(
        "Qlib数据目录",
        value=default_qlib_dir,
        help="Qlib格式数据所在目录"
    )
    
    # 初始化查看器
    try:
        viewer = DataViewer(qlib_dir)
        stock_list = viewer.get_stock_list()
        
        if not stock_list:
            st.error("未找到股票数据，请检查数据目录")
            return
        
        st.sidebar.success(f"已加载 {len(stock_list)} 只股票")
        
    except Exception as e:
        st.error(f"初始化失败: {e}")
        return
    
    # 查看模式
    view_mode = st.sidebar.radio(
        "查看模式",
        ["单股票分析", "复权对比", "多股票对比"]
    )
    
    # 日期范围
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "开始日期",
            value=datetime.now() - timedelta(days=365)
        )
    with col2:
        end_date = st.date_input(
            "结束日期",
            value=datetime.now()
        )
    
    # 根据模式选择股票
    if view_mode == "多股票对比":
        selected_stocks = st.sidebar.multiselect(
            "选择股票（最多5只）",
            options=stock_list,
            default=stock_list[:3] if len(stock_list) >= 3 else stock_list,
            max_selections=5
        )
    else:
        selected_stock = st.sidebar.selectbox(
            "选择股票",
            options=stock_list,
            index=0
        )
        selected_stocks = [selected_stock]
    
    # 价格类型
    price_type = st.sidebar.selectbox(
        "价格类型",
        ["原始价格", "前复权", "后复权"]
    )
    
    # 获取数据
    if st.sidebar.button("📊 加载数据", type="primary"):
        with st.spinner("正在加载数据..."):
            data = viewer.get_stock_data(
                selected_stocks,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if data.empty:
                st.warning("未获取到数据")
                return
            
            # 保存到session state
            st.session_state['data'] = data
            st.session_state['selected_stocks'] = selected_stocks
            st.session_state['view_mode'] = view_mode
            st.session_state['price_type'] = price_type
    
    # 显示数据
    if 'data' in st.session_state:
        data = st.session_state['data']
        selected_stocks = st.session_state['selected_stocks']
        view_mode = st.session_state['view_mode']
        price_type = st.session_state['price_type']
        
        # 根据模式显示图表
        if view_mode == "单股票分析":
            st.subheader(f"📈 {selected_stocks[0]} 价格走势")
            fig = viewer.plot_candlestick(selected_stocks[0], data, price_type)
            st.plotly_chart(fig, use_container_width=True)
            
        elif view_mode == "复权对比":
            st.subheader(f"📊 {selected_stocks[0]} 复权对比")
            fig = viewer.plot_price_comparison(selected_stocks[0], data)
            st.plotly_chart(fig, use_container_width=True)
            
            # 说明
            with st.expander("ℹ️ 复权说明"):
                st.markdown("""
                ### 复权方式说明
                
                - **原始价格**: 未经复权调整的实际交易价格
                - **前复权**: 保持最新价格不变，调整历史价格。适合查看当前价格的历史走势。
                - **后复权**: 将历史价格调整到最新价格水平。适合分析长期走势的连续性。
                
                ### 计算公式
                ```
                后复权价格 = 原始价格 × (当日复权因子 / 最新复权因子)
                前复权价格 = 原始价格 × (当日复权因子 / 最新复权因子)
                ```
                
                **注意**: Tushare的adj_factor定义下，前复权和后复权的计算公式相同，
                区别在于选择不同的基准日期。
                """)
        
        else:  # 多股票对比
            st.subheader("📊 多股票对比")
            
            # 归一化选项
            normalize = st.checkbox("归一化（显示涨跌幅）", value=True)
            
            fig = viewer.plot_multiple_stocks(
                selected_stocks,
                data,
                price_type,
                normalize
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 显示原始数据
        with st.expander("📋 查看原始数据"):
            st.dataframe(data, use_container_width=True)
    
    else:
        st.info("👈 请在左侧配置参数并点击"加载数据"按钮")
    
    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>Qlib 数据查看器 | 基于 Streamlit + Plotly</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
