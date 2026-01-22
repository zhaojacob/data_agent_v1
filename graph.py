"""
data_agent/graph.py
===================
数据分析智能助手 - LangGraph Agent

功能概述：
- 连接 PostgreSQL 数据库进行 SQL 查询
- 执行 Python 代码进行数据分析
- 使用 matplotlib/seaborn 生成可视化图表
- 通过 Tavily 进行网络搜索

依赖：
- psycopg (v3): PostgreSQL 连接库
- langchain: LLM 框架
- pandas: 数据处理
- matplotlib/seaborn: 可视化

配置：
- 数据库配置在 .env 文件中设置（PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DBNAME）
"""

import os
from dotenv import load_dotenv 
from langchain_deepseek import ChatDeepSeek
from typing import Annotated
from typing_extensions import TypedDict
from langchain.agents import create_agent
from langchain.tools import tool
from pydantic import BaseModel, Field
import matplotlib
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
# import pymysql  # 原 MySQL 连接库（已弃用）
# import psycopg2  # PostgreSQL 连接库 v2（已弃用）
import psycopg  # PostgreSQL 连接库 v3（当前使用）
from langchain_tavily import TavilySearch
from e2b_code_interpreter import Sandbox  # E2B 云端代码沙盒
import sqlparse  # SQL 解析和验证

# 浏览器自动化工具（browser-use 版本，AI 驱动）
try:
    from tools.browser_tool import browser_task
    BROWSER_TOOLS_AVAILABLE = True
except ImportError:
    BROWSER_TOOLS_AVAILABLE = False
    print("[警告] 浏览器工具未加载，请安装: pip install browser-use && playwright install chromium")

# 加载环境变量（从 .env 文件读取配置）
load_dotenv(override=True)


# ============================================================================
# 第一部分：网络搜索工具
# ============================================================================
# 功能：当用户询问与数据分析无关的问题（如新闻、实时信息）时，调用 Tavily 搜索引擎
# 实现：使用 langchain_tavily 的 TavilySearch，需要在 .env 中配置 TAVILY_API_KEY
# 注意：本地开发需要代理才能访问，Render 部署不需要
# ============================================================================

search_tool = TavilySearch(max_results=5, topic="general")


# ============================================================================
# 第二部分：SQL 查询工具 (sql_inter)
# ============================================================================
# 功能：在 PostgreSQL 数据库中执行 SQL 查询语句，返回查询结果
# 实现：
#   1. 验证 SQL 安全性（仅允许 SELECT，禁止危险操作）
#   2. 从 .env 读取数据库连接配置
#   3. 使用 psycopg v3 建立连接
#   4. 执行用户提供的 SQL 语句
#   5. 将结果转为 JSON 字符串返回
# 适用场景：查看数据、统计分析、条件筛选等只读操作
# 安全性：代码层验证 + 数据库只读用户双重防护
# ============================================================================


# SQL 安全验证函数
def validate_sql(query: str) -> tuple:
    """
    验证 SQL 查询的安全性
    
    :param query: SQL 查询语句
    :return: (is_valid: bool, message: str)
    
    验证规则：
    1. 仅允许 SELECT 语句
    2. 禁止危险关键字（DROP, DELETE, INSERT 等）
    3. 禁止访问系统表（pg_shadow, pg_roles 等）
    """
    # 禁止的 SQL 关键字
    FORBIDDEN_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 
        'INSERT', 'UPDATE', 'GRANT', 'REVOKE', 'EXECUTE',
        'COPY', 'VACUUM', 'REINDEX', 'CLUSTER'
    ]
    
    # 禁止访问的系统表
    FORBIDDEN_TABLES = [
        'pg_shadow', 'pg_roles', 'pg_authid', 'pg_auth_members',
        'pg_user', 'pg_group', 'information_schema'
    ]
    
    if not query or not query.strip():
        return False, "SQL 查询不能为空"
    
    # 解析 SQL
    try:
        parsed = sqlparse.parse(query)
    except Exception as e:
        return False, f"SQL 解析失败：{e}"
    
    if not parsed:
        return False, "无效的 SQL 语法"
    
    # 检查每个语句
    for statement in parsed:
        # 获取语句类型
        stmt_type = statement.get_type()
        
        # 只允许 SELECT 和 UNKNOWN（某些复杂查询可能被识别为 UNKNOWN）
        if stmt_type and stmt_type.upper() not in ['SELECT', 'UNKNOWN']:
            return False, f"仅允许 SELECT 查询，收到：{stmt_type}"
    
    # 转为大写进行关键字检查
    upper_query = query.upper()
    
    # 检查禁止的关键字
    for keyword in FORBIDDEN_KEYWORDS:
        # 使用单词边界检查，避免误判（如 "UPDATED_AT" 中的 "UPDATE"）
        import re
        if re.search(r'\b' + keyword + r'\b', upper_query):
            return False, f"禁止使用 {keyword} 操作"
    
    # 检查禁止的系统表
    lower_query = query.lower()
    for table in FORBIDDEN_TABLES:
        if table.lower() in lower_query:
            return False, f"禁止访问系统表：{table}"
    
    return True, "验证通过"


