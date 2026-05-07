package com.ventilation.discovery.controller;

import com.ventilation.discovery.dto.ServiceIn;
import com.ventilation.discovery.dto.ServiceOut;
import com.ventilation.discovery.service.DiscoveryService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequiredArgsConstructor
public class DiscoveryController {

    private final DiscoveryService discoveryService;

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok", "service", "discovery-service");
    }

    @GetMapping("/registry")
    public List<ServiceOut> registry() {
        return discoveryService.listAll();
    }

    @GetMapping("/registry/{name}")
    public ServiceOut getService(@PathVariable String name) {
        return discoveryService.getByName(name);
    }

    @PostMapping("/registry")
    public ServiceOut register(@RequestBody ServiceIn body) {
        return discoveryService.register(body);
    }

    @DeleteMapping("/registry/{name}")
    public Map<String, String> unregister(@PathVariable String name) {
        discoveryService.unregister(name);
        return Map.of("deleted", name);
    }
}
