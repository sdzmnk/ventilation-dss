package com.ventilation.configsvc.dto;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.Data;

@Data
public class ParamIn {
    private String key;
    private JsonNode value;
    private String description;
}
