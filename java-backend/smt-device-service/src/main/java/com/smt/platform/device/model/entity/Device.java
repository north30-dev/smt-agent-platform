package com.smt.platform.device.model.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 设备实体（对应 device 表）。
 *
 * <p>字段与 OpenAPI 的 Device schema 对齐。</p>
 */
@Data
@TableName("device")
public class Device implements Serializable {

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

    /** 软删除标记：0-未删除，1-已删除 */
    @TableLogic
    private Integer deleted;

    /** 创建时间 */
    private LocalDateTime createTime;

    /** 最近更新时间 */
    private LocalDateTime updateTime;
}
