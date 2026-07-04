package com.smt.platform.common.config;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * MyBatis-Plus 自动填充处理器（M5）。
 *
 * <p>配合 {@link com.smt.platform.common.entity.BaseEntity} 使用，
 * 在 INSERT/UPDATE 时自动填充 createTime/updateTime/createBy/updateBy/deleted 字段，
 * 消除各 ServiceImpl 中手写时间填充的重复代码。</p>
 *
 * <p>strictInsertFill/strictUpdateFill 仅在字段为 null 时填充，
 * 不会覆盖业务层显式设置的值。</p>
 *
 * <p>createBy/updateBy 当前从 SecurityContext 获取，Phase 2 暂未接入用户上下文，
 * 默认填 "system"；Phase 3 接入 JWT 后改为从 SecurityContext 提取用户名。</p>
 */
@Component
public class MyMetaObjectHandler implements MetaObjectHandler {

    private static final String DEFAULT_OPERATOR = "system";

    @Override
    public void insertFill(MetaObject metaObject) {
        this.strictInsertFill(metaObject, "createTime", LocalDateTime.class, LocalDateTime.now());
        this.strictInsertFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());
        this.strictInsertFill(metaObject, "createBy", String.class, DEFAULT_OPERATOR);
        this.strictInsertFill(metaObject, "updateBy", String.class, DEFAULT_OPERATOR);
        this.strictInsertFill(metaObject, "deleted", Integer.class, 0);
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        this.strictUpdateFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());
        this.strictUpdateFill(metaObject, "updateBy", String.class, DEFAULT_OPERATOR);
    }
}
