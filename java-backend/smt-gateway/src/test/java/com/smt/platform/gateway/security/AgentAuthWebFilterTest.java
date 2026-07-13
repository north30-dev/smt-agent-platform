package com.smt.platform.gateway.security;

import com.smt.platform.common.utils.JwtUtil;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.reactive.server.WebTestClient;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * AgentAuthWebFilter 集成测试。
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
@Import(JwtUtil.class)
class AgentAuthWebFilterTest {

    @Autowired
    private WebTestClient webTestClient;

    @Autowired
    private JwtUtil jwtUtil;

    @Nested
    @DisplayName("filter authentication")
    class FilterAuthenticationTest {

        @Test
        @DisplayName("should return 401 when no token")
        void shouldReturn401_whenNoToken() {
            webTestClient.get().uri("/api/agent/knowledge/documents")
                    .exchange()
                    .expectStatus().isEqualTo(401)
                    .expectBody()
                    .jsonPath("$.error").isEqualTo("unauthorized")
                    .jsonPath("$.message").isEqualTo("token 缺失");
        }

        @Test
        @DisplayName("should return 401 when token is invalid")
        void shouldReturn401_whenTokenIsInvalid() {
            webTestClient.get().uri("/api/agent/knowledge/documents")
                    .header("Authorization", "Bearer invalid.token.here")
                    .exchange()
                    .expectStatus().isEqualTo(401)
                    .expectBody()
                    .jsonPath("$.error").isEqualTo("unauthorized")
                    .jsonPath("$.message").isEqualTo("token 无效或已过期");
        }

        @Test
        @DisplayName("should pass filter when token is valid")
        void shouldPassFilter_whenTokenIsValid() {
            String token = jwtUtil.generateToken("test-user", List.of("ADMIN"), 3600000L);
            webTestClient.get().uri("/api/agent/knowledge/documents")
                    .header("Authorization", "Bearer " + token)
                    .exchange()
                    .expectStatus().value(status -> assertThat(status)
                            .as("合法 token 不应被 filter 拦截返回 401")
                            .isNotEqualTo(401));
        }

        @Test
        @DisplayName("should not intercept device path when default")
        void shouldNotInterceptDevicePath_whenDefault() {
            webTestClient.get().uri("/api/device/1")
                    .exchange()
                    .expectStatus().value(status -> assertThat(status)
                            .as("/api/device/** 不应被 AgentAuthWebFilter 拦截返回 401")
                            .isNotEqualTo(401));
        }

        @Test
        @DisplayName("should pass maintenance route when token is valid")
        void shouldPassMaintenanceRoute_whenTokenIsValid() {
            String token = jwtUtil.generateToken("test-user", List.of("ADMIN"), 3600000L);
            webTestClient.get().uri("/api/agent/maintenance/health/1")
                    .header("Authorization", "Bearer " + token)
                    .exchange()
                    .expectStatus().value(status -> assertThat(status)
                            .as("合法 token 访问 maintenance 路由不应被 filter 拦截返回 401")
                            .isNotEqualTo(401));
        }

        @Test
        @DisplayName("should return 401 when token is expired")
        void shouldReturn401_whenTokenIsExpired() {
            String expiredToken = jwtUtil.generateToken("test-user", List.of("ADMIN"), -1000L);
            webTestClient.get().uri("/api/agent/knowledge/documents")
                    .header("Authorization", "Bearer " + expiredToken)
                    .exchange()
                    .expectStatus().isEqualTo(401)
                    .expectBody()
                    .jsonPath("$.error").isEqualTo("unauthorized")
                    .jsonPath("$.message").isEqualTo("token 无效或已过期");
        }

        @Test
        @DisplayName("should return 401 when authorization prefix is not Bearer")
        void shouldReturn401_whenAuthorizationPrefixIsNotBearer() {
            webTestClient.get().uri("/api/agent/knowledge/documents")
                    .header("Authorization", "Basic some-base64-credentials")
                    .exchange()
                    .expectStatus().isEqualTo(401)
                    .expectBody()
                    .jsonPath("$.error").isEqualTo("unauthorized")
                    .jsonPath("$.message").isEqualTo("token 缺失");
        }
    }
}
