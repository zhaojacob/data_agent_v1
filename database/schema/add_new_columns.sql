-- ============================================================
-- 为 news 表添加新字段
-- ============================================================
-- 用途：补充 JSON 中的额外字段
-- 使用：在 pgAdmin 中执行
-- ============================================================

-- 1. 添加新字段
ALTER TABLE business_data.news 
ADD COLUMN IF NOT EXISTS search_title TEXT,
ADD COLUMN IF NOT EXISTS search_summary TEXT,
ADD COLUMN IF NOT EXISTS search_pub_time VARCHAR(50),
ADD COLUMN IF NOT EXISTS author VARCHAR(100),
ADD COLUMN IF NOT EXISTS content_length INTEGER,
ADD COLUMN IF NOT EXISTS source_chinese VARCHAR(100),
ADD COLUMN IF NOT EXISTS date_only DATE,
ADD COLUMN IF NOT EXISTS datetime_str VARCHAR(50),
ADD COLUMN IF NOT EXISTS timestamp_unix BIGINT;

-- 2. 添加字段注释
COMMENT ON COLUMN business_data.news.search_title IS '搜索时显示的标题';
COMMENT ON COLUMN business_data.news.search_summary IS '搜索摘要';
COMMENT ON COLUMN business_data.news.search_pub_time IS '搜索时显示的发布时间（原始格式）';
COMMENT ON COLUMN business_data.news.author IS '作者';
COMMENT ON COLUMN business_data.news.content_length IS '内容长度（字符数）';
COMMENT ON COLUMN business_data.news.source_chinese IS '中文来源名称';
COMMENT ON COLUMN business_data.news.date_only IS '发布日期（仅年月日）';
COMMENT ON COLUMN business_data.news.datetime_str IS '日期时间字符串（原始格式）';
COMMENT ON COLUMN business_data.news.timestamp_unix IS 'Unix时间戳';

-- 3. 创建索引（可选，如果需要按作者查询）
CREATE INDEX IF NOT EXISTS idx_news_author ON business_data.news(author);

-- 4. 验证新字段
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    column_default
FROM information_schema.columns
WHERE table_schema = 'business_data' 
  AND table_name = 'news'
  AND column_name IN ('search_title', 'search_summary', 'search_pub_time', 
                      'author', 'content_length', 'source_chinese',
                      'date_only', 'datetime_str', 'timestamp_unix')
ORDER BY ordinal_position;
