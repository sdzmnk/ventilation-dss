package com.ventilation.chat.repository;

import com.ventilation.chat.model.Room;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface RoomRepository extends JpaRepository<Room, Long> {
    List<Room> findByDmFalseOrderByNameAsc();
    Optional<Room> findByName(String name);

    @Query(value = """
            SELECT r.id FROM chat.rooms r
            WHERE r.is_dm = TRUE
              AND (SELECT COUNT(*) FROM chat.dm_participants dp
                   WHERE dp.room_id = r.id AND dp.user_id IN (:uid1, :uid2)) = 2
            LIMIT 1
            """, nativeQuery = true)
    Optional<Long> findDmRoomId(@Param("uid1") Long uid1, @Param("uid2") Long uid2);
}
