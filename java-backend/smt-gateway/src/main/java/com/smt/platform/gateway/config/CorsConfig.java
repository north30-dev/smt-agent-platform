package com.smt.platform.gateway.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.reactive.CorsWebFilter;
import org.springframework.web.cors.reactive.UrlBasedCorsConfigurationSource;

import java.util.Arrays;

/**
 * 网关跨域配置（reactive 版），来源白名单 + 全方法 + 全请求头。
 *
 * <p>仅 dev profile 加载（P0-3 修复）：</p>
 * <ul>
 *   <li>dev：白名单来源（localhost:5173/3000 + 生产域名占位）+ 携带凭据，便于本地前后端联调</li>
 *   <li>prod：本类不加载，生产环境通过配置中心下发白名单 origin 列表</li>
 * </ul>
 */
@Profile("dev")
@Configuration
public class CorsConfig {

    @Bean
    public CorsWebFilter corsWebFilter() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOriginPatterns(Arrays.asList(
                "http://localhost:5173", "http://localhost:3000", "https://smt.example.com"));
        config.addAllowedMethod("*");
        config.addAllowedHeader("*");
        config.setAllowCredentials(true);
        config.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsWebFilter(source);
    }
}
