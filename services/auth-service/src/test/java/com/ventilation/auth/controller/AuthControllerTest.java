package com.ventilation.auth.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ventilation.auth.dto.LoginRequest;
import com.ventilation.auth.dto.RegisterRequest;
import com.ventilation.auth.dto.TokenResponse;
import com.ventilation.auth.service.AuthService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.ventilation.auth.config.SecurityConfig;

@WebMvcTest(AuthController.class)
@Import(SecurityConfig.class)
class AuthControllerTest {

    @Autowired MockMvc mockMvc;
    @Autowired ObjectMapper objectMapper;
    @MockBean AuthService authService;

    private TokenResponse fakeTokens() {
        return new TokenResponse(
                "access.token.here",
                "refresh.token.here",
                Map.of("id", 1L, "username", "alice", "email", "alice@test.com", "role", "operator")
        );
    }

    @Test
    void health_returns200WithStatus() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"))
                .andExpect(jsonPath("$.service").value("auth-service"));
    }

    @Test
    void register_validPayload_returns201() throws Exception {
        when(authService.register(any())).thenReturn(fakeTokens());

        RegisterRequest req = new RegisterRequest();
        req.setUsername("alice");
        req.setEmail("alice@test.com");
        req.setPassword("password123");

        mockMvc.perform(post("/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.access_token").value("access.token.here"))
                .andExpect(jsonPath("$.refresh_token").value("refresh.token.here"));
    }

    @Test
    void register_conflictUsername_returns409() throws Exception {
        when(authService.register(any()))
                .thenThrow(new ResponseStatusException(HttpStatus.CONFLICT, "Conflict"));

        RegisterRequest req = new RegisterRequest();
        req.setUsername("alice");
        req.setEmail("alice@test.com");
        req.setPassword("password123");

        mockMvc.perform(post("/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isConflict());
    }

    @Test
    void login_validCredentials_returns200() throws Exception {
        when(authService.login(any())).thenReturn(fakeTokens());

        LoginRequest req = new LoginRequest();
        req.setUsername("alice");
        req.setPassword("password123");

        mockMvc.perform(post("/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.access_token").exists());
    }

    @Test
    void login_wrongCredentials_returns401() throws Exception {
        when(authService.login(any()))
                .thenThrow(new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Bad creds"));

        LoginRequest req = new LoginRequest();
        req.setUsername("alice");
        req.setPassword("wrong");

        mockMvc.perform(post("/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void me_withValidToken_returns200() throws Exception {
        when(authService.me("good.token"))
                .thenReturn(Map.of("id", 1L, "username", "alice", "email", "alice@test.com", "role", "operator"));

        mockMvc.perform(get("/auth/me")
                        .header("Authorization", "Bearer good.token"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("alice"));
    }

    @Test
    void me_withInvalidToken_returns401() throws Exception {
        when(authService.me("bad.token"))
                .thenThrow(new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid"));

        mockMvc.perform(get("/auth/me")
                        .header("Authorization", "Bearer bad.token"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void verify_validToken_returns200() throws Exception {
        when(authService.verify("tok"))
                .thenReturn(Map.of("sub", "1", "role", "operator", "kind", "access"));

        mockMvc.perform(get("/auth/verify").param("token", "tok"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.role").value("operator"));
    }
}
