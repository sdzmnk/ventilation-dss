package com.ventilation.discovery.scheduler;

import com.ventilation.discovery.service.DiscoveryService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

@Component
@RequiredArgsConstructor
@Slf4j
public class HealthCheckScheduler {

    private final DiscoveryService discoveryService;
    private final WebClient.Builder webClientBuilder;

    @Scheduled(fixedDelay = 15000, initialDelay = 5000)
    public void checkAll() {
        discoveryService.findAll().forEach(entry -> {
            boolean healthy = false;
            try {
                Integer status = webClientBuilder.build()
                        .get()
                        .uri(entry.getUrl() + "/health")
                        .retrieve()
                        .toBodilessEntity()
                        .map(r -> r.getStatusCode().value())
                        .timeout(java.time.Duration.ofSeconds(3))
                        .onErrorReturn(500)
                        .block();
                healthy = status != null && status == 200;
            } catch (Exception ignored) {
            }
            try {
                discoveryService.updateHealth(entry.getName(), healthy);
            } catch (Exception ignored) {
            }
        });
    }
}
