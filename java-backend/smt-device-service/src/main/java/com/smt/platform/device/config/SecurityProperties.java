package com.smt.platform.device.config;

import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 安全与认证配置（绑定 smt.security 前缀）。
 *
 * <p>Phase 1 单用户：从配置文件读取凭据；
 * Phase 2 接 DB 用户表后迁移至数据库存储。</p>
 */
@Data
@Component
@ConfigurationProperties(prefix = "smt.security")
public class SecurityProperties {

    private Admin admin = new Admin();

    private Jwt jwt = new Jwt();

    @Data
    @NoArgsConstructor
    public static class Admin {

        /** 管理员用户名 */
        private String username;

        /** 管理员密码（BCrypt 哈希） */
        private String password;
    }

    @Data
    @NoArgsConstructor
    public static class Jwt {

        /** JWT 过期时间（秒），默认 86400（24 小时） */
        private long expirySeconds = 86400L;
    }
}
