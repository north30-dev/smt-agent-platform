package com.smt.platform.device.model.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

/**
 * 登录响应 DTO。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LoginResponseDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** JWT Token */
    @NotBlank(message = "Token 不能为空")
    @Size(max = 2048, message = "Token 长度不能超过 2048 个字符")
    private String token;

    /** Token 类型（固定 "Bearer"） */
    @NotBlank(message = "Token 类型不能为空")
    @Size(max = 16, message = "Token 类型长度不能超过 16 个字符")
    private String tokenType;

    /** 过期时间（秒） */
    private long expiresIn;

    /** 用户名 */
    @NotBlank(message = "用户名不能为空")
    @Size(max = 64, message = "用户名长度不能超过 64 个字符")
    private String username;

    /** 角色列表 */
    private List<String> roles;
}
