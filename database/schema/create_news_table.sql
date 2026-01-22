-- ============================================================
-- 新闻数据表设计
-- ============================================================
-- 用于存储 financial-news-brief 爬取的金融新闻数据
-- 与 business_data.students_scores 保持设计风格一致
-- ============================================================

-- 创建 schema（如果不存在）
CREATE SCHEMA IF NOT EXISTS business_data;

-- 清理旧版本（如果在 public schema 中存在）
DROP TRIGGER IF EXISTS update_news_updated_at ON public.news;
DROP TABLE IF EXISTS public.news CASCADE;

-- 如果表已存在则删除（可选，首次创建时使用）
-- DROP TABLE IF EXISTS business_data.news CASCADE;

-- 创建新闻表
CREATE TABLE IF NOT EXISTS business_data.news (
    -- 主键
    id SERIAL PRIMARY KEY,
    
    -- 基本信息
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    source VARCHAR(100),
    source_chinese VARCHAR(100),  -- 中文来源名称
    
    -- 搜索相关
    search_title TEXT,            -- 搜索时的标题
    search_summary TEXT,          -- 搜索摘要
    search_pub_time VARCHAR(50),  -- 搜索时显示的发布时间（原始格式）
    
    -- 内容
    content TEXT,
    content_length INTEGER,       -- 内容长度
    author VARCHAR(100),          -- 作者
    
    -- 时间信息（多种格式）
    publish_time TIMESTAMPTZ,     -- 发布时间（标准格式）
    date_only DATE,               -- 仅日期
    datetime_str VARCHAR(50),     -- 日期时间字符串（原始格式）
    timestamp_unix BIGINT,        -- Unix 时间戳
    fetch_time TIMESTAMPTZ DEFAULT NOW(),  -- 爬取时间
    
    -- 分类信息
    keyword VARCHAR(100),  -- 搜索关键词
    batch_id VARCHAR(50),  -- 批次ID（如 batch_20260120_090818）
    
    -- 元数据
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建索引（提高查询性能）
CREATE INDEX IF NOT EXISTS idx_news_keyword ON business_data.news(keyword);
CREATE INDEX IF NOT EXISTS idx_news_source ON business_data.news(source);
CREATE INDEX IF NOT EXISTS idx_news_publish_time ON business_data.news(publish_time DESC);
CREATE INDEX IF NOT EXISTS idx_news_batch_id ON business_data.news(batch_id);
CREATE INDEX IF NOT EXISTS idx_news_author ON business_data.news(author);

-- 创建更新时间触发器（自动更新 updated_at）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 删除旧触发器（如果存在）
DROP TRIGGER IF EXISTS update_news_updated_at ON business_data.news;

-- 创建新触发器
CREATE TRIGGER update_news_updated_at 
    BEFORE UPDATE ON business_data.news 
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 添加表注释
COMMENT ON TABLE business_data.news IS '金融新闻数据表';

-- 添加列注释
COMMENT ON COLUMN business_data.news.id IS '新闻ID（自增主键）';
COMMENT ON COLUMN business_data.news.title IS '新闻标题';
COMMENT ON COLUMN business_data.news.url IS '新闻链接（唯一）';
COMMENT ON COLUMN business_data.news.source IS '新闻来源代码（如：cnfin）';
COMMENT ON COLUMN business_data.news.source_chinese IS '新闻来源中文名（如：新华财经）';
COMMENT ON COLUMN business_data.news.search_title IS '搜索时显示的标题';
COMMENT ON COLUMN business_data.news.search_summary IS '搜索摘要';
COMMENT ON COLUMN business_data.news.search_pub_time IS '搜索时显示的发布时间（原始格式）';
COMMENT ON COLUMN business_data.news.content IS '新闻正文内容';
COMMENT ON COLUMN business_data.news.content_length IS '内容长度（字符数）';
COMMENT ON COLUMN business_data.news.author IS '作者';
COMMENT ON COLUMN business_data.news.publish_time IS '新闻发布时间（标准时间戳格式）';
COMMENT ON COLUMN business_data.news.date_only IS '发布日期（仅年月日）';
COMMENT ON COLUMN business_data.news.datetime_str IS '日期时间字符串（原始格式）';
COMMENT ON COLUMN business_data.news.timestamp_unix IS 'Unix时间戳';
COMMENT ON COLUMN business_data.news.fetch_time IS '爬取时间';
COMMENT ON COLUMN business_data.news.keyword IS '搜索关键词（如：证监会、ETF规模）';
COMMENT ON COLUMN business_data.news.batch_id IS '爬取批次ID';
COMMENT ON COLUMN business_data.news.created_at IS '数据库记录创建时间';
COMMENT ON COLUMN business_data.news.updated_at IS '数据库记录更新时间';

-- 验证：查看表结构
-- \d business_data.news

-- 创建全文搜索索引（如果需要）
-- CREATE INDEX idx_news_title_fts ON business_data.news USING gin(to_tsvector('chinese', title));
-- CREATE INDEX idx_news_content_fts ON business_data.news USING gin(to_tsvector('chinese', content));

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_news_updated_at BEFORE UPDATE
    ON business_data.news FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 添加注释
COMMENT ON TABLE business_data.news IS '金融新闻数据表';
COMMENT ON COLUMN business_data.news.keyword IS '搜索关键词（如：证监会、ETF规模）';
COMMENT ON COLUMN business_data.news.batch_id IS '爬取批次ID';
