# BizException

> 业务异常基类，携带 `ResultCode` 状态码，由 `GlobalExceptionHandler` 统一捕获并转换为 `Result` 响应。

**包路径**: `com.smt.platform.common.exception`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/exception/BizException.java`

---

## 类签名

```java
@Getter
public class BizException extends RuntimeException
```

**父类**: `RuntimeException`
**实现接口**: 无

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `serialVersionUID` | `long` | `private static final` | 序列化版本号，值为 `1L` |
| `resultCode` | `ResultCode` | `private final` | 关联的业务状态码 |

---

## 构造方法

### `BizException(ResultCode resultCode)`

> 使用预定义状态码构造异常

**签名**: `public BizException(ResultCode resultCode)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `resultCode` | `ResultCode` | 是 | 业务状态码 |

**实现**: 调用 `super(resultCode.getMessage())`，存储 `resultCode`

---

### `BizException(ResultCode resultCode, String message)`

> 使用预定义状态码 + 自定义消息构造异常

**签名**: `public BizException(ResultCode resultCode, String message)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `resultCode` | `ResultCode` | 是 | 业务状态码 |
| `message` | `String` | 是 | 自定义错误描述 |

**实现**: 调用 `super(message)`，存储 `resultCode`

---

### `BizException(String message)`

> 使用自定义消息构造异常（默认状态码 BIZ_ERROR）

**签名**: `public BizException(String message)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message` | `String` | 是 | 自定义错误描述 |

**实现**: 调用 `super(message)`，`resultCode` 默认为 `ResultCode.BIZ_ERROR`

---

## Lombok 生成方法

- `getResultCode()` — 返回关联的 `ResultCode`

---

## 使用示例

```java
// 抛出"资源不存在"异常
throw new BizException(ResultCode.NOT_FOUND);

// 抛出"业务错误"异常（自定义消息）
throw new BizException(ResultCode.BIZ_ERROR, "设备编码已存在");

// 抛出"业务错误"异常（默认 BIZ_ERROR）
throw new BizException("自定义错误信息");
```
