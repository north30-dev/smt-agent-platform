package com.smt.platform.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.smt.platform.common.exception.BizException;
import com.smt.platform.common.response.ResultCode;
import com.smt.platform.device.mapper.DeviceDataMapper;
import com.smt.platform.device.mapper.DeviceMapper;
import com.smt.platform.device.model.entity.DeviceData;
import com.smt.platform.device.service.DeviceDataService;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/**
 * 设备实时/历史数据服务实现。
 */
@Service
public class DeviceDataServiceImpl extends ServiceImpl<DeviceDataMapper, DeviceData>
        implements DeviceDataService {

    private final DeviceMapper deviceMapper;

    public DeviceDataServiceImpl(DeviceMapper deviceMapper) {
        this.deviceMapper = deviceMapper;
    }

    @Override
    public void saveData(Long deviceId, String datapointCode, String value, LocalDateTime timestamp) {
        DeviceData data = new DeviceData();
        data.setDeviceId(deviceId);
        data.setDatapointCode(datapointCode);
        data.setValue(value);
        data.setTimestamp(timestamp);
        baseMapper.insert(data);
    }

    @Override
    public IPage<DeviceData> queryHistory(Long deviceId, String datapointCode,
                                          LocalDateTime startTime, LocalDateTime endTime,
                                          int page, int size) {
        if (startTime.isAfter(endTime)) {
            throw new BizException(ResultCode.PARAM_ERROR, "起始时间不能晚于结束时间");
        }
        if (deviceMapper.selectById(deviceId) == null) {
            throw new BizException(ResultCode.NOT_FOUND, "设备不存在");
        }
        Page<DeviceData> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<DeviceData> wrapper = new LambdaQueryWrapper<DeviceData>()
                .eq(DeviceData::getDeviceId, deviceId)
                .eq(DeviceData::getDatapointCode, datapointCode)
                .ge(DeviceData::getTimestamp, startTime)
                .le(DeviceData::getTimestamp, endTime)
                .orderByAsc(DeviceData::getTimestamp);
        return baseMapper.selectPage(pageParam, wrapper);
    }
}
