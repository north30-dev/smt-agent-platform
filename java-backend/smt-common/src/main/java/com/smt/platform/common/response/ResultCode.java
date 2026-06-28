package com.smt.platform.common.response;

import lombok.Getter;

/**
 * 业务状态码枚举。
 */
@Getter
public enum ResultCode {

    /** 操作成功 */
    SUCCESS(200, "操作成功"),
    /** 参数错误 */
    PARAM_ERROR(400, "参数错误"),
    /** 未认证或认证已过期 */
    UNAUTHORIZED(401, "未认证或认证已过期"),
    /** 无访问权限 */
    FORBIDDEN(403, "无访问权限"),
    /** 资源不存在 */
    NOT_FOUND(404, "资源不存在"),
    /** 业务处理失败 */
    BIZ_ERROR(500, "业务处理失败"),
    /** 系统内部错误 */
    SYSTEM_ERROR(500, "系统内部错误");

    private final int code;

    private final String message;

    ResultCode(int code, String message) {
        this.code = code;
        this.message = message;
    }
}
