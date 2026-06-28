package com.smt.platform.device.controller;

import com.smt.platform.common.response.Result;
import com.smt.platform.device.model.entity.DeviceData;
import com.smt.platform.device.model.vo.PageVO;
import com.smt.platform.device.service.DeviceDataService;
import org.springframework.format.annotation.DateTimeFormat;
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
 */
@RestController
@RequestMapping("/api/device/{deviceId}/data")
public class DeviceDataController {

    private final DeviceDataService deviceDataService;

    public DeviceDataController(DeviceDataService deviceDataService) {
        this.deviceDataService = deviceDataService;
    }

    /** 按采集点编码与时间范围分页查询历史数据，按 timestamp 升序 */
    @GetMapping
    public Result<PageVO<DeviceData>> history(
            @PathVariable Long deviceId,
            @RequestParam String datapointCode,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "100") int size) {
        return Result.success(PageVO.of(deviceDataService.queryHistory(
                deviceId, datapointCode, startTime, endTime, page, size)));
    }
}
