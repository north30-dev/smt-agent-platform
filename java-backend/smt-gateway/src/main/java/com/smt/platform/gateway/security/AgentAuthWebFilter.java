package com.smt.platform.gateway.security;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smt.platform.common.utils.JwtUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Import;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * 网关 reactive JWT 鉴权过滤器（P0-4）。
 *
 * <p>仅拦截 {@code /api/agent/**} 路径，校验 {@code Authorization: Bearer <token>} 头，
 * 复用 {@link JwtUtil} 校验 token。无 token 或 token 无效时返回 401 JSON，
 * 与 Python 侧 {@code ErrorResponse(error, message)} 结构对齐。</p>
 *
 * <p>{@code /api/device/**} 路径放行：device-service 已有 Phase 1 的 Servlet 版
 * SecurityFilterChain 兜底，网关层不重复鉴权。</p>
 *
 * <p>用 {@code @Import(JwtUtil.class)} 单独引入 JwtUtil Bean，不扩大 ComponentScan 范围，
 * 保持 reactive 运行时纯净，避免误加载 smt-common 中的 Servlet 配置。</p>
 */
@Slf4j
@Component
@Import(JwtUtil.class)
public class AgentAuthWebFilter implements WebFilter, Ordered {

    private static final String AGENT_PATH_PREFIX = "/api/agent/";

    private final JwtUtil jwtUtil;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${smt.security.jwt.header:Authorization}")
    private String headerName;

    @Value("${smt.security.jwt.prefix:Bearer }")
    private String headerPrefix;

    public AgentAuthWebFilter(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        String path = exchange.getRequest().getPath().value();
        if (!path.startsWith(AGENT_PATH_PREFIX)) {
            return chain.filter(exchange);
        }

        String token = extractToken(exchange);
        if (token == null) {
            log.debug("Agent 鉴权失败：缺少 Bearer token path={}", path);
            return writeUnauthorized(exchange, "token 缺失");
        }

        if (!jwtUtil.validateToken(token)) {
            log.debug("Agent 鉴权失败：token 无效或已过期 path={}", path);
            return writeUnauthorized(exchange, "token 无效或已过期");
        }

        return chain.filter(exchange);
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 10;
    }

    /**
     * 从 Authorization 头提取 Bearer token。
     */
    private String extractToken(ServerWebExchange exchange) {
        String header = exchange.getRequest().getHeaders().getFirst(headerName);
        if (!StringUtils.hasText(header) || !header.startsWith(headerPrefix)) {
            return null;
        }
        return header.substring(headerPrefix.length()).trim();
    }

    /**
     * 写 401 JSON 响应，body 结构与 Python 侧 ErrorResponse 对齐。
     */
    private Mono<Void> writeUnauthorized(ServerWebExchange exchange, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        byte[] body;
        try {
            body = objectMapper.writeValueAsBytes(Map.of("error", "unauthorized", "message", message));
        } catch (JsonProcessingException e) {
            body = "{\"error\":\"unauthorized\",\"message\":\"token 缺失或无效\"}".getBytes(StandardCharsets.UTF_8);
        }
        DataBuffer buffer = response.bufferFactory().wrap(body);
        return response.writeWith(Mono.just(buffer));
    }
}
