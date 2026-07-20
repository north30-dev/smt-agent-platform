package com.smt.platform.device.service.impl;

import com.smt.platform.common.utils.JwtUtil;
import com.smt.platform.device.config.SecurityProperties;
import com.smt.platform.device.model.dto.CurrentUserDTO;
import com.smt.platform.device.model.dto.LoginRequestDTO;
import com.smt.platform.device.model.dto.LoginResponseDTO;
import com.smt.platform.device.service.AuthService;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 认证服务实现（P0-4 RBAC 骨架）。
 *
 * <p>Phase 1 单用户：凭据从 {@link SecurityProperties} 读取，
 * Phase 2 接 DB 用户表 + 多角色。</p>
 */
@Service
public class AuthServiceImpl implements AuthService {

    private final JwtUtil jwtUtil;
    private final PasswordEncoder passwordEncoder;
    private final SecurityProperties securityProperties;

    public AuthServiceImpl(JwtUtil jwtUtil, PasswordEncoder passwordEncoder, SecurityProperties securityProperties) {
        this.jwtUtil = jwtUtil;
        this.passwordEncoder = passwordEncoder;
        this.securityProperties = securityProperties;
    }

    @Override
    public LoginResponseDTO login(LoginRequestDTO request) {
        String adminUsername = securityProperties.getAdmin().getUsername();
        String adminPasswordHash = securityProperties.getAdmin().getPassword();

        if (!adminUsername.equals(request.getUsername())
                || !passwordEncoder.matches(request.getPassword(), adminPasswordHash)) {
            throw new BadCredentialsException("用户名或密码错误");
        }

        // Phase 1 单用户固定 ADMIN 角色
        List<String> roles = List.of("ADMIN");
        long expiryMs = securityProperties.getJwt().getExpirySeconds() * 1000L;
        String token = jwtUtil.generateToken(request.getUsername(), roles, expiryMs);

        return new LoginResponseDTO(token, "Bearer",
                securityProperties.getJwt().getExpirySeconds(),
                request.getUsername(), roles);
    }

    @Override
    public CurrentUserDTO getCurrentUser(String username) {
        return new CurrentUserDTO(username, true);
    }
}
