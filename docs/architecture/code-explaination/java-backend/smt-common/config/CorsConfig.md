# CorsConfig

> 开发环境 CORS 跨域配置，仅在 `dev` Profile 下生效。

**包路径**: `com.smt.platform.common.config`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/config/CorsConfig.java`

---

## 类签名

```java
@Profile("dev")
@Configuration
public class CorsConfig implements WebMvcConfigurer
```

**父类**: `Object`
**实现接口**: `org.springframework.web.servlet.config.annotation.WebMvcConfigurer`
**Spring 注解**: `@Profile("dev")`, `@Configuration`

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `DEV_ALLOWED_ORIGIN_PATTERNS` | `String[]` | `private static final` | 允许的来源模式数组 |

**允许的来源**:
- `http://localhost:*`
- `http://127.0.0.1:*`
- `https://localhost:*`
- `https://127.0.0.1:*`

---

## 方法

### `addCorsMappings(CorsRegistry registry)`

> 注册 CORS 映射配置

**签名**: `public void addCorsMappings(CorsRegistry registry)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `registry` | `CorsRegistry` | Spring CORS 注册表 |

**配置项**:

| 配置 | 值 | 说明 |
|------|---|------|
| 路径 | `/**` | 所有路径 |
| 允许来源 | `DEV_ALLOWED_ORIGIN_PATTERNS` | localhost/127.0.0.1 |
| 允许方法 | GET, POST, PUT, DELETE, OPTIONS, PATCH | 所有常用 HTTP 方法 |
| 允许头部 | `*` | 所有请求头 |
| 允许凭证 | `true` | 允许携带 Cookie |
| 预检缓存 | `3600` 秒 | 1 小时 |

**生效条件**: 仅在 `dev` Profile 下激活
