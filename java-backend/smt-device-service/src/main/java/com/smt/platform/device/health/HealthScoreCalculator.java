package com.smt.platform.device.health;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.smt.platform.device.mapper.DeviceDataMapper;
import com.smt.platform.device.mapper.DeviceMapper;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.model.entity.DeviceData;
import com.smt.platform.device.service.DeviceService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 简易设备健康评分计算器。
 *
 * <p>基于设备状态与最近 5 分钟实时数据按规则计算评分（0-100），
 * 并更新到 device.health_score 字段。</p>
 *
 * <p>m8 改造：11 个硬编码常量与魔法数字抽取到 {@link HealthScoreProperties}，
 * 默认值与原硬编码完全一致，可通过 {@code smt.health.score.*} 配置覆盖。
 * 默认配置下评分结果与原硬编码 100% 等价。</p>
 *
 * <p>Batch 4 改造：{@link #refreshHealthScore} 加 {@link Async} 注解，
 * 异步执行评分重算避免阻塞 MQTT 回调；CallerRunsPolicy 保证队列满时退化为同步执行。</p>
 *
 * <ul>
 *   <li>状态 MAINTENANCE：固定 30 分（默认，可配置）</li>
 *   <li>状态 STOPPED：固定 50 分（默认，可配置）</li>
 *   <li>状态 RUNNING：基础 100 分，按最近 5 分钟数据扣分
 *     <ul>
 *       <li>采集点 code 含 "temp"/"temperature"：value &gt; 80 扣 20，&gt; 100 扣 40</li>
 *       <li>采集点 code 含 "vibration"/"vib"：value &gt; 10 扣 20，&gt; 20 扣 40</li>
 *       <li>同一采集点仅取最近一条（timestamp 最大）参与计算，避免重复扣分</li>
 *     </ul>
 *   </li>
 * </ul>
 * <p>评分下限 0、上限 100；value 非数字时忽略，不扣分。</p>
 */
@Component
public class HealthScoreCalculator {

    private static final Logger log = LoggerFactory.getLogger(HealthScoreCalculator.class);

    private final DeviceService deviceService;
    private final DeviceMapper deviceMapper;
    private final DeviceDataMapper deviceDataMapper;
    private final HealthScoreProperties props;

    public HealthScoreCalculator(DeviceService deviceService,
                                 DeviceMapper deviceMapper,
                                 DeviceDataMapper deviceDataMapper,
                                 HealthScoreProperties props) {
        this.deviceService = deviceService;
        this.deviceMapper = deviceMapper;
        this.deviceDataMapper = deviceDataMapper;
        this.props = props;
    }

    /**
     * 刷新指定设备的健康评分：取设备 → 取最近 5 分钟数据 → 计算评分 → 更新 device.health_score。
     *
     * <p>设备不存在时直接返回并记录日志，不抛异常。</p>
     *
     * @param deviceId 设备 ID
     */
    @Async("healthScoreExecutor")
    public void refreshHealthScore(Long deviceId) {
        // P0-1 后 getById 走 MyBatis-Plus 默认实现，设备不存在时返回 null（不抛 BizException）
        Device device = deviceService.getById(deviceId);
        if (device == null) {
            log.warn("健康评分计算跳过：设备不存在 deviceId={}", deviceId);
            return;
        }

        LocalDateTime since = LocalDateTime.now().minusMinutes(props.getRecentWindowMinutes());
        List<DeviceData> recentData = deviceDataMapper.selectList(new LambdaQueryWrapper<DeviceData>()
                .eq(DeviceData::getDeviceId, deviceId)
                .ge(DeviceData::getTimestamp, since));

        int score = calculate(device, recentData);

        // 仅含 id + healthScore 的实体更新，避免覆盖其他字段
        Device update = new Device();
        update.setId(deviceId);
        update.setHealthScore(score);
        deviceMapper.updateById(update);
        log.debug("健康评分已更新 deviceId={}, score={}, status={}", deviceId, score, device.getStatus());
    }

    /**
     * 按规则计算设备健康评分（0-100），便于单测。
     *
     * @param device     设备（含 status）
     * @param recentData 最近时间窗内的实时数据（可为 null 或空）
     * @return 评分 [0,100]
     */
    public int calculate(Device device, List<DeviceData> recentData) {
        if (device == null) {
            return props.getScoreMin();
        }
        String status = device.getStatus();
        if ("MAINTENANCE".equals(status)) {
            return props.getScoreMaintenance();
        }
        if ("STOPPED".equals(status)) {
            return props.getScoreStopped();
        }
        // RUNNING 及其它未知状态均按 RUNNING 规则处理（基础 100 扣分）

        // 同一采集点取最近一条（timestamp 最大）参与计算，避免重复扣分
        Map<String, DeviceData> latestByCode = new HashMap<>();
        if (recentData != null) {
            for (DeviceData d : recentData) {
                String code = d.getDatapointCode();
                if (code == null) {
                    continue;
                }
                DeviceData exist = latestByCode.get(code);
                if (exist == null) {
                    latestByCode.put(code, d);
                } else if (isAfter(d.getTimestamp(), exist.getTimestamp())) {
                    latestByCode.put(code, d);
                }
            }
        }

        int score = props.getBaseScore();
        for (DeviceData d : latestByCode.values()) {
            String code = d.getDatapointCode().toLowerCase();
            Double n = tryParseDouble(d.getValue());
            if (n == null) {
                continue;
            }
            if (code.contains("temp") || code.contains("temperature")) {
                if (n > props.getTempThresholdHigh()) {
                    score -= props.getDeductionHigh();
                } else if (n > props.getTempThresholdLow()) {
                    score -= props.getDeductionLow();
                }
            } else if (code.contains("vibration") || code.contains("vib")) {
                if (n > props.getVibThresholdHigh()) {
                    score -= props.getDeductionHigh();
                } else if (n > props.getVibThresholdLow()) {
                    score -= props.getDeductionLow();
                }
            }
        }

        return Math.max(props.getScoreMin(), Math.min(props.getScoreMax(), score));
    }

    /**
     * 判断 cur 是否晚于 exist（null 视为最早）。
     */
    private static boolean isAfter(LocalDateTime cur, LocalDateTime exist) {
        if (cur == null) {
            return false;
        }
        return exist == null || cur.isAfter(exist);
    }

    /**
     * 安全解析字符串为 double，无法解析返回 null。
     */
    private static Double tryParseDouble(String s) {
        if (s == null || s.isEmpty()) {
            return null;
        }
        try {
            return Double.parseDouble(s.trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
