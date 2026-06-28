package com.smt.platform.device.model.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 设备数据点（历史值）实体（对应 device_data 表）。
 */
@Data
@TableName("device_data")
public class DeviceData implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 数据记录 ID */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 设备 ID */
    private Long deviceId;

    /** 采集点编码 */
    private String datapointCode;

    /** 数据值（统一用 String 传输，前端按 dataType 转换） */
    private String value;

    /** 数据采集时间 */
    @TableField("timestamp")
    private LocalDateTime timestamp;
}
