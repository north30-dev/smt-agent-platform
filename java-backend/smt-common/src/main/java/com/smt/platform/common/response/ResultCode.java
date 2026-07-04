package com.smt.platform.common.response;

import lombok.Getter;

/**
 * 业务状态码枚举。
 *
 * <p>m7 改造：补全 409/422/429/503/504 状态码，避免所有非 200 响应都挤在 500，
 * 便于前端按状态码区分处理（冲突/校验/限流/依赖不可用/网关超时）。</p>
 *
 * <p>向后兼容：原 7 个码值（200/400/401/403/404/500/500）保持不变，
 * BIZ_ERROR 与 SYSTEM_ERROR 同为 500 但 message 区分（"业务处理失败" vs "系统内部错误"），
 * 前端可按 message 或新增的 subCode 字段区分。</p>
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
    /** 资源冲突（如唯一约束冲突、并发更新版本不匹配） */
    CONFLICT(409, "资源冲突"),
    /** 数据校验失败（JSR-380 校验未通过） */
    VALIDATION_FAILED(422, "数据校验失败"),
    /** 请求过于频繁（限流触发） */
    TOO_MANY_REQUESTS(429, "请求过于频繁"),
    /** 业务处理失败（应用层业务规则不满足） */
    BIZ_ERROR(500, "业务处理失败"),
    /** 系统内部错误（未捕获异常、DB 异常等） */
    SYSTEM_ERROR(500, "系统内部错误"),
    /** 依赖服务不可用（如 Redis/Kafka/Milvus 不可达） */
    SERVICE_UNAVAILABLE(503, "依赖服务不可用"),
    /** 网关超时（上游服务响应超时） */
    GATEWAY_TIMEOUT(504, "网关超时");

    private final int code;

    private final String message;

    ResultCode(int code, String message) {
        this.code = code;
        this.message = message;
    }
}
