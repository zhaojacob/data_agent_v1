-- 创建user_schema_table

-- 1. 定义角色 (The Actor)
CREATE USER agent_reader WITH PASSWORD '272102abc';

-- 2. 定义结构 (The Structure)
CREATE SCHEMA IF NOT EXISTS business_data;     -- 存放业务数据
CREATE SCHEMA IF NOT EXISTS agent_memory;      -- 存放 Agent 记忆

-- 3. 定义规则 (The Rules)
-- 规则A: 业务数据允许只读访问
GRANT USAGE ON SCHEMA business_data TO agent_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA business_data TO agent_reader;                        --能看文件 (Select Tables)
ALTER DEFAULT PRIVILEGES IN SCHEMA business_data GRANT SELECT ON TABLES TO agent_reader;   --确保以后新进来的文件也能看

-- 规则B: 记忆数据完全保密 (无需操作)
-- 因为我们不给 agent_reader 任何关于 agent_memory 的权限
-- 只有管理员(postgres)能读写记忆，这正是我们想要的。





-- 1. 如果表已存在则删除 (注意加上 schema 前缀)
DROP TABLE IF EXISTS business_data.students_scores;

-- 2. 创建学生成绩表
CREATE TABLE business_data.students_scores (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    course1 INT CHECK (course1 >= 0 AND course1 <= 100),
    course2 INT CHECK (course2 >= 0 AND course2 <= 100),
    course3 INT CHECK (course3 >= 0 AND course3 <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 添加表注释
COMMENT ON TABLE business_data.students_scores IS '学生成绩表';

-- 4. 添加列注释 (注意这里是三段式: schema.table.column)
COMMENT ON COLUMN business_data.students_scores.id IS '学生ID（自增）';
COMMENT ON COLUMN business_data.students_scores.name IS '学生姓名';
COMMENT ON COLUMN business_data.students_scores.course1 IS '课程1成绩';
COMMENT ON COLUMN business_data.students_scores.course2 IS '课程2成绩';
COMMENT ON COLUMN business_data.students_scores.course3 IS '课程3成绩';
COMMENT ON COLUMN business_data.students_scores.created_at IS '创建时间';

-- 5. 插入 10 位学生的成绩数据
INSERT INTO business_data.students_scores (name, course1, course2, course3)
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

-- 6. 验证：查看所有数据
SELECT * FROM business_data.students_scores ORDER BY id;