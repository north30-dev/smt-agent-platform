package com.smt.platform.device.health;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.smt.platform.common.exception.BizException;
import com.smt.platform.device.mapper.DeviceDataMapper;
import com.smt.platform.device.mapper.DeviceMapper;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.model.entity.DeviceData;
import com.smt.platform.device.service.DeviceService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
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
 * <ul>
 *   <li>状态 MAINTENANCE：固定 30 分</li>
 *   <li>状态 STOPPED：固定 50 分</li>
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

    /** 维修态固定评分 */
    private static final int SCORE_MAINTENANCE = 30;
    /** 停机态固定评分 */
    private static final int SCORE_STOPPED = 50;
    /** 运行态基础评分 */
    private static final int BASE_SCORE = 100;
    /** 评分上限 */
    private static final int SCORE_MAX = 100;
    /** 评分下限 */
    private static final int SCORE_MIN = 0;
    /** 最近数据时间窗（分钟） */
    private static final long RECENT_WINDOW_MINUTES = 5L;

    /** 温度一级阈值（>80 扣 20） */
    private static final double TEMP_THRESHOLD_LOW = 80.0;
    /** 温度二级阈值（>100 扣 40） */
    private static final double TEMP_THRESHOLD_HIGH = 100.0;
    /** 振动一级阈值（>10 扣 20） */
    private static final double VIB_THRESHOLD_LOW = 10.0;
    /** 振动二级阈值（>20 扣 40） */
    private static final double VIB_THRESHOLD_HIGH = 20.0;

    private final DeviceService deviceService;
    private final DeviceMapper deviceMapper;
    private final DeviceDataMapper deviceDataMapper;

    public HealthScoreCalculator(DeviceService deviceService,
                                 DeviceMapper deviceMapper,
                                 DeviceDataMapper deviceDataMapper) {
        this.deviceService = deviceService;
        this.deviceMapper = deviceMapper;
        this.deviceDataMapper = deviceDataMapper;
    }

    /**
     * 刷新指定设备的健康评分：取设备 → 取最近 5 分钟数据 → 计算评分 → 更新 device.health_score。
     *
     * <p>设备不存在时直接返回并记录日志，不抛异常。</p>
     *
     * @param deviceId 设备 ID
     */
    public void refreshHealthScore(Long deviceId) {
        Device device;
        try {
            device = deviceService.getById(deviceId);
        } catch (BizException e) {
            // DeviceService.getById 在设备不存在时抛 BizException，视为设备不存在
            log.warn("健康评分计算跳过：设备不存在 deviceId={}", deviceId);
            return;
        }
        if (device == null) {
            log.warn("健康评分计算跳过：设备不存在 deviceId={}", deviceId);
            return;
        }

        LocalDateTime since = LocalDateTime.now().minusMinutes(RECENT_WINDOW_MINUTES);
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
            return SCORE_MIN;
        }
        String status = device.getStatus();
        if ("MAINTENANCE".equals(status)) {
            return SCORE_MAINTENANCE;
        }
        if ("STOPPED".equals(status)) {
            return SCORE_STOPPED;
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

        int score = BASE_SCORE;
        for (DeviceData d : latestByCode.values()) {
            String code = d.getDatapointCode().toLowerCase();
            Double n = tryParseDouble(d.getValue());
            if (n == null) {
                continue;
            }
            if (code.contains("temp") || code.contains("temperature")) {
                if (n > TEMP_THRESHOLD_HIGH) {
                    score -= 40;
                } else if (n > TEMP_THRESHOLD_LOW) {
                    score -= 20;
                }
            } else if (code.contains("vibration") || code.contains("vib")) {
                if (n > VIB_THRESHOLD_HIGH) {
                    score -= 40;
                } else if (n > VIB_THRESHOLD_LOW) {
                    score -= 20;
                }
            }
        }

        return Math.max(SCORE_MIN, Math.min(SCORE_MAX, score));
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
