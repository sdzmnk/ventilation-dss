package com.ventilation.discovery.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Component
@ConfigurationProperties(prefix = "discovery")
@Getter @Setter
public class DiscoveryProperties {
    private Map<String, String> defaultServices = new HashMap<>();
}
