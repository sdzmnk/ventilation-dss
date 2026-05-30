package com.ventilation.configsvc.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.DoubleNode;
import com.ventilation.configsvc.dto.ParamIn;
import com.ventilation.configsvc.dto.ParamOut;
import com.ventilation.configsvc.model.Parameter;
import com.ventilation.configsvc.repository.ParameterRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ConfigServiceTest {

    @Mock ParameterRepository repo;
    @Spy ObjectMapper mapper = new ObjectMapper();
    @InjectMocks ConfigService configService;

    private Parameter buildParam(long id, String key, String value, String description) {
        Parameter p = new Parameter();
        p.setId(id);
        p.setKey(key);
        p.setValue(value);
        p.setDescription(description);
        p.setUpdatedAt(LocalDateTime.now());
        return p;
    }


    @Test
    void listAll_returnsAllParams() {
        List<Parameter> params = List.of(
                buildParam(1L, "airflow_max_m3h", "40000", "Макс потік"),
                buildParam(2L, "radiation_limit_uSv", "20.0", "Ліміт радіації")
        );
        when(repo.findAllByOrderByKeyAsc()).thenReturn(params);

        List<ParamOut> result = configService.listAll();

        assertThat(result).hasSize(2);
        assertThat(result.get(0).getKey()).isEqualTo("airflow_max_m3h");
        assertThat(result.get(1).getKey()).isEqualTo("radiation_limit_uSv");
    }

    @Test
    void listAll_empty_returnsEmptyList() {
        when(repo.findAllByOrderByKeyAsc()).thenReturn(List.of());
        assertThat(configService.listAll()).isEmpty();
    }


    @Test
    void getByKey_existingKey_returnsParam() {
        Parameter p = buildParam(1L, "fan_power_kw", "15.0", "Потужність");
        when(repo.findByKey("fan_power_kw")).thenReturn(Optional.of(p));

        ParamOut result = configService.getByKey("fan_power_kw");

        assertThat(result.getKey()).isEqualTo("fan_power_kw");
        assertThat(result.getDescription()).isEqualTo("Потужність");
    }

    @Test
    void getByKey_missingKey_throws404() {
        when(repo.findByKey("nonexistent")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> configService.getByKey("nonexistent"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.NOT_FOUND));
    }


    @Test
    void upsert_newKey_createsNewParameter() {
        when(repo.findByKey("new_param")).thenReturn(Optional.empty());

        Parameter saved = buildParam(5L, "new_param", "42", "New");
        when(repo.save(any(Parameter.class))).thenReturn(saved);

        ParamIn body = new ParamIn();
        body.setValue(new ObjectMapper().valueToTree(42));
        body.setDescription("New");

        ParamOut result = configService.upsert("new_param", body);

        assertThat(result.getKey()).isEqualTo("new_param");
        verify(repo).save(any(Parameter.class));
    }

    @Test
    void upsert_existingKey_updatesParameter() {
        Parameter existing = buildParam(1L, "fan_power_kw", "15.0", "Потужність");
        when(repo.findByKey("fan_power_kw")).thenReturn(Optional.of(existing));

        Parameter updated = buildParam(1L, "fan_power_kw", "20.0", "Updated");
        when(repo.save(any(Parameter.class))).thenReturn(updated);

        ParamIn body = new ParamIn();
        body.setValue(new ObjectMapper().valueToTree(20.0));
        body.setDescription("Updated");

        ParamOut result = configService.upsert("fan_power_kw", body);

        assertThat(result.getKey()).isEqualTo("fan_power_kw");
        verify(repo).save(any(Parameter.class));
    }


    @Test
    void delete_callsRepositoryDeleteByKey() {
        configService.delete("radiation_limit_uSv");
        verify(repo).deleteByKey("radiation_limit_uSv");
    }

    @Test
    void delete_nonExistentKey_doesNotThrow() {
        doNothing().when(repo).deleteByKey("ghost");
        assertThatCode(() -> configService.delete("ghost")).doesNotThrowAnyException();
    }
}
