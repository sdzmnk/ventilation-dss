package com.ventilation.chat.controller;

import com.ventilation.chat.dto.*;
import com.ventilation.chat.service.ChatService;
import io.jsonwebtoken.Claims;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ChatControllerTest {

    @Mock ChatService chatService;
    @InjectMocks ChatController controller;

    private Authentication auth(long userId, String role) {
        Claims claims = mock(Claims.class);
        when(claims.get("username", String.class)).thenReturn("user" + userId);
        return new UsernamePasswordAuthenticationToken(
                userId, claims,
                List.of(new SimpleGrantedAuthority("ROLE_" + role.toUpperCase()))
        );
    }

    @Test
    void health_returnsOkMap() {
        Map<String, String> result = controller.health();
        assertThat(result.get("status")).isEqualTo("ok");
        assertThat(result.get("service")).isEqualTo("chat-service");
    }


    @Test
    void listUsers_returnsUsersExceptSelf() {
        List<UserOut> users = List.of(
                new UserOut(2L, "bob"),
                new UserOut(3L, "carol")
        );
        when(chatService.listUsers(1L)).thenReturn(users);

        List<UserOut> result = controller.listUsers(auth(1L, "operator"));

        assertThat(result).hasSize(2);
        verify(chatService).listUsers(1L);
    }


    @Test
    void listRooms_returnsAllAccessibleRooms() {
        RoomOut room = new RoomOut();
        room.setId(1L);
        room.setName("general");
        room.set_dm(false);

        when(chatService.listRooms(1L)).thenReturn(List.of(room));

        List<RoomOut> result = controller.listRooms(auth(1L, "operator"));

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getName()).isEqualTo("general");
    }


    @Test
    void createRoom_callsServiceWithName() {
        RoomIn body = new RoomIn();
        body.setName("devops");

        RoomOut created = new RoomOut();
        created.setId(10L);
        created.setName("devops");
        when(chatService.createRoom("devops")).thenReturn(created);

        RoomOut result = controller.createRoom(body, auth(1L, "operator"));

        assertThat(result.getName()).isEqualTo("devops");
        verify(chatService).createRoom("devops");
    }


    @Test
    void getOrCreateDm_callsServiceWithBothUserIds() {
        RoomOut dmRoom = new RoomOut();
        dmRoom.setId(20L);
        dmRoom.set_dm(true);
        dmRoom.setOther_user_id(2L);
        dmRoom.setOther_username("bob");
        when(chatService.getOrCreateDm(1L, 2L)).thenReturn(dmRoom);

        RoomOut result = controller.getOrCreateDm(2L, auth(1L, "operator"));

        assertThat(result.getId()).isEqualTo(20L);
        assertThat(result.is_dm()).isTrue();
        verify(chatService).getOrCreateDm(1L, 2L);
    }


    @Test
    void history_returnsMessagesWithSafeLimit() {
        MessageOut msg = new MessageOut(1L, 1L, 2L, "bob", "Hello", "2024-01-01T00:00:00");
        when(chatService.history(1L, 5L, 100)).thenReturn(List.of(msg));

        List<MessageOut> result = controller.history(5L, 100, auth(1L, "operator"));

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getBody()).isEqualTo("Hello");
    }

    @Test
    void history_limitsMaxTo500() {
        when(chatService.history(eq(1L), eq(5L), eq(500))).thenReturn(List.of());

        controller.history(5L, 9999, auth(1L, "operator"));

        verify(chatService).history(1L, 5L, 500);
    }

    @Test
    void history_limitsMinTo1() {
        when(chatService.history(eq(1L), eq(5L), eq(1))).thenReturn(List.of());

        controller.history(5L, -10, auth(1L, "operator"));

        verify(chatService).history(1L, 5L, 1);
    }


    @Test
    void send_callsServiceWithUsernameFromClaims() {
        MessageIn body = new MessageIn();
        body.setBody("Hello world");

        MessageOut saved = new MessageOut(1L, 1L, 1L, "user1", "Hello world", "2024-01-01T00:00:00");
        when(chatService.sendAndBroadcast(1L, "user1", 1L, "Hello world")).thenReturn(saved);

        MessageOut result = controller.send(1L, body, auth(1L, "operator"));

        assertThat(result.getBody()).isEqualTo("Hello world");
        verify(chatService).sendAndBroadcast(1L, "user1", 1L, "Hello world");
    }
}
