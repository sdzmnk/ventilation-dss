package com.ventilation.chat.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ventilation.chat.dto.MessageOut;
import com.ventilation.chat.dto.RoomOut;
import com.ventilation.chat.dto.UserOut;
import com.ventilation.chat.model.DmParticipant;
import com.ventilation.chat.model.Message;
import com.ventilation.chat.model.Room;
import com.ventilation.chat.repository.*;
import com.ventilation.chat.websocket.RoomHub;
import io.jsonwebtoken.Claims;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ChatService {

    private final RoomRepository roomRepo;
    private final DmParticipantRepository dmRepo;
    private final MessageRepository messageRepo;
    private final AuthUserRepository authUserRepo;
    private final RoomHub hub;
    private final ObjectMapper mapper;

    public List<UserOut> listUsers(Long currentUserId) {
        return authUserRepo.findByActiveTrueAndIdNotOrderByUsernameAsc(currentUserId)
                .stream()
                .map(u -> new UserOut(u.getId(), u.getUsername()))
                .collect(Collectors.toList());
    }

    public List<RoomOut> listRooms(Long userId) {
        List<RoomOut> result = new ArrayList<>();

        roomRepo.findByDmFalseOrderByNameAsc().forEach(r -> {
            RoomOut out = new RoomOut();
            out.setId(r.getId());
            out.setName(r.getName());
            out.set_dm(false);
            result.add(out);
        });

        dmRepo.findUserDmRooms(userId).forEach(row -> {
            Long roomId = ((Number) row[0]).longValue();
            Long otherUserId = ((Number) row[1]).longValue();
            authUserRepo.findById(otherUserId).ifPresent(u -> {
                RoomOut out = new RoomOut();
                out.setId(roomId);
                out.set_dm(true);
                out.setOther_user_id(otherUserId);
                out.setOther_username(u.getUsername());
                result.add(out);
            });
        });

        return result;
    }

    @Transactional
    public RoomOut createRoom(String name) {
        Room room = roomRepo.findByName(name).orElseGet(() -> {
            Room r = new Room();
            r.setName(name);
            r.setDm(false);
            return roomRepo.save(r);
        });
        RoomOut out = new RoomOut();
        out.setId(room.getId());
        out.setName(room.getName());
        out.set_dm(false);
        return out;
    }

    @Transactional
    public RoomOut getOrCreateDm(Long currentUserId, Long otherUserId) {
        if (currentUserId.equals(otherUserId)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Не можна писати собі в чат");
        }
        Long roomId = roomRepo.findDmRoomId(currentUserId, otherUserId).orElse(null);
        if (roomId == null) {
            Room room = new Room();
            room.setDm(true);
            room = roomRepo.save(room);
            roomId = room.getId();
            dmRepo.save(new DmParticipant(roomId, currentUserId));
            dmRepo.save(new DmParticipant(roomId, otherUserId));
        }
        Long finalRoomId = roomId;
        String otherUsername = authUserRepo.findById(otherUserId)
                .map(u -> u.getUsername()).orElse(null);
        RoomOut out = new RoomOut();
        out.setId(finalRoomId);
        out.set_dm(true);
        out.setOther_user_id(otherUserId);
        out.setOther_username(otherUsername);
        return out;
    }

    public boolean hasAccess(Long userId, Long roomId) {
        Room room = roomRepo.findById(roomId).orElse(null);
        if (room == null) return false;
        if (!room.isDm()) return true;
        return dmRepo.existsByRoomIdAndUserId(roomId, userId);
    }

    public List<MessageOut> history(Long userId, Long roomId, int limit) {
        if (!hasAccess(userId, roomId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Немає доступу до цього чату");
        }
        List<Message> msgs = messageRepo.findByRoomIdDesc(roomId, limit);
        List<MessageOut> out = new ArrayList<>();
        for (int i = msgs.size() - 1; i >= 0; i--) {
            out.add(toDto(msgs.get(i)));
        }
        return out;
    }

    @Transactional
    public MessageOut sendAndBroadcast(Long userId, String username, Long roomId, String body) {
        if (!hasAccess(userId, roomId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Немає доступу до цього чату");
        }
        MessageOut msg = saveMessage(roomId, userId, username, body);
        try {
            hub.broadcast(roomId, mapper.writeValueAsString(msg));
        } catch (Exception ignored) {
        }
        return msg;
    }

    @Transactional
    public String saveAndSerialize(Long roomId, Claims claims, String body) {
        Long userId = Long.parseLong(claims.getSubject());
        String username = claims.get("username", String.class);
        MessageOut msg = saveMessage(roomId, userId, username, body);
        try {
            return mapper.writeValueAsString(msg);
        } catch (Exception e) {
            return "{}";
        }
    }

    private MessageOut saveMessage(Long roomId, Long userId, String username, String body) {
        Message msg = new Message();
        msg.setRoomId(roomId);
        msg.setUserId(userId);
        msg.setUsername(username);
        msg.setBody(body);
        msg.setCreatedAt(LocalDateTime.now());
        msg = messageRepo.save(msg);
        return toDto(msg);
    }

    private MessageOut toDto(Message m) {
        return new MessageOut(
                m.getId(), m.getRoomId(), m.getUserId(),
                m.getUsername(), m.getBody(),
                m.getCreatedAt() != null ? m.getCreatedAt().toString() : null
        );
    }
}
