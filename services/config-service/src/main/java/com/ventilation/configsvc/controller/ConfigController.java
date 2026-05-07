package com.ventilation.configsvc.controller;

import com.ventilation.configsvc.dto.ParamIn;
import com.ventilation.configsvc.dto.ParamOut;
import com.ventilation.configsvc.service.ConfigService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

@RestController
@RequiredArgsConstructor
public class ConfigController {

    private final ConfigService configService;

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok", "service", "config-service");
    }

    @GetMapping("/config")
    public List<ParamOut> listParams(Authentication auth) {
        return configService.listAll();
    }

    @GetMapping("/config/{key}")
    public ParamOut getParam(@PathVariable String key, Authentication auth) {
        return configService.getByKey(key);
    }

    @PutMapping("/config/{key}")
    public ParamOut upsertParam(@PathVariable String key,
                                 @RequestBody ParamIn body,
                                 Authentication auth) {
        requireAdmin(auth);
        return configService.upsert(key, body);
    }

    @DeleteMapping("/config/{key}")
    public Map<String, String> deleteParam(@PathVariable String key, Authentication auth) {
        requireAdmin(auth);
        configService.delete(key);
        return Map.of("deleted", key);
    }

    private void requireAdmin(Authentication auth) {
        if (auth == null || !auth.getAuthorities().contains(new SimpleGrantedAuthority("ROLE_ADMIN"))) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN,
                    "Лише адміністратор може змінювати конфігурацію");
        }
    }
}
