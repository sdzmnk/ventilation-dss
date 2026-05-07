package com.ventilation.chat.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Data @NoArgsConstructor @AllArgsConstructor
public class MessageOut {
    private Long id;
    private Long room_id;
    private Long user_id;
    private String username;
    private String body;
    private String created_at;
}
