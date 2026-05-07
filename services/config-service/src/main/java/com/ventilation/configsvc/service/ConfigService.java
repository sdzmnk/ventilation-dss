package com.ventilation.configsvc.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ventilation.configsvc.dto.ParamIn;
import com.ventilation.configsvc.dto.ParamOut;
import com.ventilation.configsvc.model.Parameter;
import com.ventilation.configsvc.repository.ParameterRepository;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ConfigService {

    private final ParameterRepository repo;
    private final ObjectMapper mapper;

    public List<ParamOut> listAll() {
        return repo.findAllByOrderByKeyAsc().stream()
                .map(this::toDto)
                .collect(Collectors.toList());
    }

    public ParamOut getByKey(String key) {
        return repo.findByKey(key)
                .map(this::toDto)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Параметр не знайдено"));
    }

    @Transactional
    public ParamOut upsert(String key, ParamIn body) {
        Parameter param = repo.findByKey(key).orElse(new Parameter());
        param.setKey(key);
        param.setValue(body.getValue() != null ? body.getValue().toString() : "null");
        if (body.getDescription() != null || param.getDescription() == null) {
            param.setDescription(body.getDescription());
        }
        param.setUpdatedAt(LocalDateTime.now());
        return toDto(repo.save(param));
    }

    @Transactional
    public void delete(String key) {
        repo.deleteByKey(key);
    }

    private ParamOut toDto(Parameter p) {
        ParamOut out = new ParamOut();
        out.setId(p.getId());
        out.setKey(p.getKey());
        out.setDescription(p.getDescription());
        out.setUpdated_at(p.getUpdatedAt() != null ? p.getUpdatedAt().toString() : null);
        if (p.getValue() != null) {
            try {
                out.setValue(mapper.readTree(p.getValue()));
            } catch (Exception e) {
                out.setValue(mapper.valueToTree(p.getValue()));
            }
        }
        return out;
    }
}
