# AuthErrorHandlers

> 认证错误处理器配置，提供 401/403 的 JSON 响应处理。

**包路径**: `com.smt.platform.common.security`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/security/AuthErrorHandlers.java`

---

## 类签名

```java
@Configuration
public class AuthErrorHandlers
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@Configuration`

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `log` | `Logger` | `private static final` | SLF4J 日志器 |
| `objectMapper` | `ObjectMapper` | `private final` | Jackson 序列化器（内联实例化） |

---

## Bean 方法

### `authenticationEntryPoint()`

> 401 认证失败处理器

**签名**: `public AuthenticationEntryPoint authenticationEntryPoint()`

**注解**: `@Bean`

**返回值**: `AuthenticationEntryPoint` — Lambda 实现

**逻辑**:
1. WARN 日志：记录 HTTP 方法、请求 URI、异常消息
2. 调用 `writeJson(response, 401, Result.error(UNAUTHORIZED, "未认证或认证已过期"))`

---

### `accessDeniedHandler()`

> 403 权限不足处理器

**签名**: `public AccessDeniedHandler accessDeniedHandler()`

**注解**: `@Bean`

**返回值**: `AccessDeniedHandler` — Lambda 实现

**逻辑**:
1. WARN 日志：记录 HTTP 方法、请求 URI、异常消息
2. 调用 `writeJson(response, 403, Result.error(FORBIDDEN, "无访问权限"))`

---

### `writeJson(HttpServletResponse response, HttpStatus status, Result<Void> body)`

> 写入 JSON 响应

**签名**: `private void writeJson(HttpServletResponse response, HttpStatus status, Result<Void> body)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `response` | `HttpServletResponse` | HTTP 响应 |
| `status` | `HttpStatus` | HTTP 状态码 |
| `body` | `Result<Void>` | 响应体 |

**逻辑**: 设置 HTTP 状态码 → Content-Type=`application/json` → CharacterEncoding=UTF-8 → 序列化 body → 写入 `response.getWriter()`

**异常**: `IOException` — 写入失败时抛出
