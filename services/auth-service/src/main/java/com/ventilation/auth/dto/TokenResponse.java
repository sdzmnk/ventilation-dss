package com.ventilation.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.util.Map;

@Data @AllArgsConstructor
public class TokenResponse {
    private String access_token;
    private String refresh_token;
    private String token_type = "bearer";
    private Map<String, Object> user;

    public TokenResponse(String accessToken, String refreshToken, Map<String, Object> user) {
        this.access_token = accessToken;
        this.refresh_token = refreshToken;
        this.user = user;
    }
}