# 工具描述（供 LLM 理解工具用途）
description_sql_inter = """
当用户需要进行数据库查询工作时，请调用该函数。
该函数用于在指定PostgreSQL服务器上运行一段SQL代码，完成数据查询相关工作，
并且当前函数是使用psycopg连接PostgreSQL数据库。
本函数只负责运行SQL代码并进行数据查询，若要进行数据提取，则使用另一个extract_data函数。
注意：仅支持 SELECT 查询，禁止 DROP、DELETE、INSERT 等修改操作。
"""

# 定义输入参数的结构化模型
class SQLQuerySchema(BaseModel):
    sql_query: str = Field(description=description_sql_inter)


@tool(args_schema=SQLQuerySchema)
def sql_inter(sql_query: str) -> str:
    """
    执行 SQL 查询并返回结果
    
    :param sql_query: SQL 查询语句（如 SELECT * FROM table_name）
    :return: 查询结果的 JSON 字符串
    
    安全说明：
        1. 仅允许 SELECT 查询
        2. 禁止 DROP、DELETE、INSERT 等修改操作
        3. 禁止访问系统表
        4. 建议配合数据库只读用户使用
    """
    # ============================================================
    # 第一道防线：代码层 SQL 验证
    # ============================================================
    is_valid, message = validate_sql(sql_query)
    if not is_valid:
        return f"❌ 查询被拒绝：{message}"
    
    # ============================================================
    # 使用配置模块自动选择数据库
    # ============================================================
    from config import get_db_connection_string
    
    try:
        connection = psycopg.connect(get_db_connection_string())
    except Exception as e:
        return f"❌ 数据库连接失败：{e}"
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            results = cursor.fetchall()
    except Exception as e:
        return f"❌ 查询执行失败：{e}"
    finally:
        connection.close()

    # 将结果转为 JSON 字符串返回（便于 LLM 解析）
    # 使用 default=str 处理 datetime 等特殊类型
    return json.dumps(results, ensure_ascii=False, default=str)


# ============================================================================
# 第三部分：数据提取工具 (extract_data)
# ============================================================================
# 功能：从 PostgreSQL 提取数据并保存为 pandas DataFrame
# 实现：
#   1. 执行 SQL 查询
#   2. 使用 pandas.read_sql() 将结果转为 DataFrame
#   3. 将 DataFrame 保存到全局变量，供后续 Python 代码使用
# 适用场景：需要对数据进行进一步分析、绘图时，先提取数据
# ============================================================================

class ExtractQuerySchema(BaseModel):
    sql_query: str = Field(description="用于从 PostgreSQL 提取数据的 SQL 查询语句。")
    df_name: str = Field(description="指定用于保存结果的 pandas 变量名称（字符串形式）。")


@tool(args_schema=ExtractQuerySchema)
def extract_data(sql_query: str, df_name: str) -> str:
    """
    从数据库提取数据并保存为 pandas DataFrame
    
    :param sql_query: SQL 查询语句
    :param df_name: DataFrame 变量名（如 'df_students'）
    :return: 操作结果信息
    
    安全说明：
        1. 仅允许 SELECT 查询
        2. 禁止 DROP、DELETE、INSERT 等修改操作
    """
    # ============================================================
    # SQL 安全验证
    # ============================================================
    is_valid, message = validate_sql(sql_query)
    if not is_valid:
        return f"❌ 查询被拒绝：{message}"
    
    print("正在调用 extract_data 工具运行 SQL 查询...")
    
    # ============================================================
    # 使用配置模块自动选择数据库
    # ============================================================
    from config import get_db_connection_string

    try:
        # 创建 PostgreSQL 数据库连接 (psycopg v3)
        connection = psycopg.connect(get_db_connection_string())
    except Exception as e:
        return f"❌ 数据库连接失败：{e}"

    try:
        # 执行 SQL 并转为 DataFrame
        df = pd.read_sql(sql_query, connection)
        # 保存到全局变量（供 python_inter 和 fig_inter 使用）
        globals()[df_name] = df
        return f"✅ 成功创建 pandas 对象 `{df_name}`，包含从 PostgreSQL 提取的数据，共 {len(df)} 行。"
    except Exception as e:
        return f"❌ 执行失败：{e}"
    finally:
        connection.close()


