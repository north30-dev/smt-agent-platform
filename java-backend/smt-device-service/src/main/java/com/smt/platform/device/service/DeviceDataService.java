package com.smt.platform.device.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import com.smt.platform.device.model.entity.DeviceData;

import java.time.LocalDateTime;

/**
 * 设备实时/历史数据服务接口。
 *
 * <p>本服务是后续数据接入层（Task 7 OPC UA / Task 8 MQTT）与健康评分
 * （Task 10）的依赖，方法签名需保持稳定。</p>
 */
public interface DeviceDataService extends IService<DeviceData> {

    /**
     * 存储一条设备实时数据。供数据接入层（OPC UA/MQTT 回调）调用。
     *
     * @param deviceId      设备 ID
     * @param datapointCode 采集点编码
     * @param value         数据值（统一用字符串传输）
     * @param timestamp     数据采集时间
     */
    void saveData(Long deviceId, String datapointCode, String value, LocalDateTime timestamp);

    /**
     * 按设备 + 采集点 + 时间范围分页查询历史数据，结果按 timestamp 升序。
     *
     * @param deviceId      设备 ID
     * @param datapointCode 采集点编码
     * @param startTime     起始时间（含）
     * @param endTime       结束时间（含）
     * @param page          页码，从 1 开始
     * @param size          每页条数
     * @return 分页历史数据
     */
    IPage<DeviceData> queryHistory(Long deviceId, String datapointCode,
                                   LocalDateTime startTime, LocalDateTime endTime,
                                   int page, int size);
}
