package com.smt.platform.device.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.smt.platform.device.model.entity.Device;
import org.apache.ibatis.annotations.Mapper;

/**
 * 设备表 Mapper。
 */
@Mapper
public interface DeviceMapper extends BaseMapper<Device> {
}