# ============================================================================
# 第四部分：Python 代码执行工具 (python_inter)
# ============================================================================
# 功能：在 E2B 云端沙盒中执行用户提供的 Python 代码（非绘图类）
# 实现：
#   1. 创建 E2B 沙盒实例
#   2. 在沙盒中执行代码
#   3. 返回执行结果
# 适用场景：数据处理、统计计算、变量操作等
# 注意：绘图代码请使用 fig_inter 工具
# 安全性：代码在隔离的云端沙盒中执行，无法访问主机系统
# ============================================================================

class PythonCodeInput(BaseModel):
    py_code: str = Field(
        description="一段合法的 Python 代码字符串，例如 '2 + 2' 或 'x = 3\\ny = x * 2'"
    )


@tool(args_schema=PythonCodeInput)
def python_inter(py_code: str) -> str:
    """
    在 E2B 云端沙盒中执行 Python 代码并返回结果（仅限非绘图代码）
    
    :param py_code: Python 代码字符串
    :return: 执行结果
    
    安全说明：
        代码在 E2B 云端沙盒中执行，与主机系统完全隔离，
        无法访问本地文件、网络或执行系统命令。
    """
    # 检查 E2B API Key 是否配置
    e2b_api_key = os.getenv('E2B_API_KEY')
    if not e2b_api_key:
        return "❌ E2B 沙盒不可用：未配置 E2B_API_KEY 环境变量"
    
    try:
        # 创建 E2B 沙盒（使用新版 API: Sandbox.create()）
        sbx = Sandbox.create()
        
        # 在沙盒中执行代码
        execution = sbx.run_code(py_code)
        
        # 获取执行结果
        result_parts = []
        
        # 标准输出（stdout 是列表，需要合并）
        if execution.logs.stdout:
            if isinstance(execution.logs.stdout, list):
                result_parts.extend(execution.logs.stdout)
            else:
                result_parts.append(str(execution.logs.stdout))
        
        # 标准错误（stderr 也是列表）
        if execution.logs.stderr:
            if isinstance(execution.logs.stderr, list):
                for err in execution.logs.stderr:
                    result_parts.append(f"[stderr] {err}")
            else:
                result_parts.append(f"[stderr] {execution.logs.stderr}")
        
        # 执行结果（如表达式的返回值）
        if execution.results:
            for r in execution.results:
                if hasattr(r, 'text') and r.text:
                    result_parts.append(r.text)
        
        # 错误信息
        if execution.error:
            sbx.kill()
            return f"❌ 执行失败：{execution.error.name}: {execution.error.value}"
        
        # 关闭沙盒
        sbx.kill()
        
        if result_parts:
            return "\n".join(result_parts)
        else:
            return "✅ 代码执行成功（无输出）"
            
    except Exception as e:
        return f"❌ 沙盒执行失败：{type(e).__name__}: {e}"


# === 原本地执行代码（已弃用，存在安全风险）===
# @tool(args_schema=PythonCodeInput)
# def python_inter_unsafe(py_code: str) -> str:
#     g = globals()
#     try:
#         return str(eval(py_code, g))
#     except:
#         global_vars_before = set(g.keys())
#         try:            
#             exec(py_code, g)
#         except Exception as e:
#             return f"代码执行时报错: {e}"
#         global_vars_after = set(g.keys())
#         new_vars = global_vars_after - global_vars_before
#         if new_vars:
#             result = {var: g[var] for var in new_vars}
#             return str(result)
#         else:
#             return "已经顺利执行代码"


# ============================================================================
# 第五部分：绘图工具 (fig_inter)
# ============================================================================
# 功能：在 E2B 云端沙盒中执行 Python 绘图代码，生成图片并保存到本地
# 实现：
#   1. 创建 E2B 沙盒
#   2. 在沙盒中执行绘图代码
#   3. 将图片保存到沙盒临时文件
#   4. 从沙盒下载图片到本地
#   5. 返回图片相对路径（供前端显示）
# 适用场景：数据可视化、图表生成
# 安全性：代码在隔离的云端沙盒中执行，无法访问主机系统
# ============================================================================

class FigCodeInput(BaseModel):
    py_code: str = Field(
        description="要执行的 Python 绘图代码，必须使用 matplotlib/seaborn 创建图像并赋值给变量"
    )
    fname: str = Field(
        description="图像对象的变量名，例如 'fig'，用于从代码中提取并保存为图片"
    )


