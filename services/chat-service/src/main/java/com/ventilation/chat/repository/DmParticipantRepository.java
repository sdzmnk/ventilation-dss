package com.ventilation.chat.repository;

import com.ventilation.chat.model.DmParticipant;
import com.ventilation.chat.model.DmParticipantId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface DmParticipantRepository extends JpaRepository<DmParticipant, DmParticipantId> {
    boolean existsByRoomIdAndUserId(Long roomId, Long userId);
    List<DmParticipant> findByRoomId(Long roomId);

    @Query(value = """
            SELECT dp.room_id, dp.user_id FROM chat.dm_participants dp
            WHERE dp.room_id IN (
                SELECT dp2.room_id FROM chat.dm_participants dp2 WHERE dp2.user_id = :userId
            ) AND dp.user_id != :userId
            """, nativeQuery = true)
    List<Object[]> findUserDmRooms(@Param("userId") Long userId);
}
