package com.smt.platform.device.model.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.io.Serializable;

/**
 * 新增设备请求体 DTO。
 */
@Data
public class DeviceCreateDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 设备编码（全局唯一） */
    @NotBlank(message = "设备编码不能为空")
    private String deviceCode;

    /** 设备名称 */
    @NotBlank(message = "设备名称不能为空")
    private String deviceName;

    /** 设备类型：PRINTER/MOUNTER/REFLOW/AOI/SPI/OTHER */
    @NotBlank(message = "设备类型不能为空")
    private String deviceType;

    /** 所属产线 */
    @NotBlank(message = "所属产线不能为空")
    private String productionLine;

    /** 设备 IP 地址 */
    @NotBlank(message = "设备IP不能为空")
    private String ipAddress;

    /** 通信协议类型：OPC_UA/MQTT */
    @NotBlank(message = "协议类型不能为空")
    private String protocolType;

    /** OPC UA 端点（protocolType=OPC_UA 时必填） */
    private String opcUaEndpoint;

    /** 设备状态：RUNNING/STOPPED/MAINTENANCE */
    @NotBlank(message = "设备状态不能为空")
    private String status;
}
