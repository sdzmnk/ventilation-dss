package com.ventilation.configsvc.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ventilation.configsvc.dto.ParamIn;
import com.ventilation.configsvc.dto.ParamOut;
import com.ventilation.configsvc.service.ConfigService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ConfigControllerTest {

    @Mock ConfigService configService;
    @InjectMocks ConfigController controller;

    private Authentication adminAuth() {
        return new UsernamePasswordAuthenticationToken(
                1L, null, List.of(new SimpleGrantedAuthority("ROLE_ADMIN"))
        );
    }

    private Authentication operatorAuth() {
        return new UsernamePasswordAuthenticationToken(
                2L, null, List.of(new SimpleGrantedAuthority("ROLE_OPERATOR"))
        );
    }

    private ParamOut sampleParam(String key, String description) {
        ParamOut p = new ParamOut();
        p.setId(1L);
        p.setKey(key);
        p.setDescription(description);
        return p;
    }

    @Test
    void health_returnsOkMap() {
        Map<String, String> result = controller.health();
        assertThat(result.get("status")).isEqualTo("ok");
        assertThat(result.get("service")).isEqualTo("config-service");
    }

    // ===== GET /config =====

    @Test
    void listParams_anyAuthRole_callsService() {
        List<ParamOut> params = List.of(
                sampleParam("radiation_limit_uSv", "Ліміт радіації"),
                sampleParam("fan_power_kw", "Потужність")
        );
        when(configService.listAll()).thenReturn(params);

        List<ParamOut> result = controller.listParams(operatorAuth());

        assertThat(result).hasSize(2);
        verify(configService).listAll();
    }

    // ===== GET /config/{key} =====

    @Test
    void getParam_existingKey_returnsParam() {
        ParamOut param = sampleParam("fan_power_kw", "Потужність вентилятора");
        when(configService.getByKey("fan_power_kw")).thenReturn(param);

        ParamOut result = controller.getParam("fan_power_kw", operatorAuth());

        assertThat(result.getKey()).isEqualTo("fan_power_kw");
    }

    // ===== PUT /config/{key} =====

    @Test
    void upsertParam_asAdmin_callsService() {
        ParamIn body = new ParamIn();
        body.setValue(new ObjectMapper().valueToTree(20.0));

        ParamOut saved = sampleParam("radiation_limit_uSv", "Updated");
        when(configService.upsert("radiation_limit_uSv", body)).thenReturn(saved);

        ParamOut result = controller.upsertParam("radiation_limit_uSv", body, adminAuth());

        assertThat(result.getKey()).isEqualTo("radiation_limit_uSv");
        verify(configService).upsert("radiation_limit_uSv", body);
    }

    @Test
    void upsertParam_asOperator_throws403() {
        ParamIn body = new ParamIn();
        body.setValue(new ObjectMapper().valueToTree(20.0));

        assertThatThrownBy(() -> controller.upsertParam("key", body, operatorAuth()))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.FORBIDDEN));
    }

    @Test
    void upsertParam_nullAuth_throws403() {
        ParamIn body = new ParamIn();
        assertThatThrownBy(() -> controller.upsertParam("key", body, null))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.FORBIDDEN));
    }

    // ===== DELETE /config/{key} =====

    @Test
    void deleteParam_asAdmin_callsService() {
        Map<String, String> result = controller.deleteParam("old_key", adminAuth());

        verify(configService).delete("old_key");
        assertThat(result.get("deleted")).isEqualTo("old_key");
    }

    @Test
    void deleteParam_asOperator_throws403() {
        assertThatThrownBy(() -> controller.deleteParam("key", operatorAuth()))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.FORBIDDEN));
    }
}
