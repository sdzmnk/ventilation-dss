package com.ventilation.chat.controller;

import com.ventilation.chat.dto.*;
import com.ventilation.chat.service.ChatService;
import io.jsonwebtoken.Claims;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok", "service", "chat-service");
    }

    @GetMapping("/chat/users")
    public List<UserOut> listUsers(Authentication auth) {
        return chatService.listUsers(userId(auth));
    }

    @GetMapping("/chat/rooms")
    public List<RoomOut> listRooms(Authentication auth) {
        return chatService.listRooms(userId(auth));
    }

    @PostMapping("/chat/rooms")
    public RoomOut createRoom(@RequestBody RoomIn body, Authentication auth) {
        return chatService.createRoom(body.getName());
    }

    @PostMapping("/chat/dm/{userId}")
    public RoomOut getOrCreateDm(@PathVariable Long userId, Authentication auth) {
        return chatService.getOrCreateDm(userId(auth), userId);
    }

    @GetMapping("/chat/rooms/{roomId}/messages")
    public List<MessageOut> history(@PathVariable Long roomId,
                                     @RequestParam(defaultValue = "100") int limit,
                                     Authentication auth) {
        int safeLimit = Math.max(1, Math.min(limit, 500));
        return chatService.history(userId(auth), roomId, safeLimit);
    }

    @PostMapping("/chat/rooms/{roomId}/messages")
    public MessageOut send(@PathVariable Long roomId,
                            @RequestBody MessageIn body,
                            Authentication auth) {
        Claims claims = (Claims) auth.getCredentials();
        String username = claims != null ? claims.get("username", String.class) : null;
        return chatService.sendAndBroadcast(userId(auth), username, roomId, body.getBody());
    }

    private Long userId(Authentication auth) {
        return (Long) auth.getPrincipal();
    }
}
