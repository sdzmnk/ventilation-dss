package com.ventilation.chat.repository;

import com.ventilation.chat.model.Message;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface MessageRepository extends JpaRepository<Message, Long> {

    @Query(value = """
            SELECT * FROM chat.messages WHERE room_id = :roomId
            ORDER BY created_at DESC LIMIT :lim
            """, nativeQuery = true)
    List<Message> findByRoomIdDesc(@Param("roomId") Long roomId, @Param("lim") int lim);
}