@tool(args_schema=FigCodeInput)
def fig_inter(py_code: str, fname: str) -> str:
    """
    在 E2B 云端沙盒中执行绘图代码并保存图片
    
    :param py_code: Python 绘图代码
    :param fname: 图像变量名（如 'fig'）
    :return: 图片保存路径
    
    使用示例：
        fig = plt.figure(figsize=(10,6))
        plt.plot([1,2,3], [4,5,6])
        fig.tight_layout()
    
    注意事项：
        1. 必须创建 fig 对象并赋值
        2. 不要调用 plt.show()
        3. 建议调用 fig.tight_layout() 优化布局
        4. 文本标签建议使用英文（避免中文乱码）
    
    安全说明：
        代码在 E2B 云端沙盒中执行，与主机系统完全隔离。
    """
    import time
    import base64
    
    # 检查 E2B API Key 是否配置
    e2b_api_key = os.getenv('E2B_API_KEY')
    if not e2b_api_key:
        return "❌ E2B 沙盒不可用：未配置 E2B_API_KEY 环境变量"
    
    # 图片保存路径配置（从 .env 读取）
    images_dir = os.getenv('IMAGES_DIR')
    if not images_dir:
        images_dir = os.path.join(os.path.dirname(__file__), 'images')
    
    os.makedirs(images_dir, exist_ok=True)
    
    # 生成唯一文件名（避免浏览器缓存）
    timestamp = int(time.time())
    image_filename = f"{fname}_{timestamp}.png"
    sandbox_path = f"/tmp/{image_filename}"
    local_path = os.path.join(images_dir, image_filename)
    rel_path = os.path.join("images", image_filename)
    
    # 构建完整的绘图代码（在沙盒中执行）
    full_code = f"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# 用户绘图代码
{py_code}

# 保存图片到沙盒临时文件
{fname}.savefig('{sandbox_path}', bbox_inches='tight', dpi=150)
plt.close('all')
print('图片已保存到沙盒')
"""
    
    try:
        # 创建 E2B 沙盒（使用新版 API: Sandbox.create()）
        sbx = Sandbox.create()
        
        # 执行绘图代码
        execution = sbx.run_code(full_code)
        
        # 检查执行错误
        if execution.error:
            sbx.kill()
            return f"❌ 绘图失败：{execution.error.name}: {execution.error.value}"
        
        # 从沙盒下载图片
        try:
            # 使用 files.read() 读取二进制文件，指定 format='bytes'
            file_content = sbx.files.read(sandbox_path, format='bytes')
            
            # 打印调试信息
            print(f"[fig_inter] 文件内容类型: {type(file_content)}")
            print(f"[fig_inter] 文件内容长度: {len(file_content) if file_content else 0}")
            
            if not file_content:
                sbx.kill()
                return f"❌ 图片下载失败：沙盒返回空内容，沙盒路径: {sandbox_path}"
            
            # 保存到服务器本地
            with open(local_path, 'wb') as f:
                f.write(file_content)
            
            sbx.kill()
            
            # 验证文件是否保存成功
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                print(f"[fig_inter] 图片保存成功: {local_path}, 大小: {file_size} 字节")
                # 返回格式：明确告诉 Agent 图片路径，让它传递给用户
                image_url = f"/images/{image_filename}"
                return f"""✅ 图片已成功生成！

**重要：请在回复中包含以下图片链接，让用户可以看到图表：**

![{fname}]({image_url})

图片访问路径: {image_url}
文件大小: {file_size} 字节

