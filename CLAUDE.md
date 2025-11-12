# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在处理此仓库代码时提供指导。

## 项目概述

Clove 是一个复杂的 Claude.ai 反向代理,提供 OAuth API 访问和 Web 界面反向代理双重功能。采用 FastAPI (Python) 后端和 React (TypeScript) 前端构建,使各种 AI 应用能够以高兼容性连接到 Claude。

## 常用开发命令

### 构建和运行

```bash
# 完整构建(前端 + Python wheel)
make build

# 仅构建前端
make build-frontend
# 或手动执行:
cd front && pnpm install && pnpm run build

# 仅构建 Python wheel
make build-wheel

# 安装并运行
make install
clove

# 开发模式
make install-dev
make run
# 或
python -m app.main
```

### 前端开发

```bash
cd front
pnpm install      # 安装依赖
pnpm run dev      # 开发服务器(端口 5173,代理到后端 5201)
pnpm run build    # 生产构建
pnpm run lint     # 运行 ESLint
```

### Python 开发

```bash
# 安装可选依赖
pip install -e ".[rnet,curl,dev]"

# 开发模式运行
python -m app.main

# 代码检查(需安装 ruff)
ruff check app/
ruff format app/
```

## 架构概览

### 双模式运行
1. **OAuth 模式**: 直接访问 Claude API,支持完整功能(系统消息、预填充等)
2. **Web 反代模式**: 当 OAuth 不可用时模拟 Claude.ai 网页端

### 请求处理管道
核心架构使用处理器管道模式(责任链模式):

```
请求 → ClaudeAI处理管道 → [
    ClaudeAPIProcessor (OAuth) 或 ClaudeWebProcessor (Web)
    → EventParsingProcessor
    → ToolCallEventProcessor
    → StreamingResponseProcessor
    → ... 专用处理器
] → 响应
```

关键处理器:
- `app/processors/claude_ai/pipeline.py`: 主管道协调器
- `app/processors/claude_ai/claude_api_processor.py`: OAuth API 处理
- `app/processors/claude_ai/claude_web_processor.py`: Web 界面处理
- `app/processors/claude_ai/tool_call_event_processor.py`: 函数调用支持

### 服务层架构
- **账户服务** (`app/services/account.py`): 多账户管理与故障转移
- **会话服务** (`app/services/session.py`): Claude.ai 会话生命周期管理
- **OAuth 服务** (`app/services/oauth.py`): OAuth 认证流程
- **缓存服务** (`app/services/cache.py`): 响应缓存

### API 端点
- `/v1/messages`: Claude messages API(OpenAI 兼容)
- `/chat/completions`: OpenAI chat completions 兼容性
- `/models`: 可用模型列表
- `/accounts`: 账户管理
- `/settings`: 配置管理
- `/statistics`: 使用统计

### 配置管理
配置优先级(从高到低):
1. 环境变量
2. .env 文件
3. config.json 文件
4. `app/core/config.py` 中的默认值

核心配置类: `app/core/config.py:Settings`

### 前端架构
- **React 19** 与 TypeScript
- **Vite** 构建工具与 Tailwind CSS
- **Shadcn/UI** 组件库
- **API 客户端**: `front/src/api/` 使用 Axios
- **页面**: Dashboard、Accounts、Settings (`front/src/pages/`)

## 关键实现细节

### 双模式运行机制详解

#### OAuth 模式 (`ClaudeAPIProcessor`)
- **API 端点**: `https://api.anthropic.com/v1/messages`
- **认证方式**: `Authorization: Bearer {access_token}`
- **请求头**:
  - `anthropic-beta: oauth-2025-04-20`
  - `anthropic-version: 2023-06-01`
  - `Content-Type: application/json`
- **响应头特征**:
  - `anthropic-ratelimit-unified-reset`: 速率限制重置时间戳
  - 保留所有原始 API 响应头(除 `content-encoding` 和 `content-length`)
- **优势**:
  - 完整的 API 功能支持(system messages、prefilling 等)
  - 官方标准接口,稳定性高
  - 支持速率限制管理和自动恢复

#### Web 反代模式 (`ClaudeWebProcessor`)
- **目标地址**: `https://claude.ai`
- **认证方式**: Cookie-based 认证
- **会话管理**:
  - 维护会话状态 (`session_manager`)
  - 自动处理会话初始化和清理
  - 支持文件上传(图片等)
