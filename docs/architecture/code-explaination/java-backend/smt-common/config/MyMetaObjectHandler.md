# MyMetaObjectHandler

> MyBatis-Plus 自动填充处理器，在 INSERT 和 UPDATE 操作时自动填充审计字段。

**包路径**: `com.smt.platform.common.config`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/config/MyMetaObjectHandler.java`

---

## 类签名

```java
@Component
public class MyMetaObjectHandler implements MetaObjectHandler
```

**父类**: `Object`
**实现接口**: `com.baomidou.mybatisplus.core.handlers.MetaObjectHandler`
**Spring 注解**: `@Component`

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `DEFAULT_OPERATOR` | `String` | `private static final` | 默认操作人，值为 `"system"`（待 JWT 用户上下文接入后替换） |

---

## 方法

### `insertFill(MetaObject metaObject)`

> INSERT 操作时自动填充 5 个字段

**签名**: `public void insertFill(MetaObject metaObject)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `metaObject` | `MetaObject` | MyBatis-Plus 元对象 |

**填充逻辑**:

| 字段 | 填充值 | 填充条件 |
|------|--------|---------|
| `createTime` | `LocalDateTime.now()` | 字段为 null 时 |
| `updateTime` | `LocalDateTime.now()` | 字段为 null 时 |
| `createBy` | `"system"` | 字段为 null 时 |
| `updateBy` | `"system"` | 字段为 null 时 |
| `deleted` | `0` | 字段为 null 时 |

**实现**: 使用 `strictInsertFill`，仅在字段当前值为 null 时填充

---

### `updateFill(MetaObject metaObject)`

> UPDATE 操作时自动填充 2 个字段

**签名**: `public void updateFill(MetaObject metaObject)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `metaObject` | `MetaObject` | MyBatis-Plus 元对象 |

**填充逻辑**:

| 字段 | 填充值 | 填充条件 |
|------|--------|---------|
| `updateTime` | `LocalDateTime.now()` | 字段为 null 时 |
| `updateBy` | `"system"` | 字段为 null 时 |

**实现**: 使用 `strictUpdateFill`，仅在字段当前值为 null 时填充
