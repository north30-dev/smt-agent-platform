package com.smt.platform.device.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.smt.platform.device.model.entity.DeviceDataPoint;
import org.apache.ibatis.annotations.Mapper;

/**
 * 设备采集点表 Mapper。
 */
@Mapper
public interface DeviceDataPointMapper extends BaseMapper<DeviceDataPoint> {
}
