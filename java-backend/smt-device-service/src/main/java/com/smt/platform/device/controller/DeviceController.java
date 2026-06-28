package com.smt.platform.device.controller;

import com.smt.platform.common.response.Result;
import com.smt.platform.device.model.dto.DeviceCreateDTO;
import com.smt.platform.device.model.dto.DeviceUpdateDTO;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.model.vo.PageVO;
import com.smt.platform.device.service.DeviceService;
import jakarta.validation.Valid;
import org.springframework.beans.BeanUtils;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 设备台账 REST 接口。
 *
 * <p>路径前缀 /api/device，与 OpenAPI 契约对齐。</p>
 */
@RestController
@RequestMapping("/api/device")
public class DeviceController {

    private final DeviceService deviceService;

    public DeviceController(DeviceService deviceService) {
        this.deviceService = deviceService;
    }

    /** 新增设备 */
    @PostMapping
    public Result<Device> create(@Valid @RequestBody DeviceCreateDTO dto) {
        Device device = new Device();
        BeanUtils.copyProperties(dto, device);
        return Result.success(deviceService.create(device));
    }

    /** 更新设备（部分字段更新，deviceCode 不可改） */
    @PutMapping("/{id}")
    public Result<Device> update(@PathVariable Long id, @Valid @RequestBody DeviceUpdateDTO dto) {
        Device device = new Device();
        BeanUtils.copyProperties(dto, device);
        return Result.success(deviceService.update(id, device));
    }

    /** 删除设备（软删除） */
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        deviceService.delete(id);
        return Result.success();
    }

    /** 查询设备详情 */
    @GetMapping("/{id}")
    public Result<Device> getById(@PathVariable Long id) {
        return Result.success(deviceService.getById(id));
    }

    /** 分页查询设备列表，支持按产线/类型/状态筛选 */
    @GetMapping("/list")
    public Result<PageVO<Device>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String productionLine,
            @RequestParam(required = false) String deviceType,
            @RequestParam(required = false) String status) {
        return Result.success(PageVO.of(deviceService.pageList(page, size, productionLine, deviceType, status)));
    }
}
