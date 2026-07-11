# BaseEntity

> 实体基类，提供审计字段（创建时间/更新时间/操作人）和软删除支持，所有实体类应继承此类。

**包路径**: `com.smt.platform.common.entity`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/entity/BaseEntity.java`

---

## 类签名

```java
@Getter
@Setter
public abstract class BaseEntity implements Serializable
```

**父类**: `Object`
**实现接口**: `Serializable`
**修饰符**: `abstract`

---

## 字段

| 字段 | 类型 | 修饰符 | MyBatis-Plus 注解 | 说明 |
|------|------|--------|-------------------|------|
| `serialVersionUID` | `long` | `private static final` | — | 序列化版本号，值为 `1L` |
| `createTime` | `LocalDateTime` | `private` | `@TableField(fill = FieldFill.INSERT)` | 创建时间，INSERT 时自动填充 |
| `updateTime` | `LocalDateTime` | `private` | `@TableField(fill = FieldFill.INSERT_UPDATE)` | 更新时间，INSERT 和 UPDATE 时自动填充 |
| `createBy` | `String` | `private` | `@TableField(fill = FieldFill.INSERT)` | 创建人，INSERT 时自动填充 |
| `updateBy` | `String` | `private` | `@TableField(fill = FieldFill.INSERT_UPDATE)` | 更新人，INSERT 和 UPDATE 时自动填充 |
| `deleted` | `Integer` | `private` | `@TableLogic`, `@TableField(fill = FieldFill.INSERT)` | 软删除标记（0=正常, 1=已删除） |

---

## Lombok 生成方法

- `getCreateTime()` / `setCreateTime(LocalDateTime)`
- `getUpdateTime()` / `setUpdateTime(LocalDateTime)`
- `getCreateBy()` / `setCreateBy(String)`
- `getUpdateBy()` / `setUpdateBy(String)`
- `getDeleted()` / `setDeleted(Integer)`

---

## 注意事项

- `@TableLogic` 注解使 MyBatis-Plus 自动将 `SELECT` 转为 `WHERE deleted=0`，`DELETE` 转为 `UPDATE deleted=1`
- 自动填充逻辑由 `MyMetaObjectHandler` 实现
- 继承此类的实体需配合 `@TableName` 注解使用
