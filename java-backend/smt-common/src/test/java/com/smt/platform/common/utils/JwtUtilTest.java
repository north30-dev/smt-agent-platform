package com.smt.platform.common.utils;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.HashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * JwtUtil 单元测试：覆盖生成-解析闭环、过期 token、篡改 token 场景。
 */
class JwtUtilTest {

    private static final String SECRET = "smt-agent-platform-jwt-secret-key-32bytes-min";

    private JwtUtil jwtUtil;

    @BeforeEach
    void setUp() {
        jwtUtil = new JwtUtil();
        ReflectionTestUtils.setField(jwtUtil, "secret", SECRET);
    }

    @Nested
    @DisplayName("generateAndParseToken")
    class GenerateAndParseTokenTest {

        @Test
        @DisplayName("should restore claims when default")
        void shouldRestoreClaims_whenDefault() {
            Map<String, Object> claims = new HashMap<>();
            claims.put("userId", 1001L);
            claims.put("username", "admin");

            String token = jwtUtil.generateToken(claims, 60_000L);
            assertThat(token).isNotBlank();

            Claims parsed = jwtUtil.parseToken(token);
            assertThat(parsed.get("userId")).isEqualTo(1001);
            assertThat(parsed.get("username")).isEqualTo("admin");
        }
    }

    @Nested
    @DisplayName("parseToken")
    class ParseTokenTest {

        @Test
        @DisplayName("should throw ExpiredJwtException when token is expired")
        void shouldThrowExpiredJwtException_whenTokenIsExpired() {
            String token = jwtUtil.generateToken(Map.of(), -1000L);

            assertThatThrownBy(() -> jwtUtil.parseToken(token))
                    .isInstanceOf(ExpiredJwtException.class);
        }

        @Test
        @DisplayName("should throw JwtException when token is tampered")
        void shouldThrowJwtException_whenTokenIsTampered() {
            String token = jwtUtil.generateToken(Map.of("username", "admin"), 60_000L);
            String tampered = token.substring(0, token.length() - 4) + "ABCD";

            assertThatThrownBy(() -> jwtUtil.parseToken(tampered))
                    .isInstanceOf(JwtException.class);
        }
    }

    @Nested
    @DisplayName("validateToken")
    class ValidateTokenTest {

        @Test
        @DisplayName("should return true when token is valid")
        void shouldReturnTrue_whenTokenIsValid() {
            String token = jwtUtil.generateToken(Map.of("username", "admin"), 60_000L);
            assertThat(jwtUtil.validateToken(token)).isTrue();
        }

        @Test
        @DisplayName("should return false when token is invalid")
        void shouldReturnFalse_whenTokenIsInvalid() {
            assertThat(jwtUtil.validateToken("not.a.valid.token")).isFalse();
        }

        @Test
        @DisplayName("should return false when token is empty")
        void shouldReturnFalse_whenTokenIsEmpty() {
            assertThat(jwtUtil.validateToken("")).isFalse();
        }

        @Test
        @DisplayName("should return false when token is null")
        void shouldReturnFalse_whenTokenIsNull() {
            assertThat(jwtUtil.validateToken(null)).isFalse();
        }
    }
}
