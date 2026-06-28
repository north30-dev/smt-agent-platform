package com.smt.platform.device.model.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 设备采集点实体（对应 device_data_point 表）。
 */
@Data
@TableName("device_data_point")
public class DeviceDataPoint implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 采集点 ID */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 所属设备 ID */
    private Long deviceId;

    /** 采集点编码（同一设备下唯一） */
    private String datapointCode;

    /** 采集点名称 */
    private String datapointName;

    /** 节点路径（OPC UA NodeId 或 MQTT Topic） */
    private String nodePath;

    /** 数据类型：NUMBER/STRING/BOOLEAN */
    private String dataType;

    /** 采样周期（毫秒） */
    private Integer sampleIntervalMs;

    /** 创建时间 */
    private LocalDateTime createTime;
}
