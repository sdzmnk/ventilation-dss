package com.ventilation.user.controller;

import com.ventilation.user.dto.ProfileIn;
import com.ventilation.user.dto.ProfileOut;
import com.ventilation.user.dto.RoleIn;
import com.ventilation.user.service.UserService;
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
public class UserController {

    private final UserService userService;

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok", "service", "user-service");
    }

    @GetMapping("/users")
    public List<ProfileOut> listUsers(Authentication auth) {
        requireAdmin(auth);
        return userService.listAll();
    }

    @GetMapping("/users/me")
    public ProfileOut me(Authentication auth) {
        return userService.getProfile(userId(auth));
    }

    @PutMapping("/users/me")
    public ProfileOut updateMe(@RequestBody ProfileIn data, Authentication auth) {
        return userService.updateProfile(userId(auth), data);
    }

    @GetMapping("/users/{id}")
    public ProfileOut getUser(@PathVariable Long id, Authentication auth) {
        if (!isAdmin(auth) && !userId(auth).equals(id)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Недостатньо прав");
        }
        return userService.getProfile(id);
    }

    @PutMapping("/users/{id}")
    public ProfileOut updateUser(@PathVariable Long id,
                                  @RequestBody ProfileIn data,
                                  Authentication auth) {
        requireAdmin(auth);
        return userService.updateProfile(id, data);
    }

    @PatchMapping("/users/{id}/role")
    public ProfileOut changeRole(@PathVariable Long id,
                                  @RequestBody RoleIn body,
                                  Authentication auth) {
        requireAdmin(auth);
        return userService.changeRole(id, body.getRole());
    }

    @DeleteMapping("/users/{id}")
    public Map<String, Long> deleteUser(@PathVariable Long id, Authentication auth) {
        requireAdmin(auth);
        userService.delete(id);
        return Map.of("deleted", id);
    }

    private Long userId(Authentication auth) {
        return (Long) auth.getPrincipal();
    }

    private boolean isAdmin(Authentication auth) {
        return auth.getAuthorities().contains(new SimpleGrantedAuthority("ROLE_ADMIN"));
    }

    private void requireAdmin(Authentication auth) {
        if (!isAdmin(auth)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Доступ дозволено лише адміністратору");
        }
    }
}
