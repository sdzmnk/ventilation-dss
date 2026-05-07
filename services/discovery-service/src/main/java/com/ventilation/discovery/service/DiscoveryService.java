package com.ventilation.discovery.service;

import com.ventilation.discovery.config.DiscoveryProperties;
import com.ventilation.discovery.dto.ServiceIn;
import com.ventilation.discovery.dto.ServiceOut;
import com.ventilation.discovery.model.ServiceEntry;
import com.ventilation.discovery.repository.ServiceRepository;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class DiscoveryService {

    private final ServiceRepository repo;
    private final DiscoveryProperties properties;

    @EventListener(ApplicationReadyEvent.class)
    @Transactional
    public void seed() {
        properties.getDefaultServices().forEach((name, url) -> {
            ServiceEntry entry = repo.findByName(name).orElse(new ServiceEntry());
            entry.setName(name);
            entry.setUrl(url);
            if (entry.getId() == null) {
                entry.setHealthy(true);
                entry.setLastSeen(LocalDateTime.now());
            }
            repo.save(entry);
        });
    }

    public List<ServiceOut> listAll() {
        return repo.findAllByOrderByNameAsc().stream().map(this::toDto).collect(Collectors.toList());
    }

    public ServiceOut getByName(String name) {
        return repo.findByName(name)
                .map(this::toDto)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Сервіс не зареєстровано"));
    }

    @Transactional
    public ServiceOut register(ServiceIn in) {
        ServiceEntry entry = repo.findByName(in.getName()).orElse(new ServiceEntry());
        entry.setName(in.getName());
        entry.setUrl(in.getUrl());
        entry.setHealthy(true);
        entry.setLastSeen(LocalDateTime.now());
        return toDto(repo.save(entry));
    }

    @Transactional
    public void unregister(String name) {
        repo.deleteByName(name);
    }

    @Transactional
    public void updateHealth(String name, boolean healthy) {
        repo.updateHealth(name, healthy, LocalDateTime.now());
    }

    public List<ServiceEntry> findAll() {
        return repo.findAll();
    }

    private ServiceOut toDto(ServiceEntry e) {
        ServiceOut out = new ServiceOut();
        out.setId(e.getId());
        out.setName(e.getName());
        out.setUrl(e.getUrl());
        out.setHealthy(e.isHealthy());
        out.setLast_seen(e.getLastSeen() != null ? e.getLastSeen().toString() : null);
        return out;
    }
}
