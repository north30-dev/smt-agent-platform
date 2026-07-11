# GlobalExceptionHandler

> 全局异常处理器，捕获所有 Controller 层异常并转换为统一 `Result` 响应格式。

**包路径**: `com.smt.platform.common.exception`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/exception/GlobalExceptionHandler.java`

---

## 类签名

```java
@RestControllerAdvice
public class GlobalExceptionHandler
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@RestControllerAdvice`（全局 `@ControllerAdvice` + `@ResponseBody`）

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `log` | `Logger` | `private static final` | SLF4J 日志器 |

---

## 异常处理方法

### `handleBizException(BizException e)`

> 处理业务异常，根据 `ResultCode` 映射 HTTP 状态码

**签名**: `public ResponseEntity<Result<Void>> handleBizException(BizException e)`

**注解**: `@ExceptionHandler(BizException.class)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `e` | `BizException` | 捕获的业务异常 |

**返回值**: `ResponseEntity<Result<Void>>` — HTTP 状态码由 `HttpStatus.resolve(code)` 映射，失败时降级为 500

**逻辑**: WARN 日志 → 解析 HTTP 状态码 → 返回 `Result.error(code, message)`

---

### `handleMethodArgumentNotValid(MethodArgumentNotValidException e)`

> 处理 `@Valid` 参数校验失败

**签名**: `public Result<Void> handleMethodArgumentNotValid(MethodArgumentNotValidException e)`

**注解**: `@ExceptionHandler(MethodArgumentNotValidException.class)`, `@ResponseStatus(HttpStatus.BAD_REQUEST)`

**逻辑**: 收集所有字段校验错误 → 拼接为 `"field:message; ..."` 格式 → 返回 `Result.error(PARAM_ERROR, message)`

---

### `handleConstraintViolation(ConstraintViolationException e)`

> 处理方法级别参数校验失败

**签名**: `public Result<Void> handleConstraintViolation(ConstraintViolationException e)`

**注解**: `@ExceptionHandler(ConstraintViolationException.class)`, `@ResponseStatus(HttpStatus.BAD_REQUEST)`

**逻辑**: 收集所有约束违反 → 拼接为 `"propertyPath:message; ..."` 格式 → 返回 `Result.error(PARAM_ERROR, message)`

---

### `handleAuthenticationException(AuthenticationException e)`

> 处理认证失败（401）

**签名**: `public Result<Void> handleAuthenticationException(AuthenticationException e)`

**注解**: `@ExceptionHandler(AuthenticationException.class)`, `@ResponseStatus(HttpStatus.UNAUTHORIZED)`

**逻辑**: WARN 日志 → 返回 `Result.error(UNAUTHORIZED, "未认证或认证已过期")`

---

### `handleAccessDeniedException(AccessDeniedException e)`

> 处理权限不足（403）

**签名**: `public Result<Void> handleAccessDeniedException(AccessDeniedException e)`

**注解**: `@ExceptionHandler(AccessDeniedException.class)`, `@ResponseStatus(HttpStatus.FORBIDDEN)`

**逻辑**: WARN 日志 → 返回 `Result.error(FORBIDDEN, "无访问权限")`

---

### `handleMissingParam(MissingServletRequestParameterException e)`

> 处理缺少必填参数（400）

**签名**: `public Result<Void> handleMissingParam(MissingServletRequestParameterException e)`

**注解**: `@ExceptionHandler(MissingServletRequestParameterException.class)`, `@ResponseStatus(HttpStatus.BAD_REQUEST)`

**逻辑**: WARN 日志（含参数名） → 返回 `Result.error(PARAM_ERROR, "缺少必填参数: " + name)`

---

### `handleTypeMismatch(MethodArgumentTypeMismatchException e)`

> 处理参数类型不匹配（400）

**签名**: `public Result<Void> handleTypeMismatch(MethodArgumentTypeMismatchException e)`

**注解**: `@ExceptionHandler(MethodArgumentTypeMismatchException.class)`, `@ResponseStatus(HttpStatus.BAD_REQUEST)`

**逻辑**: WARN 日志（含参数名和值） → 返回 `Result.error(PARAM_ERROR, "参数类型不匹配: " + name)`

---

### `handleNotReadable(HttpMessageNotReadableException e)`

> 处理请求体格式错误（400）

**签名**: `public Result<Void> handleNotReadable(HttpMessageNotReadableException e)`

**注解**: `@ExceptionHandler(HttpMessageNotReadableException.class)`, `@ResponseStatus(HttpStatus.BAD_REQUEST)`

**逻辑**: WARN 日志 → 返回 `Result.error(PARAM_ERROR, "请求体格式错误或缺失")`

---

### `handleNoHandlerFound(NoHandlerFoundException e, HttpServletRequest request)`

> 处理请求路径不存在（404）

**签名**: `public Result<Void> handleNoHandlerFound(NoHandlerFoundException e, HttpServletRequest request)`

**注解**: `@ExceptionHandler(NoHandlerFoundException.class)`, `@ResponseStatus(HttpStatus.NOT_FOUND)`

**逻辑**: 提取 URI → WARN 日志 → 返回 `Result.error(NOT_FOUND, "请求路径不存在: " + uri)`

---

### `handleException(Exception e)`

> 兜底处理所有未捕获异常（500）

**签名**: `public Result<Void> handleException(Exception e)`

**注解**: `@ExceptionHandler(Exception.class)`, `@ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)`

**逻辑**: ERROR 日志（含完整堆栈） → 返回 `Result.error(SYSTEM_ERROR)` — 防止堆栈信息泄露给客户端

---

## 异常处理映射表

| 异常类型 | HTTP 状态码 | ResultCode | 说明 |
|---------|------------|------------|------|
| `BizException` | 动态 | 动态 | 由 resultCode 决定 |
| `MethodArgumentNotValidException` | 400 | PARAM_ERROR | 字段校验失败 |
| `ConstraintViolationException` | 400 | PARAM_ERROR | 方法参数校验失败 |
| `AuthenticationException` | 401 | UNAUTHORIZED | 认证失败 |
| `AccessDeniedException` | 403 | FORBIDDEN | 权限不足 |
| `MissingServletRequestParameterException` | 400 | PARAM_ERROR | 缺少必填参数 |
| `MethodArgumentTypeMismatchException` | 400 | PARAM_ERROR | 参数类型不匹配 |
| `HttpMessageNotReadableException` | 400 | PARAM_ERROR | 请求体格式错误 |
| `NoHandlerFoundException` | 404 | NOT_FOUND | 路径不存在 |
| `Exception` | 500 | SYSTEM_ERROR | 兜底处理 |
