package com.smt.platform.device.config;

import com.influxdb.client.InfluxDBClient;
import com.influxdb.client.InfluxDBClientFactory;
import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * InfluxDB 2.x 客户端配置（Batch 4）。
 *
 * <p>从 {@code smt.influxdb.*} 读取连接参数，构造 {@link InfluxDBClient} Bean。
 * InfluxDB 不可达时不阻断 Spring 启动（{@link InfluxDBClient} 创建是惰性的，
 * 实际连接在首次写入时建立），首次写入失败由 {@link com.smt.platform.device.repository.InfluxDBRepository} 兜底。</p>
 *
 * <p>配置项均支持 ENV 覆盖（{@code SMT_INFLUXDB_URL/TOKEN/ORG/BUCKET}），
 * dev 默认值便于本地启动，生产由 ENV 覆盖。</p>
 */
@Slf4j
@Getter
@Setter
@Configuration
@ConfigurationProperties(prefix = "smt.influxdb")
public class InfluxDBConfig {

    /** InfluxDB 2.x 服务地址（含端口），如 http://localhost:8086 */
    private String url = "http://localhost:8086";

    /** InfluxDB 2.x 访问 Token（生产由 ENV 注入，dev 用占位符） */
    private String token = "dev-only-token";

    /** InfluxDB 2.x Organization 名称（yml 配置项 org-name，Spring relaxed binding 自动映射） */
    private String orgName = "smt";

    /** InfluxDB 2.x Bucket 名称（时序数据存储桶） */
    private String bucket = "device_data";

    /**
     * 构造 InfluxDBClient Bean。
     *
     * <p>{@code destroyMethod = "close"} 确保应用关闭时释放 HTTP 连接池。</p>
     */
    @Bean(destroyMethod = "close")
    public InfluxDBClient influxDBClient() {
        log.info("初始化 InfluxDBClient: url={}, org={}, bucket={}", url, orgName, bucket);
        return InfluxDBClientFactory.create(url, token.toCharArray(), orgName, bucket);
    }
}
