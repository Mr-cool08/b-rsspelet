"""Bounded, authenticated game chat for the single Socket.IO server process."""

import re
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from time import monotonic
from unicodedata import category, normalize


PUBLIC_CHAT_ROOM = "company:chat"
PUBLIC_MESSAGE_LIMIT = 240
RATE_WINDOW = 10
MESSAGES_PER_USER = 5

BLOCKED_WORDS = re.compile(
    r"(?<![^\W_])(?:fitt(?:a|an|or)|hor(?:a|an|or)|kuk(?:en|ar)?|"
    r"nigg(?:er|ers|a|as)|faggots?|fuck(?:er|ers|ing)?|bitch(?:es)?)(?![^\W_])",
    re.IGNORECASE,
)
LINKS = re.compile(
    r"(?:\b[a-z][a-z0-9+.-]*\s*://|\bwww\s*\.|"
    r"\b(?:[\w-]+\.)+[a-z]{2,24}\b|\b(?:\d{1,3}\.){3}\d{1,3}\b)",
    re.IGNORECASE,
)

DUEL_PRESETS = {
    "ez": ("message", "EZ"),
    "gg": ("message", "Bra match!"),
    "gl": ("message", "Lycka till!"),
    "well_played": ("message", "Bra spelat!"),
    "wave": ("emoji", "👋"),
    "thumbs_up": ("emoji", "👍"),
    "fire": ("emoji", "🔥"),
    "laugh": ("emoji", "😂"),
}
BOT_REPLIES = {"ez": "laugh", "well_played": "thumbs_up"}


def chat_error(code):
    return {"ok": False, "error": code}


class ChatRateLimit:
    def __init__(self, *, total_limit=None):
        self.by_user = OrderedDict()
        self.recent = deque()
        self.total_limit = total_limit

    def allow(self, user_id, now):
        cutoff = now - RATE_WINDOW
        while self.by_user and next(iter(self.by_user.values()))[-1] <= cutoff:
            self.by_user.popitem(last=False)
        if self.total_limit is not None:
            while self.recent and self.recent[0] <= cutoff:
                self.recent.popleft()
            if len(self.recent) >= self.total_limit:
                return False

        user_times = self.by_user.setdefault(user_id, deque())
        while user_times and user_times[0] <= cutoff:
            user_times.popleft()
        if len(user_times) >= MESSAGES_PER_USER:
            return False
        user_times.append(now)
        self.by_user.move_to_end(user_id)
        if self.total_limit is not None:
            self.recent.append(now)
        return True


class ChatHistory:
    def __init__(self, limit):
        self.messages = deque(maxlen=limit)
        self.next_id = 1

    def add(self, user_id, name, text, **details):
        message = {
            "id": self.next_id,
            "userId": user_id,
            "name": name,
            "text": text,
            "time": datetime.now(UTC).isoformat(timespec="milliseconds"),
            **details,
        }
        self.next_id += 1
        self.messages.append(message)
        return message

    def snapshot(self):
        return {"ok": True, "messages": list(self.messages)}


class DuelChat:
    def __init__(self, match_id, players, bot_id):
        self.match_id = match_id
        self.players = players
        self.bot_id = bot_id
        self.history = ChatHistory(30)

    def add(self, user_id, preset):
        kind, text = DUEL_PRESETS[preset]
        return self.history.add(user_id, self.players[user_id], text,
                                matchId=self.match_id, preset=preset, kind=kind)


def clean_public_text(raw):
    if not isinstance(raw, str) or len(raw) > PUBLIC_MESSAGE_LIMIT:
        return None, "chat_invalid"
    normalized = normalize("NFKC", raw)
    text = "".join(
        char for char in normalized
        if char.isspace() or char == "\u200d" or category(char) not in {"Cc", "Cf", "Cs"}
    )
    text = " ".join(text.split())
    if not text or len(text) > PUBLIC_MESSAGE_LIMIT:
        return None, "chat_invalid"
    # Preserve emoji joiners in the display, but ignore them when checking words and links.
    scan = text.replace("\u200d", "")
    if not scan.strip():
        return None, "chat_invalid"
    if LINKS.search(scan):
        return None, "chat_links"
    if BLOCKED_WORDS.search(scan):
        text = BLOCKED_WORDS.sub(lambda match: "*" * len(match[0]), scan)
    return text, None


@dataclass
class PublicChatConnection:
    user_id: int
    name: str
    session_token: str
    subscribed: bool = False


class PublicChat:
    def __init__(self, app, socketio, namespace):
        self.socketio = socketio
        self.namespace = namespace
        self.clock = app.config.get("CHAT_CLOCK", app.config.get("MATCH_CLOCK", monotonic))
        self._lock = RLock()
        self._connections = {}
        self._history = ChatHistory(50)
        self._limit = ChatRateLimit(total_limit=30)

    def connect(self, sid, user, token):
        with self._lock:
            self._connections[sid] = PublicChatConnection(user.id, user.username, token)

    def disconnect(self, sid):
        with self._lock:
            self._connections.pop(sid, None)

    def disconnect_session(self, token):
        with self._lock:
            sids = [sid for sid, connection in self._connections.items() if connection.session_token == token]
            for sid in sids:
                self._connections.pop(sid)
        for sid in sids:
            self.socketio.server.disconnect(sid, namespace=self.namespace)

    def subscribe(self, sid, payload):
        if payload not in (None, {}):
            return chat_error("chat_invalid")
        with self._lock:
            connection = self._connections.get(sid)
            if connection is None:
                return chat_error("chat_unavailable")
            if not connection.subscribed:
                self.socketio.server.enter_room(sid, PUBLIC_CHAT_ROOM, namespace=self.namespace)
                connection.subscribed = True
            return self._history.snapshot()

    def send(self, sid, payload):
        if not isinstance(payload, dict) or payload.keys() != {"text"}:
            return chat_error("chat_invalid")
        text, error = clean_public_text(payload["text"])
        if error:
            return chat_error(error)
        with self._lock:
            connection = self._connections.get(sid)
            if not connection or not connection.subscribed:
                return chat_error("chat_unavailable")
            if not self._limit.allow(connection.user_id, self.clock()):
                return chat_error("chat_rate_limited")
            message = self._history.add(connection.user_id, connection.name, text)
            self.socketio.emit("company_chat_message", message, to=PUBLIC_CHAT_ROOM, namespace=self.namespace)
            return {"ok": True}
