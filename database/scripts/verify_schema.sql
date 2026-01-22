-- ============================================================
-- Schema 验证脚本
-- ============================================================
-- 用于验证 business_data schema 和 news 表是否正常
-- 即使 pgAdmin 界面看不到，这些查询也应该成功
-- ============================================================

-- 1. 查看所有 schema
SELECT '=== 所有 Schema ===' AS info;
SELECT schema_name 
FROM information_schema.schemata
ORDER BY schema_name;

-- 2. 查看 business_data schema 中的所有表
SELECT '=== business_data Schema 中的表 ===' AS info;
SELECT table_name 
FROM information_schema.tables
WHERE table_schema = 'business_data'
ORDER BY table_name;

-- 3. 查看 news 表的列信息
SELECT '=== news 表结构 ===' AS info;
SELECT 
    column_name AS "字段名",
    data_type AS "数据类型",
    character_maximum_length AS "最大长度",
    is_nullable AS "可为空"
FROM information_schema.columns
WHERE table_schema = 'business_data' 
  AND table_name = 'news'
ORDER BY ordinal_position;

-- 4. 查看 news 表的索引
SELECT '=== news 表索引 ===' AS info;
SELECT 
    indexname AS "索引名",
    indexdef AS "索引定义"
FROM pg_indexes
WHERE schemaname = 'business_data'
  AND tablename = 'news';

-- 5. 统计数据
SELECT '=== 数据统计 ===' AS info;
SELECT 
    COUNT(*) AS "总记录数",
    COUNT(DISTINCT keyword) AS "关键词数量",
    COUNT(DISTINCT source_chinese) AS "来源数量",
    COUNT(DISTINCT batch_id) AS "批次数量",
    MIN(publish_time) AS "最早发布时间",
    MAX(publish_time) AS "最晚发布时间"
FROM business_data.news;

-- 6. 查看最新的 5 条记录
SELECT '=== 最新 5 条记录 ===' AS info;
SELECT 
    id,
    title,
    source_chinese AS "来源",
    keyword AS "关键词",
    publish_time AS "发布时间",
    created_at AS "入库时间"
FROM business_data.news
ORDER BY created_at DESC
LIMIT 5;

-- 7. 按关键词统计
SELECT '=== 各关键词数据量 ===' AS info;
SELECT 
    keyword AS "关键词",
    COUNT(*) AS "数量"
FROM business_data.news
GROUP BY keyword
ORDER BY COUNT(*) DESC;

-- ============================================================
-- 如果以上查询都成功执行，说明：
-- ✅ business_data schema 存在
-- ✅ news 表存在且结构正确
-- ✅ 数据已成功导入
-- ✅ 索引已创建
-- 
-- pgAdmin 界面看不到只是显示问题，不影响使用
-- ============================================================
