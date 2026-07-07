package com.smt.platform.common.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 跨域配置（开发期收敛到 localhost 白名单），适用于 Servlet（spring-webmvc）应用。
 *
 * <p>仅 dev profile 加载（P0-3 修复 + F2 收敛）：</p>
 * <ul>
 *   <li>dev：允许 localhost / 127.0.0.1 任意端口 + 携带凭据，覆盖 Vite(5173) 等本地前端</li>
 *   <li>prod：本类不加载，生产环境通过网关或配置中心下发白名单 origin 列表</li>
 * </ul>
 *
 * <p>注意：reactive 网关（smt-gateway）需使用 {@code CorsWebFilter}，不应加载本类。</p>
 */
@Profile("dev")
@Configuration
public class CorsConfig implements WebMvcConfigurer {

    private static final String[] DEV_ALLOWED_ORIGIN_PATTERNS = {
        "http://localhost:*",
        "http://127.0.0.1:*",
        "https://localhost:*",
        "https://127.0.0.1:*",
    };

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns(DEV_ALLOWED_ORIGIN_PATTERNS)
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }
}
