package com.ventilation.auth.service;

import com.ventilation.auth.dto.LoginRequest;
import com.ventilation.auth.dto.RegisterRequest;
import com.ventilation.auth.dto.TokenResponse;
import com.ventilation.auth.model.User;
import com.ventilation.auth.repository.UserRepository;
import io.jsonwebtoken.Claims;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository users;
    private final JwtService jwt;
    private final PasswordEncoder passwordEncoder;

    public TokenResponse register(RegisterRequest req) {
        if (users.existsByUsername(req.getUsername()) || users.existsByEmail(req.getEmail())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "Користувач з таким логіном чи поштою вже існує");
        }
        User user = new User();
        user.setUsername(req.getUsername());
        user.setEmail(req.getEmail());
        user.setPasswordHash(passwordEncoder.encode(req.getPassword()));
        user.setRole("operator");
        users.save(user);
        return issueTokens(user);
    }

    public TokenResponse login(LoginRequest req) {
        User user = users.findByUsername(req.getUsername())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED,
                        "Неправильний логін або пароль"));
        if (!user.isActive() || !passwordEncoder.matches(req.getPassword(), user.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Неправильний логін або пароль");
        }
        return issueTokens(user);
    }

    public TokenResponse refresh(String refreshToken) {
        Claims claims;
        try {
            claims = jwt.validateToken(refreshToken);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Недійсний токен");
        }
        if (!"refresh".equals(claims.get("kind", String.class))) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Очікувався refresh токен");
        }
        long userId = Long.parseLong(claims.getSubject());
        User user = users.findById(userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED,
                        "Користувача не знайдено"));
        return issueTokens(user);
    }

    public Map<String, Object> me(String token) {
        Claims claims;
        try {
            claims = jwt.validateToken(token);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Недійсний токен");
        }
        long userId = Long.parseLong(claims.getSubject());
        User user = users.findById(userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND,
                        "Користувача не знайдено"));
        return userMap(user);
    }

    public Map<String, Object> verify(String token) {
        try {
            Claims claims = jwt.validateToken(token);
            return Map.of(
                    "sub", claims.getSubject(),
                    "role", claims.get("role", String.class),
                    "kind", claims.get("kind", String.class)
            );
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Недійсний токен");
        }
    }

    private TokenResponse issueTokens(User user) {
        String access = jwt.generateAccessToken(user.getId(), user.getRole(), user.getUsername());
        String refresh = jwt.generateRefreshToken(user.getId(), user.getRole(), user.getUsername());
        return new TokenResponse(access, refresh, userMap(user));
    }

    private Map<String, Object> userMap(User user) {
        return Map.of(
                "id", user.getId(),
                "username", user.getUsername(),
                "email", user.getEmail(),
                "role", user.getRole()
        );
    }
}
