# CorsConfig

> 网关 CORS 跨域配置（响应式），仅在 `dev` Profile 下生效。

**包路径**: `com.smt.platform.gateway.config`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-gateway/src/main/java/com/smt/platform/gateway/config/CorsConfig.java`

---

## 类签名

```java
@Profile("dev")
@Configuration
public class CorsConfig
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@Profile("dev")`, `@Configuration`

---

## Bean 方法

### `corsWebFilter()`

> 创建 CORS WebFilter

**签名**: `public CorsWebFilter corsWebFilter()`

**注解**: `@Bean`

**返回值**: `CorsWebFilter` — 响应式 CORS 过滤器

**配置项**:

| 配置 | 值 | 说明 |
|------|---|------|
| 允许来源 | `localhost:5173`, `localhost:3000`, `smt.example.com` | 开发环境域名 |
| 允许方法 | `*` | 所有 HTTP 方法 |
| 允许头部 | `*` | 所有请求头 |
| 允许凭证 | `true` | 允许携带 Cookie |
| 预检缓存 | `3600` 秒 | 1 小时 |
| 路径 | `/**` | 所有路径 |

**生效条件**: 仅在 `dev` Profile 下激活

---

## 注意事项

- 此配置使用 `UrlBasedCorsConfigurationSource` + `CorsWebFilter`（WebFlux 响应式）
- 与 `smt-common` 中的 `CorsConfig`（Servlet 非响应式）互不影响，分别服务于不同技术栈