请务必在你的回复中包含上面的 Markdown 图片语法，这样用户才能看到图表。"""
            else:
                return f"❌ 图片保存失败：文件未创建，目标路径: {local_path}"
            
        except Exception as e:
            sbx.kill()
            import traceback
            error_detail = traceback.format_exc()
            print(f"[fig_inter] 下载失败详情:\n{error_detail}")
            return f"❌ 图片下载失败：{type(e).__name__}: {e}\n沙盒路径: {sandbox_path}\n本地路径: {local_path}"
            
    except Exception as e:
        return f"❌ 沙盒执行失败：{type(e).__name__}: {e}"


# ============================================================================
# 第七部分：数据共享工具（SQL 查询 + 沙盒分析）
# ============================================================================
# 功能：解决主进程与 E2B 沙盒之间数据无法共享的问题
# 原理：
#   1. 在主进程中执行 SQL 查询
#   2. 将结果序列化为 JSON
#   3. 将 JSON 数据嵌入到 Python 代码中
#   4. 在 E2B 沙盒中反序列化并执行分析
# ============================================================================

class AnalyzeDataInput(BaseModel):
    sql_query: str = Field(
        description="SQL 查询语句，用于从数据库提取数据。必须是 SELECT 语句。示例：SELECT * FROM business_data.news LIMIT 100"
    )
    analysis_code: str = Field(
        description="Python 分析代码。数据已预加载到变量 `df`（pandas DataFrame），直接使用即可。示例：print(df.describe())"
    )


@tool(args_schema=AnalyzeDataInput)
def analyze_data(sql_query: str, analysis_code: str) -> str:
    """
    从数据库查询数据并在 E2B 沙盒中进行 Python 分析
    
    工作流程：
    1. 在主进程中执行 SQL 查询，获取数据
    2. 将数据序列化为 JSON 并嵌入 Python 代码
    3. 在 E2B 沙盒中执行分析代码
    
    :param sql_query: SQL 查询语句（仅支持 SELECT）
    :param analysis_code: Python 分析代码，数据已在变量 `df` 中
    :return: 分析结果
    
    使用示例：
        sql_query: "SELECT * FROM business_data.news WHERE keyword='证监会'"
        analysis_code: '''
            print(f"数据量: {len(df)}")
            print(df['source'].value_counts())
            print(df.describe())
        '''
    """
    # ============================================================
    # 第一步：验证 SQL 安全性
    # ============================================================
    is_valid, message = validate_sql(sql_query)
    if not is_valid:
        return f"❌ SQL 查询被拒绝：{message}"
    
    # ============================================================
    # 第二步：检查 E2B API Key
    # ============================================================
    e2b_api_key = os.getenv('E2B_API_KEY')
    if not e2b_api_key:
        return "❌ E2B 沙盒不可用：未配置 E2B_API_KEY 环境变量"
    
    # ============================================================
    # 第三步：在主进程中查询数据库
    # ============================================================
    from config import get_db_connection_string
    
    try:
        connection = psycopg.connect(get_db_connection_string())
        df = pd.read_sql(sql_query, connection)
        connection.close()
        
        row_count = len(df)
        if row_count == 0:
            return "⚠️ SQL 查询返回空结果，没有数据可供分析"
        
        # 限制数据量（避免 JSON 过大）
        MAX_ROWS = 10000
        if row_count > MAX_ROWS:
            df = df.head(MAX_ROWS)
            warning = f"⚠️ 数据量较大（{row_count} 行），已截取前 {MAX_ROWS} 行进行分析\n\n"
        else:
            warning = ""
            
        print(f"[analyze_data] 查询成功，共 {row_count} 行数据")
        
    except Exception as e:
        return f"❌ 数据库查询失败：{e}"
    
    # ============================================================
    # 第四步：序列化数据为 JSON
    # ============================================================
    try:
        # 处理特殊类型（datetime 等）
        data_json = df.to_json(orient='records', force_ascii=False, date_format='iso')
    except Exception as e:
        return f"❌ 数据序列化失败：{e}"
    
    # ============================================================
    # 第五步：构建沙盒代码
    # ============================================================
    sandbox_code = f'''
import pandas as pd
import numpy as np
import json
from datetime import datetime

# ========== 从 JSON 恢复 DataFrame ==========
_data_json = """{data_json}"""
df = pd.DataFrame(json.loads(_data_json))

# 打印数据概览
print(f"📊 数据已加载: {{len(df)}} 行 x {{len(df.columns)}} 列")
print(f"📋 列名: {{list(df.columns)}}")
print("-" * 50)

# ========== 用户分析代码 ==========
{analysis_code}
'''
    
    # ============================================================
    # 第六步：在 E2B 沙盒中执行
    # ============================================================
    try:
        sbx = Sandbox.create()
        execution = sbx.run_code(sandbox_code)
        
        result_parts = []
        
        # 收集输出
        if execution.logs.stdout:
            if isinstance(execution.logs.stdout, list):
                result_parts.extend(execution.logs.stdout)
            else:
                result_parts.append(str(execution.logs.stdout))
        
        if execution.logs.stderr:
            if isinstance(execution.logs.stderr, list):
                for err in execution.logs.stderr:
                    result_parts.append(f"[stderr] {err}")
            else:
                result_parts.append(f"[stderr] {execution.logs.stderr}")
        
        if execution.results:
            for r in execution.results:
                if hasattr(r, 'text') and r.text:
                    result_parts.append(r.text)
        
        if execution.error:
            sbx.kill()
            return f"❌ 分析代码执行失败：{execution.error.name}: {execution.error.value}"
        
        sbx.kill()
        
        if result_parts:
            return warning + "\n".join(result_parts)
        else:
            return warning + "✅ 分析代码执行成功（无输出）"
            
    except Exception as e:
        return f"❌ 沙盒执行失败：{type(e).__name__}: {e}"


class PlotDataInput(BaseModel):
    sql_query: str = Field(
        description="SQL 查询语句，用于从数据库提取绘图数据。必须是 SELECT 语句。"
    )
    plot_code: str = Field(
        description="Python 绘图代码。数据已预加载到变量 `df`，必须创建 `fig` 对象。不要调用 plt.show()。"
    )
    fname: str = Field(
        default="fig",
        description="图像对象的变量名，默认为 'fig'"
    )


@tool(args_schema=PlotDataInput)
def plot_data(sql_query: str, plot_code: str, fname: str = "fig") -> str:
    """
    从数据库查询数据并在 E2B 沙盒中绑图
    
    工作流程：
    1. 在主进程中执行 SQL 查询，获取数据
    2. 将数据序列化为 JSON 并嵌入 Python 代码
    3. 在 E2B 沙盒中执行绘图代码
    4. 下载图片到本地
    
    :param sql_query: SQL 查询语句（仅支持 SELECT）
    :param plot_code: Python 绘图代码，数据已在变量 `df` 中，必须创建 `fig` 对象
    :param fname: 图像变量名，默认 'fig'
    :return: 图片路径或错误信息
    
    使用示例：
        sql_query: "SELECT keyword, COUNT(*) as cnt FROM business_data.news GROUP BY keyword"
        plot_code: '''
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(df['keyword'], df['cnt'], color='steelblue')
            ax.set_xlabel('Keyword')
            ax.set_ylabel('Count')
            ax.set_title('News Distribution by Keyword')
            ax.tick_params(axis='x', rotation=45)
            fig.tight_layout()
        '''
    """
    import time
    
    # ============================================================
    # 第一步：验证 SQL 安全性
    # ============================================================
    is_valid, message = validate_sql(sql_query)
    if not is_valid:
        return f"❌ SQL 查询被拒绝：{message}"
    
    # ============================================================
    # 第二步：检查 E2B API Key
    # ============================================================
    e2b_api_key = os.getenv('E2B_API_KEY')
    if not e2b_api_key:
        return "❌ E2B 沙盒不可用：未配置 E2B_API_KEY 环境变量"
    
    # ============================================================
    # 第三步：在主进程中查询数据库
    # ============================================================
    from config import get_db_connection_string
    
    try:
        connection = psycopg.connect(get_db_connection_string())
        df = pd.read_sql(sql_query, connection)
        connection.close()
        
        row_count = len(df)
        if row_count == 0:
            return "⚠️ SQL 查询返回空结果，没有数据可供绑图"
        
        # 限制数据量
        MAX_ROWS = 10000
        if row_count > MAX_ROWS:
            df = df.head(MAX_ROWS)
            print(f"[plot_data] 数据量较大，已截取前 {MAX_ROWS} 行")
            
        print(f"[plot_data] 查询成功，共 {row_count} 行数据")
        
    except Exception as e:
        return f"❌ 数据库查询失败：{e}"
    
    # ============================================================
    # 第四步：序列化数据为 JSON
    # ============================================================
    try:
        data_json = df.to_json(orient='records', force_ascii=False, date_format='iso')
    except Exception as e:
        return f"❌ 数据序列化失败：{e}"
    
    # ============================================================
    # 第五步：配置图片路径
    # ============================================================
    images_dir = os.getenv('IMAGES_DIR')
    if not images_dir:
        images_dir = os.path.join(os.path.dirname(__file__), 'images')
    os.makedirs(images_dir, exist_ok=True)
    
    timestamp = int(time.time())
    image_filename = f"{fname}_{timestamp}.png"
    sandbox_path = f"/tmp/{image_filename}"
    local_path = os.path.join(images_dir, image_filename)
    
    # ============================================================
    # 第六步：构建沙盒绑图代码
    # ============================================================
    sandbox_code = f'''
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import json
from datetime import datetime

# ========== 从 JSON 恢复 DataFrame ==========
_data_json = """{data_json}"""
df = pd.DataFrame(json.loads(_data_json))

print(f"📊 数据已加载: {{len(df)}} 行 x {{len(df.columns)}} 列")

# ========== 用户绑图代码 ==========
{plot_code}

# ========== 保存图片 ==========
{fname}.savefig('{sandbox_path}', bbox_inches='tight', dpi=150)
plt.close('all')
print('✅ 图片已生成')
'''
    
    # ============================================================
    # 第七步：在 E2B 沙盒中执行
    # ============================================================
    try:
        sbx = Sandbox.create()
        execution = sbx.run_code(sandbox_code)
        
        if execution.error:
            sbx.kill()
            return f"❌ 绑图失败：{execution.error.name}: {execution.error.value}"
        
        # 下载图片
        try:
            file_content = sbx.files.read(sandbox_path, format='bytes')
            
            if not file_content:
                sbx.kill()
                return f"❌ 图片下载失败：沙盒返回空内容"
            
            with open(local_path, 'wb') as f:
                f.write(file_content)
            
            sbx.kill()
            
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                image_url = f"/images/{image_filename}"
                return f"""✅ 图片已成功生成！

