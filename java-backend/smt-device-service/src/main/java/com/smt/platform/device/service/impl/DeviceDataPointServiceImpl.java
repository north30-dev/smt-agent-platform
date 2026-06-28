package com.smt.platform.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.smt.platform.common.exception.BizException;
import com.smt.platform.common.response.ResultCode;
import com.smt.platform.device.mapper.DeviceDataPointMapper;
import com.smt.platform.device.mapper.DeviceMapper;
import com.smt.platform.device.model.entity.DeviceDataPoint;
import com.smt.platform.device.service.DeviceDataPointService;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 设备采集点服务实现。
 */
@Service
public class DeviceDataPointServiceImpl
        extends ServiceImpl<DeviceDataPointMapper, DeviceDataPoint>
        implements DeviceDataPointService {

    private final DeviceMapper deviceMapper;

    public DeviceDataPointServiceImpl(DeviceMapper deviceMapper) {
        this.deviceMapper = deviceMapper;
    }

    @Override
    public DeviceDataPoint create(Long deviceId, DeviceDataPoint datapoint) {
        if (deviceMapper.selectById(deviceId) == null) {
            throw new BizException(ResultCode.NOT_FOUND, "设备不存在");
        }
        datapoint.setDeviceId(deviceId);
        datapoint.setCreateTime(LocalDateTime.now());
        baseMapper.insert(datapoint);
        return datapoint;
    }

    @Override
    public List<DeviceDataPoint> listByDeviceId(Long deviceId) {
        return baseMapper.selectList(new LambdaQueryWrapper<DeviceDataPoint>()
                .eq(DeviceDataPoint::getDeviceId, deviceId)
                .orderByAsc(DeviceDataPoint::getId));
    }
}
