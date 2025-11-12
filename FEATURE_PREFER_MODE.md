# Prefer Mode 功能实现文档

## 功能概述

为 Clove 添加了账户认证模式偏好设置功能,允许用户手动指定账户使用 OAuth API 还是 Web 反代模式,并在响应中标识实际使用的模式。

## 实现的功能

### 1. 账户添加时指定认证模式偏好

用户可以在添加或编辑账户时选择:
- **自动模式** (默认): 优先使用 OAuth API,失败时自动降级到 Web 反代
- **OAuth 模式**: 仅使用 OAuth API,不会降级到 Web 反代
- **Web 模式**: 仅使用 Web 反代,跳过 OAuth API

### 2. 响应头标识实际使用的模式

所有 `/v1/messages` 请求的响应中都会包含 `X-Clove-Mode` 响应头:
- `X-Clove-Mode: oauth` - 使用了 OAuth API 模式
- `X-Clove-Mode: web` - 使用了 Web 反代模式

## 后端实现

### 核心文件修改

#### 1. 数据模型 (`app/core/account.py`)

```python
class Account:
    def __init__(
        self,
        organization_uuid: str,
        capabilities: Optional[List[str]] = None,
        cookie_value: Optional[str] = None,
        oauth_token: Optional[OAuthToken] = None,
        auth_type: AuthType = AuthType.COOKIE_ONLY,
        prefer_mode: Optional[str] = None,  # 新增字段
    ):
        ...
        self.prefer_mode = prefer_mode  # 'oauth', 'web', or None
```

#### 2. API 接口 (`app/api/routes/accounts.py`)

**请求模型:**
```python
class AccountCreate(BaseModel):
    cookie_value: Optional[str] = None
    oauth_token: Optional[OAuthTokenCreate] = None
    organization_uuid: Optional[UUID] = None
    capabilities: Optional[List[str]] = None
    prefer_mode: Optional[str] = Field(None, description="...")  # 新增

class AccountUpdate(BaseModel):
    cookie_value: Optional[str] = None
    oauth_token: Optional[OAuthTokenCreate] = None
    capabilities: Optional[List[str]] = None
    status: Optional[AccountStatus] = None
    prefer_mode: Optional[str] = Field(None, description="...")  # 新增
```

**响应模型:**
```python
class AccountResponse(BaseModel):
    organization_uuid: str
    capabilities: Optional[List[str]]
    cookie_value: Optional[str]
    status: AccountStatus
    auth_type: AuthType
    is_pro: bool
    is_max: bool
    has_oauth: bool
    last_used: str
    resets_at: Optional[str] = None
    prefer_mode: Optional[str] = Field(None, description="...")  # 新增
```

#### 3. 处理器逻辑

**OAuth 处理器** (`app/processors/claude_ai/claude_api_processor.py:91-94`):
```python
# 检查账户是否偏好 Web 模式,如果是则跳过 OAuth
if account and account.prefer_mode == "web":
    logger.info(f"Account {account.organization_uuid[:8]}... prefers web mode, skipping OAuth")
    return context

# 成功处理后标记模式
context.metadata["clove_mode"] = "oauth"
```

**Web 处理器** (`app/processors/claude_ai/claude_web_processor.py:57-66`):
```python
# 检查账户是否偏好 OAuth 模式(记录警告但仍继续,作为降级备份)
if (
    context.claude_session
    and context.claude_session.account
    and context.claude_session.account.prefer_mode == "oauth"
):
    logger.warning("Account prefers OAuth mode but OAuth failed, using web as fallback")

# 成功处理后标记模式
context.metadata["clove_mode"] = "web"
```

**响应处理器** (`app/processors/claude_ai/streaming_response_processor.py:58-60`):
```python
# 流式响应添加响应头
if "clove_mode" in context.metadata:
    headers["X-Clove-Mode"] = context.metadata["clove_mode"]
```

`app/processors/claude_ai/non_streaming_response_processor.py:60-62`:
```python
# 非流式响应添加响应头
if "clove_mode" in context.metadata:
    headers["X-Clove-Mode"] = context.metadata["clove_mode"]
```

## 前端实现

### 核心文件修改

#### 1. 类型定义 (`front/src/api/types.ts`)

