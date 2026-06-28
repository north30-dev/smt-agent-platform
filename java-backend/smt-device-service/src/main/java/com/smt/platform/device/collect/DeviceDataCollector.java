package com.smt.platform.device.collect;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.smt.platform.device.collect.opcua.OpcUaSubscriber;
import com.smt.platform.device.health.HealthScoreCalculator;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.model.entity.DeviceDataPoint;
import com.smt.platform.device.service.DeviceDataPointService;
import com.smt.platform.device.service.DeviceDataService;
import com.smt.platform.device.service.DeviceService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 设备数据采集器。
 *
 * <p>应用启动时遍历所有 protocolType=OPC_UA 且未删除的设备，按采集点配置
 * （nodePath 即 OPC UA NodeId）建立订阅，节点值变化时回调
 * {@link DeviceDataService#saveData} 写入实时数据。</p>
 *
 * <p>单台设备订阅失败仅记录日志，不影响其他设备。数据写入后异步触发健康评分刷新，
 * 评分失败仅记日志，不影响数据存储主流程。</p>
 */
@Component
public class DeviceDataCollector implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(DeviceDataCollector.class);

    /** OPC UA 协议类型标识（与 Device.protocolType 取值对齐） */
    private static final String PROTOCOL_OPC_UA = "OPC_UA";

    private final DeviceService deviceService;
    private final DeviceDataPointService deviceDataPointService;
    private final DeviceDataService deviceDataService;
    private final OpcUaSubscriber opcUaSubscriber;
    private final HealthScoreCalculator healthScoreCalculator;

    public DeviceDataCollector(DeviceService deviceService,
                               DeviceDataPointService deviceDataPointService,
                               DeviceDataService deviceDataService,
                               OpcUaSubscriber opcUaSubscriber,
                               HealthScoreCalculator healthScoreCalculator) {
        this.deviceService = deviceService;
        this.deviceDataPointService = deviceDataPointService;
        this.deviceDataService = deviceDataService;
        this.opcUaSubscriber = opcUaSubscriber;
        this.healthScoreCalculator = healthScoreCalculator;
    }

    @Override
    public void run(ApplicationArguments args) {
        startSubscriptions();
    }

    /**
     * 启动时为所有 OPC_UA 设备建立订阅。
     */
    public void startSubscriptions() {
        // Device.deleted 带 @TableLogic，list 自动过滤已删除设备
        List<Device> devices = deviceService.list(new LambdaQueryWrapper<Device>()
                .eq(Device::getProtocolType, PROTOCOL_OPC_UA));
        if (devices == null || devices.isEmpty()) {
            log.info("无 OPC_UA 设备需要订阅，跳过采集器初始化");
            return;
        }
        log.info("开始建立 OPC UA 订阅，待订阅设备数={}", devices.size());
        for (Device device : devices) {
            try {
                subscribeOneDevice(device);
            } catch (Exception e) {
                // 单台设备订阅失败不影响其他设备
                log.error("设备 OPC UA 订阅失败 deviceId={} deviceCode={} 原因={}",
                        device.getId(), device.getDeviceCode(), e.getMessage(), e);
            }
        }
    }

    /**
     * 为单台设备建立 OPC UA 订阅。
     */
    private void subscribeOneDevice(Device device) {
        Long deviceId = device.getId();
        String endpoint = device.getOpcUaEndpoint();
        List<DeviceDataPoint> points = deviceDataPointService.listByDeviceId(deviceId);
        if (points == null || points.isEmpty()) {
            log.warn("设备无采集点，跳过 OPC UA 订阅 deviceId={} deviceCode={}",
                    deviceId, device.getDeviceCode());
            return;
        }

        // 保持插入顺序，与 createMonitoredItems 请求顺序对齐
        Map<String, String> nodeIdToCode = new LinkedHashMap<>();
        for (DeviceDataPoint point : points) {
            String nodePath = point.getNodePath();
            if (nodePath == null || nodePath.isBlank()) {
                log.warn("采集点 nodePath 为空，跳过 deviceId={} datapointCode={}",
                        deviceId, point.getDatapointCode());
                continue;
            }
            nodeIdToCode.put(nodePath, point.getDatapointCode());
        }
        if (nodeIdToCode.isEmpty()) {
            log.warn("设备无有效采集点（nodePath 均为空），跳过 deviceId={}", deviceId);
            return;
        }

        opcUaSubscriber.subscribe(endpoint, nodeIdToCode, deviceId, (datapointCode, value) -> {
            deviceDataService.saveData(deviceId, datapointCode, value, LocalDateTime.now());
            // 数据写入后刷新健康评分；评分失败仅记日志，不影响数据存储主流程
            try {
                healthScoreCalculator.refreshHealthScore(deviceId);
            } catch (Exception ex) {
                log.warn("OPC UA 数据写入后刷新健康评分失败 deviceId={} 原因={}",
                        deviceId, ex.getMessage(), ex);
            }
        });
    }
}
