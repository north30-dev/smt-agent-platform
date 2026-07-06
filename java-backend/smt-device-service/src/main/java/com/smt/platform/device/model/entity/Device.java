package com.smt.platform.device.model.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.smt.platform.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 设备实体（对应 device 表）。
 *
 * <p>字段与 OpenAPI 的 Device schema 对齐。</p>
 *
 * <p>M5 改造：继承 {@link BaseEntity}，统一 createTime/updateTime/createBy/updateBy/deleted
 * 字段由 {@link com.smt.platform.common.config.MyMetaObjectHandler} 自动填充，
 * 不再在 ServiceImpl 中手写时间戳。</p>
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("device")
public class Device extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 设备 ID */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 设备编码（全局唯一） */
    private String deviceCode;

    /** 设备名称 */
    private String deviceName;

    /** 设备类型：PRINTER/MOUNTER/REFLOW/AOI/SPI/OTHER */
    private String deviceType;

    /** 所属产线 */
    private String productionLine;

    /** 设备 IP 地址 */
    private String ipAddress;

    /** 通信协议类型：OPC_UA/MQTT */
    private String protocolType;

    /** OPC UA 端点（仅 protocolType=OPC_UA 时使用） */
    private String opcUaEndpoint;

    /** 设备状态：RUNNING/STOPPED/MAINTENANCE */
    private String status;

    /** 健康评分（0-100，分数越高越健康） */
    private Integer healthScore;
}
