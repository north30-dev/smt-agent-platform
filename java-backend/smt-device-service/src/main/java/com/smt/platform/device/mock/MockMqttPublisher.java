package com.smt.platform.device.mock;

import com.smt.platform.device.collect.mqtt.MqttSubscriberManager;
import com.smt.platform.device.config.MockProperties;
import com.smt.platform.device.config.MockProperties.MockDevice;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;

/**
 * Mock MQTT 数据生成器。
 *
 * <p>当 {@code smt.mock.enabled=true} 时，启动一个 {@link ScheduledExecutorService}，
 * 按 {@code smt.mock.interval-ms} 周期向配置的 MQTT topic 发布模拟设备数据
 * （{@code {"value":"<随机值>","timestamp":"<ISO-8601>"}}），便于无真实设备环境下演示。
 * {@code smt.mock.enabled=false} 时不启动调度，零开销。</p>
 *
 * <p>通过复用 {@link MqttSubscriberManager#publish} 发布消息，与订阅端共享同一 broker 连接。
 * 使用 {@code @Order(20)} 确保在 {@link com.smt.platform.device.collect.MqttDataCollector}
 * 完成订阅后再开始发布。</p>
 */
@Slf4j
@Component
@Order(20)
public class MockMqttPublisher implements ApplicationRunner {

    private final MockProperties mockProperties;
    private final MqttSubscriberManager mqttSubscriberManager;

    private ScheduledExecutorService scheduler;

    public MockMqttPublisher(MockProperties mockProperties,
                             MqttSubscriberManager mqttSubscriberManager) {
        this.mockProperties = mockProperties;
        this.mqttSubscriberManager = mqttSubscriberManager;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (!mockProperties.isEnabled()) {
            log.info("Mock 数据生成器未启用 (smt.mock.enabled=false)");
            return;
        }
        start();
    }

    /**
     * 启动周期发布调度。首条消息在一个周期后发布，留出订阅建立时间。
     */
    public void start() {
        List<MockDevice> devices = mockProperties.getDevices();
        if (devices == null || devices.isEmpty()) {
            log.warn("Mock 数据生成器已启用但无模拟设备配置，跳过启动");
            return;
        }
        long intervalMs = mockProperties.getIntervalMs();
        if (intervalMs <= 0) {
            intervalMs = 5000L;
        }
        scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "mock-mqtt-publisher");
            t.setDaemon(true);
            return t;
        });
        scheduler.scheduleAtFixedRate(this::publishAll, intervalMs, intervalMs, TimeUnit.MILLISECONDS);
        log.info("Mock 数据生成器已启动 周期={}ms 模拟采集点数={}", intervalMs, devices.size());
    }

    /**
     * 单轮发布：遍历所有模拟设备采集点，生成数据并发布。
     * 单条发布失败仅记日志，不影响后续发布。
     */
    private void publishAll() {
        for (MockDevice device : mockProperties.getDevices()) {
            try {
                String value = generateValue(device.getDatapointCode());
                String timestamp = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
                String payload = "{\"value\":\"" + value + "\",\"timestamp\":\"" + timestamp + "\"}";
                mqttSubscriberManager.publish(device.getTopic(), payload);
            } catch (Exception e) {
                log.error("Mock 数据发布失败 deviceId={} topic={} 原因={}",
                        device.getDeviceId(), device.getTopic(), e.getMessage(), e);
            }
        }
    }

    /**
     * 根据采集点编码生成模拟值。
     * <ul>
     *   <li>温度类（datapointCode 含 temp，不区分大小写）：随机 60-95</li>
     *   <li>振动类（含 vibration/vib）：随机 5-25</li>
     *   <li>其他：随机 0-100</li>
     * </ul>
     * 包级可见以便单元测试验证取值范围。
     *
     * @param datapointCode 采集点编码
     * @return 字符串形式的随机值
     */
    String generateValue(String datapointCode) {
        if (datapointCode == null || datapointCode.isBlank()) {
            return String.valueOf(ThreadLocalRandom.current().nextInt(0, 101));
        }
        String lower = datapointCode.toLowerCase();
        if (lower.contains("temp")) {
            return String.valueOf(ThreadLocalRandom.current().nextInt(60, 96));
        }
        if (lower.contains("vibration") || lower.contains("vib")) {
            return String.valueOf(ThreadLocalRandom.current().nextInt(5, 26));
        }
        return String.valueOf(ThreadLocalRandom.current().nextInt(0, 101));
    }

    /**
     * 关闭调度器，避免线程泄漏。
     */
    @PreDestroy
    public void stop() {
        if (scheduler != null && !scheduler.isShutdown()) {
            scheduler.shutdown();
            log.info("Mock 数据生成器调度器已关闭");
        }
    }
}
