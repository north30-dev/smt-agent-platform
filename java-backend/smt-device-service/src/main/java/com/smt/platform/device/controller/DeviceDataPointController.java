package com.smt.platform.device.controller;

import com.smt.platform.common.response.Result;
import com.smt.platform.device.model.dto.DataPointCreateDTO;
import com.smt.platform.device.model.entity.DeviceDataPoint;
import com.smt.platform.device.service.DeviceDataPointService;
import jakarta.validation.Valid;
import org.springframework.beans.BeanUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 设备采集点配置 REST 接口。
 *
 * <p>路径前缀 /api/device/{deviceId}/datapoints，与 OpenAPI 契约对齐。</p>
 */
@RestController
@RequestMapping("/api/device/{deviceId}/datapoints")
public class DeviceDataPointController {

    private final DeviceDataPointService deviceDataPointService;

    public DeviceDataPointController(DeviceDataPointService deviceDataPointService) {
        this.deviceDataPointService = deviceDataPointService;
    }

    /** 为指定设备新增采集点 */
    @PostMapping
    public Result<DeviceDataPoint> create(@PathVariable Long deviceId,
                                          @Valid @RequestBody DataPointCreateDTO dto) {
        DeviceDataPoint datapoint = new DeviceDataPoint();
        BeanUtils.copyProperties(dto, datapoint);
        return Result.success(deviceDataPointService.create(deviceId, datapoint));
    }

    /** 查询指定设备下的全部采集点 */
    @GetMapping
    public Result<List<DeviceDataPoint>> list(@PathVariable Long deviceId) {
        return Result.success(deviceDataPointService.listByDeviceId(deviceId));
    }
}
