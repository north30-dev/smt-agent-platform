package com.smt.platform.device.controller;

import com.smt.platform.common.response.Result;
import com.smt.platform.common.response.ResultCode;
import com.smt.platform.device.model.dto.LoginRequestDTO;
import com.smt.platform.device.service.AuthService;

import jakarta.validation.Valid;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

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
@Tag(name = "认证", description = "用户认证与鉴权")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    /**
     * 用户登录：校验凭据，签发 JWT。
     */
    @PostMapping("/login")
    @Operation(summary = "用户登录", description = "校验用户名密码，签发 JWT Token")
    public Result<?> login(@Valid @RequestBody LoginRequestDTO request) {
        return Result.success(authService.login(request));
    }

    /**
     * 查询当前登录用户信息（需认证）。
     */
    @GetMapping("/me")
    @Operation(summary = "当前用户信息", description = "查询当前登录用户信息，需认证")
    public Result<?> me(HttpServletRequest request) {
        Object principal = request.getUserPrincipal();
        if (principal == null) {
            return Result.error(ResultCode.UNAUTHORIZED);
        }
        return Result.success(authService.getCurrentUser(principal.toString()));
    }
}
