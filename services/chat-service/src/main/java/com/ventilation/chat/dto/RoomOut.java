package com.ventilation.chat.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class RoomOut {
    private Long id;
    private String name;
    @JsonProperty("is_dm")
    private boolean is_dm;
    private Long other_user_id;
    private String other_username;
}
