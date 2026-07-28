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
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.BeanWrapper;
import org.springframework.beans.BeanWrapperImpl;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.beans.PropertyDescriptor;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Set;

/**
 * 设备台账服务实现。
 *
 * <p>P0-1 修复：移除对 {@link com.baomidou.mybatisplus.extension.service.IService#getById} 的覆写，
 * 新增 {@link #getByIdOrThrow(Serializable)} 承担异常语义，恢复 IService 契约。</p>
 *
 * <p>P0-2 修复：类级 {@link Transactional} 为所有写操作加事务边界；
 * {@link #create} 捕获 {@link DuplicateKeyException} 转 {@link BizException}，
 * 依赖 DB 唯一索引 {@code uk_device_code} 兜底并发写入。</p>
 *
 * <p>M5 改造：createTime/updateTime/deleted 由 {@link com.smt.platform.common.config.MyMetaObjectHandler}
 * 自动填充，不再手写时间戳。</p>
 *
 * <p>M2 改造：{@link #update} 方法 8 字段判空拷贝改为 {@link BeanUtils#copyProperties} + null 属性过滤，
 * 保护 id/deviceCode/createTime/deleted 不被覆盖，行为与原判空逻辑等价。</p>
 */
@Slf4j
@Service
@Transactional
public class DeviceServiceImpl extends ServiceImpl<DeviceMapper, Device> implements DeviceService {

    /**
     * update 时受保护字段：不允许通过 update 修改。
     * id 主键、deviceCode 业务唯一键、createTime/deleted 由 DB/MetaObjectHandler 管理。
     * updateTime 不在保护列表中（由 MetaObjectHandler 在 updateById 时自动填充）。
     */
    private static final Set<String> PROTECTED_FIELDS =
            Set.of("id", "deviceCode", "createTime", "deleted", "createBy", "updateBy", "updateTime", "class");

    @Override
    public Device create(Device device) {
        // 设备编码全局唯一校验（应用层快速失败，避免无效请求打到 DB）
        Long count = baseMapper.selectCount(new LambdaQueryWrapper<Device>()
                .eq(Device::getDeviceCode, device.getDeviceCode()));
        if (count != null && count > 0) {
            throw new BizException(ResultCode.PARAM_ERROR, "设备编码已存在: " + device.getDeviceCode());
        }
        // 业务默认值（非审计字段，保留手写）
        if (device.getStatus() == null) {
            device.setStatus("RUNNING");
        }
        if (device.getHealthScore() == null) {
            device.setHealthScore(100);
        }
        // createTime/updateTime/deleted 由 MetaObjectHandler.insertFill 自动填充（M5）
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
        // M2：仅复制 device 中非 null 且非受保护字段到 existing，等价于原 8 字段判空拷贝
        BeanUtils.copyProperties(device, existing, getCopyIgnorePropertyNames(device));
        existing.setId(id);
        // updateTime 由 MetaObjectHandler.updateFill 在 updateById 时自动填充（M5）
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

    /**
     * 返回应被忽略的属性名数组：source 中值为 null 的属性 + 受保护字段。
     * 用于 {@link BeanUtils#copyProperties} 的第三参数，实现"仅复制非 null 且非受保护字段"。
     */
    private static String[] getCopyIgnorePropertyNames(Object source) {
        BeanWrapper wrapper = new BeanWrapperImpl(source);
        return Arrays.stream(wrapper.getPropertyDescriptors())
                .map(PropertyDescriptor::getName)
                .filter(name -> wrapper.getPropertyValue(name) == null || PROTECTED_FIELDS.contains(name))
                .toArray(String[]::new);
    }
}
