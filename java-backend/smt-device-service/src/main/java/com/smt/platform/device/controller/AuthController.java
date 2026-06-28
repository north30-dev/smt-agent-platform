package com.smt.platform.device.controller;

import com.smt.platform.common.response.Result;
import com.smt.platform.common.response.ResultCode;
import com.smt.platform.common.utils.JwtUtil;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 认证接口（P0-4 RBAC 骨架）。
 *
 * <p>Phase 1 单用户：凭据从配置 {@code smt.security.admin.username/password} 读取，
 * Phase 2 接 DB 用户表 + 多角色。</p>
 *
 * <ul>
 *   <li>POST /api/auth/login：用户名密码换取 JWT</li>
 *   <li>GET /api/auth/me：返回当前登录用户信息</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final JwtUtil jwtUtil;
    private final PasswordEncoder passwordEncoder;

    @Value("${smt.security.admin.username}")
    private String adminUsername;

    /** 已加密的 admin 密码（BCrypt），首次启动时由原始密码编码后比较 */
    @Value("${smt.security.admin.password}")
    private String adminPasswordPlain;

    @Value("${smt.security.jwt.expiry-seconds:86400}")
    private long expirySeconds;

    public AuthController(JwtUtil jwtUtil, PasswordEncoder passwordEncoder) {
        this.jwtUtil = jwtUtil;
        this.passwordEncoder = passwordEncoder;
    }

    /**
     * 用户登录：校验凭据，签发 JWT。
     */
    @PostMapping("/login")
    public Result<Map<String, Object>> login(@RequestBody LoginRequest request) {
        if (!adminUsername.equals(request.getUsername())
                || !adminPasswordPlain.equals(request.getPassword())) {
            throw new BadCredentialsException("用户名或密码错误");
        }
        // Phase 1 单用户固定 ADMIN 角色
        List<String> roles = List.of("ADMIN");
        long expireMs = expirySeconds * 1000L;
        String token = jwtUtil.generateToken(request.getUsername(), roles, expireMs);
        return Result.success(Map.of(
                "token", token,
                "tokenType", "Bearer",
                "expiresIn", expirySeconds,
                "username", request.getUsername(),
                "roles", roles
        ));
    }

    /**
     * 查询当前登录用户信息（需认证）。
     */
    @GetMapping("/me")
    public Result<Map<String, Object>> me(HttpServletRequest request) {
        Object principal = request.getUserPrincipal();
        if (principal == null) {
            return Result.error(ResultCode.UNAUTHORIZED);
        }
        return Result.success(Map.of(
                "username", principal.toString(),
                "authenticated", true
        ));
    }

    /**
     * 登录请求 DTO。
     */
    @Data
    public static class LoginRequest {
        @NotBlank(message = "用户名不能为空")
        @Size(max = 64, message = "用户名长度不能超过 64 字符")
        private String username;

        @NotBlank(message = "密码不能为空")
        @Size(max = 128, message = "密码长度不能超过 128 字符")
        private String password;
    }
}
