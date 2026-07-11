# SecurityConfig

> Spring Security 核心配置，定义过滤链、URL 权限规则和密码编码器。

**包路径**: `com.smt.platform.common.security`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/security/SecurityConfig.java`

---

## 类签名

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@Configuration`, `@EnableWebSecurity`, `@EnableMethodSecurity`

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `jwtAuthenticationFilter` | `JwtAuthenticationFilter` | `private final` | JWT 认证过滤器 |
| `authenticationEntryPoint` | `AuthenticationEntryPoint` | `private final` | 401 入口点处理 |
| `accessDeniedHandler` | `AccessDeniedHandler` | `private final` | 403 拒绝处理 |

---

## 构造方法

```java
public SecurityConfig(
    JwtAuthenticationFilter jwtAuthenticationFilter,
    AuthenticationEntryPoint authenticationEntryPoint,
    AccessDeniedHandler accessDeniedHandler
)
```

构造器注入三个 Security Bean。

---

## Bean 方法

### `securityFilterChain(HttpSecurity http)`

> 配置 Spring Security 过滤链

**签名**: `public SecurityFilterChain securityFilterChain(HttpSecurity http)`

**注解**: `@Bean`

**返回值**: `SecurityFilterChain`

**配置规则**:

| 配置项 | 值 | 说明 |
|--------|---|------|
| CSRF | 禁用 | 无状态 API 不需要 |
| Session | STATELESS | 不创建 HTTP Session |

**URL 权限规则**（按顺序匹配）:

| URL | 权限 | 说明 |
|-----|------|------|
| `POST /api/auth/login` | permitAll | 登录接口无需认证 |
| `GET /api/auth/me` | authenticated | 获取当前用户需认证 |
| `/actuator/health`, `/actuator/info` | permitAll | 健康检查公开 |
| `/actuator/**` | hasRole("ADMIN") | 管理端点需 ADMIN 角色 |
| `GET /api/**` | permitAll | GET 请求匿名可读 |
| 其他 `/api/**` | authenticated | 写操作需认证 |
| 其他所有路径 | permitAll | 默认放行 |

**过滤器链**: 在 `UsernamePasswordAuthenticationFilter` 之前添加 `jwtAuthenticationFilter`

---

### `passwordEncoder()`

> 密码编码器

**签名**: `public PasswordEncoder passwordEncoder()`

**注解**: `@Bean`

**返回值**: `BCryptPasswordEncoder` — BCrypt 密码哈希

---

### `authenticationManager(AuthenticationConfiguration config)`

> 认证管理器

**签名**: `public AuthenticationManager authenticationManager(AuthenticationConfiguration config)`

**注解**: `@Bean`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `config` | `AuthenticationConfiguration` | Spring 自动配置 |

**返回值**: `AuthenticationManager` — 供 `AuthController` 手动认证调用
