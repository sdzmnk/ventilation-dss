package com.ventilation.chat.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ventilation.chat.dto.MessageOut;
import com.ventilation.chat.dto.RoomOut;
import com.ventilation.chat.dto.UserOut;
import com.ventilation.chat.model.AuthUser;
import com.ventilation.chat.model.DmParticipant;
import com.ventilation.chat.model.Message;
import com.ventilation.chat.model.Room;
import com.ventilation.chat.repository.*;
import com.ventilation.chat.websocket.RoomHub;
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
class ChatServiceTest {

    @Mock RoomRepository roomRepo;
    @Mock DmParticipantRepository dmRepo;
    @Mock MessageRepository messageRepo;
    @Mock AuthUserRepository authUserRepo;
    @Mock RoomHub hub;
    @Spy ObjectMapper mapper = new ObjectMapper();
    @InjectMocks ChatService chatService;

    private AuthUser buildUser(long id, String username) {
        AuthUser u = new AuthUser();
        u.setId(id);
        u.setUsername(username);
        u.setActive(true);
        return u;
    }

    private Room buildPublicRoom(long id, String name) {
        Room r = new Room();
        r.setId(id);
        r.setName(name);
        r.setDm(false);
        return r;
    }

    private Room buildDmRoom(long id) {
        Room r = new Room();
        r.setId(id);
        r.setDm(true);
        return r;
    }

    private Message buildMessage(long id, long roomId, long userId, String username, String body) {
        Message m = new Message();
        m.setId(id);
        m.setRoomId(roomId);
        m.setUserId(userId);
        m.setUsername(username);
        m.setBody(body);
        m.setCreatedAt(LocalDateTime.now());
        return m;
    }

    // ===== listUsers =====

    @Test
    void listUsers_excludesCurrentUser() {
        List<AuthUser> others = List.of(
                buildUser(2L, "bob"),
                buildUser(3L, "carol")
        );
        when(authUserRepo.findByActiveTrueAndIdNotOrderByUsernameAsc(1L)).thenReturn(others);

        List<UserOut> result = chatService.listUsers(1L);

        assertThat(result).hasSize(2);
        assertThat(result).extracting(UserOut::getUsername).containsExactly("bob", "carol");
    }

    @Test
    void listUsers_noOtherUsers_returnsEmpty() {
        when(authUserRepo.findByActiveTrueAndIdNotOrderByUsernameAsc(1L)).thenReturn(List.of());
        assertThat(chatService.listUsers(1L)).isEmpty();
    }

    // ===== listRooms =====

    @Test
    void listRooms_returnsPublicRoomsAndDmRooms() {
        Room general = buildPublicRoom(1L, "general");
        Room alerts = buildPublicRoom(2L, "alerts");
        when(roomRepo.findByDmFalseOrderByNameAsc()).thenReturn(List.of(alerts, general));
        when(dmRepo.findUserDmRooms(5L)).thenReturn(List.of());

        List<RoomOut> result = chatService.listRooms(5L);

        assertThat(result).hasSize(2);
        assertThat(result.get(0).getName()).isEqualTo("alerts");
    }

    // ===== createRoom =====

    @Test
    void createRoom_newRoom_createsAndReturns() {
        when(roomRepo.findByName("devops")).thenReturn(Optional.empty());
        Room saved = buildPublicRoom(10L, "devops");
        when(roomRepo.save(any(Room.class))).thenReturn(saved);

        RoomOut result = chatService.createRoom("devops");

        assertThat(result.getName()).isEqualTo("devops");
        assertThat(result.is_dm()).isFalse();
        verify(roomRepo).save(any(Room.class));
    }

    @Test
    void createRoom_existingRoom_returnsExisting() {
        Room existing = buildPublicRoom(5L, "general");
        when(roomRepo.findByName("general")).thenReturn(Optional.of(existing));

        RoomOut result = chatService.createRoom("general");

        assertThat(result.getId()).isEqualTo(5L);
        verify(roomRepo, never()).save(any());
    }

    // ===== getOrCreateDm =====

