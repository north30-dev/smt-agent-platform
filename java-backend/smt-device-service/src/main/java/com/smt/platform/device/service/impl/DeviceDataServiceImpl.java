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
import com.smt.platform.device.repository.InfluxDBRepository;
import com.smt.platform.device.service.DeviceDataService;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/**
 * 设备实时/历史数据服务实现。
 *
 * <p>Batch 4 改造：{@link #saveData} 加 {@link Async} 注解，异步执行 PG 写入 + InfluxDB 双写，
 * 避免阻塞 MQTT 回调线程。使用 {@code deviceDataExecutor} 线程池（见 {@code AsyncConfig}），
 * CallerRunsPolicy 拒绝策略保证队列满时退化为同步执行，与原同步行为等价（最坏情况）。</p>
 *
 * <p>InfluxDB 双写失败由 {@link InfluxDBRepository} 内部 try-catch 兜底，不影响 PG 主流程。</p>
 */
@Service
public class DeviceDataServiceImpl extends ServiceImpl<DeviceDataMapper, DeviceData>
        implements DeviceDataService {

    private final DeviceMapper deviceMapper;
    private final InfluxDBRepository influxDBRepository;

    public DeviceDataServiceImpl(DeviceMapper deviceMapper, InfluxDBRepository influxDBRepository) {
        this.deviceMapper = deviceMapper;
        this.influxDBRepository = influxDBRepository;
    }

    @Async("deviceDataExecutor")
    @Override
    public void saveData(Long deviceId, String datapointCode, String value, LocalDateTime timestamp) {
        DeviceData data = new DeviceData();
        data.setDeviceId(deviceId);
        data.setDatapointCode(datapointCode);
        data.setValue(value);
        data.setTimestamp(timestamp);
        baseMapper.insert(data);
        // P1 InfluxDB 双写：失败由 InfluxDBRepository 内部 try-catch 兜底，不影响 PG 主流程
        influxDBRepository.writeDeviceData(deviceId, datapointCode, value, timestamp);
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
