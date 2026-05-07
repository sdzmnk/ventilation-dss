package com.ventilation.chat.model;

import java.io.Serializable;
import java.util.Objects;

public class DmParticipantId implements Serializable {
    private Long roomId;
    private Long userId;

    public DmParticipantId() {}

    public DmParticipantId(Long roomId, Long userId) {
        this.roomId = roomId;
        this.userId = userId;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof DmParticipantId)) return false;
        DmParticipantId that = (DmParticipantId) o;
        return Objects.equals(roomId, that.roomId) && Objects.equals(userId, that.userId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(roomId, userId);
    }
}
