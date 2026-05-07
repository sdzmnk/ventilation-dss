package com.ventilation.discovery.service;

import com.ventilation.discovery.config.DiscoveryProperties;
import com.ventilation.discovery.dto.ServiceIn;
import com.ventilation.discovery.dto.ServiceOut;
import com.ventilation.discovery.model.ServiceEntry;
import com.ventilation.discovery.repository.ServiceRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class DiscoveryServiceTest {

    @Mock ServiceRepository repo;
    @Mock DiscoveryProperties properties;
    @InjectMocks DiscoveryService discoveryService;

    private ServiceEntry buildEntry(long id, String name, String url, boolean healthy) {
        ServiceEntry e = new ServiceEntry();
        e.setId(id);
        e.setName(name);
        e.setUrl(url);
        e.setHealthy(healthy);
        e.setLastSeen(LocalDateTime.now());
        return e;
    }

    // ===== seed =====

    @Test
    void seed_registersDefaultServices() {
        Map<String, String> defaults = Map.of(
                "auth-service", "http://auth-service:8001",
                "data-service", "http://data-service:8003"
        );
        when(properties.getDefaultServices()).thenReturn(defaults);
        when(repo.findByName(anyString())).thenReturn(Optional.empty());
        when(repo.save(any(ServiceEntry.class))).thenAnswer(i -> i.getArgument(0));

        discoveryService.seed();

        verify(repo, times(2)).save(any(ServiceEntry.class));
    }

    @Test
    void seed_updatesExistingEntry() {
        ServiceEntry existing = buildEntry(1L, "auth-service", "http://old:8001", false);
        Map<String, String> defaults = Map.of("auth-service", "http://auth-service:8001");
        when(properties.getDefaultServices()).thenReturn(defaults);
        when(repo.findByName("auth-service")).thenReturn(Optional.of(existing));
        when(repo.save(any(ServiceEntry.class))).thenAnswer(i -> i.getArgument(0));

        discoveryService.seed();

        verify(repo).save(argThat(e -> "http://auth-service:8001".equals(e.getUrl())));
    }

    // ===== listAll =====

    @Test
    void listAll_returnsAllServicesOrdered() {
        List<ServiceEntry> entries = List.of(
                buildEntry(1L, "auth-service", "http://auth-service:8001", true),
                buildEntry(2L, "data-service", "http://data-service:8003", false)
        );
        when(repo.findAllByOrderByNameAsc()).thenReturn(entries);

        List<ServiceOut> result = discoveryService.listAll();

        assertThat(result).hasSize(2);
        assertThat(result.get(0).getName()).isEqualTo("auth-service");
        assertThat(result.get(0).isHealthy()).isTrue();
        assertThat(result.get(1).isHealthy()).isFalse();
    }

    @Test
    void listAll_empty_returnsEmptyList() {
        when(repo.findAllByOrderByNameAsc()).thenReturn(List.of());
        assertThat(discoveryService.listAll()).isEmpty();
    }

    // ===== getByName =====

    @Test
    void getByName_existingService_returnsDto() {
        ServiceEntry entry = buildEntry(1L, "chat-service", "http://chat-service:8007", true);
        when(repo.findByName("chat-service")).thenReturn(Optional.of(entry));

        ServiceOut result = discoveryService.getByName("chat-service");

        assertThat(result.getName()).isEqualTo("chat-service");
        assertThat(result.getUrl()).isEqualTo("http://chat-service:8007");
        assertThat(result.isHealthy()).isTrue();
    }

    @Test
    void getByName_unknownService_throws404() {
        when(repo.findByName("unknown")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> discoveryService.getByName("unknown"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.NOT_FOUND));
    }

    // ===== register =====

    @Test
    void register_newService_savesAndReturns() {
        when(repo.findByName("new-service")).thenReturn(Optional.empty());
        ServiceEntry saved = buildEntry(10L, "new-service", "http://new:9000", true);
        when(repo.save(any(ServiceEntry.class))).thenReturn(saved);

        ServiceIn in = new ServiceIn();
        in.setName("new-service");
        in.setUrl("http://new:9000");

        ServiceOut result = discoveryService.register(in);

        assertThat(result.getName()).isEqualTo("new-service");
        assertThat(result.isHealthy()).isTrue();
        verify(repo).save(any(ServiceEntry.class));
    }

    @Test
    void register_existingService_updatesUrl() {
        ServiceEntry existing = buildEntry(5L, "data-service", "http://old:8003", false);
        when(repo.findByName("data-service")).thenReturn(Optional.of(existing));

        ServiceEntry updated = buildEntry(5L, "data-service", "http://data-service:8003", true);
        when(repo.save(any(ServiceEntry.class))).thenReturn(updated);

        ServiceIn in = new ServiceIn();
        in.setName("data-service");
        in.setUrl("http://data-service:8003");

        ServiceOut result = discoveryService.register(in);

        assertThat(result.isHealthy()).isTrue();
        verify(repo).save(argThat(e -> "http://data-service:8003".equals(e.getUrl())));
    }

    // ===== unregister =====

    @Test
    void unregister_callsDeleteByName() {
        discoveryService.unregister("obsolete-service");
        verify(repo).deleteByName("obsolete-service");
    }

    // ===== updateHealth =====

    @Test
    void updateHealth_healthy_callsRepository() {
        discoveryService.updateHealth("auth-service", true);
        verify(repo).updateHealth(eq("auth-service"), eq(true), any(LocalDateTime.class));
    }

    @Test
    void updateHealth_unhealthy_callsRepositoryWithFalse() {
        discoveryService.updateHealth("broken-service", false);
        verify(repo).updateHealth(eq("broken-service"), eq(false), any(LocalDateTime.class));
    }
}
