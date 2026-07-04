package com.smt.platform.common.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableLogic;
import lombok.Getter;
import lombok.Setter;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 实体基类（M5）：统一 createTime/updateTime/createBy/updateBy/deleted 字段，
 * 配合 {@link com.smt.platform.common.config.MyMetaObjectHandler} 实现自动填充。
 *
 * <p>子类继承本类后，无需再声明这五个字段。DB 表必须具备对应列
 * （device 表已具备；device_data_point/device_data 表缺列，不继承本类）。</p>
 *
 * <p>字段填充策略：</p>
 * <ul>
 *   <li>createTime/createBy/deleted：仅 INSERT 时填充</li>
 *   <li>updateTime/updateBy：INSERT 与 UPDATE 均填充</li>
 *   <li>deleted：逻辑删除标记，{@link TableLogic} 自动转换为 update deleted=1</li>
 * </ul>
 */
@Getter
@Setter
public abstract class BaseEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 创建时间（INSERT 自动填充） */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /** 最近更新时间（INSERT/UPDATE 自动填充） */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    /** 创建人（INSERT 自动填充，Phase 2 暂用 "system"） */
    @TableField(fill = FieldFill.INSERT)
    private String createBy;

    /** 更新人（INSERT/UPDATE 自动填充，Phase 2 暂用 "system"） */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private String updateBy;

    /** 逻辑删除标记：0-未删除，1-已删除（INSERT 自动填充为 0） */
    @TableLogic
    @TableField(fill = FieldFill.INSERT)
    private Integer deleted;
}
