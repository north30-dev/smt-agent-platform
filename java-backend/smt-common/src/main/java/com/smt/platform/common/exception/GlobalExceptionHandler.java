package com.smt.platform.common.exception;

import com.smt.platform.common.response.Result;
import com.smt.platform.common.response.ResultCode;
import jakarta.validation.ConstraintViolationException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.NoHandlerFoundException;

import java.util.stream.Collectors;

/**
 * 全局异常处理器。
 *
 * <p>统一捕获业务异常、参数校验异常及未知异常，返回 {@link Result} 结构，
 * 不向前端暴露堆栈信息。</p>
 *
 * <p>P0-4 修复：新增 {@link AuthenticationException} 与 {@link AccessDeniedException} 处理器，
 * 与 {@code AuthErrorHandlers} 配合，确保 401/403 在异常链路中也返回 JSON。</p>
 *
 * <p>M4 修复：{@link #handleBizException} 改用 {@link ResponseEntity} 动态映射 HTTP 状态码，
 * 使 HTTP status 与 {@link ResultCode#getCode()} 对齐（如 NOT_FOUND → 404、PARAM_ERROR → 400）；
 * 新增 {@link MissingServletRequestParameterException}、
 * {@link MethodArgumentTypeMismatchException}、
 * {@link NoHandlerFoundException}、
 * {@link HttpMessageNotReadableException} 四类异常处理器，
 * 不再走兜底 500。</p>
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * 捕获业务异常，HTTP 状态码与 {@link ResultCode#getCode()} 对齐。
     *
     * <p>M4 修复：原先无 {@code @ResponseStatus} 导致 HTTP 200 + body code 404 的语义错位。
     * 现通过 {@link ResponseEntity} 动态设置 HTTP 状态码，返回体仍为 {@link Result}。</p>
     */
    @ExceptionHandler(BizException.class)
    public ResponseEntity<Result<Void>> handleBizException(BizException e) {
        log.warn("业务异常: {}", e.getMessage());
        HttpStatus status = HttpStatus.resolve(e.getResultCode().getCode());
        if (status == null) {
            status = HttpStatus.INTERNAL_SERVER_ERROR;
        }
        return ResponseEntity.status(status).body(Result.error(e.getResultCode(), e.getMessage()));
    }

    /**
     * 捕获请求体参数校验异常（@Valid + @RequestBody）。
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleMethodArgumentNotValid(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(fe -> fe.getField() + ":" + fe.getDefaultMessage())
                .collect(Collectors.joining("; "));
        log.warn("参数校验失败: {}", message);
        return Result.error(ResultCode.PARAM_ERROR, message);
    }

    /**
     * 捕获路径/表单参数校验异常（@Validated + @RequestParam / @PathVariable）。
     */
    @ExceptionHandler(ConstraintViolationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleConstraintViolation(ConstraintViolationException e) {
        String message = e.getConstraintViolations().stream()
                .map(cv -> cv.getPropertyPath() + ":" + cv.getMessage())
                .collect(Collectors.joining("; "));
        log.warn("约束校验失败: {}", message);
        return Result.error(ResultCode.PARAM_ERROR, message);
    }

    /**
     * 捕获 Spring Security 认证异常（P0-4 修复）：未提供 token 或 token 无效。
     */
    @ExceptionHandler(AuthenticationException.class)
    @ResponseStatus(HttpStatus.UNAUTHORIZED)
    public Result<Void> handleAuthenticationException(AuthenticationException e) {
        log.warn("认证失败: {}", e.getMessage());
        return Result.error(ResultCode.UNAUTHORIZED, "未认证或认证已过期");
    }

    /**
     * 捕获 Spring Security 授权异常（P0-4 修复）：已认证但权限不足。
     */
    @ExceptionHandler(AccessDeniedException.class)
    @ResponseStatus(HttpStatus.FORBIDDEN)
    public Result<Void> handleAccessDeniedException(AccessDeniedException e) {
        log.warn("访问被拒绝: {}", e.getMessage());
        return Result.error(ResultCode.FORBIDDEN, "无访问权限");
    }

    /**
     * 捕获缺失必填请求参数（{@code @RequestParam required=true} 未传）。
     *
     * <p>M4 修复：原先走兜底 500，现返回 400 + 具体缺失参数名。</p>
     */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleMissingParam(MissingServletRequestParameterException e) {
        log.warn("缺少必填参数: {}", e.getParameterName());
        return Result.error(ResultCode.PARAM_ERROR, "缺少必填参数: " + e.getParameterName());
    }

    /**
     * 捕获路径变量类型转换失败（如 {@code /api/device/abc} 中 Long 转换失败）。
     *
     * <p>M4 修复：原先走兜底 500，现返回 400 + 具体参数名。</p>
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleTypeMismatch(MethodArgumentTypeMismatchException e) {
        log.warn("参数类型不匹配: {}={}", e.getName(), e.getValue());
        return Result.error(ResultCode.PARAM_ERROR, "参数类型不匹配: " + e.getName());
    }

    /**
     * 捕获请求体 JSON 格式错误（反序列化失败或 body 缺失）。
     *
     * <p>M4 修复：原先走兜底 500，现返回 400。</p>
     */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleNotReadable(HttpMessageNotReadableException e) {
        log.warn("请求体格式错误: {}", e.getMessage());
        return Result.error(ResultCode.PARAM_ERROR, "请求体格式错误或缺失");
    }

    /**
     * 捕获请求路径不存在。
     *
     * <p>M4 修复：原先走默认 Whitelabel 404 页，现返回 JSON 404。
     * 需配合 {@code spring.mvc.throw-exception-if-no-handler-found=true}。</p>
     */
    @ExceptionHandler(NoHandlerFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public Result<Void> handleNoHandlerFound(NoHandlerFoundException e) {
        log.warn("路径不存在: {}", e.getRequestURL());
        return Result.error(ResultCode.NOT_FOUND, "请求路径不存在: " + e.getRequestURL());
    }

    /**
     * 兜底捕获未知异常，避免堆栈外泄。
     */
    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Result<Void> handleException(Exception e) {
        log.error("系统异常", e);
        return Result.error(ResultCode.SYSTEM_ERROR);
    }
}
