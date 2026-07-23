package com.smt.platform.device.controller;

import com.smt.platform.common.exception.GlobalExceptionHandler;
import com.smt.platform.device.model.dto.LoginRequestDTO;
import com.smt.platform.device.model.dto.LoginResponseDTO;
import com.smt.platform.device.service.AuthService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * AuthController MockMvc 测试（standalone，不加载 Spring 上下文）。
 */
@ExtendWith(MockitoExtension.class)
class AuthControllerTest {

    @Mock
    private AuthService authService;

    @InjectMocks
    private AuthController authController;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(authController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Nested
    @DisplayName("login")
    class LoginTest {

        @Test
        @DisplayName("should return 200 and token when login success")
        void shouldReturn200AndToken_whenLoginSuccess() throws Exception {
            LoginResponseDTO response = new LoginResponseDTO(
                    "mock-jwt-token", "Bearer", 86400L, "admin", List.of("ADMIN"));
            when(authService.login(any(LoginRequestDTO.class))).thenReturn(response);

            String json = "{\"username\":\"admin\",\"password\":\"correct-password\"}";

            mockMvc.perform(post("/api/auth/login")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(json))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.code").value(200))
                    .andExpect(jsonPath("$.data.token").value("mock-jwt-token"))
                    .andExpect(jsonPath("$.data.tokenType").value("Bearer"))
                    .andExpect(jsonPath("$.data.username").value("admin"))
                    .andExpect(jsonPath("$.data.roles[0]").value("ADMIN"));
        }

        @Test
        @DisplayName("should return 401 when login fails")
        void shouldReturn401_whenLoginFails() throws Exception {
            when(authService.login(any(LoginRequestDTO.class)))
                    .thenThrow(new BadCredentialsException("用户名或密码错误"));

            String json = "{\"username\":\"admin\",\"password\":\"wrong-password\"}";

            mockMvc.perform(post("/api/auth/login")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(json))
                    .andExpect(status().isUnauthorized())
                    .andExpect(jsonPath("$.code").value(401));
        }
    }

    @Nested
    @DisplayName("me")
    class MeTest {

        @Test
        @DisplayName("should return 200 with code 401 when no user principal")
        void shouldReturn200WithCode401_whenNoUserPrincipal() throws Exception {
            mockMvc.perform(get("/api/auth/me"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.code").value(401))
                    .andExpect(jsonPath("$.message").value("未认证或认证已过期"));
        }
    }
}
