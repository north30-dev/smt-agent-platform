# AgentAuthWebFilter

> 网关 JWT 认证过滤器，对 `/api/agent/**` 路径进行 Token 校验。

**包路径**: `com.smt.platform.gateway.security`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-gateway/src/main/java/com/smt/platform/gateway/security/AgentAuthWebFilter.java`

---

## 类签名

```java
@Component
@Import(JwtUtil.class)
public class AgentAuthWebFilter implements WebFilter, Ordered
```

**父类**: `Object`
**实现接口**: `WebFilter`, `Ordered`
**Spring 注解**: `@Component`, `@Import(JwtUtil.class)`

---

## 字段

| 字段 | 类型 | 修饰符 | 注解 | 说明 |
|------|------|--------|------|------|
| `log` | `Logger` | `private static final` | — | SLF4J 日志器 |
| `AGENT_PATH_PREFIX` | `String` | `private static final` | — | 代理路径前缀 `"/api/agent/"` |
| `jwtUtil` | `JwtUtil` | `private final` | — | JWT 工具类 |
| `objectMapper` | `ObjectMapper` | `private final` | — | JSON 序列化器 |
| `headerName` | `String` | `private` | `@Value("${smt.security.jwt.header:Authorization}")` | HTTP 头名称 |
| `headerPrefix` | `String` | `private` | `@Value("${smt.security.jwt.prefix:Bearer }")` | Token 前缀 |

---

## 构造方法

```java
public AgentAuthWebFilter(JwtUtil jwtUtil)
```

构造器注入 `JwtUtil`。

---

## 方法

### `filter(ServerWebExchange exchange, WebFilterChain chain)`

> 核心过滤逻辑

**签名**: `public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `exchange` | `ServerWebExchange` | 服务端 Web 交换对象 |
| `chain` | `WebFilterChain` | 过滤器链 |

**返回值**: `Mono<Void>` — 响应式空值

**逻辑**:

1. **路径过滤**: 请求路径不以 `/api/agent/` 开头 → 直接放行 `chain.filter(exchange)`
2. **提取 Token**: 调用 `extractToken(exchange)` 提取 JWT
3. **Token 缺失**: 返回 401 + `"token 缺失"`
4. **Token 无效/过期**: 调用 `jwtUtil.validateToken()` 校验 → 失败返回 401 + `"token 无效或已过期"`
5. **Token 有效**: 放行 `chain.filter(exchange)`

---

### `getOrder()`

> 过滤器优先级

**签名**: `public int getOrder()`

**返回值**: `int` — `Ordered.HIGHEST_PRECEDENCE + 10`（极高优先级）

---

### `extractToken(ServerWebExchange exchange)`

> 从请求头提取 JWT

**签名**: `private String extractToken(ServerWebExchange exchange)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `exchange` | `ServerWebExchange` | 服务端 Web 交换对象 |

**返回值**: `String` — JWT 字符串，无 Token 返回 `null`

**逻辑**: 读取 `headerName` 头 → 空或不以 `headerPrefix` 开头返回 null → 去除前缀返回 trimmed token

---

### `writeUnauthorized(ServerWebExchange exchange, String message)`

> 写入 401 JSON 响应

**签名**: `private Mono<Void> writeUnauthorized(ServerWebExchange exchange, String message)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `exchange` | `ServerWebExchange` | 服务端 Web 交换对象 |
| `message` | `String` | 错误消息 |

**返回值**: `Mono<Void>` — 响应式空值

**逻辑**: 设置 401 状态码 → Content-Type=`application/json` → 序列化 `{"error":"unauthorized","message":"..."}` → 写入 DataBuffer
