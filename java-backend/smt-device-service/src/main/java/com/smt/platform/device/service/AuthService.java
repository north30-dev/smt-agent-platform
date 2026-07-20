package com.smt.platform.device.service;

import com.smt.platform.device.model.dto.CurrentUserDTO;
import com.smt.platform.device.model.dto.LoginRequestDTO;
import com.smt.platform.device.model.dto.LoginResponseDTO;

/**
 * 认证服务接口（P0-4 RBAC 骨架）。
 *
 * <p>Phase 1 单用户：凭据从配置读取；
 * Phase 2 接 DB 用户表后迁移至数据库校验。</p>
 */
public interface AuthService {

    /**
     * 用户登录：校验凭据，签发 JWT。
     *
     * @param request 登录请求（用户名 + 密码）
     * @return JWT Token 信息
     * @throws org.springframework.security.authentication.BadCredentialsException 凭据错误时抛出
     */
    LoginResponseDTO login(LoginRequestDTO request);

    /**
     * 查询当前登录用户信息。
     *
     * @param username 当前登录用户名
     * @return 用户信息
     */
    CurrentUserDTO getCurrentUser(String username);
}