    @Test
    void getOrCreateDm_samePerson_throws400() {
        assertThatThrownBy(() -> chatService.getOrCreateDm(1L, 1L))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.BAD_REQUEST));
    }

    @Test
    void getOrCreateDm_existingDm_returnsDmRoom() {
        when(roomRepo.findDmRoomId(1L, 2L)).thenReturn(Optional.of(99L));
        AuthUser other = buildUser(2L, "bob");
        when(authUserRepo.findById(2L)).thenReturn(Optional.of(other));

        RoomOut result = chatService.getOrCreateDm(1L, 2L);

        assertThat(result.getId()).isEqualTo(99L);
        assertThat(result.is_dm()).isTrue();
        assertThat(result.getOther_username()).isEqualTo("bob");
        verify(roomRepo, never()).save(any());
    }

    @Test
    void getOrCreateDm_newDm_createsRoomAndParticipants() {
        when(roomRepo.findDmRoomId(1L, 2L)).thenReturn(Optional.empty());
        Room dmRoom = buildDmRoom(50L);
        when(roomRepo.save(any(Room.class))).thenReturn(dmRoom);
        when(dmRepo.save(any(DmParticipant.class))).thenReturn(null);
        AuthUser other = buildUser(2L, "bob");
        when(authUserRepo.findById(2L)).thenReturn(Optional.of(other));

        RoomOut result = chatService.getOrCreateDm(1L, 2L);

        assertThat(result.getId()).isEqualTo(50L);
        assertThat(result.is_dm()).isTrue();
        verify(dmRepo, times(2)).save(any(DmParticipant.class));
    }

    // ===== hasAccess =====

    @Test
    void hasAccess_publicRoom_returnsTrue() {
        Room room = buildPublicRoom(1L, "general");
        when(roomRepo.findById(1L)).thenReturn(Optional.of(room));

        assertThat(chatService.hasAccess(99L, 1L)).isTrue();
    }

    @Test
    void hasAccess_dmRoom_participantReturnsTrue() {
        Room room = buildDmRoom(2L);
        when(roomRepo.findById(2L)).thenReturn(Optional.of(room));
        when(dmRepo.existsByRoomIdAndUserId(2L, 5L)).thenReturn(true);

        assertThat(chatService.hasAccess(5L, 2L)).isTrue();
    }

    @Test
    void hasAccess_dmRoom_nonParticipantReturnsFalse() {
        Room room = buildDmRoom(2L);
        when(roomRepo.findById(2L)).thenReturn(Optional.of(room));
        when(dmRepo.existsByRoomIdAndUserId(2L, 99L)).thenReturn(false);

        assertThat(chatService.hasAccess(99L, 2L)).isFalse();
    }

    @Test
    void hasAccess_roomNotFound_returnsFalse() {
        when(roomRepo.findById(999L)).thenReturn(Optional.empty());
        assertThat(chatService.hasAccess(1L, 999L)).isFalse();
    }

    // ===== history =====

    @Test
    void history_noAccess_throws403() {
        Room dmRoom = buildDmRoom(10L);
        when(roomRepo.findById(10L)).thenReturn(Optional.of(dmRoom));
        when(dmRepo.existsByRoomIdAndUserId(10L, 99L)).thenReturn(false);

        assertThatThrownBy(() -> chatService.history(99L, 10L, 50))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.FORBIDDEN));
    }

    @Test
    void history_publicRoom_returnsMessagesInChronologicalOrder() {
        Room room = buildPublicRoom(1L, "general");
        when(roomRepo.findById(1L)).thenReturn(Optional.of(room));

        Message m1 = buildMessage(1L, 1L, 2L, "bob", "Hello");
        Message m2 = buildMessage(2L, 1L, 3L, "carol", "World");
        when(messageRepo.findByRoomIdDesc(1L, 10)).thenReturn(List.of(m2, m1));

        List<MessageOut> result = chatService.history(5L, 1L, 10);

        assertThat(result).hasSize(2);
        assertThat(result.get(0).getBody()).isEqualTo("Hello");
        assertThat(result.get(1).getBody()).isEqualTo("World");
    }

    // ===== sendAndBroadcast =====

    @Test
    void sendAndBroadcast_noAccess_throws403() {
        Room dmRoom = buildDmRoom(20L);
        when(roomRepo.findById(20L)).thenReturn(Optional.of(dmRoom));
        when(dmRepo.existsByRoomIdAndUserId(20L, 7L)).thenReturn(false);

        assertThatThrownBy(() -> chatService.sendAndBroadcast(7L, "eve", 20L, "Hi"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.FORBIDDEN));
    }

    @Test
    void sendAndBroadcast_hasAccess_savesAndBroadcasts() throws Exception {
        Room room = buildPublicRoom(1L, "general");
        when(roomRepo.findById(1L)).thenReturn(Optional.of(room));

        Message saved = buildMessage(100L, 1L, 5L, "alice", "Test message");
        when(messageRepo.save(any(Message.class))).thenReturn(saved);

        MessageOut result = chatService.sendAndBroadcast(5L, "alice", 1L, "Test message");

        assertThat(result.getBody()).isEqualTo("Test message");
        assertThat(result.getUsername()).isEqualTo("alice");
        verify(hub).broadcast(eq(1L), anyString());
    }
}
