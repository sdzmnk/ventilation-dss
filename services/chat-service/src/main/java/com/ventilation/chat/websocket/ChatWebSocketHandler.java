package com.ventilation.chat.websocket;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ventilation.chat.service.ChatService;
import com.ventilation.chat.service.JwtService;
import io.jsonwebtoken.Claims;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.*;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.net.URI;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
@RequiredArgsConstructor
@Slf4j
public class ChatWebSocketHandler extends TextWebSocketHandler {

    private final JwtService jwtService;
    private final ChatService chatService;
    private final RoomHub hub;
    private final ObjectMapper objectMapper;

    private final Map<String, Long> sessionRoom = new ConcurrentHashMap<>();
    private final Map<String, Claims> sessionClaims = new ConcurrentHashMap<>();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        String token = extractToken(session.getUri());
        Claims claims = jwtService.tryValidate(token);
        if (claims == null) {
            session.close(CloseStatus.POLICY_VIOLATION);
            return;
        }

        Long roomId = extractRoomId(session.getUri());
        Long userId = Long.parseLong(claims.getSubject());

        if (!chatService.hasAccess(userId, roomId)) {
            session.close(CloseStatus.POLICY_VIOLATION);
            return;
        }

        sessionRoom.put(session.getId(), roomId);
        sessionClaims.put(session.getId(), claims);
        hub.join(roomId, session);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        Long roomId = sessionRoom.get(session.getId());
        Claims claims = sessionClaims.get(session.getId());
        if (roomId == null || claims == null) return;

        String body;
        try {
            JsonNode node = objectMapper.readTree(message.getPayload());
            body = node.path("body").asText(message.getPayload());
        } catch (Exception e) {
            body = message.getPayload();
        }
        body = body.substring(0, Math.min(body.length(), 4000)).strip();
        if (body.isEmpty()) return;

        String json = chatService.saveAndSerialize(roomId, claims, body);
        hub.broadcast(roomId, json);
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        Long roomId = sessionRoom.remove(session.getId());
        sessionClaims.remove(session.getId());
        if (roomId != null) {
            hub.leave(roomId, session);
        }
    }

    private String extractToken(URI uri) {
        if (uri == null || uri.getQuery() == null) return null;
        for (String param : uri.getQuery().split("&")) {
            if (param.startsWith("token=")) {
                return param.substring(6);
            }
        }
        return null;
    }

    private Long extractRoomId(URI uri) {
        if (uri == null) return null;
        String path = uri.getPath();
        // path: /chat/ws/{roomId}
        String[] parts = path.split("/");
        try {
            return Long.parseLong(parts[parts.length - 1]);
        } catch (Exception e) {
            return null;
        }
    }
}