```typescript
export interface AccountCreate {
  cookie_value?: string;
  oauth_token?: OAuthToken;
  organization_uuid?: string;
  capabilities?: string[];
  prefer_mode?: 'oauth' | 'web' | null;  // 新增
}

export interface AccountUpdate {
  cookie_value?: string;
  oauth_token?: OAuthToken;
  capabilities?: string[];
  status?: 'valid' | 'invalid' | 'rate_limited';
  prefer_mode?: 'oauth' | 'web' | null;  // 新增
}

export interface AccountResponse {
  organization_uuid: string;
  capabilities?: string[];
  cookie_value?: string;
  status: 'valid' | 'invalid' | 'rate_limited';
  auth_type: 'cookie_only' | 'oauth_only' | 'both';
  is_pro: boolean;
  is_max: boolean;
  has_oauth: boolean;
  last_used: string;
  resets_at?: string;
  prefer_mode?: 'oauth' | 'web' | null;  // 新增
}
```

#### 2. 账户表单 (`front/src/components/AccountModal.tsx`)

**表单状态:**
```typescript
const [formData, setFormData] = useState({
    cookie_value: '',
    organization_uuid: '',
    capabilities: [] as string[],
    prefer_mode: null as 'oauth' | 'web' | null,  // 新增
})
```

**选择器组件 (在高级选项中):**
```tsx
<div className='space-y-2'>
    <Label htmlFor='preferMode'>认证模式偏好</Label>
    <Select
        value={formData.prefer_mode || 'auto'}
        onValueChange={value =>
            setFormData({
                ...formData,
                prefer_mode: value === 'auto' ? null : (value as 'oauth' | 'web')
            })
        }
    >
        <SelectTrigger className='w-full' id='preferMode'>
            <SelectValue placeholder='选择认证模式偏好' />
        </SelectTrigger>
        <SelectContent>
            <SelectItem value='auto'>自动 (优先 OAuth)</SelectItem>
            <SelectItem value='oauth'>仅 OAuth API</SelectItem>
            <SelectItem value='web'>仅 Web 反代</SelectItem>
        </SelectContent>
    </Select>
    <p className='text-xs text-muted-foreground'>
        自动模式会优先使用 OAuth,失败后降级到 Web 反代
    </p>
</div>
```

#### 3. 账户列表 (`front/src/pages/Accounts.tsx`)

**桌面端表格:**
```tsx
<TableHead>模式偏好</TableHead>
...
<TableCell>
    <Badge variant='outline'>
        {account.prefer_mode === 'oauth' ? 'OAuth' :
         account.prefer_mode === 'web' ? 'Web' : '自动'}
    </Badge>
</TableCell>
```

**移动端卡片:**
```tsx
<div className='flex justify-between'>
    <span className='text-muted-foreground'>模式偏好</span>
    <Badge variant='outline' className='text-xs'>
        {account.prefer_mode === 'oauth' ? 'OAuth' :
         account.prefer_mode === 'web' ? 'Web' : '自动'}
    </Badge>
</div>
```

## API 使用示例

### 创建账户并指定模式偏好

```bash
# 创建 OAuth 偏好账户
curl -X POST http://localhost:5201/api/accounts \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cookie_value": "sessionKey=sk-ant-sid01-...",
    "prefer_mode": "oauth",
    "capabilities": ["chat", "claude_pro"]
  }'

# 创建 Web 偏好账户
curl -X POST http://localhost:5201/api/accounts \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cookie_value": "sessionKey=sk-ant-sid01-...",
    "prefer_mode": "web",
    "capabilities": ["chat"]
  }'

# 创建自动模式账户(默认)
curl -X POST http://localhost:5201/api/accounts \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cookie_value": "sessionKey=sk-ant-sid01-...",
    "capabilities": ["chat"]
  }'
```

### 更新账户模式偏好

```bash
curl -X PUT http://localhost:5201/api/accounts/{organization_uuid} \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "prefer_mode": "web"
  }'
```

### 检查响应中的模式标识

```bash
curl -i -X POST http://localhost:5201/v1/messages \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'

# 响应头中包含:
# X-Clove-Mode: oauth  或  X-Clove-Mode: web
```

