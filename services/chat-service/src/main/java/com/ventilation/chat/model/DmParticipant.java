package com.ventilation.chat.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Entity
@Table(schema = "chat", name = "dm_participants")
@IdClass(DmParticipantId.class)
@Getter @Setter @NoArgsConstructor @AllArgsConstructor
public class DmParticipant {

    @Id
    @Column(name = "room_id")
    private Long roomId;

    @Id
    @Column(name = "user_id")
    private Long userId;
}
