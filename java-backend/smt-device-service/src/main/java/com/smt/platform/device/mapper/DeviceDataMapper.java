package com.smt.platform.device.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.smt.platform.device.model.entity.DeviceData;
import org.apache.ibatis.annotations.Mapper;

/**
 * 设备数据表 Mapper。
 */
@Mapper
public interface DeviceDataMapper extends BaseMapper<DeviceData> {
}