**重要：请在回复中包含以下图片链接，让用户可以看到图表：**

![{fname}]({image_url})

图片访问路径: {image_url}
文件大小: {file_size} 字节

请务必在你的回复中包含上面的 Markdown 图片语法，这样用户才能看到图表。"""
            else:
                return f"❌ 图片保存失败"
                
        except Exception as e:
            sbx.kill()
            return f"❌ 图片下载失败：{type(e).__name__}: {e}"
            
    except Exception as e:
        return f"❌ 沙盒执行失败：{type(e).__name__}: {e}"


# === 原本地执行代码（已弃用，存在安全风险）===
# @tool(args_schema=FigCodeInput)
# def fig_inter_unsafe(py_code: str, fname: str) -> str:
#     current_backend = matplotlib.get_backend()
#     matplotlib.use('Agg')
#     local_vars = {"plt": plt, "pd": pd, "sns": sns}
#     images_dir = os.getenv('IMAGES_DIR')
#     if not images_dir:
#         images_dir = os.path.join(os.path.dirname(__file__), 'images')
#     os.makedirs(images_dir, exist_ok=True)
#     try:
#         g = globals()
#         exec(py_code, g, local_vars)
#         g.update(local_vars)
#         fig = local_vars.get(fname, None)
#         if fig:
#             import time
#             timestamp = int(time.time())
#             image_filename = f"{fname}_{timestamp}.png"
#             abs_path = os.path.join(images_dir, image_filename)
#             rel_path = os.path.join("images", image_filename)
#             fig.savefig(abs_path, bbox_inches='tight')
#             return f"✅ 图片已保存，路径为: {rel_path}"
#         else:
#             return "⚠️ 图像对象未找到"
#     except Exception as e:
#         return f"❌ 执行失败：{e}"
#     finally:
#         plt.close('all')
#         matplotlib.use(current_backend)


# ============================================================================
# 第六部分：Agent 配置与创建
# ============================================================================
# 功能：组装所有工具，创建 LangGraph Agent
# 实现：
#   1. 定义系统提示词（指导 LLM 如何使用工具）
#   2. 注册所有工具
#   3. 创建 DeepSeek 模型实例
#   4. 使用 create_agent 创建 Agent
# ============================================================================

# 系统提示词：指导 LLM 如何使用各个工具
prompt = """
你是一名经验丰富的智能数据分析助手，擅长帮助用户高效完成以下任务：

