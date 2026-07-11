# JwtAuthenticationFilter

> JWT 认证过滤器，从 HTTP 请求头提取 Token 并设置 Spring Security 上下文。

**包路径**: `com.smt.platform.common.security`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/security/JwtAuthenticationFilter.java`

---

## 类签名

```java
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter
```

**父类**: `org.springframework.web.filter.OncePerRequestFilter`
**实现接口**: 无
**Spring 注解**: `@Component`

---

## 字段

| 字段 | 类型 | 修饰符 | 注解 | 说明 |
|------|------|--------|------|------|
| `log` | `Logger` | `private static final` | — | SLF4J 日志器 |
| `jwtUtil` | `JwtUtil` | `private final` | — | JWT 工具类 |
| `headerName` | `String` | `private` | `@Value("${smt.security.jwt.header:Authorization}")` | HTTP 头名称，默认 `"Authorization"` |
| `headerPrefix` | `String` | `private` | `@Value("${smt.security.jwt.prefix:Bearer }")` | Token 前缀，默认 `"Bearer "` |

---

## 构造方法

```java
public JwtAuthenticationFilter(JwtUtil jwtUtil)
```

构造器注入 `JwtUtil`。

---

## 方法

### `doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)`

> 核心过滤逻辑

**签名**: `protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `request` | `HttpServletRequest` | HTTP 请求 |
| `response` | `HttpServletResponse` | HTTP 响应 |
| `filterChain` | `FilterChain` | 过滤器链 |

**逻辑**:

1. 调用 `extractToken(request)` 提取 JWT
2. Token 非空时：
   - 解析 Token → 提取 `subject`（用户名）和 `roles`（角色列表）
   - 将 roles 转为 `SimpleGrantedAuthority`（添加 `ROLE_` 前缀）
   - 创建 `UsernamePasswordAuthenticationToken` → 设置到 `SecurityContextHolder`
3. 解析异常时：DEBUG 日志 → 清除 SecurityContext（匿名身份） → 不抛异常
4. 始终调用 `filterChain.doFilter()` 继续过滤链

---

### `extractToken(HttpServletRequest request)`

> 从请求头提取 JWT 字符串

**签名**: `private String extractToken(HttpServletRequest request)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `request` | `HttpServletRequest` | HTTP 请求 |

**返回值**: `String` — JWT 字符串，无 Token 或格式不对时返回 `null`

**逻辑**: 读取 `headerName` 头 → 空或不以 `headerPrefix` 开头返回 null → 去除前缀返回 trimmed token

---

### `toAuthorities(Object rolesObj)`

> 将 JWT roles claim 转换为 Spring Security 权限列表

**签名**: `private List<SimpleGrantedAuthority> toAuthorities(Object rolesObj)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `rolesObj` | `Object` | JWT 中的 roles claim（期望 `List<?>`） |

**返回值**: `List<SimpleGrantedAuthority>` — 权限列表

**逻辑**: 将每个 role 字符串添加 `"ROLE_"` 前缀（如 `"ADMIN"` → `"ROLE_ADMIN"`）以匹配 `hasRole()` 表达式。输入非列表/空/元素非字符串时返回空列表。
