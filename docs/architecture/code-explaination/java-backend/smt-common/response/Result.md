# Result\<T\>

> 统一 REST API 响应封装，所有接口返回值均包装为此类型。

**包路径**: `com.smt.platform.common.response`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/response/Result.java`

---

## 类签名

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Result<T> implements Serializable
```

**父类**: `Object`
**实现接口**: `Serializable`
**泛型参数**: `T` — 业务数据类型

---

## 构造方法

| 构造方法 | 参数 | 说明 |
|---------|------|------|
| `Result()` | 无 | 无参构造（Lombok `@NoArgsConstructor`） |
| `Result(int code, String message, T data)` | `code`: 状态码, `message`: 提示信息, `data`: 业务数据 | 全参构造（Lombok `@AllArgsConstructor`） |

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `serialVersionUID` | `long` | `private static final` | 序列化版本号，值为 `1L` |
| `code` | `int` | `private` | 业务状态码（200 = 成功） |
| `message` | `String` | `private` | 提示信息 |
| `data` | `T` | `private` | 业务数据载荷 |

---

## 公开方法

### `success()`

> 创建成功响应（无数据）

**签名**: `public static <T> Result<T> success()`

**返回值**: `Result<T>` — code=200, message="操作成功", data=null

---

### `success(T data)`

> 创建成功响应（带数据）

**签名**: `public static <T> Result<T> success(T data)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `data` | `T` | 否 | 业务数据载荷 |

**返回值**: `Result<T>` — code=200, message="操作成功", data=指定值

---

### `error(int code, String message)`

> 创建错误响应（自定义状态码）

**签名**: `public static <T> Result<T> error(int code, String message)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | `int` | 是 | 错误状态码 |
| `message` | `String` | 是 | 错误描述 |

**返回值**: `Result<T>` — 指定 code 和 message, data=null

---

### `error(ResultCode resultCode)`

> 创建错误响应（使用 ResultCode 枚举）

**签名**: `public static <T> Result<T> error(ResultCode resultCode)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `resultCode` | `ResultCode` | 是 | 预定义状态码枚举 |

**返回值**: `Result<T>` — 使用枚举的 code 和 message

---

### `error(ResultCode resultCode, String message)`

> 创建错误响应（使用 ResultCode 枚举 + 自定义消息）

**签名**: `public static <T> Result<T> error(ResultCode resultCode, String message)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `resultCode` | `ResultCode` | 是 | 预定义状态码枚举 |
| `message` | `String` | 是 | 自定义错误描述（覆盖枚举默认消息） |

**返回值**: `Result<T>` — 使用枚举的 code + 自定义 message

---

## Lombok 生成方法

以下方法由 Lombok `@Data` 自动生成：

- `getCode()` / `setCode(int code)`
- `getMessage()` / `setMessage(String message)`
- `getData()` / `setData(T data)`
- `equals(Object o)`
- `hashCode()`
- `toString()`

---

## 使用示例

```java
// 成功响应
return Result.success(device);

// 成功响应（无数据）
return Result.success(null);

// 错误响应
return Result.error(ResultCode.NOT_FOUND);

// 错误响应（自定义消息）
return Result.error(ResultCode.BIZ_ERROR, "设备编码已存在");
```
