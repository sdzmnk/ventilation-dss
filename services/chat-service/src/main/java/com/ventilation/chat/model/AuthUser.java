package com.ventilation.chat.model;

import jakarta.persistence.*;
import lombok.Getter;

@Entity
@Table(schema = "auth", name = "users")
@Getter
public class AuthUser {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String username;

    @Column(name = "is_active")
    private boolean active;
}
