package com.smt.platform.device.model.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.io.Serializable;

/**
 * 新增采集点请求体 DTO。
 */
@Data
public class DataPointCreateDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 采集点编码（同一设备下唯一） */
    @NotBlank(message = "采集点编码不能为空")
    private String datapointCode;

    /** 采集点名称 */
    @NotBlank(message = "采集点名称不能为空")
    private String datapointName;

    /** 节点路径（OPC UA NodeId 或 MQTT Topic） */
    @NotBlank(message = "节点路径不能为空")
    private String nodePath;

    /** 数据类型：NUMBER/STRING/BOOLEAN */
    @NotBlank(message = "数据类型不能为空")
    private String dataType;

    /** 采样周期（毫秒，最小 100） */
    @NotNull(message = "采样周期不能为空")
    @Min(value = 100, message = "采样周期不能小于100毫秒")
    private Integer sampleIntervalMs;
}
