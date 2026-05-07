package com.ventilation.user.service;

import com.ventilation.user.dto.ProfileIn;
import com.ventilation.user.dto.ProfileOut;
import com.ventilation.user.model.User;
import com.ventilation.user.model.UserProfile;
import com.ventilation.user.repository.UserProfileRepository;
import com.ventilation.user.repository.UserRepository;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepo;
    private final UserProfileRepository profileRepo;

    public List<ProfileOut> listAll() {
        return userRepo.findAll().stream()
                .map(u -> buildProfile(u, profileRepo.findByUserId(u.getId()).orElse(null)))
                .collect(Collectors.toList());
    }

    public ProfileOut getProfile(Long userId) {
        User user = userRepo.findById(userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Користувача не знайдено"));
        return buildProfile(user, profileRepo.findByUserId(userId).orElse(null));
    }

    @Transactional
    public ProfileOut updateProfile(Long userId, ProfileIn data) {
        userRepo.findById(userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Користувача не знайдено"));
        UserProfile profile = profileRepo.findByUserId(userId).orElse(new UserProfile());
        profile.setUserId(userId);
        profile.setFullName(data.getFull_name());
        profile.setPosition(data.getPosition());
        profile.setDepartment(data.getDepartment());
        profile.setPhone(data.getPhone());
        profile.setUpdatedAt(LocalDateTime.now());
        profileRepo.save(profile);
        return getProfile(userId);
    }

    @Transactional
    public ProfileOut changeRole(Long userId, String role) {
        if (!List.of("admin", "engineer", "operator").contains(role)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Невідома роль");
        }
        int updated = userRepo.updateRole(userId, role);
        if (updated == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Користувача не знайдено");
        }
        return getProfile(userId);
    }

    @Transactional
    public void delete(Long userId) {
        userRepo.deleteById(userId);
    }

    private ProfileOut buildProfile(User user, UserProfile profile) {
        ProfileOut out = new ProfileOut();
        out.setUser_id(user.getId());
        out.setUsername(user.getUsername());
        out.setEmail(user.getEmail());
        out.setRole(user.getRole());
        if (profile != null) {
            out.setFull_name(profile.getFullName());
            out.setPosition(profile.getPosition());
            out.setDepartment(profile.getDepartment());
            out.setPhone(profile.getPhone());
        }
        return out;
    }
}
