# JwtUtil

> JWT 工具类，提供 Token 签发、解析和验证功能，基于 HMAC-SHA 算法。

**包路径**: `com.smt.platform.common.utils`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/utils/JwtUtil.java`

---

## 类签名

```java
@Component
public class JwtUtil
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@Component`

---

## 字段

| 字段 | 类型 | 修饰符 | 注解 | 说明 |
|------|------|--------|------|------|
| `secret` | `String` | `private` | `@Value("${smt.security.jwt.secret}")` | HMAC-SHA 密钥，需 >= 32 字节 |

---

## 方法

### `generateToken(Map<String, Object> claims, long expireMs)`

> 使用自定义 Claims 签发 Token

**签名**: `public String generateToken(Map<String, Object> claims, long expireMs)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `claims` | `Map<String, Object>` | 是 | 自定义声明键值对 |
| `expireMs` | `long` | 是 | 过期时间（毫秒） |

**返回值**: `String` — Compact JWT 字符串

**逻辑**: 设置 claims → 设置 issuedAt=now → 设置 expiration=now+expireMs → HMAC-SHA 签名

---

### `generateToken(String subject, List<String> roles, long expireMs)`

> 签发带用户标识和角色的 Token

**签名**: `public String generateToken(String subject, List<String> roles, long expireMs)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `subject` | `String` | 是 | 用户标识（如用户名） |
| `roles` | `List<String>` | 是 | 角色列表（如 `["ADMIN", "USER"]`） |
| `expireMs` | `long` | 是 | 过期时间（毫秒） |

**返回值**: `String` — Compact JWT 字符串

**逻辑**: 设置 subject → 将 roles 存入 `"roles"` claim → 设置 issuedAt/expiration → HMAC-SHA 签名

---

### `parseToken(String token)`

> 解析并验证 Token

**签名**: `public Claims parseToken(String token)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `token` | `String` | 是 | JWT 字符串 |

**返回值**: `Claims` — 解析后的声明对象

**异常**: `JwtException` — 签名无效或 Token 过期时抛出

**逻辑**: 验证签名 → 验证过期时间 → 返回 Claims

---

### `validateToken(String token)`

> 验证 Token 是否有效

**签名**: `public boolean validateToken(String token)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `token` | `String` | 是 | JWT 字符串 |

**返回值**: `boolean` — 有效返回 `true`，无效（签名错误/过期）返回 `false`

**逻辑**: 在 try-catch 中调用 `parseToken()`，成功返回 `true`，捕获 `JwtException`/`IllegalArgumentException` 返回 `false`

---

### `toKey()`

> 将密钥字符串转换为 SecretKey

**签名**: `private SecretKey toKey()`

**返回值**: `SecretKey` — HMAC-SHA 密钥对象

**逻辑**: UTF-8 编码 → `Keys.hmacShaKeyFor()` 创建密钥
