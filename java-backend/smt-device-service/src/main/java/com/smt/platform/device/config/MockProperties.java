package com.smt.platform.device.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * Mock 数据生成器配置（绑定 smt.mock 前缀）。
 *
 * <p>{@code smt.mock.enabled=false} 时 {@link com.smt.platform.device.mock.MockMqttPublisher}
 * 不启动调度，零开销。</p>
 */
@Data
@Component
@ConfigurationProperties(prefix = "smt.mock")
public class MockProperties {

    /** 是否启用 Mock 数据生成（默认 false） */
    private boolean enabled = false;

    /** 发布周期（毫秒），默认 5000 */
    private long intervalMs = 5000L;

    /** 模拟设备与采集点列表 */
    private List<MockDevice> devices = new ArrayList<>();

    /**
     * 单个模拟采集点配置（扁平结构：deviceId + datapointCode + topic）。
     */
    @Data
    public static class MockDevice {

        /** 设备 ID */
        private Long deviceId;

        /** 采集点编码 */
        private String datapointCode;

        /** MQTT topic */
        private String topic;
    }
}
