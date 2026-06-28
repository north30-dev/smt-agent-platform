package com.smt.platform.device;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 设备服务主启动类。
 *
 * <p>扫描根包 com.smt.platform，以便加载 smt-common 中的公共配置
 * （JacksonConfig / CorsConfig / GlobalExceptionHandler / JwtUtil）。</p>
 */
@SpringBootApplication(scanBasePackages = "com.smt.platform")
@MapperScan("com.smt.platform.device.mapper")
public class SmtDeviceServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(SmtDeviceServiceApplication.class, args);
    }
}
