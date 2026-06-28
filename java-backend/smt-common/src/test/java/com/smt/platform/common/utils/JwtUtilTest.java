package com.smt.platform.common.utils;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.HashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link JwtUtil} 单元测试：覆盖生成-解析闭环、过期 token、篡改 token 场景。
 */
class JwtUtilTest {

    /** 至少 32 字节，用于 HS256 */
    private static final String SECRET = "smt-agent-platform-jwt-secret-key-32bytes-min";

    private JwtUtil jwtUtil;

    @BeforeEach
    void setUp() {
        jwtUtil = new JwtUtil();
        ReflectionTestUtils.setField(jwtUtil, "secret", SECRET);
    }

    @Test
    void generateAndParseToken_shouldRestoreClaims() {
        Map<String, Object> claims = new HashMap<>();
        claims.put("userId", 1001L);
        claims.put("username", "admin");

        String token = jwtUtil.generateToken(claims, 60_000L);
        assertThat(token).isNotBlank();

        Claims parsed = jwtUtil.parseToken(token);
        assertThat(parsed.get("userId")).isEqualTo(1001);
        assertThat(parsed.get("username")).isEqualTo("admin");
    }

    @Test
    void parseToken_expiredToken_shouldThrow() {
        // 过期时长为负，生成的 token 立即过期
        String token = jwtUtil.generateToken(Map.of(), -1000L);

        assertThatThrownBy(() -> jwtUtil.parseToken(token))
                .isInstanceOf(ExpiredJwtException.class);
    }

    @Test
    void parseToken_tamperedToken_shouldThrow() {
        String token = jwtUtil.generateToken(Map.of("username", "admin"), 60_000L);
        // 篡改签名末尾字符
        String tampered = token.substring(0, token.length() - 4) + "ABCD";

        assertThatThrownBy(() -> jwtUtil.parseToken(tampered))
                .isInstanceOf(JwtException.class);
    }

    @Test
    void validateToken_validToken_returnsTrue() {
        String token = jwtUtil.generateToken(Map.of("username", "admin"), 60_000L);
        assertThat(jwtUtil.validateToken(token)).isTrue();
    }

    @Test
    void validateToken_invalidToken_returnsFalse() {
        assertThat(jwtUtil.validateToken("not.a.valid.token")).isFalse();
    }
}
