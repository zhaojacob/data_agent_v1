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
    
    # 加载环境变量
    load_dotenv(override=True)
    
    # ----------------------------------------------------------------
    # 数据库配置说明：
    # os.getenv('变量名', '默认值') 的工作原理：
    # - 优先从 .env 文件读取变量值
    # - 如果 .env 中没有定义该变量，则使用第二个参数作为默认值
    # 
    # 示例：os.getenv('PG_USER', 'postgres')
    #   → 如果 .env 中有 PG_USER=financial-news-brief，返回 'financial-news-brief'
    #   → 如果 .env 中没有 PG_USER，返回默认值 'postgres'
    # ----------------------------------------------------------------
    host = os.getenv('PG_HOST', 'localhost')       # 数据库地址，默认本机
    user = os.getenv('PG_USER', 'postgres')        # 用户名，默认 postgres
    password = os.getenv('PG_PASSWORD')            # 密码（必须在 .env 中配置）
    dbname = os.getenv('PG_DBNAME', 'postgres')    # 数据库名，默认 postgres
    port = os.getenv('PG_PORT', '5432')            # 端口，默认 5432
    
    # ============================================================
    # 第二道防线：使用只读用户连接数据库
    # 即使代码验证被绕过，数据库层面也会拒绝写操作
    # ============================================================
    try:
        connection = psycopg.connect(
            host=host,
            user=user,
            password=password,
            dbname=dbname,
            port=int(port)
        )
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
    
    load_dotenv(override=True)
    
    # 从 .env 读取数据库配置（说明见 sql_inter 函数）
    host = os.getenv('PG_HOST', 'localhost')
    user = os.getenv('PG_USER', 'postgres')
    password = os.getenv('PG_PASSWORD')
    dbname = os.getenv('PG_DBNAME', 'postgres')
    port = os.getenv('PG_PORT', '5432')

    try:
        # 创建 PostgreSQL 数据库连接 (psycopg v3)
        connection = psycopg.connect(
            host=host,
            user=user,
            password=password,
            dbname=dbname,
            port=int(port)
        )
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

1. **数据库查询：**
   - 当用户需要获取数据库中某些数据或进行SQL查询时，请调用`sql_inter`工具。
   - 该工具已内置 PostgreSQL 连接参数，你只需生成 SQL 语句即可。
   - **重要**：所有业务数据表都在 `business_data` schema 中，查询时必须使用完整表名。
   - 示例：`SELECT * FROM business_data.students_scores` 或 `SELECT * FROM business_data.表名 WHERE 条件`。

2. **数据表提取：**
   - 当用户希望将数据库中的表格导入 Python 环境进行后续分析时，请调用`extract_data`工具。
   - 需要提供 SQL 查询语句和 DataFrame 变量名。
   - **重要**：表名必须带 schema 前缀，如 `SELECT * FROM business_data.students_scores`。

3. **非绘图类 Python 代码执行：**
   - 当用户需要执行 Python 脚本或进行数据处理、统计计算时，请调用`python_inter`工具。
   - 仅限执行非绘图类代码，例如变量定义、数据分析等。

4. **绘图类 Python 代码执行：**
   - 当用户需要进行可视化展示时，请调用`fig_inter`工具。
   - 必须创建 fig 对象（如 `fig = plt.figure()`）。
   - 不要调用 `plt.show()`，否则图像将无法保存。
   - **重要**：工具返回的图片 Markdown 链接（如 `![图表](/images/xxx.png)`）必须原样包含在你的回复中，不要省略或改写。

5. **网络搜索：**
   - 当用户提出与数据分析无关的问题（如最新新闻、实时信息），请调用`search_tool`工具。

**工具使用优先级：**
- 如需数据库数据，请先使用`sql_inter`或`extract_data`获取，再执行 Python 分析或绘图。
- 如需绘图，请先确保数据已加载为 pandas 对象。

**回答要求：**
- 所有回答均使用**简体中文**，清晰、礼貌、简洁。
- 如果调用工具返回结构化 JSON 数据，你应提取关键信息简要说明。
- 若需要用户提供更多信息，请主动提出明确的问题。
- **如果 fig_inter 工具返回了图片 Markdown 链接（如 `![图表](/images/xxx.png)`），你必须原样复制到回复中，不要改写或省略。**
- 图片链接格式示例：`![图表描述](/images/fig_1234567890.png)`

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
   - 禁止使用 `requests`、`urllib`、`socket` 等进行网络请求
   - 禁止数据外传或连接外部服务器

3. **禁止危险代码：**
   - 禁止使用 `eval()`、`exec()`、`compile()` 执行动态代码
   - 禁止使用 `__import__`、`getattr`、`setattr` 等反射操作
   - 禁止访问 `__builtins__`、`__globals__`、`__code__` 等内部属性

4. **资源限制：**
   - 禁止执行超过 60 秒的长时间计算
   - 禁止使用 `GridSearchCV`、`RandomizedSearchCV` 等大规模超参数搜索
   - 禁止创建超大数组或无限循环
   - 如需复杂模型训练，请使用简单参数，避免资源耗尽

5. **SQL 限制：**
   - 仅允许 SELECT 查询
   - 禁止 DROP、DELETE、TRUNCATE、ALTER、INSERT、UPDATE 等修改操作
   - 禁止查询系统表（如 pg_shadow、pg_roles）

6. **缺少库的处理：**
   - 如果代码需要未安装的库，请告知用户手动安装，不要尝试自动安装
   - 示例回复："此分析需要 xgboost 库，请运行 `pip install xgboost` 后重试"

请根据以上原则为用户提供精准、高效的协助。
"""

# 注册所有工具
tools = [
    search_tool,    # 网络搜索
    sql_inter,      # SQL 查询
    extract_data,   # 数据提取
    python_inter,   # Python 执行
    fig_inter,      # 绘图
]

# 创建 LLM 模型（使用 DeepSeek）
model = ChatDeepSeek(model="deepseek-chat")

# 创建 Agent
agent = create_agent(model=model, tools=tools, system_prompt=prompt)
