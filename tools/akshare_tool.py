"""
AKShare 金融数据工具
===================
提供 A 股、港股、美股、基金、期货等金融数据

功能：
- 股票行情数据
- 财务报表数据
- 宏观经济数据
- 新闻资讯数据
- 基金数据

文档：https://akshare.akfamily.xyz/
"""

import akshare as ak
import pandas as pd
import json
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import tool


# ============================================================
# 股票数据工具
# ============================================================

class StockDataInput(BaseModel):
    """股票数据输入参数"""
    symbol: str = Field(description="股票代码，如：000001（平安银行）、600519（贵州茅台）")
    data_type: str = Field(
        default="realtime",
        description="数据类型：realtime(实时), daily(日线), financial(财务报表)"
    )
    start_date: Optional[str] = Field(default=None, description="开始日期，格式：20240101")
    end_date: Optional[str] = Field(default=None, description="结束日期，格式：20241231")


@tool(args_schema=StockDataInput)
def get_stock_data(
    symbol: str,
    data_type: str = "realtime",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    获取股票数据
    
    Args:
        symbol: 股票代码（6位数字）
        data_type: 数据类型（realtime/daily/financial）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
    
    Returns:
        股票数据的 JSON 字符串
    
    示例：
        get_stock_data("600519", "realtime")  # 茅台实时行情
        get_stock_data("000001", "daily", "20240101", "20241231")  # 平安银行日线
    """
    try:
        if data_type == "realtime":
            # 实时行情
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == symbol]
            
            if stock_data.empty:
                return f"❌ 未找到股票代码：{symbol}"
            
            result = stock_data.to_dict('records')[0]
            
        elif data_type == "daily":
            # 日线数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date or "20240101",
                end_date=end_date or pd.Timestamp.now().strftime("%Y%m%d"),
                adjust="qfq"  # 前复权
            )
            
            result = {
                "symbol": symbol,
                "period": "daily",
                "count": len(df),
                "latest": df.tail(10).to_dict('records'),
                "summary": {
                    "最新价": float(df['收盘'].iloc[-1]),
                    "涨跌幅": float(df['涨跌幅'].iloc[-1]),
                    "成交量": int(df['成交量'].iloc[-1]),
                    "成交额": float(df['成交额'].iloc[-1]),
                }
            }
            
        elif data_type == "financial":
            # 财务报表
            df = ak.stock_financial_report_sina(stock=symbol, symbol="资产负债表")
            
            result = {
                "symbol": symbol,
                "report_type": "资产负债表",
                "latest_report": df.head(1).to_dict('records')[0] if not df.empty else {}
            }
        
        else:
            return f"❌ 不支持的数据类型：{data_type}"
        
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
        
    except Exception as e:
        return f"❌ 获取股票数据失败：{type(e).__name__}: {e}"


# ============================================================
# 宏观经济数据工具
# ============================================================

class MacroDataInput(BaseModel):
    """宏观经济数据输入参数"""
    indicator: str = Field(
        description="指标名称：gdp(GDP), cpi(CPI), pmi(PMI), m2(货币供应量)"
    )


@tool(args_schema=MacroDataInput)
def get_macro_data(indicator: str) -> str:
    """
    获取宏观经济数据
    
    Args:
        indicator: 指标名称（gdp/cpi/pmi/m2）
    
    Returns:
        宏观数据的 JSON 字符串
    
    示例：
        get_macro_data("cpi")  # 获取 CPI 数据
        get_macro_data("gdp")  # 获取 GDP 数据
    """
    try:
        if indicator == "gdp":
            df = ak.macro_china_gdp()
        elif indicator == "cpi":
            df = ak.macro_china_cpi()
        elif indicator == "pmi":
            df = ak.macro_china_pmi()
        elif indicator == "m2":
            df = ak.macro_china_money_supply()
        else:
            return f"❌ 不支持的指标：{indicator}"
        
        result = {
            "indicator": indicator,
            "count": len(df),
            "latest": df.tail(12).to_dict('records'),  # 最近12个月
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
        
    except Exception as e:
        return f"❌ 获取宏观数据失败：{type(e).__name__}: {e}"


# ============================================================
# 基金数据工具
# ============================================================

class FundDataInput(BaseModel):
    """基金数据输入参数"""
    fund_code: str = Field(description="基金代码，如：000001（华夏成长）")


@tool(args_schema=FundDataInput)
def get_fund_data(fund_code: str) -> str:
    """
    获取基金数据
    
    Args:
        fund_code: 基金代码（6位数字）
    
    Returns:
        基金数据的 JSON 字符串
    
    示例：
        get_fund_data("000001")  # 华夏成长基金
    """
    try:
        # 基金净值数据
        df = ak.fund_open_fund_info_em(fund=fund_code, indicator="单位净值走势")
        
        if df.empty:
            return f"❌ 未找到基金代码：{fund_code}"
        
        result = {
            "fund_code": fund_code,
            "count": len(df),
            "latest_nav": df.tail(10).to_dict('records'),
            "summary": {
                "最新净值": float(df['单位净值'].iloc[-1]),
                "累计净值": float(df['累计净值'].iloc[-1]),
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
        
    except Exception as e:
        return f"❌ 获取基金数据失败：{type(e).__name__}: {e}"


# ============================================================
# 新闻资讯工具
# ============================================================

class NewsDataInput(BaseModel):
    """新闻数据输入参数"""
    symbol: Optional[str] = Field(default=None, description="股票代码（可选）")
    news_type: str = Field(default="market", description="新闻类型：market(市场), stock(个股)")


@tool(args_schema=NewsDataInput)
def get_financial_news(symbol: Optional[str] = None, news_type: str = "market") -> str:
    """
    获取金融新闻
    
    Args:
        symbol: 股票代码（可选，用于个股新闻）
        news_type: 新闻类型（market/stock）
    
    Returns:
        新闻数据的 JSON 字符串
    
    示例：
        get_financial_news(news_type="market")  # 市场新闻
        get_financial_news(symbol="600519", news_type="stock")  # 茅台新闻
    """
    try:
        if news_type == "market":
            # 市场新闻
            df = ak.stock_news_em()
            
        elif news_type == "stock" and symbol:
            # 个股新闻
            df = ak.stock_news_em(symbol=symbol)
        
        else:
            return f"❌ 参数错误：news_type={news_type}, symbol={symbol}"
        
        result = {
            "news_type": news_type,
            "symbol": symbol,
            "count": len(df),
            "news": df.head(20).to_dict('records')  # 最新20条
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
        
    except Exception as e:
        return f"❌ 获取新闻失败：{type(e).__name__}: {e}"


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    """测试 AKShare 工具"""
    
    # 测试股票数据
    print("=== 股票实时行情 ===")
    result = get_stock_data("600519", "realtime")
    print(result)
    
    # 测试宏观数据
    print("\n=== CPI 数据 ===")
    result = get_macro_data("cpi")
    print(result)
    
    # 测试基金数据
    print("\n=== 基金净值 ===")
    result = get_fund_data("000001")
    print(result)
    
    # 测试新闻
    print("\n=== 市场新闻 ===")
    result = get_financial_news(news_type="market")
    print(result)
