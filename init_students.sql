-- ============================================================
-- init_students.sql
-- 学生成绩表初始化脚本
-- 
-- 使用方法：
--   方式1: pgAdmin 中打开并执行
--   方式2: psql -U financial-news-brief -d data_agent -f init_students.sql
-- ============================================================

-- 如果表已存在则删除
DROP TABLE IF EXISTS students_scores;

-- 创建学生成绩表
-- SERIAL: PostgreSQL 的自增类型（相当于 MySQL 的 AUTO_INCREMENT）
CREATE TABLE students_scores (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    course1 INT CHECK (course1 >= 0 AND course1 <= 100),
    course2 INT CHECK (course2 >= 0 AND course2 <= 100),
    course3 INT CHECK (course3 >= 0 AND course3 <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 添加表注释
COMMENT ON TABLE students_scores IS '学生成绩表';
COMMENT ON COLUMN students_scores.id IS '学生ID（自增）';
COMMENT ON COLUMN students_scores.name IS '学生姓名';
COMMENT ON COLUMN students_scores.course1 IS '课程1成绩';
COMMENT ON COLUMN students_scores.course2 IS '课程2成绩';
COMMENT ON COLUMN students_scores.course3 IS '课程3成绩';
COMMENT ON COLUMN students_scores.created_at IS '创建时间';

-- 插入 10 位学生的成绩数据
INSERT INTO students_scores (name, course1, course2, course3)
VALUES
    ('学生1', 85, 92, 78),
    ('学生2', 76, 88, 91),
    ('学生3', 90, 85, 80),
    ('学生4', 65, 70, 72),
    ('学生5', 82, 89, 95),
    ('学生6', 91, 93, 87),
    ('学生7', 77, 78, 85),
    ('学生8', 88, 92, 91),
    ('学生9', 84, 76, 80),
    ('学生10', 89, 90, 92);

-- 验证：查看所有数据
SELECT * FROM students_scores ORDER BY id;

-- 验证：查看表结构
\d students_scores
