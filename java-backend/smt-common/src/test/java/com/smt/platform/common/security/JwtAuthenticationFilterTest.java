package com.smt.platform.common.security;

import com.smt.platform.common.utils.JwtUtil;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * JwtAuthenticationFilter 单元测试（Mockito mock JwtUtil，不依赖 Spring Security 上下文）。
 */
@ExtendWith(MockitoExtension.class)
class JwtAuthenticationFilterTest {

    @Mock
    private JwtUtil jwtUtil;

    @Mock
    private FilterChain filterChain;

    @InjectMocks
    private JwtAuthenticationFilter jwtAuthenticationFilter;

    @BeforeEach
    void setUp() {
        SecurityContextHolder.clearContext();
        ReflectionTestUtils.setField(jwtAuthenticationFilter, "headerName", "Authorization");
        ReflectionTestUtils.setField(jwtAuthenticationFilter, "headerPrefix", "Bearer ");
    }

    @Nested
    @DisplayName("doFilterInternal")
    class DoFilterInternalTest {

        @Test
        @DisplayName("should set authentication when valid Bearer token")
        void shouldSetAuthentication_whenValidBearerToken() throws Exception {
            Claims claims = org.mockito.Mockito.mock(Claims.class);
            when(claims.getSubject()).thenReturn("admin");
            when(claims.get("roles")).thenReturn(List.of("ADMIN"));
            when(jwtUtil.parseToken("valid-token")).thenReturn(claims);

            MockHttpServletRequest request = new MockHttpServletRequest();
            request.addHeader("Authorization", "Bearer valid-token");
            MockHttpServletResponse response = new MockHttpServletResponse();

            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            assertThat(auth).isNotNull();
            assertThat(auth.getPrincipal()).isEqualTo("admin");
            assertThat(auth.getAuthorities()).hasSize(1);
            assertThat(auth.getAuthorities().iterator().next().getAuthority()).isEqualTo("ROLE_ADMIN");
            verify(filterChain).doFilter(request, response);
        }

        @Test
        @DisplayName("should not set authentication when no Authorization header")
        void shouldNotSetAuthentication_whenNoAuthHeader() throws Exception {
            MockHttpServletRequest request = new MockHttpServletRequest();
            MockHttpServletResponse response = new MockHttpServletResponse();

            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            assertThat(auth).isNull();
            verify(filterChain).doFilter(request, response);
        }

        @Test
        @DisplayName("should not set authentication when token has no Bearer prefix")
        void shouldNotSetAuthentication_whenTokenHasNoBearerPrefix() throws Exception {
            MockHttpServletRequest request = new MockHttpServletRequest();
            request.addHeader("Authorization", "InvalidPrefix token");
            MockHttpServletResponse response = new MockHttpServletResponse();

            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            assertThat(auth).isNull();
        }

        @Test
        @DisplayName("should not set authentication when token is expired")
        void shouldNotSetAuthentication_whenTokenIsExpired() throws Exception {
            when(jwtUtil.parseToken("expired-token")).thenThrow(new JwtException("Token expired"));

            MockHttpServletRequest request = new MockHttpServletRequest();
            request.addHeader("Authorization", "Bearer expired-token");
            MockHttpServletResponse response = new MockHttpServletResponse();

            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            assertThat(auth).isNull();
            verify(filterChain).doFilter(request, response);
        }

        @Test
        @DisplayName("should not set authentication when token is tampered")
        void shouldNotSetAuthentication_whenTokenIsTampered() throws Exception {
            when(jwtUtil.parseToken("tampered-token")).thenThrow(new JwtException("Invalid signature"));

            MockHttpServletRequest request = new MockHttpServletRequest();
            request.addHeader("Authorization", "Bearer tampered-token");
            MockHttpServletResponse response = new MockHttpServletResponse();

            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            assertThat(auth).isNull();
        }

        @Test
        @DisplayName("should parse roles when roles claim present")
        void shouldParseRoles_whenRolesClaimPresent() throws Exception {
            Claims claims = org.mockito.Mockito.mock(Claims.class);
            when(claims.getSubject()).thenReturn("admin");
            when(claims.get("roles")).thenReturn(List.of("ADMIN", "OPERATOR"));
            when(jwtUtil.parseToken("token-with-roles")).thenReturn(claims);

            MockHttpServletRequest request = new MockHttpServletRequest();
            request.addHeader("Authorization", "Bearer token-with-roles");
            MockHttpServletResponse response = new MockHttpServletResponse();

            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            assertThat(auth.getAuthorities()).hasSize(2);
            assertThat(auth.getAuthorities()).extracting("authority")
                    .containsExactlyInAnyOrder("ROLE_ADMIN", "ROLE_OPERATOR");
        }

        @Test
        @DisplayName("should return empty authorities when no roles claim")
        void shouldReturnEmptyAuthorities_whenNoRolesClaim() throws Exception {
            Claims claims = org.mockito.Mockito.mock(Claims.class);
            when(claims.getSubject()).thenReturn("user");
            when(claims.get("roles")).thenReturn(null);
            when(jwtUtil.parseToken("token-no-roles")).thenReturn(claims);

            MockHttpServletRequest request = new MockHttpServletRequest();
            request.addHeader("Authorization", "Bearer token-no-roles");
            MockHttpServletResponse response = new MockHttpServletResponse();

            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            assertThat(auth.getAuthorities()).isEmpty();
        }
    }

    @Nested
    @DisplayName("extractToken")
    class ExtractTokenTest {

        @Test
        @DisplayName("should extract token when valid Bearer header")
        void shouldExtractToken_whenValidBearerHeader() throws Exception {
            Claims claims = org.mockito.Mockito.mock(Claims.class);
            when(claims.getSubject()).thenReturn("admin");
            when(claims.get("roles")).thenReturn(List.of("ADMIN"));
            when(jwtUtil.parseToken("my-token")).thenReturn(claims);

            MockHttpServletRequest request = new MockHttpServletRequest();
            request.addHeader("Authorization", "Bearer my-token");
            MockHttpServletResponse response = new MockHttpServletResponse();

            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            verify(jwtUtil).parseToken("my-token");
        }

        @Test
        @DisplayName("should handle empty Authorization header")
        void shouldHandleEmptyAuthorizationHeader() throws Exception {
            MockHttpServletRequest request = new MockHttpServletRequest();
            request.addHeader("Authorization", "");
            MockHttpServletResponse response = new MockHttpServletResponse();

            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            assertThat(auth).isNull();
        }

        @Test
        @DisplayName("should handle Bearer with no token")
        void shouldHandleBearerWithNoToken() throws Exception {
            MockHttpServletRequest request = new MockHttpServletRequest();
            request.addHeader("Authorization", "Bearer ");
            MockHttpServletResponse response = new MockHttpServletResponse();

            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            assertThat(auth).isNull();
        }
    }
}
