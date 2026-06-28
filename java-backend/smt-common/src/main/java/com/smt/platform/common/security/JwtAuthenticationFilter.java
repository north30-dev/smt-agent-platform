package com.smt.platform.common.security;

import com.smt.platform.common.utils.JwtUtil;
import io.jsonwebtoken.Claims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;
import java.util.List;

/**
 * JWT 认证过滤器（P0-4 RBAC 骨架）。
 *
 * <p>从 {@code Authorization} 头解析 {@code Bearer <token>}，调用 {@link JwtUtil#parseToken}
 * 校验通过后构造 {@link UsernamePasswordAuthenticationToken} 放入 SecurityContext，
 * 后续 Controller 可通过 {@code @PreAuthorize} 或 {@code SecurityContextHolder} 获取当前用户。</p>
 *
 * <p>异常/无效 token：不抛异常，让后续 {@code authorizeHttpRequests} 决定是否拒绝
 * （保持 GET /api/** 可匿名语义）。</p>
 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(JwtAuthenticationFilter.class);

    private final JwtUtil jwtUtil;

    @Value("${smt.security.jwt.header:Authorization}")
    private String headerName;

    @Value("${smt.security.jwt.prefix:Bearer }")
    private String headerPrefix;

    public JwtAuthenticationFilter(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String token = extractToken(request);
        if (token != null) {
            try {
                Claims claims = jwtUtil.parseToken(token);
                String subject = claims.getSubject();
                Object rolesObj = claims.get("roles");
                List<SimpleGrantedAuthority> authorities = toAuthorities(rolesObj);
                UsernamePasswordAuthenticationToken authentication =
                        new UsernamePasswordAuthenticationToken(subject, null, authorities);
                SecurityContextHolder.getContext().setAuthentication(authentication);
            } catch (Exception e) {
                // 无效 token 不抛异常，让 SecurityFilterChain 的 authorizeHttpRequests 决定是否拒绝
                log.debug("JWT 解析失败，将以匿名身份继续处理 reason={}", e.getMessage());
                SecurityContextHolder.clearContext();
            }
        }
        filterChain.doFilter(request, response);
    }

    /**
     * 从 Authorization 头提取 Bearer token。
     */
    private String extractToken(HttpServletRequest request) {
        String header = request.getHeader(headerName);
        if (!StringUtils.hasText(header) || !header.startsWith(headerPrefix)) {
            return null;
        }
        return header.substring(headerPrefix.length()).trim();
    }

    /**
     * 将 JWT 中的 roles claim 转为 Spring Security authorities。
     *
     * <p>每个 role 会加上 {@code ROLE_} 前缀以匹配 {@code hasRole()} 表达式。</p>
     */
    @SuppressWarnings("unchecked")
    private List<SimpleGrantedAuthority> toAuthorities(Object rolesObj) {
        if (!(rolesObj instanceof List<?> roles) || roles.isEmpty()) {
            return Collections.emptyList();
        }
        try {
            return roles.stream()
                    .filter(r -> r instanceof String)
                    .map(r -> "ROLE_" + r)
                    .map(SimpleGrantedAuthority::new)
                    .toList();
        } catch (ClassCastException e) {
            return Collections.emptyList();
        }
    }
}
