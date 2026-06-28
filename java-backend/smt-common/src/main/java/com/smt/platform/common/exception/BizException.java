package com.smt.platform.common.exception;

import com.smt.platform.common.response.ResultCode;
import lombok.Getter;

/**
 * 自定义业务异常。
 *
 * <p>业务层遇到可预期的业务错误时抛出，由 {@link GlobalExceptionHandler} 统一捕获。</p>
 */
@Getter
public class BizException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    /** 对应的业务状态码 */
    private final ResultCode resultCode;

    public BizException(ResultCode resultCode) {
        super(resultCode.getMessage());
        this.resultCode = resultCode;
    }

    public BizException(ResultCode resultCode, String message) {
        super(message);
        this.resultCode = resultCode;
    }

    public BizException(String message) {
        super(message);
        this.resultCode = ResultCode.BIZ_ERROR;
    }
}
