package com.ventilation.configsvc.dto;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.Data;

@Data
public class ParamOut {
    private Long id;
    private String key;
    private JsonNode value;
    private String description;
    private String updated_at;
}