- **响应头特征**:
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`
  - 标准 SSE (Server-Sent Events) 格式
- **使用场景**:
  - OAuth 不可用或被限制时的备选方案
  - 需要模拟浏览器行为的场景

#### 模式切换逻辑
在 `app/processors/claude_ai/pipeline.py` 中:
1. 优先尝试 `ClaudeAPIProcessor` (OAuth 模式)
2. 如果 OAuth 不可用(无账户、速率限制等),自动降级到 `ClaudeWebProcessor`
3. 两种模式的输出最终都会经过相同的事件解析和响应处理器

#### 如何区分响应来源
通过响应头判断:
- **OAuth 模式**: 包含 `anthropic-*` 开头的响应头
- **Web 反代模式**: 仅包含标准流式响应头,无 Anthropic 特定头

### 添加新功能
1. **新 API 端点**: 在 `app/api/routes/` 添加路由,在 `app/api/main.py` 注册
2. **新处理器**: 继承 `app/processors/base.py` 中的 `BaseProcessor`,添加到管道
3. **新前端页面**: 在 `front/src/pages/` 创建,在 `App.tsx` 添加路由

### 模型处理与账户路由

#### 模型与账户类型映射
系统根据请求的模型自动选择具有相应权限的账户:

**Max Models (需要 Max 套餐账户)**:
- `claude-opus-4-1-20250805` (默认配置)
- 配置位置: `app/core/config.py:256` 中的 `max_models` 列表
- 环境变量: `MAX_MODELS` (逗号分隔)

**账户能力判断**:
- `is_pro`: 检查 capabilities 是否包含 `pro`、`enterprise`、`raven`、`max` 关键词
- `is_max`: 检查 capabilities 是否包含 `max` 关键词
- 实现位置: `app/core/account.py:148-166`

**账户选择逻辑** (`app/processors/claude_ai/claude_api_processor.py:85-89`):
```python
account = await account_manager.get_account_for_oauth(
    is_max=True if (model in settings.max_models) else None
)
```

#### 可用模型列表
在 `app/models/openai.py:40-65` 中定义:
- `claude-3-5-haiku-20241022` - Claude Haiku 3.5
- `claude-opus-4-1-20250805` - Claude Opus 4.1 (需要 Max 账户)
- `claude-opus-4-20250514` - Claude Opus 4
- `claude-sonnet-4-20250514` - Claude Sonnet 4

#### Token 计数
- 使用 tiktoken 和模型特定编码
- 实现位置: `app/processors/claude_ai/token_counter_processor.py`

### 会话管理
- 通过后台任务自动清理会话
- 会话持久化到 `data/` 目录
- Web 模式使用基于 Cookie 的认证

### 错误处理
- 全局错误处理器: `app/core/error_handler.py`
- 各模块的自定义异常
- 使用 loguru 结构化日志到 `logs/` 目录

### 账户管理机制
- **多账户负载均衡**: 基于最少会话数和最早使用时间选择账户
- **速率限制恢复**: 自动追踪和恢复被限速的账户
- **OAuth Token 刷新**: 自动在 Token 过期前 5 分钟刷新
- **认证类型**: 支持三种类型
  - `COOKIE_ONLY`: 仅 Cookie 认证(仅 Web 模式)
  - `OAUTH_ONLY`: 仅 OAuth 认证(仅 API 模式)
  - `BOTH`: 双重认证(两种模式都可用)

## 开发注意事项

### 测试
目前未实现正式测试框架。添加测试时:
- Python 测试考虑使用 pytest
- 测试文件命名为 `test_*.py` 或 `*_test.py`
- 前端测试使用 Vitest(已随 Vite 配置)

### 类型安全
- Python: 全面使用类型提示,可用 mypy 验证
- TypeScript: 启用严格模式,运行 `tsc` 进行类型检查

### 异步模式
- 所有 I/O 操作使用 async/await
- 长时间运行操作使用后台任务
- 使用 httpx 进行正确的连接池管理

### 安全注意事项
- 永不提交密钥或 API keys
- 敏感配置使用环境变量
- 使用 Pydantic 模型验证所有用户输入
- CORS 配置在 `app/api/main.py`

## 调试技巧

1. **日志**: 检查 `logs/` 目录获取详细日志
2. **API 测试**: 使用内置 FastAPI 文档 `http://localhost:5201/docs`
3. **前端调试**: React DevTools 和 Network 标签用于 API 调试
4. **会话问题**: 检查 `data/` 目录的会话持久化文件
5. **OAuth 流程**: 在浏览器 DevTools 中监控重定向链

## 常见任务

### 添加新的 Claude 模型
1. 在 `app/models/openai.py:40-65` 的 `AVAILABLE_MODELS` 列表中添加模型定义
2. 如果是 Max 级别模型,更新 `app/core/config.py:256` 的 `max_models` 列表
3. 如需要在 `app/models/claude.py` 添加 token 编码配置

示例:
```python
# 在 app/models/openai.py 添加新模型
Model(
    id="claude-opus-5-20260101",
    display_name="Claude Opus 5",
    created_at="2026-01-01T00:00:00Z",
    created=1735689600,
)

# 如果需要 Max 账户,在 .env 或 config.json 中配置
MAX_MODELS=claude-opus-4-1-20250805,claude-opus-5-20260101
```

### 配置账户类型要求
在 `config.json` 或环境变量中配置:
```bash
# 环境变量方式
export MAX_MODELS="claude-opus-4-1-20250805,claude-new-max-model"

# 或在 data/config.json 中
{
  "max_models": ["claude-opus-4-1-20250805", "claude-new-max-model"]
}
```

### 修改请求/响应格式
1. 更新 `app/models/` 中的 Pydantic 模型
2. 调整 `app/processors/claude_ai/` 中的处理器
3. 如需要更新 API 路由

### 前端样式
- 使用 Tailwind CSS 类
- 遵循 Shadcn/UI 组件模式
- 保持暗色模式支持