1. **数据库查询（仅查看数据）：**
   - 当用户只需要查看数据库中的数据时，使用 `sql_inter` 工具。
   - **重要**：所有业务数据表都在 `business_data` schema 中，查询时必须使用完整表名。
   - 示例：`SELECT * FROM business_data.news LIMIT 10`

2. **数据分析（查询 + 统计）：** ⭐ 推荐
   - 当用户需要对数据库数据进行 Python 分析时，使用 `analyze_data` 工具。
   - 该工具会先执行 SQL 查询，然后将数据传递到 E2B 沙盒中进行分析。
   - **数据已预加载到变量 `df`（pandas DataFrame）**，直接在 analysis_code 中使用。
   - 示例：
     ```
     sql_query: "SELECT * FROM business_data.news WHERE keyword='证监会'"
     analysis_code: '''
         print(f"数据量: {len(df)}")
         print(df['source'].value_counts())
         print(df.describe())
     '''
     ```

3. **数据可视化（查询 + 绑图）：** ⭐ 推荐
   - 当用户需要根据数据库数据生成图表时，使用 `plot_data` 工具。
   - 该工具会先执行 SQL 查询，然后将数据传递到 E2B 沙盒中绑图。
   - **数据已预加载到变量 `df`**，必须创建 `fig` 对象，不要调用 `plt.show()`。
   - 示例：
     ```
     sql_query: "SELECT keyword, COUNT(*) as cnt FROM business_data.news GROUP BY keyword"
     plot_code: '''
         fig, ax = plt.subplots(figsize=(12, 6))
         ax.bar(df['keyword'], df['cnt'], color='steelblue')
         ax.set_title('News by Keyword')
         fig.tight_layout()
     '''
     ```
   - **重要**：工具返回的图片 Markdown 链接必须原样包含在你的回复中。

