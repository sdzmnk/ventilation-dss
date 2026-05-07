package com.ventilation.auth.controller;

import com.ventilation.auth.dto.LoginRequest;
import com.ventilation.auth.dto.RefreshRequest;
import com.ventilation.auth.dto.RegisterRequest;
import com.ventilation.auth.dto.TokenResponse;
import com.ventilation.auth.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok", "service", "auth-service");
    }

    @PostMapping("/auth/register")
    @ResponseStatus(HttpStatus.CREATED)
    public TokenResponse register(@Valid @RequestBody RegisterRequest req) {
        return authService.register(req);
    }

    @PostMapping("/auth/login")
    public TokenResponse login(@Valid @RequestBody LoginRequest req) {
        return authService.login(req);
    }

    @PostMapping("/auth/refresh")
    public TokenResponse refresh(@Valid @RequestBody RefreshRequest req) {
        return authService.refresh(req.getRefresh_token());
    }

    @GetMapping("/auth/me")
    public Map<String, Object> me(@RequestHeader("Authorization") String authHeader) {
        String token = authHeader.startsWith("Bearer ") ? authHeader.substring(7) : authHeader;
        return authService.me(token);
    }

    @GetMapping("/auth/verify")
    public Map<String, Object> verify(@RequestParam String token) {
        return authService.verify(token);
    }
}
