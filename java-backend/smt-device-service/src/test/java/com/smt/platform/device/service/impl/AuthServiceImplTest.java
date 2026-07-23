package com.smt.platform.device.service.impl;

import com.smt.platform.common.utils.JwtUtil;
import com.smt.platform.device.config.SecurityProperties;
import com.smt.platform.device.model.dto.CurrentUserDTO;
import com.smt.platform.device.model.dto.LoginRequestDTO;
import com.smt.platform.device.model.dto.LoginResponseDTO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * AuthServiceImpl 单元测试（Mockito mock JwtUtil/PasswordEncoder/SecurityProperties，不依赖真实基础设施）。
 */
@ExtendWith(MockitoExtension.class)
class AuthServiceImplTest {

    @Mock
    private JwtUtil jwtUtil;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private SecurityProperties securityProperties;

    @InjectMocks
    private AuthServiceImpl authService;

    @BeforeEach
    void setUp() {
        SecurityProperties.Admin admin = new SecurityProperties.Admin();
        admin.setUsername("admin");
        admin.setPassword("$2a$10$hashedPassword");
        lenient().when(securityProperties.getAdmin()).thenReturn(admin);

        SecurityProperties.Jwt jwt = new SecurityProperties.Jwt();
        jwt.setExpirySeconds(86400L);
        lenient().when(securityProperties.getJwt()).thenReturn(jwt);
    }

    @Nested
    @DisplayName("login")
    class LoginTest {

        @Test
        @DisplayName("should return token when credentials are valid")
        void shouldReturnToken_whenCredentialsAreValid() {
            LoginRequestDTO request = new LoginRequestDTO();
            request.setUsername("admin");
            request.setPassword("correct-password");
            when(passwordEncoder.matches("correct-password", "$2a$10$hashedPassword")).thenReturn(true);
            when(jwtUtil.generateToken(eq("admin"), eq(List.of("ADMIN")), anyLong()))
                    .thenReturn("mock-jwt-token");

            LoginResponseDTO response = authService.login(request);

            assertThat(response.getToken()).isEqualTo("mock-jwt-token");
            assertThat(response.getTokenType()).isEqualTo("Bearer");
            assertThat(response.getExpiresIn()).isEqualTo(86400L);
            assertThat(response.getUsername()).isEqualTo("admin");
            assertThat(response.getRoles()).containsExactly("ADMIN");
            verify(jwtUtil).generateToken(eq("admin"), eq(List.of("ADMIN")), anyLong());
        }

        @Test
        @DisplayName("should throw BadCredentialsException when username is wrong")
        void shouldThrowBadCredentialsException_whenUsernameIsWrong() {
            LoginRequestDTO request = new LoginRequestDTO();
            request.setUsername("wrong-user");
            request.setPassword("any-password");

            assertThatThrownBy(() -> authService.login(request))
                    .isInstanceOf(BadCredentialsException.class)
                    .hasMessageContaining("用户名或密码错误");
        }

        @Test
        @DisplayName("should throw BadCredentialsException when password is wrong")
        void shouldThrowBadCredentialsException_whenPasswordIsWrong() {
            LoginRequestDTO request = new LoginRequestDTO();
            request.setUsername("admin");
            request.setPassword("wrong-password");
            when(passwordEncoder.matches("wrong-password", "$2a$10$hashedPassword")).thenReturn(false);

            assertThatThrownBy(() -> authService.login(request))
                    .isInstanceOf(BadCredentialsException.class)
                    .hasMessageContaining("用户名或密码错误");
        }

        @Test
        @DisplayName("should call PasswordEncoder.matches when login")
        void shouldCallPasswordEncoder_whenLogin() {
            LoginRequestDTO request = new LoginRequestDTO();
            request.setUsername("admin");
            request.setPassword("test-password");
            when(passwordEncoder.matches("test-password", "$2a$10$hashedPassword")).thenReturn(true);
            when(jwtUtil.generateToken(eq("admin"), eq(List.of("ADMIN")), anyLong()))
                    .thenReturn("token");

            authService.login(request);

            verify(passwordEncoder).matches("test-password", "$2a$10$hashedPassword");
        }
    }

    @Nested
    @DisplayName("getCurrentUser")
    class GetCurrentUserTest {

        @Test
        @DisplayName("should return current user when username provided")
        void shouldReturnCurrentUser_whenUsernameProvided() {
            CurrentUserDTO user = authService.getCurrentUser("admin");

            assertThat(user.getUsername()).isEqualTo("admin");
            assertThat(user.isAuthenticated()).isTrue();
        }
    }
}
