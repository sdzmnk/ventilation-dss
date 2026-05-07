package com.ventilation.gateway.controller;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@Slf4j
public class GatewayController {

    private final WebClient webClient = WebClient.builder().build();

    @Value("${services.auth}")   private String authUrl;
    @Value("${services.user}")   private String userUrl;
    @Value("${services.data}")   private String dataUrl;
    @Value("${services.analytic}") private String analyticUrl;
    @Value("${services.config}") private String configUrl;
    @Value("${services.discovery}") private String discoveryUrl;
    @Value("${services.chat}")   private String chatUrl;

    @GetMapping("/health")
    public Map<String, Object> health() {
        return Map.of(
                "status", "ok",
                "service", "gateway-service",
                "routes", List.of("/auth", "/users", "/zones", "/sensors", "/readings",
                        "/simulate", "/analytic", "/config", "/registry", "/chat")
        );
    }

    @GetMapping("/services")
    public Mono<Map<String, Object>> servicesStatus() {
        Map<String, String> targets = new HashMap<>();
        targets.put("auth-service", authUrl);
        targets.put("user-service", userUrl);
        targets.put("data-service", dataUrl);
        targets.put("analytic-service", analyticUrl);
        targets.put("config-service", configUrl);
        targets.put("discovery-service", discoveryUrl);
        targets.put("chat-service", chatUrl);

        Map<String, Object> result = new HashMap<>();
        List<Mono<Void>> probes = targets.entrySet().stream()
                .map(e -> probe(e.getKey(), e.getValue(), result))
                .toList();

        return Mono.when(probes).thenReturn(result);
    }

    private Mono<Void> probe(String name, String baseUrl, Map<String, Object> result) {
        return webClient.get()
                .uri(baseUrl + "/health")
                .retrieve()
                .bodyToMono(Object.class)
                .timeout(Duration.ofSeconds(3))
                .map(body -> Map.of("url", baseUrl, "healthy", true, "body", body))
                .onErrorResume(e -> Mono.just(Map.of("url", baseUrl, "healthy", false, "error", e.getMessage())))
                .doOnNext(info -> result.put(name, info))
                .then();
    }
}
