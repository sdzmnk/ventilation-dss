package com.ventilation.auth.service;

import com.ventilation.auth.dto.LoginRequest;
import com.ventilation.auth.dto.RegisterRequest;
import com.ventilation.auth.dto.TokenResponse;
import com.ventilation.auth.model.User;
import com.ventilation.auth.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock UserRepository users;
    @Mock JwtService jwt;
    @Mock PasswordEncoder passwordEncoder;
    @InjectMocks AuthService authService;

    private User buildUser(long id, String username, String email, String role, boolean active) {
        User u = new User();
        u.setId(id);
        u.setUsername(username);
        u.setEmail(email);
        u.setPasswordHash("$2a$10$hashedpassword");
        u.setRole(role);
        u.setActive(active);
        return u;
    }

    @BeforeEach
    void setUpJwt() {
        when(jwt.generateAccessToken(anyLong(), anyString(), anyString())).thenReturn("access.token");
        when(jwt.generateRefreshToken(anyLong(), anyString(), anyString())).thenReturn("refresh.token");
    }


    @Test
    void register_success_returnsTokens() {
        when(users.existsByUsername("alice")).thenReturn(false);
        when(users.existsByEmail("alice@test.com")).thenReturn(false);
        when(passwordEncoder.encode("pass123")).thenReturn("hashed");
        User saved = buildUser(1L, "alice", "alice@test.com", "operator", true);
        when(users.save(any(User.class))).thenReturn(saved);

        RegisterRequest req = new RegisterRequest();
        req.setUsername("alice");
        req.setEmail("alice@test.com");
        req.setPassword("pass123");

        TokenResponse resp = authService.register(req);

        assertThat(resp.getAccess_token()).isEqualTo("access.token");
        assertThat(resp.getRefresh_token()).isEqualTo("refresh.token");
        verify(users).save(any(User.class));
    }

    @Test
    void register_duplicateUsername_throws409() {
        when(users.existsByUsername("alice")).thenReturn(true);

        RegisterRequest req = new RegisterRequest();
        req.setUsername("alice");
        req.setEmail("alice@test.com");
        req.setPassword("pass123");

        assertThatThrownBy(() -> authService.register(req))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.CONFLICT));
    }

    @Test
    void register_duplicateEmail_throws409() {
        when(users.existsByUsername("alice")).thenReturn(false);
        when(users.existsByEmail("alice@test.com")).thenReturn(true);

        RegisterRequest req = new RegisterRequest();
        req.setUsername("alice");
        req.setEmail("alice@test.com");
        req.setPassword("pass123");

        assertThatThrownBy(() -> authService.register(req))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.CONFLICT));
    }


    @Test
    void login_success_returnsTokens() {
        User user = buildUser(2L, "bob", "bob@test.com", "engineer", true);
        when(users.findByUsername("bob")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("pass", user.getPasswordHash())).thenReturn(true);

        LoginRequest req = new LoginRequest();
        req.setUsername("bob");
        req.setPassword("pass");

        TokenResponse resp = authService.login(req);
        assertThat(resp.getAccess_token()).isEqualTo("access.token");
    }

    @Test
    void login_wrongPassword_throws401() {
        User user = buildUser(2L, "bob", "bob@test.com", "operator", true);
        when(users.findByUsername("bob")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches(anyString(), anyString())).thenReturn(false);

        LoginRequest req = new LoginRequest();
        req.setUsername("bob");
        req.setPassword("wrong");

        assertThatThrownBy(() -> authService.login(req))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.UNAUTHORIZED));
    }

    @Test
    void login_unknownUser_throws401() {
        when(users.findByUsername("ghost")).thenReturn(Optional.empty());

        LoginRequest req = new LoginRequest();
        req.setUsername("ghost");
        req.setPassword("any");

        assertThatThrownBy(() -> authService.login(req))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.UNAUTHORIZED));
    }

    @Test
    void login_inactiveUser_throws401() {
        User user = buildUser(3L, "inactive", "i@test.com", "operator", false);
        when(users.findByUsername("inactive")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches(anyString(), anyString())).thenReturn(true);

        LoginRequest req = new LoginRequest();
        req.setUsername("inactive");
        req.setPassword("pass");

        assertThatThrownBy(() -> authService.login(req))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.UNAUTHORIZED));
    }


    @Test
    void me_validToken_returnsUserMap() {
        io.jsonwebtoken.Claims claims = mock(io.jsonwebtoken.Claims.class);
        when(claims.getSubject()).thenReturn("5");
        when(jwt.validateToken("good.token")).thenReturn(claims);

        User user = buildUser(5L, "carol", "carol@test.com", "admin", true);
        when(users.findById(5L)).thenReturn(Optional.of(user));

        Map<String, Object> result = authService.me("good.token");

        assertThat(result.get("username")).isEqualTo("carol");
        assertThat(result.get("role")).isEqualTo("admin");
    }

    @Test
    void me_invalidToken_throws401() {
        when(jwt.validateToken("bad.token")).thenThrow(new RuntimeException("invalid"));

        assertThatThrownBy(() -> authService.me("bad.token"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.UNAUTHORIZED));
    }


    @Test
    void verify_validToken_returnsClaims() {
        io.jsonwebtoken.Claims claims = mock(io.jsonwebtoken.Claims.class);
        when(claims.getSubject()).thenReturn("10");
        when(claims.get("role", String.class)).thenReturn("operator");
        when(claims.get("kind", String.class)).thenReturn("access");
        when(jwt.validateToken("valid.token")).thenReturn(claims);

        Map<String, Object> result = authService.verify("valid.token");

        assertThat(result.get("sub")).isEqualTo("10");
        assertThat(result.get("role")).isEqualTo("operator");
        assertThat(result.get("kind")).isEqualTo("access");
    }

    @Test
    void verify_invalidToken_throws401() {
        when(jwt.validateToken("bad")).thenThrow(new RuntimeException("invalid"));

        assertThatThrownBy(() -> authService.verify("bad"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.UNAUTHORIZED));
    }


    @Test
    void refresh_validRefreshToken_returnsNewTokens() {
        io.jsonwebtoken.Claims claims = mock(io.jsonwebtoken.Claims.class);
        when(claims.getSubject()).thenReturn("1");
        when(claims.get("kind", String.class)).thenReturn("refresh");
        when(jwt.validateToken("refresh.tok")).thenReturn(claims);

        User user = buildUser(1L, "admin", "admin@test.com", "admin", true);
        when(users.findById(1L)).thenReturn(Optional.of(user));

        TokenResponse resp = authService.refresh("refresh.tok");
        assertThat(resp.getAccess_token()).isEqualTo("access.token");
    }

    @Test
    void refresh_accessTokenAsRefresh_throws401() {
        io.jsonwebtoken.Claims claims = mock(io.jsonwebtoken.Claims.class);
        when(claims.getSubject()).thenReturn("1");
        when(claims.get("kind", String.class)).thenReturn("access");
        when(jwt.validateToken("access.tok")).thenReturn(claims);

        assertThatThrownBy(() -> authService.refresh("access.tok"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.UNAUTHORIZED));
    }
}
