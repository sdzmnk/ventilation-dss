package com.ventilation.auth.service;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Date;
import java.util.UUID;

@Service
public class JwtService {

    @Value("${jwt.secret}")
    private String jwtSecret;

    @Value("${jwt.access-token-ttl}")
    private long accessTokenTtl;

    @Value("${jwt.refresh-token-ttl}")
    private long refreshTokenTtl;

    public String generateAccessToken(long userId, String role, String username) {
        return buildToken(String.valueOf(userId), role, username, "access", accessTokenTtl);
    }

    public String generateRefreshToken(long userId, String role, String username) {
        return buildToken(String.valueOf(userId), role, username, "refresh", refreshTokenTtl);
    }

    private String buildToken(String subject, String role, String username, String kind, long ttlSeconds) {
        Date now = new Date();
        Date expiry = new Date(now.getTime() + ttlSeconds * 1000L);
        return Jwts.builder()
                .subject(subject)
                .claim("role", role)
                .claim("username", username)
                .claim("kind", kind)
                .claim("jti", UUID.randomUUID().toString())
                .issuedAt(now)
                .expiration(expiry)
                .signWith(signingKey())
                .compact();
    }

    public Claims validateToken(String token) {
        return Jwts.parser()
                .verifyWith(signingKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    private SecretKey signingKey() {
        byte[] bytes = jwtSecret.getBytes(StandardCharsets.UTF_8);
        // Ensure at least 32 bytes for HMAC-SHA256
        if (bytes.length < 32) {
            bytes = Arrays.copyOf(bytes, 32);
        }
        return new SecretKeySpec(bytes, "HmacSHA256");
    }
}
