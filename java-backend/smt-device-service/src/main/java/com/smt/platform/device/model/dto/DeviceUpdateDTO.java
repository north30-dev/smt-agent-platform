package com.smt.platform.device.model.dto;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.io.Serializable;

/**
 * 更新设备请求体 DTO。
 *
 * <p>支持部分字段更新，未传字段保持原值；deviceCode 不允许通过本接口修改。</p>
 *
 * <p>M3 修复：字段全部可选（部分更新语义），不加 {@code @NotBlank}/@NotNull，
 * 仅约束格式（长度 + 枚举值合法）。{@code opcUaEndpoint} 与 {@code protocolType}
 * 联动校验用 {@code @AssertTrue}。</p>
 */
@Data
public class DeviceUpdateDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 设备名称 */
    @Size(max = 128, message = "设备名称长度不能超过128个字符")
    private String deviceName;

    /** 设备类型：PRINTER/MOUNTER/REFLOW/AOI/SPI/OTHER */
    @Pattern(regexp = "PRINTER|MOUNTER|REFLOW|AOI|SPI|OTHER", message = "设备类型必须为 PRINTER/MOUNTER/REFLOW/AOI/SPI/OTHER 之一")
    @Size(max = 32, message = "设备类型长度不能超过32个字符")
    private String deviceType;

    /** 所属产线 */
    @Size(max = 32, message = "所属产线长度不能超过32个字符")
    private String productionLine;

    /** 设备 IP 地址 */
    @Size(max = 64, message = "设备IP长度不能超过64个字符")
    private String ipAddress;

    /** 通信协议类型：OPC_UA/MQTT */
    @Pattern(regexp = "OPC_UA|MQTT", message = "协议类型必须为 OPC_UA 或 MQTT")
    @Size(max = 16, message = "协议类型长度不能超过16个字符")
    private String protocolType;

    /** OPC UA 端点 */
    @Size(max = 256, message = "OPC UA端点长度不能超过256个字符")
    private String opcUaEndpoint;

    /** 设备状态：RUNNING/STOPPED/MAINTENANCE */
    @Pattern(regexp = "RUNNING|STOPPED|MAINTENANCE", message = "设备状态必须为 RUNNING/STOPPED/MAINTENANCE 之一")
    @Size(max = 16, message = "设备状态长度不能超过16个字符")
    private String status;

    /**
     * 联动校验：protocolType=OPC_UA 时 opcUaEndpoint 必填。
     *
     * <p>部分更新语义：protocolType 为 null 时不校验（表示不更新该字段）；
     * protocolType=OPC_UA 且 opcUaEndpoint 也传了时才校验非空。</p>
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
