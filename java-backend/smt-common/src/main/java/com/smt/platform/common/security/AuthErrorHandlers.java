package com.smt.platform.common.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smt.platform.common.response.Result;
import com.smt.platform.common.response.ResultCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;

import java.io.IOException;

/**
 * Spring Security 认证/授权错误响应处理器（P0-4 RBAC 骨架）。
 *
 * <p>Spring Security 默认返回 HTML 错误页，本配置统一返回 {@link Result} JSON 结构，
 * 便于前端按 code 字段统一处理。</p>
 *
 * <ul>
 *   <li>401 未认证：{@link ResultCode#UNAUTHORIZED}</li>
 *   <li>403 无权限：{@link ResultCode#FORBIDDEN}</li>
 * </ul>
 */
@Configuration
public class AuthErrorHandlers {

    private static final Logger log = LoggerFactory.getLogger(AuthErrorHandlers.class);

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 未认证入口点：访问受保护资源但未提供有效 token 时触发，返回 401 JSON。
     */
    @Bean
    public AuthenticationEntryPoint authenticationEntryPoint() {
        return (HttpServletRequest request, HttpServletResponse response,
                AuthenticationException ex) -> {
            log.warn("未认证访问 method={} path={} reason={}",
                    request.getMethod(), request.getRequestURI(), ex.getMessage());
            writeJson(response, HttpStatus.UNAUTHORIZED,
                    Result.error(ResultCode.UNAUTHORIZED, "未认证或认证已过期"));
        };
    }

    /**
     * 访问拒绝处理器：已认证但权限不足时触发，返回 403 JSON。
     */
    @Bean
    public AccessDeniedHandler accessDeniedHandler() {
        return (HttpServletRequest request, HttpServletResponse response,
                AccessDeniedException ex) -> {
            log.warn("访问被拒绝 method={} path={} reason={}",
                    request.getMethod(), request.getRequestURI(), ex.getMessage());
            writeJson(response, HttpStatus.FORBIDDEN,
                    Result.error(ResultCode.FORBIDDEN, "无访问权限"));
        };
    }

    private void writeJson(HttpServletResponse response, HttpStatus status, Result<Void> body) throws IOException {
        response.setStatus(status.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        response.getWriter().write(objectMapper.writeValueAsString(body));
    }
}
