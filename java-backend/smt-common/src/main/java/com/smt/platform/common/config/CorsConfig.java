package com.smt.platform.common.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 跨域配置（开发期允许所有来源），适用于 Servlet（spring-webmvc）应用。
 *
 * <p>仅 dev profile 加载（P0-3 修复）：</p>
 * <ul>
 *   <li>dev：允许任意来源 + 携带凭据，便于本地前后端联调</li>
 *   <li>prod：本类不加载，生产环境通过网关或配置中心下发白名单 origin 列表</li>
 * </ul>
 *
 * <p>注意：reactive 网关（smt-gateway）需使用 {@code CorsWebFilter}，不应加载本类。</p>
 */
@Profile("dev")
@Configuration
public class CorsConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }
}
