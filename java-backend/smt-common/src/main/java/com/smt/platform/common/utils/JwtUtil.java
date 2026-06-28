package com.smt.platform.common.utils;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.List;
import java.util.Map;

/**
 * JWT 工具类，基于 jjwt 0.12.x API。
 *
 * <p>密钥从配置项 {@code smt.security.jwt.secret} 注入（P0-5 凭据环境变量化后路径变更），
 * 需 >= 32 字节以支持 HS256。</p>
 */
@Component
public class JwtUtil {

    @Value("${smt.security.jwt.secret}")
    private String secret;

    /**
     * 生成 token。
     *
     * @param claims   自定义声明
     * @param expireMs 过期时长（毫秒）
     * @return JWT 字符串
     */
    public String generateToken(Map<String, Object> claims, long expireMs) {
        SecretKey key = toKey();
        long now = System.currentTimeMillis();
        return Jwts.builder()
                .claims(claims)
                .issuedAt(new Date(now))
                .expiration(new Date(now + expireMs))
                .signWith(key)
                .compact();
    }

    /**
     * 生成 token（携带 subject 与 roles，P0-4 RBAC 骨架使用）。
     *
     * @param subject  用户标识（如 username）
     * @param roles    角色列表（写入 "roles" claim，备 Phase 2 多角色使用）
     * @param expireMs 过期时长（毫秒）
     * @return JWT 字符串
     */
    public String generateToken(String subject, List<String> roles, long expireMs) {
        SecretKey key = toKey();
        long now = System.currentTimeMillis();
        return Jwts.builder()
                .subject(subject)
                .claim("roles", roles)
                .issuedAt(new Date(now))
                .expiration(new Date(now + expireMs))
                .signWith(key)
                .compact();
    }

    /**
     * 解析 token，返回声明集合。
     *
     * @param token JWT 字符串
     * @return Claims
     * @throws JwtException token 过期或被篡改时抛出
     */
    public Claims parseToken(String token) {
        SecretKey key = toKey();
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    /**
     * 校验 token 是否有效（未过期且签名正确）。
     *
     * @param token JWT 字符串
     * @return 有效返回 true，否则 false
     */
    public boolean validateToken(String token) {
        try {
            parseToken(token);
            return true;
        } catch (JwtException | IllegalArgumentException e) {
            return false;
        }
    }

    private SecretKey toKey() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }
}
