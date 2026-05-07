package com.ventilation.auth.service;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.MalformedJwtException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import static org.assertj.core.api.Assertions.*;

class JwtServiceTest {

    private JwtService jwtService;

    @BeforeEach
    void setUp() {
        jwtService = new JwtService();
        ReflectionTestUtils.setField(jwtService, "jwtSecret", "test-secret-for-unit-tests-minimum-32-chars!!");
        ReflectionTestUtils.setField(jwtService, "accessTokenTtl", 3600L);
        ReflectionTestUtils.setField(jwtService, "refreshTokenTtl", 2592000L);
    }

    @Test
    void generateAccessToken_returnsNonBlankToken() {
        String token = jwtService.generateAccessToken(1L, "admin", "alice");
        assertThat(token).isNotBlank();
    }

    @Test
    void generateAccessToken_claimsAreCorrect() {
        String token = jwtService.generateAccessToken(42L, "engineer", "bob");
        Claims claims = jwtService.validateToken(token);

        assertThat(claims.getSubject()).isEqualTo("42");
        assertThat(claims.get("role", String.class)).isEqualTo("engineer");
        assertThat(claims.get("username", String.class)).isEqualTo("bob");
        assertThat(claims.get("kind", String.class)).isEqualTo("access");
    }

    @Test
    void generateRefreshToken_kindIsRefresh() {
        String token = jwtService.generateRefreshToken(7L, "operator", "carol");
        Claims claims = jwtService.validateToken(token);

        assertThat(claims.get("kind", String.class)).isEqualTo("refresh");
        assertThat(claims.getSubject()).isEqualTo("7");
    }

    @Test
    void validateToken_withValidToken_returnsClaims() {
        String token = jwtService.generateAccessToken(1L, "admin", "admin");
        assertThatCode(() -> jwtService.validateToken(token)).doesNotThrowAnyException();
    }

    @Test
    void validateToken_withTamperedToken_throws() {
        String token = jwtService.generateAccessToken(1L, "admin", "admin");
        String tampered = token.substring(0, token.length() - 5) + "XXXXX";
        assertThatThrownBy(() -> jwtService.validateToken(tampered))
                .isInstanceOf(Exception.class);
    }

    @Test
    void validateToken_withTokenSignedByDifferentSecret_throws() {
        JwtService other = new JwtService();
        ReflectionTestUtils.setField(other, "jwtSecret", "completely-different-secret-value-12345678!!");
        ReflectionTestUtils.setField(other, "accessTokenTtl", 3600L);
        ReflectionTestUtils.setField(other, "refreshTokenTtl", 2592000L);

        String foreign = other.generateAccessToken(1L, "admin", "admin");
        assertThatThrownBy(() -> jwtService.validateToken(foreign))
                .isInstanceOf(Exception.class);
    }

    @Test
    void generateAccessToken_expiredToken_throws() {
        JwtService shortLived = new JwtService();
        ReflectionTestUtils.setField(shortLived, "jwtSecret", "test-secret-for-unit-tests-minimum-32-chars!!");
        ReflectionTestUtils.setField(shortLived, "accessTokenTtl", -1L);
        ReflectionTestUtils.setField(shortLived, "refreshTokenTtl", 2592000L);

        String token = shortLived.generateAccessToken(1L, "operator", "user");
        assertThatThrownBy(() -> jwtService.validateToken(token))
                .isInstanceOf(ExpiredJwtException.class);
    }

    @Test
    void validateToken_withMalformedString_throws() {
        assertThatThrownBy(() -> jwtService.validateToken("not.a.jwt"))
                .isInstanceOf(MalformedJwtException.class);
    }

    @Test
    void generateAccessToken_differentUsers_differentTokens() {
        String t1 = jwtService.generateAccessToken(1L, "admin", "alice");
        String t2 = jwtService.generateAccessToken(2L, "operator", "bob");
        assertThat(t1).isNotEqualTo(t2);
    }
}
