# JacksonConfig

> Jackson 序列化配置，统一日期格式、时区和序列化行为。

**包路径**: `com.smt.platform.common.config`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/config/JacksonConfig.java`

---

## 类签名

```java
@Configuration
public class JacksonConfig
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@Configuration`

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `DATE_TIME_PATTERN` | `String` | `private static final` | 日期时间格式，值为 `"yyyy-MM-dd HH:mm:ss"` |
| `DATE_PATTERN` | `String` | `private static final` | 日期格式，值为 `"yyyy-MM-dd"` |

---

## Bean 方法

### `objectMapper()`

> 创建全局 ObjectMapper Bean

**签名**: `public ObjectMapper objectMapper()`

**注解**: `@Bean`, `@ConditionalOnMissingBean(ObjectMapper.class)`

**返回值**: `ObjectMapper` — 配置好的 Jackson 序列化器

**配置项**:

| 配置 | 值 | 说明 |
|------|---|------|
| `LocalDateTime` 序列化/反序列化 | `"yyyy-MM-dd HH:mm:ss"` | 日期时间格式 |
| `LocalDate` 序列化/反序列化 | `"yyyy-MM-dd"` | 日期格式 |
| 时区 | `Asia/Shanghai` | 序列化时区 |
| `FAIL_ON_EMPTY_BEANS` | `false` | 空对象不抛异常 |
| `FAIL_ON_UNKNOWN_PROPERTIES` | `false` | 未知属性不抛异常 |

**条件**: 仅在容器中不存在 `ObjectMapper` Bean 时创建
