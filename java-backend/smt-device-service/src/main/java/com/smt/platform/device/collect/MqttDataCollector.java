package com.smt.platform.device.collect;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.smt.platform.device.collect.mqtt.MqttSubscriberManager;
import com.smt.platform.device.health.HealthScoreCalculator;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.model.entity.DeviceDataPoint;
import com.smt.platform.device.service.DeviceDataPointService;
import com.smt.platform.device.service.DeviceDataService;
import com.smt.platform.device.service.DeviceService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * MQTT 设备数据采集器。
 *
 * <p>应用启动时遍历所有 protocolType=MQTT 且未删除的设备，按采集点配置
 * （nodePath 即 MQTT topic）订阅，消息到达时解析 payload 为统一数据点格式
 * 并调用 {@link DeviceDataService#saveData} 写入实时数据。</p>
 *
 * <p>单台设备/单个 topic 订阅失败仅记录日志，不影响其他设备。数据写入后异步触发
 * 健康评分刷新，评分失败仅记日志，不影响数据存储主流程。</p>
 *
 * <p>使用 {@code @Order(10)} 确保在 {@link com.smt.platform.device.mock.MockMqttPublisher}
 * 之前完成订阅，避免 Mock 首轮发布丢失。</p>
 */
@Slf4j
@Component
@Order(10)
public class MqttDataCollector implements ApplicationRunner {

    /** MQTT 协议类型标识（与 Device.protocolType 取值对齐） */
    private static final String PROTOCOL_MQTT = "MQTT";

    private final DeviceService deviceService;
    private final DeviceDataPointService deviceDataPointService;
    private final DeviceDataService deviceDataService;
    private final MqttSubscriberManager mqttSubscriberManager;
    private final HealthScoreCalculator healthScoreCalculator;

    public MqttDataCollector(DeviceService deviceService,
                             DeviceDataPointService deviceDataPointService,
                             DeviceDataService deviceDataService,
                             MqttSubscriberManager mqttSubscriberManager,
                             HealthScoreCalculator healthScoreCalculator) {
        this.deviceService = deviceService;
        this.deviceDataPointService = deviceDataPointService;
        this.deviceDataService = deviceDataService;
        this.mqttSubscriberManager = mqttSubscriberManager;
        this.healthScoreCalculator = healthScoreCalculator;
    }

    @Override
    public void run(ApplicationArguments args) {
        startSubscriptions();
    }

    /**
     * 启动时为所有 MQTT 设备建立订阅。
     */
    public void startSubscriptions() {
        // Device.deleted 带 @TableLogic，list 自动过滤已删除设备
        List<Device> devices = deviceService.list(new LambdaQueryWrapper<Device>()
                .eq(Device::getProtocolType, PROTOCOL_MQTT));
        if (devices == null || devices.isEmpty()) {
            log.info("无 MQTT 设备需要订阅，跳过采集器初始化");
            return;
        }
        log.info("开始建立 MQTT 订阅，待订阅设备数={}", devices.size());
        for (Device device : devices) {
            try {
                subscribeOneDevice(device);
            } catch (Exception e) {
                // 单台设备订阅失败不影响其他设备
                log.error("设备 MQTT 订阅失败 deviceId={} deviceCode={} 原因={}",
                        device.getId(), device.getDeviceCode(), e.getMessage(), e);
            }
        }
    }

    /**
     * 为单台设备建立 MQTT 订阅（逐采集点订阅）。
     */
    private void subscribeOneDevice(Device device) {
        Long deviceId = device.getId();
        List<DeviceDataPoint> points = deviceDataPointService.listByDeviceId(deviceId);
        if (points == null || points.isEmpty()) {
            log.warn("设备无采集点，跳过 MQTT 订阅 deviceId={} deviceCode={}",
                    deviceId, device.getDeviceCode());
            return;
        }
        for (DeviceDataPoint point : points) {
            String topic = point.getNodePath();
            String datapointCode = point.getDatapointCode();
            if (topic == null || topic.isBlank()) {
                log.warn("采集点 nodePath(topic) 为空，跳过 deviceId={} datapointCode={}",
                        deviceId, datapointCode);
                continue;
            }
            try {
                subscribeOnePoint(deviceId, topic, datapointCode);
            } catch (Exception e) {
                // 单个采集点订阅失败不影响同设备其他采集点
                log.error("MQTT 单采集点订阅失败 deviceId={} topic={} 原因={}",
                        deviceId, topic, e.getMessage(), e);
            }
        }
    }

    /**
     * 订阅单个采集点：注册回调，消息到达时解析 payload 并写入实时数据。
     */
    private void subscribeOnePoint(Long deviceId, String topic, String datapointCode) {
        mqttSubscriberManager.subscribe(topic, deviceId, datapointCode, (code, payload) -> {
            MqttSubscriberManager.ParsedPayload parsed = mqttSubscriberManager.parsePayload(payload);
            deviceDataService.saveData(deviceId, code, parsed.value, parsed.timestamp);
            // 数据写入后刷新健康评分；评分失败仅记日志，不影响数据存储主流程
            try {
                healthScoreCalculator.refreshHealthScore(deviceId);
            } catch (Exception ex) {
                log.warn("MQTT 数据写入后刷新健康评分失败 deviceId={} topic={} 原因={}",
                        deviceId, topic, ex.getMessage(), ex);
            }
        });
    }
}
