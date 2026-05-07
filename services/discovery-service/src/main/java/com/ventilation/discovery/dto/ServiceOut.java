package com.ventilation.discovery.dto;

import lombok.Data;

@Data
public class ServiceOut {
    private Long id;
    private String name;
    private String url;
    private boolean healthy;
    private String last_seen;
}
