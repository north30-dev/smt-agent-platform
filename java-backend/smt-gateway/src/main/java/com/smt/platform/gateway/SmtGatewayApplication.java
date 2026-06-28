package com.smt.platform.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 网关主启动类。
 *
 * <p>默认仅扫描 {@code com.smt.platform.gateway} 包，避免加载 smt-common 中
 * 基于 Servlet 的配置（如 WebMvcConfigurer），保持 reactive 运行时纯净。</p>
 */
@SpringBootApplication
public class SmtGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(SmtGatewayApplication.class, args);
    }
}
