package com.smt.platform.common.exception;

import com.smt.platform.common.response.ResultCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * GlobalExceptionHandler 单元测试（直接调用 handler 方法，不启动 Spring 上下文）。
 */
class GlobalExceptionHandlerTest {

    private GlobalExceptionHandler handler;

    @BeforeEach
    void setUp() {
        handler = new GlobalExceptionHandler();
    }

    @Nested
    @DisplayName("handleBizException")
    class HandleBizExceptionTest {

        @Test
        @DisplayName("should return 404 when BizException with NOT_FOUND")
        void shouldReturn404_whenBizExceptionWithNotFound() {
            BizException ex = new BizException(ResultCode.NOT_FOUND, "设备不存在");

            ResponseEntity<?> response = handler.handleBizException(ex);

            assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
            assertThat(response.getBody()).isNotNull();
        }

        @Test
        @DisplayName("should return 400 when BizException with PARAM_ERROR")
        void shouldReturn400_whenBizExceptionWithParamError() {
            BizException ex = new BizException(ResultCode.PARAM_ERROR, "参数错误");

            ResponseEntity<?> response = handler.handleBizException(ex);

            assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        }

        @Test
        @DisplayName("should return 500 when BizException with unknown code")
        void shouldReturn500_whenBizExceptionWithUnknownCode() {
            BizException ex = new BizException("自定义异常");

            ResponseEntity<?> response = handler.handleBizException(ex);

            assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @Nested
    @DisplayName("handleMethodArgumentNotValid")
    class HandleMethodArgumentNotValidTest {

        @Test
        @DisplayName("should return 400 when method argument not valid")
        void shouldReturn400_whenMethodArgumentNotValid() {
            BindingResult bindingResult = mock(BindingResult.class);
            FieldError fieldError = new FieldError("request", "username", "不能为空");
            when(bindingResult.getFieldErrors()).thenReturn(java.util.List.of(fieldError));
            MethodArgumentNotValidException ex = new MethodArgumentNotValidException(null, bindingResult);

            var result = handler.handleMethodArgumentNotValid(ex);

            assertThat(result.getCode()).isEqualTo(400);
            assertThat(result.getMessage()).contains("username");
        }
    }

    @Nested
    @DisplayName("handleConstraintViolation")
    class HandleConstraintViolationTest {

        @Test
        @DisplayName("should return 400 when constraint violation")
        void shouldReturn400_whenConstraintViolation() {
            ConstraintViolation<?> violation = mock(ConstraintViolation.class);
            jakarta.validation.Path path = mock(jakarta.validation.Path.class);
            when(path.toString()).thenReturn("deviceId");
            when(violation.getPropertyPath()).thenReturn(path);
            when(violation.getMessage()).thenReturn("必须大于0");
            ConstraintViolationException ex = new ConstraintViolationException(Set.of(violation));

            var result = handler.handleConstraintViolation(ex);

            assertThat(result.getCode()).isEqualTo(400);
            assertThat(result.getMessage()).contains("deviceId");
        }
    }

    @Nested
    @DisplayName("handleAuthenticationException")
    class HandleAuthenticationExceptionTest {

        @Test
        @DisplayName("should return 401 when authentication exception")
        void shouldReturn401_whenAuthenticationException() {
            BadCredentialsException ex = new BadCredentialsException("用户名或密码错误");

            var result = handler.handleAuthenticationException(ex);

            assertThat(result.getCode()).isEqualTo(401);
            assertThat(result.getMessage()).contains("未认证或认证已过期");
        }
    }

    @Nested
    @DisplayName("handleAccessDeniedException")
    class HandleAccessDeniedExceptionTest {

        @Test
        @DisplayName("should return 403 when access denied")
        void shouldReturn403_whenAccessDenied() {
            AccessDeniedException ex = new AccessDeniedException("无权限");

            var result = handler.handleAccessDeniedException(ex);

            assertThat(result.getCode()).isEqualTo(403);
            assertThat(result.getMessage()).contains("无访问权限");
        }
    }

    @Nested
    @DisplayName("handleMissingParam")
    class HandleMissingParamTest {

        @Test
        @DisplayName("should return 400 when missing parameter")
        void shouldReturn400_whenMissingParameter() {
            MissingServletRequestParameterException ex =
                    new MissingServletRequestParameterException("deviceId", "Long");

            var result = handler.handleMissingParam(ex);

            assertThat(result.getCode()).isEqualTo(400);
            assertThat(result.getMessage()).contains("deviceId");
        }
    }

    @Nested
    @DisplayName("handleTypeMismatch")
    class HandleTypeMismatchTest {

        @Test
        @DisplayName("should return 400 when type mismatch")
        void shouldReturn400_whenTypeMismatch() {
            MethodArgumentTypeMismatchException ex =
                    new MethodArgumentTypeMismatchException("abc", Long.class, "deviceId", null, new RuntimeException());

            var result = handler.handleTypeMismatch(ex);

            assertThat(result.getCode()).isEqualTo(400);
            assertThat(result.getMessage()).contains("deviceId");
        }
    }

    @Nested
    @DisplayName("handleException")
    class HandleExceptionTest {

        @Test
        @DisplayName("should return 500 when unknown exception")
        void shouldReturn500_whenUnknownException() {
            Exception ex = new RuntimeException("意外错误");

            var result = handler.handleException(ex);

            assertThat(result.getCode()).isEqualTo(500);
        }
    }
}
