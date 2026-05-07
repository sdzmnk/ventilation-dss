package com.ventilation.user.controller;

import com.ventilation.user.dto.ProfileIn;
import com.ventilation.user.dto.ProfileOut;
import com.ventilation.user.dto.RoleIn;
import com.ventilation.user.service.UserService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class UserControllerTest {

    @Mock UserService userService;
    @InjectMocks UserController controller;

    private Authentication adminAuth(long userId) {
        return new UsernamePasswordAuthenticationToken(
                userId, null,
                List.of(new SimpleGrantedAuthority("ROLE_ADMIN"))
        );
    }

    private Authentication operatorAuth(long userId) {
        return new UsernamePasswordAuthenticationToken(
                userId, null,
                List.of(new SimpleGrantedAuthority("ROLE_OPERATOR"))
        );
    }

    private ProfileOut sampleProfile(long id, String username, String role) {
        ProfileOut p = new ProfileOut();
        p.setUser_id(id);
        p.setUsername(username);
        p.setRole(role);
        p.setEmail(username + "@test.com");
        return p;
    }

    @Test
    void health_returnsOkMap() {
        Map<String, String> result = controller.health();
        assertThat(result.get("status")).isEqualTo("ok");
        assertThat(result.get("service")).isEqualTo("user-service");
    }

    // ===== GET /users =====

    @Test
    void listUsers_asAdmin_returnsAll() {
        List<ProfileOut> expected = List.of(
                sampleProfile(1L, "alice", "admin"),
                sampleProfile(2L, "bob", "operator")
        );
        when(userService.listAll()).thenReturn(expected);

        List<ProfileOut> result = controller.listUsers(adminAuth(1L));

        assertThat(result).hasSize(2);
        verify(userService).listAll();
    }

    @Test
    void listUsers_asOperator_throws403() {
        assertThatThrownBy(() -> controller.listUsers(operatorAuth(2L)))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.FORBIDDEN));
    }

    // ===== GET /users/me =====

    @Test
    void me_returnsCurrentUserProfile() {
        ProfileOut profile = sampleProfile(3L, "carol", "engineer");
        when(userService.getProfile(3L)).thenReturn(profile);

        ProfileOut result = controller.me(operatorAuth(3L));

        assertThat(result.getUsername()).isEqualTo("carol");
        verify(userService).getProfile(3L);
    }

    // ===== PUT /users/me =====

    @Test
    void updateMe_callsServiceAndReturns() {
        ProfileIn data = new ProfileIn();
        data.setFull_name("Carol Updated");

        ProfileOut updated = sampleProfile(3L, "carol", "operator");
        updated.setFull_name("Carol Updated");
        when(userService.updateProfile(3L, data)).thenReturn(updated);

        ProfileOut result = controller.updateMe(data, operatorAuth(3L));
        assertThat(result.getFull_name()).isEqualTo("Carol Updated");
    }

    // ===== GET /users/{id} =====

    @Test
    void getUser_adminCanAccessAnyUser() {
        ProfileOut profile = sampleProfile(5L, "eve", "operator");
        when(userService.getProfile(5L)).thenReturn(profile);

        ProfileOut result = controller.getUser(5L, adminAuth(1L));
        assertThat(result.getUsername()).isEqualTo("eve");
    }

    @Test
    void getUser_userCanAccessOwnProfile() {
        ProfileOut profile = sampleProfile(5L, "eve", "operator");
        when(userService.getProfile(5L)).thenReturn(profile);

        ProfileOut result = controller.getUser(5L, operatorAuth(5L));
        assertThat(result.getUsername()).isEqualTo("eve");
    }

    @Test
    void getUser_operatorAccessOtherUser_throws403() {
        assertThatThrownBy(() -> controller.getUser(99L, operatorAuth(5L)))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.FORBIDDEN));
    }

    // ===== PUT /users/{id} =====

    @Test
    void updateUser_asAdmin_callsService() {
        ProfileIn data = new ProfileIn();
        data.setFull_name("New Name");

        ProfileOut updated = sampleProfile(5L, "eve", "operator");
        when(userService.updateProfile(5L, data)).thenReturn(updated);

        controller.updateUser(5L, data, adminAuth(1L));
        verify(userService).updateProfile(5L, data);
    }

    @Test
    void updateUser_asOperator_throws403() {
        assertThatThrownBy(() -> controller.updateUser(5L, new ProfileIn(), operatorAuth(2L)))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.FORBIDDEN));
    }

    // ===== PATCH /users/{id}/role =====

    @Test
    void changeRole_asAdmin_callsService() {
        RoleIn body = new RoleIn();
        body.setRole("engineer");

        ProfileOut updated = sampleProfile(5L, "eve", "engineer");
        when(userService.changeRole(5L, "engineer")).thenReturn(updated);

        ProfileOut result = controller.changeRole(5L, body, adminAuth(1L));
        assertThat(result.getRole()).isEqualTo("engineer");
    }

    @Test
    void changeRole_asOperator_throws403() {
        RoleIn body = new RoleIn();
        body.setRole("admin");

        assertThatThrownBy(() -> controller.changeRole(5L, body, operatorAuth(2L)))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.FORBIDDEN));
    }

    // ===== DELETE /users/{id} =====

    @Test
    void deleteUser_asAdmin_callsService() {
        Map<String, Long> result = controller.deleteUser(5L, adminAuth(1L));

        verify(userService).delete(5L);
        assertThat(result.get("deleted")).isEqualTo(5L);
    }

    @Test
    void deleteUser_asOperator_throws403() {
        assertThatThrownBy(() -> controller.deleteUser(5L, operatorAuth(2L)))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.FORBIDDEN));
    }
}
