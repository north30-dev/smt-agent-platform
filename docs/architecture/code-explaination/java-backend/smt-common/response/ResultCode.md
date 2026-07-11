# ResultCode

> 预定义 REST API 业务状态码枚举，对齐 HTTP 标准状态码语义。

**包路径**: `com.smt.platform.common.response`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/response/ResultCode.java`

---

## 类签名

```java
@Getter
public enum ResultCode
```

**父类**: `Enum<ResultCode>`

---

## 枚举常量

| 常量 | code | message | 语义 |
|------|------|---------|------|
| `SUCCESS` | 200 | `"操作成功"` | 请求成功 |
| `PARAM_ERROR` | 400 | `"参数错误"` | 请求参数校验失败 |
| `UNAUTHORIZED` | 401 | `"未认证或认证已过期"` | 未提供 Token 或 Token 无效/过期 |
| `FORBIDDEN` | 403 | `"无访问权限"` | 已认证但无权访问 |
| `NOT_FOUND` | 404 | `"资源不存在"` | 请求的资源不存在 |
| `CONFLICT` | 409 | `"资源冲突"` | 资源冲突（如编码重复） |
| `VALIDATION_FAILED` | 422 | `"数据校验失败"` | 数据校验失败 |
| `TOO_MANY_REQUESTS` | 429 | `"请求过于频繁"` | 请求频率超限 |
| `BIZ_ERROR` | 500 | `"业务处理失败"` | 业务逻辑异常 |
| `SYSTEM_ERROR` | 500 | `"系统内部错误"` | 系统内部未处理异常 |
| `SERVICE_UNAVAILABLE` | 503 | `"依赖服务不可用"` | 下游服务不可达 |
| `GATEWAY_TIMEOUT` | 504 | `"网关超时"` | 网关请求超时 |

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `code` | `int` | `private final` | HTTP 风格数字状态码 |
| `message` | `String` | `private final` | 人类可读描述 |

---

## Lombok 生成方法

- `getCode()` — 返回状态码
- `getMessage()` — 返回描述信息
