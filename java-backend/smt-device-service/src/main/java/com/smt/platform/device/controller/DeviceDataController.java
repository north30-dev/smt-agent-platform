package com.smt.platform.device.controller;

import com.smt.platform.common.response.Result;
import com.smt.platform.device.model.entity.DeviceData;
import com.smt.platform.device.model.vo.PageVO;
import com.smt.platform.device.service.DeviceDataService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Positive;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;

/**
 * 设备历史数据查询 REST 接口。
 *
 * <p>路径前缀 /api/device/{deviceId}/data，与 OpenAPI 契约对齐。</p>
 *
 * <p>m6 改造：history 方法加 {@link Cacheable}，相同参数 10 分钟内命中 Redis 缓存，
 * 减少 PG 查询压力（PRD §5 性能要求）。</p>
 *
 * <p>M7-Java 改造：补 JSR-380 校验注解（{@link Positive}/{@link Max}），
 * deviceId 必须为正数，size 上限 1000 防止超大结果集拖垮 DB。</p>
 */
@RestController
@RequestMapping("/api/device/{deviceId}/data")
@Validated
public class DeviceDataController {

    private final DeviceDataService deviceDataService;

    public DeviceDataController(DeviceDataService deviceDataService) {
        this.deviceDataService = deviceDataService;
    }

    /**
     * 按采集点编码与时间范围分页查询历史数据，按 timestamp 升序。
     *
     * <p>缓存 key 格式：{@code device:data:history::{deviceId}:{datapointCode}:{startTime}:{endTime}:{page}:{size}}
     * （Spring Cache 默认 SimpleKeyGenerator 会拼接所有参数）。</p>
     */
    @GetMapping
    @Cacheable(value = "device:data:history",
            key = "#deviceId + ':' + #datapointCode + ':' + #startTime + ':' + #endTime + ':' + #page + ':' + #size")
    public Result<PageVO<DeviceData>> history(
            @PathVariable @Positive Long deviceId,
            @RequestParam String datapointCode,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime,
            @RequestParam(defaultValue = "1") @Positive int page,
            @RequestParam(defaultValue = "100") @Positive @Max(1000) int size) {
        return Result.success(PageVO.of(deviceDataService.queryHistory(
                deviceId, datapointCode, startTime, endTime, page, size)));
    }
}
