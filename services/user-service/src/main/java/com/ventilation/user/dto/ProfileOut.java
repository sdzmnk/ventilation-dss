package com.ventilation.user.dto;

import lombok.Data;

@Data
public class ProfileOut {
    private Long user_id;
    private String username;
    private String email;
    private String role;
    private String full_name;
    private String position;
    private String department;
    private String phone;
}
