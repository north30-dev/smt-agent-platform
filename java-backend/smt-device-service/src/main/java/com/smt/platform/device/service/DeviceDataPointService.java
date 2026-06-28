package com.smt.platform.device.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.smt.platform.device.model.entity.DeviceDataPoint;

import java.util.List;

/**
 * 设备采集点服务接口。
 */
public interface DeviceDataPointService extends IService<DeviceDataPoint> {

    /**
     * 为指定设备新增采集点。
     *
     * @param deviceId  设备 ID（必须存在）
     * @param datapoint 采集点信息
     * @return 写入后的采集点（含生成的 id）
     */
    DeviceDataPoint create(Long deviceId, DeviceDataPoint datapoint);

    /**
     * 查询指定设备下的全部采集点。
     *
     * @param deviceId 设备 ID
     * @return 采集点列表（不分页）
     */
    List<DeviceDataPoint> listByDeviceId(Long deviceId);
}
