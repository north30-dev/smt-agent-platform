package com.smt.platform.device.repository;

import com.influxdb.client.InfluxDBClient;
import com.influxdb.client.WriteApiBlocking;
import com.influxdb.client.domain.WritePrecision;
import com.influxdb.client.write.Point;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.ZoneOffset;

/**
 * InfluxDB 时序数据写入仓储（Batch 4 P1 双写）。
 *
 * <p>封装 device_data 时序点的写入逻辑，作为 PG 主存的补充（双写）。
 * 设计原则：<b>失败不影响 PG 主流程</b> — 所有异常在内部 try-catch 兜底，
 * 仅记录 warn 日志，不向上抛出。</p>
 *
 * <p>使用 {@link WriteApiBlocking}（阻塞 API）而非异步 WriteApi：
 * 调用方 {@link com.smt.platform.device.service.impl.DeviceDataServiceImpl#saveData}
 * 已通过 {@code @Async} 在独立线程池执行，无需再叠加 InfluxDB 客户端异步层，
 * 阻塞写入更便于错误定位与资源控制。</p>
 *
 * <p>measurement 设计：{@code device_data}；tag = {@code device_id}/{@code datapoint_code}；
 * field = {@code value}（字符串原值，避免类型推断失败）；time = 数据采集时间戳（纳秒精度）。</p>
 */
@Slf4j
@Component
public class InfluxDBRepository {

    private final InfluxDBClient influxDBClient;
    private final String bucket;
    /** InfluxDB Organization 名称（避免与 @Slf4j 的 org.slf4j 包名冲突，重命名为 orgName） */
    private final String orgName;

    public InfluxDBRepository(InfluxDBClient influxDBClient,
                              @Value("${smt.influxdb.bucket:device_data}") String bucket,
                              @Value("${smt.influxdb.org-name:smt}") String orgName) {
        this.influxDBClient = influxDBClient;
        this.bucket = bucket;
        this.orgName = orgName;
    }

    /**
     * 将设备数据点写入 InfluxDB（双写）。
     *
     * <p>写入失败仅记录 warn 日志，不抛异常，保证不阻断 PG 主流程。
     * timestamp 为 null 时使用当前时间。</p>
     *
     * @param deviceId       设备 ID
     * @param datapointCode  采集点编码
     * @param value          数据值（字符串原值）
     * @param timestamp      数据采集时间（可为 null，默认当前时间）
     */
    public void writeDeviceData(Long deviceId, String datapointCode, String value, LocalDateTime timestamp) {
        try {
            LocalDateTime ts = timestamp != null ? timestamp : LocalDateTime.now();
            Point point = Point.measurement("device_data")
                    .addTag("device_id", String.valueOf(deviceId))
                    .addTag("datapoint_code", datapointCode != null ? datapointCode : "unknown")
                    .addField("value", value != null ? value : "")
                    .time(ts.toInstant(ZoneOffset.UTC), WritePrecision.NS);

            WriteApiBlocking writeApi = influxDBClient.getWriteApiBlocking();
            writeApi.writePoint(bucket, orgName, point);
            log.debug("InfluxDB 写入成功 deviceId={}, code={}, value={}", deviceId, datapointCode, value);
        } catch (Exception e) {
            // 兜底：InfluxDB 不可达/写入失败不影响 PG 主流程
            log.warn("InfluxDB 写入失败，不影响 PG 主流程：deviceId={}, code={}, err={}",
                    deviceId, datapointCode, e.getMessage());
        }
    }
}
