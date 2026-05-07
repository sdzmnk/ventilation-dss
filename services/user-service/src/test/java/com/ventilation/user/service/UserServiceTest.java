package com.ventilation.user.service;

import com.ventilation.user.dto.ProfileIn;
import com.ventilation.user.dto.ProfileOut;
import com.ventilation.user.model.User;
import com.ventilation.user.model.UserProfile;
import com.ventilation.user.repository.UserProfileRepository;
import com.ventilation.user.repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock UserRepository userRepo;
    @Mock UserProfileRepository profileRepo;
    @InjectMocks UserService userService;

    private User buildUser(long id, String username, String email, String role) {
        User u = new User();
        u.setId(id);
        u.setUsername(username);
        u.setEmail(email);
        u.setRole(role);
        return u;
    }

    private UserProfile buildProfile(long userId, String fullName, String position) {
        UserProfile p = new UserProfile();
        p.setUserId(userId);
        p.setFullName(fullName);
        p.setPosition(position);
        p.setDepartment("Safety");
        p.setPhone("+380501234567");
        return p;
    }

    // ===== listAll =====

    @Test
    void listAll_returnsAllUsersWithProfiles() {
        User u1 = buildUser(1L, "alice", "alice@test.com", "admin");
        User u2 = buildUser(2L, "bob", "bob@test.com", "operator");
        when(userRepo.findAll()).thenReturn(List.of(u1, u2));
        when(profileRepo.findByUserId(1L)).thenReturn(Optional.of(buildProfile(1L, "Alice A", "Head")));
        when(profileRepo.findByUserId(2L)).thenReturn(Optional.empty());

        List<ProfileOut> result = userService.listAll();

        assertThat(result).hasSize(2);
        assertThat(result.get(0).getUsername()).isEqualTo("alice");
        assertThat(result.get(0).getFull_name()).isEqualTo("Alice A");
        assertThat(result.get(1).getFull_name()).isNull();
    }

    @Test
    void listAll_noUsers_returnsEmptyList() {
        when(userRepo.findAll()).thenReturn(List.of());
        assertThat(userService.listAll()).isEmpty();
    }

    // ===== getProfile =====

    @Test
    void getProfile_existingUser_returnsProfile() {
        User u = buildUser(3L, "carol", "carol@test.com", "engineer");
        when(userRepo.findById(3L)).thenReturn(Optional.of(u));
        when(profileRepo.findByUserId(3L)).thenReturn(Optional.of(buildProfile(3L, "Carol C", "Engineer")));

        ProfileOut out = userService.getProfile(3L);

        assertThat(out.getUsername()).isEqualTo("carol");
        assertThat(out.getRole()).isEqualTo("engineer");
        assertThat(out.getFull_name()).isEqualTo("Carol C");
        assertThat(out.getPosition()).isEqualTo("Engineer");
    }

    @Test
    void getProfile_missingUser_throws404() {
        when(userRepo.findById(999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userService.getProfile(999L))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.NOT_FOUND));
    }

    @Test
    void getProfile_userWithoutProfile_returnsNullFields() {
        User u = buildUser(4L, "dave", "dave@test.com", "operator");
        when(userRepo.findById(4L)).thenReturn(Optional.of(u));
        when(profileRepo.findByUserId(4L)).thenReturn(Optional.empty());

        ProfileOut out = userService.getProfile(4L);
        assertThat(out.getFull_name()).isNull();
        assertThat(out.getPosition()).isNull();
    }

    // ===== updateProfile =====

    @Test
    void updateProfile_createsNewProfileWhenAbsent() {
        User u = buildUser(5L, "eve", "eve@test.com", "operator");
        when(userRepo.findById(5L)).thenReturn(Optional.of(u)).thenReturn(Optional.of(u));
        when(profileRepo.findByUserId(5L)).thenReturn(Optional.empty()).thenReturn(Optional.empty());

        UserProfile saved = buildProfile(5L, "Eve E", "Operator");
        when(profileRepo.save(any(UserProfile.class))).thenReturn(saved);

        ProfileIn data = new ProfileIn();
        data.setFull_name("Eve E");
        data.setPosition("Operator");
        data.setDepartment("Dept");
        data.setPhone("+380");

        userService.updateProfile(5L, data);

        verify(profileRepo).save(any(UserProfile.class));
    }

    @Test
    void updateProfile_missingUser_throws404() {
        when(userRepo.findById(99L)).thenReturn(Optional.empty());

        ProfileIn data = new ProfileIn();
        data.setFull_name("X");

        assertThatThrownBy(() -> userService.updateProfile(99L, data))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.NOT_FOUND));
    }

    // ===== changeRole =====

    @Test
    void changeRole_validRoles_updates() {
        for (String role : List.of("admin", "engineer", "operator")) {
            when(userRepo.updateRole(1L, role)).thenReturn(1);
            User u = buildUser(1L, "alice", "alice@test.com", role);
            when(userRepo.findById(1L)).thenReturn(Optional.of(u));
            when(profileRepo.findByUserId(1L)).thenReturn(Optional.empty());

            ProfileOut out = userService.changeRole(1L, role);
            assertThat(out.getRole()).isEqualTo(role);
        }
    }

    @Test
    void changeRole_invalidRole_throws400() {
        assertThatThrownBy(() -> userService.changeRole(1L, "superuser"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.BAD_REQUEST));
    }

    @Test
    void changeRole_userNotFound_throws404() {
        when(userRepo.updateRole(999L, "operator")).thenReturn(0);

        assertThatThrownBy(() -> userService.changeRole(999L, "operator"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.NOT_FOUND));
    }

    // ===== delete =====

    @Test
    void delete_callsRepositoryDeleteById() {
        userService.delete(7L);
        verify(userRepo).deleteById(7L);
    }
}
