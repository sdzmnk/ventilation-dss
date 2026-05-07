package com.ventilation.chat.repository;

import com.ventilation.chat.model.AuthUser;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface AuthUserRepository extends JpaRepository<AuthUser, Long> {
    List<AuthUser> findByActiveTrueAndIdNotOrderByUsernameAsc(Long id);
    Optional<AuthUser> findByIdAndActiveTrue(Long id);
}
