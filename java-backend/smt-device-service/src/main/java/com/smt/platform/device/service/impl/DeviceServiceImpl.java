package com.smt.platform.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.smt.platform.common.exception.BizException;
import com.smt.platform.common.response.ResultCode;
import com.smt.platform.device.mapper.DeviceMapper;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.service.DeviceService;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 设备台账服务实现。
 */
@Service
public class DeviceServiceImpl extends ServiceImpl<DeviceMapper, Device> implements DeviceService {

    @Override
    public Device create(Device device) {
        // 设备编码全局唯一校验
        Long count = baseMapper.selectCount(new LambdaQueryWrapper<Device>()
                .eq(Device::getDeviceCode, device.getDeviceCode()));
        if (count != null && count > 0) {
            throw new BizException(ResultCode.PARAM_ERROR, "设备编码已存在: " + device.getDeviceCode());
        }
        LocalDateTime now = LocalDateTime.now();
        if (device.getStatus() == null) {
            device.setStatus("RUNNING");
        }
        if (device.getHealthScore() == null) {
            device.setHealthScore(100);
        }
        if (device.getDeleted() == null) {
            device.setDeleted(0);
        }
        device.setCreateTime(now);
        device.setUpdateTime(now);
        baseMapper.insert(device);
        return device;
    }

    @Override
    public Device update(Long id, Device device) {
        Device existing = baseMapper.selectById(id);
        if (existing == null) {
            throw new BizException(ResultCode.NOT_FOUND, "设备不存在");
        }
        // 部分字段更新，deviceCode 不允许修改
        if (device.getDeviceName() != null) {
            existing.setDeviceName(device.getDeviceName());
        }
        if (device.getDeviceType() != null) {
            existing.setDeviceType(device.getDeviceType());
        }
        if (device.getProductionLine() != null) {
            existing.setProductionLine(device.getProductionLine());
        }
        if (device.getIpAddress() != null) {
            existing.setIpAddress(device.getIpAddress());
        }
        if (device.getProtocolType() != null) {
            existing.setProtocolType(device.getProtocolType());
        }
        if (device.getOpcUaEndpoint() != null) {
            existing.setOpcUaEndpoint(device.getOpcUaEndpoint());
        }
        if (device.getStatus() != null) {
            existing.setStatus(device.getStatus());
        }
        if (device.getHealthScore() != null) {
            existing.setHealthScore(device.getHealthScore());
        }
        existing.setUpdateTime(LocalDateTime.now());
        baseMapper.updateById(existing);
        return existing;
    }

    @Override
    public boolean delete(Long id) {
        Device existing = baseMapper.selectById(id);
        if (existing == null) {
            throw new BizException(ResultCode.NOT_FOUND, "设备不存在");
        }
        // 逻辑删除（@TableLogic 自动转换为 update deleted=1）
        return baseMapper.deleteById(id) > 0;
    }

    @Override
    public Device getById(Serializable id) {
        Device device = baseMapper.selectById(id);
        if (device == null) {
            throw new BizException(ResultCode.NOT_FOUND, "设备不存在");
        }
        return device;
    }

    @Override
    public IPage<Device> pageList(int page, int size, String productionLine, String deviceType, String status) {
        Page<Device> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<Device> wrapper = new LambdaQueryWrapper<Device>()
                .eq(StringUtils.hasText(productionLine), Device::getProductionLine, productionLine)
                .eq(StringUtils.hasText(deviceType), Device::getDeviceType, deviceType)
                .eq(StringUtils.hasText(status), Device::getStatus, status)
                .orderByDesc(Device::getCreateTime);
        return baseMapper.selectPage(pageParam, wrapper);
    }
}
