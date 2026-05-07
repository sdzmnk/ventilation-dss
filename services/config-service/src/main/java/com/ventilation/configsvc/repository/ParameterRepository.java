package com.ventilation.configsvc.repository;

import com.ventilation.configsvc.model.Parameter;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ParameterRepository extends JpaRepository<Parameter, Long> {
    List<Parameter> findAllByOrderByKeyAsc();
    Optional<Parameter> findByKey(String key);
    void deleteByKey(String key);
}
