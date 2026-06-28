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
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 设备台账服务实现。
 *
 * <p>P0-1 修复：移除对 {@link com.baomidou.mybatisplus.extension.service.IService#getById} 的覆写，
 * 新增 {@link #getByIdOrThrow(Serializable)} 承担异常语义，恢复 IService 契约。</p>
 *
 * <p>P0-2 修复：类级 {@link Transactional} 为所有写操作加事务边界；
 * {@link #create} 捕获 {@link DuplicateKeyException} 转 {@link BizException}，
 * 依赖 DB 唯一索引 {@code uk_device_code} 兜底并发写入。</p>
 */
@Service
@Transactional
public class DeviceServiceImpl extends ServiceImpl<DeviceMapper, Device> implements DeviceService {

    private static final Logger log = LoggerFactory.getLogger(DeviceServiceImpl.class);

    @Override
    public Device create(Device device) {
        // 设备编码全局唯一校验（应用层快速失败，避免无效请求打到 DB）
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
        try {
            baseMapper.insert(device);
        } catch (DuplicateKeyException e) {
            // 并发场景下两个线程同时通过 selectCount 校验，DB 唯一索引 uk_device_code 兜底
            log.warn("设备编码唯一约束冲突（并发写入） deviceCode={}", device.getDeviceCode());
            throw new BizException(ResultCode.PARAM_ERROR, "设备编码已存在: " + device.getDeviceCode());
        }
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
    public Device getByIdOrThrow(Serializable id) {
        Device device = baseMapper.selectById(id);
        if (device == null) {
            throw new BizException(ResultCode.NOT_FOUND, "设备不存在");
        }
        return device;
    }

    @Override
    @Transactional(readOnly = true)
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
