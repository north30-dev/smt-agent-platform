package com.smt.platform.device.model.dto;

import lombok.Data;

import java.io.Serializable;

/**
 * 更新设备请求体 DTO。
 *
 * <p>支持部分字段更新，未传字段保持原值；deviceCode 不允许通过本接口修改。</p>
 */
@Data
public class DeviceUpdateDTO implements Serializable {

    private static final long serialVersionUID = 1L;

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

    /** OPC UA 端点 */
    private String opcUaEndpoint;

    /** 设备状态：RUNNING/STOPPED/MAINTENANCE */
    private String status;
}