4. **纯 Python 执行（无数据库）：**
   - 当用户需要执行与数据库无关的 Python 代码时，使用 `python_inter` 工具。
   - 此工具在隔离沙盒中运行，无法访问数据库。

5. **纯绑图（无数据库）：**
   - 当用户提供了数据（非数据库数据）需要绑图时，使用 `fig_inter` 工具。

6. **网络搜索：**
   - 当用户提出与数据分析无关的问题，使用 `search_tool` 工具。

**⭐ 工具选择指南：**
| 场景 | 推荐工具 |
|------|---------|
| 查看数据库表内容 | `sql_inter` |
| 数据库数据 + 统计分析 | `analyze_data` ⭐ |
| 数据库数据 + 图表可视化 | `plot_data` ⭐ |
| 无数据库的 Python 计算 | `python_inter` |
| 无数据库的绑图 | `fig_inter` |
| 搜索网络信息 | `search_tool` |

**回答要求：**
- 所有回答均使用**简体中文**，清晰、礼貌、简洁。
- 如果调用工具返回结构化 JSON 数据，你应提取关键信息简要说明。
- **如果工具返回了图片 Markdown 链接，你必须原样复制到回复中。**

**风格：**
- 专业、简洁、以数据驱动。
- 不要编造不存在的工具或数据。

**⚠️ 安全限制（必须严格遵守）：**

1. **禁止系统操作：**
   - 禁止使用 `os.system()`、`subprocess`、`popen`、`spawn` 等执行系统命令
   - 禁止使用 `pip install`、`conda install` 等安装任何库
   - 禁止使用 `open()` 写入或删除文件（读取数据文件除外）
   - 禁止访问 `.env`、密码、密钥等敏感文件

2. **禁止网络操作：**
   - 禁止使用 `requests`、`urllib`、`socket` 等进行网络请求（数据库连接除外）
   - 禁止数据外传或连接外部服务器

3. **禁止危险代码：**
   - 禁止使用 `eval()`、`exec()`、`compile()` 执行动态代码
   - 禁止使用 `__import__`、`getattr`、`setattr` 等反射操作
   - 禁止访问 `__builtins__`、`__globals__`、`__code__` 等内部属性

4. **资源限制：**
   - 禁止执行超过 60 秒的长时间计算
   - 禁止使用 `GridSearchCV`、`RandomizedSearchCV` 等大规模超参数搜索
   - 禁止创建超大数组或无限循环

5. **SQL 限制：**
   - 仅允许 SELECT 查询
   - 禁止 DROP、DELETE、TRUNCATE、ALTER、INSERT、UPDATE 等修改操作
   - 禁止查询系统表（如 pg_shadow、pg_roles）

请根据以上原则为用户提供精准、高效的协助。
"""

# 注册所有工具
tools = [
    search_tool,    # 网络搜索（Tavily）
    sql_inter,      # SQL 查询（仅查看数据）
    analyze_data,   # SQL + Python 分析（推荐）⭐
    plot_data,      # SQL + 绘图（推荐）⭐
    python_inter,   # Python 执行（无数据库访问）
    fig_inter,      # 绑图（无数据库访问）
    # extract_data, # 已废弃：沙盒间变量无法共享
]

# 添加浏览器工具（browser-use AI 驱动，通用）
if BROWSER_TOOLS_AVAILABLE:
    tools.append(browser_task)  # 唯一的浏览器工具，用自然语言描述任务
    print("[信息] browser-use 浏览器工具已加载")

# 创建 LLM 模型（使用 DeepSeek）
model = ChatDeepSeek(model="deepseek-chat")

# 创建记忆存储（会话内记忆）
# MemorySaver 是内存存储，重启服务后记忆丢失
# 后续可升级为 PostgresSaver 实现持久化
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()

# 创建 Agent（带记忆和递归限制）
agent = create_agent(
    model=model, 
    tools=tools, 
    system_prompt=prompt, 
    checkpointer=memory
)

# 设置默认配置（包括递归限制）
DEFAULT_CONFIG = {
    "recursion_limit": 50,  # 增加递归限制到 50（默认 25）
    "configurable": {
        "thread_id": "default"
    }
}
