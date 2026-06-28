package com.smt.platform.common.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.security.web.AuthenticationEntryPoint;

/**
 * Spring Security 配置（P0-4 RBAC 骨架）。
 *
 * <p>核心策略：</p>
 * <ul>
 *   <li>无状态 session（STATELESS），所有认证走 JWT</li>
 *   <li>关闭 CSRF（REST API 不需要）</li>
 *   <li>路径规则：
 *     <ul>
 *       <li>POST /api/auth/login：permitAll（登录端点）</li>
 *       <li>GET /api/auth/me：authenticated（查询当前用户）</li>
 *       <li>GET /api/**：permitAll（查询类接口匿名可访问）</li>
 *       <li>其他 /api/**：authenticated（写操作需认证）</li>
 *       <li>/actuator/health, /actuator/info：permitAll</li>
 *       <li>/actuator/**：hasRole('ADMIN')</li>
 *     </ul>
 *   </li>
 *   <li>JWT 过滤器在 {@link UsernamePasswordAuthenticationFilter} 之前</li>
 *   <li>401/403 返回 JSON（由 {@link AuthErrorHandlers} 提供）</li>
 *   <li>启用 {@code @EnableMethodSecurity} 支持 {@code @PreAuthorize}</li>
 * </ul>
 *
 * <p>Phase 1 单用户（配置 admin），Phase 2 接 DB 用户表 + 多角色。</p>
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthenticationFilter;
    private final AuthenticationEntryPoint authenticationEntryPoint;
    private final AccessDeniedHandler accessDeniedHandler;

    public SecurityConfig(JwtAuthenticationFilter jwtAuthenticationFilter,
                          AuthenticationEntryPoint authenticationEntryPoint,
                          AccessDeniedHandler accessDeniedHandler) {
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
        this.authenticationEntryPoint = authenticationEntryPoint;
        this.accessDeniedHandler = accessDeniedHandler;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        // 登录端点匿名可访问
                        .requestMatchers(HttpMethod.POST, "/api/auth/login").permitAll()
                        // 查询当前用户需认证（须在 GET /api/** permitAll 之前匹配）
                        .requestMatchers(HttpMethod.GET, "/api/auth/me").authenticated()
                        // 健康检查端点匿名可访问（供 Prometheus/k8s 探针）
                        .requestMatchers("/actuator/health", "/actuator/info").permitAll()
                        // 其余 actuator 端点需 ADMIN 角色
                        .requestMatchers("/actuator/**").hasRole("ADMIN")
                        // GET 类查询接口匿名可访问
                        .requestMatchers(HttpMethod.GET, "/api/**").permitAll()
                        // 其余 /api/** 写操作需认证
                        .requestMatchers("/api/**").authenticated()
                        // 其他请求放行（静态资源等）
                        .anyRequest().permitAll()
                )
                .exceptionHandling(eh -> eh
                        .authenticationEntryPoint(authenticationEntryPoint)
                        .accessDeniedHandler(accessDeniedHandler)
                )
                .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    /**
     * 密码编码器：默认 bcrypt，支持多种编码格式（便于 Phase 2 兼容历史密码）。
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    /**
     * 暴露 AuthenticationManager 供 AuthController 使用。
     */
    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }
}
