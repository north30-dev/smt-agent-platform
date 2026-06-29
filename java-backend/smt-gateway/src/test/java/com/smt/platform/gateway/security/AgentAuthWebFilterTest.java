package com.smt.platform.gateway.security;

import com.smt.platform.common.utils.JwtUtil;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.reactive.server.WebTestClient;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * AgentAuthWebFilter 集成测试（P0-4）。
 *
 * <p>用 {@code @SpringBootTest(RANDOM_PORT)} + {@code @AutoConfigureWebTestClient} 启动完整
 * reactive 网关上下文，验证 JWT 鉴权过滤器对 {@code /api/agent/**} 的拦截行为。</p>
 *
 * <p>{@code @Import(JwtUtil.class)} 显式引入 JwtUtil Bean（与 AgentAuthWebFilter 上的 @Import 互为保险），
 * 测试中注入 JwtUtil 用于签发合法 token。</p>
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
@Import(JwtUtil.class)
class AgentAuthWebFilterTest {

    @Autowired
    private WebTestClient webTestClient;

    @Autowired
    private JwtUtil jwtUtil;

    @Test
    void test_no_token_returns_401() {
        webTestClient.get().uri("/api/agent/knowledge/documents")
                .exchange()
                .expectStatus().isEqualTo(401)
                .expectBody()
                .jsonPath("$.error").isEqualTo("unauthorized")
                .jsonPath("$.message").isEqualTo("token 缺失");
    }

    @Test
    void test_invalid_token_returns_401() {
        webTestClient.get().uri("/api/agent/knowledge/documents")
                .header("Authorization", "Bearer invalid.token.here")
                .exchange()
                .expectStatus().isEqualTo(401)
                .expectBody()
                .jsonPath("$.error").isEqualTo("unauthorized")
                .jsonPath("$.message").isEqualTo("token 无效或已过期");
    }

    @Test
    void test_valid_token_passes_filter() {
        String token = jwtUtil.generateToken("test-user", List.of("ADMIN"), 3600000L);
        // filter 放行后路由转发到后端 8004（未启动），网关返回 5xx，但不应是 401
        webTestClient.get().uri("/api/agent/knowledge/documents")
                .header("Authorization", "Bearer " + token)
                .exchange()
                .expectStatus().value(status -> assertThat(status)
                        .as("合法 token 不应被 filter 拦截返回 401")
                        .isNotEqualTo(401));
    }

    @Test
    void test_device_path_not_intercepted() {
        // /api/device/** 不被 filter 拦截，后端 8081 未启动返回 5xx，但不应是 401
        webTestClient.get().uri("/api/device/1")
                .exchange()
                .expectStatus().value(status -> assertThat(status)
                        .as("/api/device/** 不应被 AgentAuthWebFilter 拦截返回 401")
                        .isNotEqualTo(401));
    }
}
