package com.smt.platform.device.collect.opcua;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * OPC UA 采样参数配置（P0-6 配置化）。
 *
 * <p>默认值符合 PRD &lt;100ms 契约：</p>
 * <ul>
 *   <li>publishingIntervalMs = 100ms（订阅发布周期）</li>
 *   <li>samplingIntervalMs = 50ms（采样周期）</li>
 *   <li>queueSize = 10（监控项队列大小）</li>
 * </ul>
 *
 * <p>所有参数均可通过环境变量覆盖：SMT_OPCUA_PUBLISHING_INTERVAL_MS / SMT_OPCUA_SAMPLING_INTERVAL_MS / SMT_OPCUA_QUEUE_SIZE。</p>
 */
@Data
@Component
@ConfigurationProperties(prefix = "smt.opcua")
public class OpcUaProperties {

    /** 订阅发布周期（毫秒），默认 100ms，符合 PRD <100ms 契约 */
    private double publishingIntervalMs = 100.0;

    /** 采样周期（毫秒），默认 50ms，符合 PRD <100ms 契约 */
    private double samplingIntervalMs = 50.0;

    /** 监控项队列大小，默认 10 */
    private int queueSize = 10;
}