## 工作流程

### 自动模式 (prefer_mode = null, 默认)

```
请求 → ClaudeAIProcessorPipeline
  ↓
ClaudeAPIProcessor (尝试 OAuth)
  ↓ 成功?
  是 → 返回响应 (X-Clove-Mode: oauth)
  否 ↓
ClaudeWebProcessor (降级到 Web)
  ↓
返回响应 (X-Clove-Mode: web)
```

### OAuth 模式 (prefer_mode = "oauth")

```
请求 → ClaudeAIProcessorPipeline
  ↓
ClaudeAPIProcessor
  ↓ 成功?
  是 → 返回响应 (X-Clove-Mode: oauth)
  否 → 抛出异常 (不降级到 Web)
```

### Web 模式 (prefer_mode = "web")

```
请求 → ClaudeAIProcessorPipeline
  ↓
ClaudeAPIProcessor (检查 prefer_mode)
  ↓ prefer_mode == "web"?
  是 → 跳过 OAuth
  ↓
ClaudeWebProcessor
  ↓
返回响应 (X-Clove-Mode: web)
```

## 测试

运行测试脚本:

```bash
python test_prefer_mode.py
```

测试覆盖:
1. 创建 OAuth 偏好账户
2. 创建 Web 偏好账户
3. 创建自动模式账户
4. 列出所有账户并检查 prefer_mode 字段
5. 发送 messages 请求并检查 X-Clove-Mode 响应头

## 数据持久化

prefer_mode 字段会随账户信息一起保存到:
- `~/.clove/data/accounts.json` (或 `DATA_FOLDER/accounts.json`)

格式:
```json
{
  "organization-uuid": {
    "organization_uuid": "...",
    "cookie_value": "...",
    "status": "valid",
    "auth_type": "both",
    "last_used": "2025-11-12T...",
    "resets_at": null,
    "oauth_token": {...},
    "prefer_mode": "oauth"  // "oauth", "web", 或 null
  }
}
```

## 兼容性说明

- **向后兼容**: 现有账户在没有 prefer_mode 字段时默认为 null (自动模式)
- **默认行为不变**: 不指定 prefer_mode 时,保持原有的优先 OAuth 后降级 Web 的逻辑
- **响应头**: 所有请求都会添加 X-Clove-Mode 响应头,不影响现有客户端

## 日志示例

```
[INFO] Account 12345678... prefers web mode, skipping OAuth
[INFO] Successfully processed request via Claude API
[INFO] Account 87654321... prefers OAuth mode but OAuth failed, using web as fallback
```

## 相关文件清单

### 后端
- `app/core/account.py` - Account 类定义
- `app/services/account.py` - AccountManager.add_account()
- `app/api/routes/accounts.py` - API 端点和模型
- `app/processors/claude_ai/claude_api_processor.py` - OAuth 处理器
- `app/processors/claude_ai/claude_web_processor.py` - Web 处理器
- `app/processors/claude_ai/streaming_response_processor.py` - 流式响应处理器
- `app/processors/claude_ai/non_streaming_response_processor.py` - 非流式响应处理器

### 前端
- `front/src/api/types.ts` - TypeScript 类型定义
- `front/src/components/AccountModal.tsx` - 账户创建/编辑表单
- `front/src/pages/Accounts.tsx` - 账户列表页面

### 测试
- `test_prefer_mode.py` - 功能测试脚本

## 注意事项

1. **OAuth 偏好账户**: 如果设置为 `prefer_mode="oauth"` 但账户没有有效的 OAuth token,请求将失败,不会降级到 Web 模式
2. **Web 偏好账户**: 如果设置为 `prefer_mode="web"` 但账户没有有效的 Cookie,请求将失败
3. **自动模式最安全**: 建议大多数用户使用自动模式,除非有特殊需求
4. **响应头**: X-Clove-Mode 响应头对所有客户端可见,可用于监控和统计

## 未来优化建议

1. 添加统计功能,记录每个账户使用 OAuth 和 Web 的频率
2. 在前端 Dashboard 显示实时的模式使用情况
3. 添加账户级别的模式切换历史记录
4. 支持基于时间的自动模式切换(如高峰期优先 Web,低峰期优先 OAuth)
