@echo off
REM ============================================================
REM Schema 验证脚本 (Windows)
REM ============================================================
REM 用于验证 business_data schema 和 news 表是否正常
REM ============================================================

echo ============================================================
echo Schema 验证工具
echo ============================================================
echo.

REM 设置数据库连接参数
set PGHOST=localhost
set PGPORT=5432
set PGUSER=postgres
set PGDATABASE=data_agent

echo 正在连接数据库...
echo 主机: %PGHOST%
echo 端口: %PGPORT%
echo 用户: %PGUSER%
echo 数据库: %PGDATABASE%
echo.

REM 执行验证脚本
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -f verify_schema.sql

echo.
echo ============================================================
echo 验证完成！
echo ============================================================
echo.
echo 如果看到数据统计和表结构，说明一切正常。
echo pgAdmin 看不到只是界面显示问题，不影响使用。
echo.
echo 解决方法：
echo 1. 在 pgAdmin 中右键点击 Schemas → Refresh
echo 2. 或断开重连 data_agent 数据库
echo 3. 或重启 pgAdmin
echo.
echo 详细说明请查看：PGADMIN_REFRESH_GUIDE.md
echo ============================================================

pause
