package com.ventilation.discovery.repository;

import com.ventilation.discovery.model.ServiceEntry;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface ServiceRepository extends JpaRepository<ServiceEntry, Long> {
    Optional<ServiceEntry> findByName(String name);
    List<ServiceEntry> findAllByOrderByNameAsc();
    void deleteByName(String name);

    @Modifying
    @Query("UPDATE ServiceEntry s SET s.healthy = :healthy, s.lastSeen = :lastSeen WHERE s.name = :name")
    void updateHealth(@Param("name") String name,
                      @Param("healthy") boolean healthy,
                      @Param("lastSeen") LocalDateTime lastSeen);
}
