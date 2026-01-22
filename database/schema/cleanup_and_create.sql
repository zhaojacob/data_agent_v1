-- ============================================================
-- 清理并重新创建新闻表
-- ============================================================
-- 用途：清理所有旧版本，重新创建干净的 business_data.news 表
-- 使用：在 pgAdmin 中执行此文件
-- ============================================================

-- 1. 清理 public schema 中的旧版本（如果存在）
DROP TRIGGER IF EXISTS update_news_updated_at ON public.news;
DROP TABLE IF EXISTS public.news CASCADE;

-- 2. 清理 business_data schema 中的旧版本（如果存在）
DROP TRIGGER IF EXISTS update_news_updated_at ON business_data.news;
DROP TABLE IF EXISTS business_data.news CASCADE;

-- 3. 创建 schema（如果不存在）
CREATE SCHEMA IF NOT EXISTS business_data;

-- 4. 创建新闻表
CREATE TABLE business_data.news (
    -- 主键
    id SERIAL PRIMARY KEY,
    
    -- 基本信息
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    source VARCHAR(100),
    
    -- 内容
    content TEXT,
    
    -- 时间信息
    publish_time TIMESTAMPTZ,
    fetch_time TIMESTAMPTZ DEFAULT NOW(),
    
    -- 分类信息
    keyword VARCHAR(100),  -- 搜索关键词
    batch_id VARCHAR(50),  -- 批次ID（如 batch_20260120_090818）
    
    -- 元数据
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. 创建索引（提高查询性能）
CREATE INDEX idx_news_keyword ON business_data.news(keyword);
CREATE INDEX idx_news_source ON business_data.news(source);
CREATE INDEX idx_news_publish_time ON business_data.news(publish_time DESC);
CREATE INDEX idx_news_batch_id ON business_data.news(batch_id);

-- 6. 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 7. 创建触发器
CREATE TRIGGER update_news_updated_at 
    BEFORE UPDATE ON business_data.news 
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 8. 添加表注释
COMMENT ON TABLE business_data.news IS '金融新闻数据表';

-- 9. 添加列注释
COMMENT ON COLUMN business_data.news.id IS '新闻ID（自增主键）';
COMMENT ON COLUMN business_data.news.title IS '新闻标题';
COMMENT ON COLUMN business_data.news.url IS '新闻链接（唯一）';
COMMENT ON COLUMN business_data.news.source IS '新闻来源（如：财联社、新华网）';
COMMENT ON COLUMN business_data.news.content IS '新闻正文内容';
COMMENT ON COLUMN business_data.news.publish_time IS '新闻发布时间';
COMMENT ON COLUMN business_data.news.fetch_time IS '爬取时间';
COMMENT ON COLUMN business_data.news.keyword IS '搜索关键词（如：证监会、ETF规模）';
COMMENT ON COLUMN business_data.news.batch_id IS '爬取批次ID';
COMMENT ON COLUMN business_data.news.created_at IS '数据库记录创建时间';
COMMENT ON COLUMN business_data.news.updated_at IS '数据库记录更新时间';

-- 10. 验证创建结果
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE tablename = 'news';

-- 查看表结构（使用 SQL 查询代替 \d 命令）
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'business_data' 
  AND table_name = 'news'
ORDER BY ordinal_position;
