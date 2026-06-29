package com.smt.platform.device.model.dto;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.io.Serializable;

/**
 * 新增设备请求体 DTO。
 *
 * <p>M3 修复：所有 String 字段加 {@code @Size} 对齐 init.sql 列长度；
 * 枚举字段（deviceType/protocolType/status）加 {@code @Pattern} 约束合法取值；
 * {@code opcUaEndpoint} 与 {@code protocolType} 联动校验用 {@code @AssertTrue}。</p>
 */
@Data
public class DeviceCreateDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 设备编码（全局唯一） */
    @NotBlank(message = "设备编码不能为空")
    @Size(max = 64, message = "设备编码长度不能超过64个字符")
    private String deviceCode;

    /** 设备名称 */
    @NotBlank(message = "设备名称不能为空")
    @Size(max = 128, message = "设备名称长度不能超过128个字符")
    private String deviceName;

    /** 设备类型：PRINTER/MOUNTER/REFLOW/AOI/SPI/OTHER */
    @NotBlank(message = "设备类型不能为空")
    @Pattern(regexp = "PRINTER|MOUNTER|REFLOW|AOI|SPI|OTHER", message = "设备类型必须为 PRINTER/MOUNTER/REFLOW/AOI/SPI/OTHER 之一")
    @Size(max = 32, message = "设备类型长度不能超过32个字符")
    private String deviceType;

    /** 所属产线 */
    @NotBlank(message = "所属产线不能为空")
    @Size(max = 32, message = "所属产线长度不能超过32个字符")
    private String productionLine;

    /** 设备 IP 地址 */
    @NotBlank(message = "设备IP不能为空")
    @Size(max = 64, message = "设备IP长度不能超过64个字符")
    private String ipAddress;

    /** 通信协议类型：OPC_UA/MQTT */
    @NotBlank(message = "协议类型不能为空")
    @Pattern(regexp = "OPC_UA|MQTT", message = "协议类型必须为 OPC_UA 或 MQTT")
    @Size(max = 16, message = "协议类型长度不能超过16个字符")
    private String protocolType;

    /** OPC UA 端点（protocolType=OPC_UA 时必填） */
    @Size(max = 256, message = "OPC UA端点长度不能超过256个字符")
    private String opcUaEndpoint;

    /** 设备状态：RUNNING/STOPPED/MAINTENANCE */
    @NotBlank(message = "设备状态不能为空")
    @Pattern(regexp = "RUNNING|STOPPED|MAINTENANCE", message = "设备状态必须为 RUNNING/STOPPED/MAINTENANCE 之一")
    @Size(max = 16, message = "设备状态长度不能超过16个字符")
    private String status;

    /**
     * 联动校验：protocolType=OPC_UA 时 opcUaEndpoint 必填。
     *
     * <p>JSR-380 要求布尔校验方法名以 is/has 开头；
     * {@code @JsonIgnore} 防止该方法被当作属性序列化到响应体。</p>
     *
     * @return 校验通过返回 true
     */
    @AssertTrue(message = "protocolType=OPC_UA 时 opcUaEndpoint 不能为空")
    @JsonIgnore
    public boolean isOpcUaEndpointRequired() {
        if (protocolType == null) {
            return true;
        }
        if ("OPC_UA".equals(protocolType)) {
            return opcUaEndpoint != null && !opcUaEndpoint.trim().isEmpty();
        }
        return true;
    }
}
