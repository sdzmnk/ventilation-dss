package com.ventilation.chat.websocket;

import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class RoomHub {

    private final Map<Long, Set<WebSocketSession>> rooms = new ConcurrentHashMap<>();

    public void join(Long roomId, WebSocketSession session) {
        rooms.computeIfAbsent(roomId, k -> Collections.newSetFromMap(new ConcurrentHashMap<>()))
             .add(session);
    }

    public void leave(Long roomId, WebSocketSession session) {
        Set<WebSocketSession> members = rooms.get(roomId);
        if (members != null) {
            members.remove(session);
        }
    }

    public void broadcast(Long roomId, String json) {
        Set<WebSocketSession> members = rooms.getOrDefault(roomId, Set.of());
        for (WebSocketSession session : members) {
            try {
                if (session.isOpen()) {
                    session.sendMessage(new TextMessage(json));
                }
            } catch (Exception ignored) {
            }
        }
    }
}
