import hmac
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from math import ceil
from random import Random
from secrets import choice
from threading import RLock
from time import monotonic
from uuid import uuid4

from flask import Flask, current_app, request, session
from flask_socketio import SocketIO
from sqlalchemy.exc import SQLAlchemyError

from .bot import TradingBot
from .data import User, db, get_rating, save_match
from .engine import BOT, PRIVATE, RANKED, GameMode, Match, RuleError
from .market_data import MarketDataUnavailable, MarketProvider
from .prediction import MAX_ROUNDS, PREDICTION, PredictionMatch
from .practice import PRACTICE_MODE, PredictionPractice
from .ranking import search_radius

TRADE_FIELDS = {
    "buy": {"percent"},
    "short": {"percent"},
    "sell": set(),
    "confirm_sell": {"choice", "positionId"},
}
RESULT_RETENTION = 900
PRIVATE_INVITE_SECONDS = 900
PRIVATE_CODE_LENGTH = 8
PRIVATE_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
BOT_USER_ID = 0  # Registered accounts receive positive IDs from SQLite.


def token_matches(expected, supplied):
    return (
        isinstance(expected, str)
        and isinstance(supplied, str)
        and hmac.compare_digest(expected.encode(), supplied.encode())
    )


@dataclass(frozen=True)
class QueueEntry:
    user_id: int
    name: str
    mode: str
    elo: int
    joined: float


@dataclass
class LiveMatch:
    game: Match | PredictionMatch
    started_at: datetime
    # Only human players in trading matches send numbered trade commands.
    next_seq: dict[int, int]
    bot: TradingBot | None = None
    retry_after: float = 0.0
    rematch_of: str | None = None


@dataclass(frozen=True)
class PrivateInvitation:
    code: str
    expires_at: float


@dataclass
class PrivateRematch:
    players: dict[int, str]
    expires_at: float
    accepted: set[int] = field(default_factory=set)


@dataclass(frozen=True)
class Connection:
    user_id: int
    session_token: str


@dataclass
class MatchService:
    app: Flask
    socketio: SocketIO
    provider: MarketProvider
    mode: GameMode = RANKED
    queue: dict[int, QueueEntry] = field(default_factory=dict, init=False)
    matches: dict[str, LiveMatch] = field(default_factory=dict, init=False)
    _match_by_user: dict[int, str] = field(default_factory=dict, init=False)
    _connections: dict[str, Connection] = field(default_factory=dict, init=False)
    _sids: dict[int, set[str]] = field(default_factory=dict, init=False)
    _results: dict[int, tuple[float, dict]] = field(default_factory=dict, init=False)
    _private_invitations: dict[int, PrivateInvitation] = field(default_factory=dict, init=False)
    _private_rematches: dict[str, PrivateRematch] = field(default_factory=dict, init=False)
    _lock: RLock = field(default_factory=RLock, init=False)
    _running: bool = field(default=False, init=False)
    _queue_reported: int = field(default=-1, init=False)
    _practices: dict[int, PredictionPractice] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.clock = self.app.config.get("MATCH_CLOCK", monotonic)
        self.countdown = self.app.config["MATCH_COUNTDOWN"]
        self.tick_seconds = self.app.config["MARKET_TICK_SECONDS"]
        self.preview_count = self.app.config["MATCH_PREVIEW_BARS"]

    def connect(self, sid, user_id, token):
        with self._lock:
            now = self.clock()
            self._connections[sid] = Connection(user_id, token)
            self._sids.setdefault(user_id, set()).add(sid)
            live = self._live_for(user_id)
            if live:
                self.socketio.server.enter_room(sid, live.game.id)
                self._advance_match(live, now)
                if live.game.id in self.matches:
                    self._send_state(live, user_id, now, sid)
                    self._send_private(user_id, now, sid=sid)
                    return
                # Finishing the match above already sent this connection the result.
                return
            self._prune_practices(now)
            practice = self._practices.get(user_id)
            if practice:
                practice.reconnect_until = None
                self._send_practice(practice, now, sid=sid)
            else:
                result = self._results.get(user_id)
                if result and result[0] > now:
                    self.socketio.emit("match_result", result[1], to=sid)
                self._emit_user("prediction_practice_ended", {"id": None}, user_id, sid=sid)
            self._notify_private_peer(user_id, now)
            self._send_private(user_id, now, sid=sid)
            self._send_queue(user_id, now, sid=sid)

    def disconnect(self, sid):
        with self._lock:
            connection = self._connections.pop(sid, None)
            if connection is None:
                return
            user_id = connection.user_id
            self._sids[user_id].discard(sid)
            if not self._sids[user_id]:
                del self._sids[user_id]
                self.queue.pop(user_id, None)
                now = self.clock()
                practice = self._practices.get(user_id)
                if practice:
                    practice.reconnect_until = now + RESULT_RETENTION
                self._notify_private_peer(user_id, now)

    def disconnect_session(self, token):
        with self._lock:
            sids = [
                sid for sid, connection in self._connections.items()
                if connection.session_token == token
            ]
            for sid in sids:
                self.disconnect(sid)
        for sid in sids:
            self.socketio.server.disconnect(sid, namespace="/")

    def queue_join(self, sid, payload=None):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            if payload is None:
                payload = {}
            if not isinstance(payload, dict) or payload.keys() - {"mode"}:
                return failure("Ogiltig köförfrågan.")
            mode = payload.get("mode", self.mode.key)
            if mode not in (self.mode.key, PREDICTION.key):
                return failure("Okänt spelläge.")
            user_id = connection.user_id
            now = self.clock()
            live = self._live_for(user_id)
            if live:
                self._send_state(live, user_id, now, sid)
                return {"ok": True}
            entry = self.queue.get(user_id)
            if entry is None or entry.mode != mode:
                user = db.session.get(User, user_id)
                if user is None:
                    return failure("Kontot finns inte längre.")
                self._drop_practice(user_id)
                self._leave_private(user_id, now)
                self._results.pop(user_id, None)
                self.queue[user_id] = QueueEntry(user_id, user.username, mode, get_rating(user_id, mode).elo, now)
            self._send_queue(user_id, now)
            self._match_queue(now)
            self._start_background()
            return {"ok": True}

    def queue_leave(self, sid):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            user_id = connection.user_id
            live = self._live_for(user_id)
            if live:
                self._send_state(live, user_id, self.clock(), sid)
                return failure("En match har redan startat.")
            self.queue.pop(user_id, None)
            self._send_queue(user_id, self.clock())
            return {"ok": True}

    def bot_start(self, sid):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            user_id = connection.user_id
            live = self._live_for(user_id)
            if live:
                self._send_state(live, user_id, self.clock(), sid)
                return {"ok": True}

            user = db.session.get(User, user_id)
            if user is None:
                return failure("Kontot finns inte längre.")
            elo = get_rating(user_id, RANKED.key).elo
            try:
                self._create_match({user_id: user.username}, BOT, bot=TradingBot(elo, Random()))
            except MarketDataUnavailable as error:
                return failure(str(error))
            self._start_background()
            return {"ok": True}

    def private_create(self, sid, payload):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            if payload not in (None, {}):
                return failure("Ogiltig inbjudningsförfrågan.")
            user_id = connection.user_id
            if self._live_for(user_id):
                return failure("Du har redan en aktiv match.")

            now = self.clock()
            self._expire_private(now)
            if user_id not in self._private_invitations:
                self._drop_practice(user_id)
                self._leave_private(user_id, now)
                self._results.pop(user_id, None)
                if self.queue.pop(user_id, None) is not None:
                    self._send_queue(user_id, now)
                used_codes = {invitation.code for invitation in self._private_invitations.values()}
                code = self._new_private_code()
                while code in used_codes:
                    code = self._new_private_code()
                self._private_invitations[user_id] = PrivateInvitation(code, now + PRIVATE_INVITE_SECONDS)
            self._send_private(user_id, now)
            self._start_background()
            return {"ok": True}

    def private_join(self, sid, payload):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            if not isinstance(payload, dict) or payload.keys() != {"code"} or not isinstance(payload["code"], str):
                return failure("Ogiltig inbjudningsförfrågan.")
            code = payload["code"].strip().upper()
            if len(code) != PRIVATE_CODE_LENGTH or any(character not in PRIVATE_CODE_ALPHABET for character in code):
                return failure("Ange en giltig matchkod.")

            now = self.clock()
            self._expire_private(now)
            host_id = next((user_id for user_id, invite in self._private_invitations.items() if invite.code == code), None)
            if host_id is None:
                return failure("Matchkoden finns inte eller har gått ut.")
            user_id = connection.user_id
            if host_id == user_id:
                return failure("Du kan inte gå med i din egen kompismatch.")
            if self._live_for(user_id) or self._live_for(host_id):
                return failure("En av spelarna har redan en aktiv match.")
            if host_id not in self._sids:
                return failure("Värden är inte ansluten. Försök igen när värden är tillbaka.")

            host = db.session.get(User, host_id)
            guest = db.session.get(User, user_id)
            if host is None or guest is None:
                return failure("En av spelarnas konton finns inte längre.")
            try:
                self._create_match({host_id: host.username, user_id: guest.username}, PRIVATE)
            except MarketDataUnavailable as error:
                return failure(str(error))
            self._start_background()
            return {"ok": True}

    def private_cancel(self, sid, payload):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            user_id = connection.user_id
            now = self.clock()
            if payload in (None, {}):
                self._private_invitations.pop(user_id, None)
                self._send_private(user_id, now)
            elif isinstance(payload, dict) and payload.keys() == {"matchId"} and isinstance(payload["matchId"], str):
                match_id, _ = self._private_rematch_for(user_id, now)
                if payload["matchId"] == match_id:
                    self._leave_private(user_id, now)
            else:
                return failure("Ogiltig förfrågan.")
            return {"ok": True}

    def private_rematch(self, sid, payload):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            if not isinstance(payload, dict) or payload.keys() != {"matchId"} or not isinstance(payload["matchId"], str):
                return failure("Ogiltig revanschförfrågan.")

            match_id = payload["matchId"]
            user_id = connection.user_id
            live = self._live_for(user_id)
            if live is not None and live.rematch_of == match_id:
                self._send_state(live, user_id, self.clock(), sid)
                return {"ok": True}

            now = self.clock()
            self._expire_private(now)
            rematch_id, rematch = self._private_rematch_for(user_id, now)
            if rematch is None or rematch_id != match_id:
                return failure("Revanschen är inte längre tillgänglig.")
            opponent_id = next(player_id for player_id in rematch.players if player_id != user_id)
            if opponent_id not in self._sids:
                return failure("Motståndaren är inte ansluten.")
            if opponent_id not in rematch.accepted:
                rematch.accepted.add(user_id)
                for player_id in rematch.players:
                    self._send_private(player_id, now)
                return {"ok": True}

            try:
                self._create_match(rematch.players, PRIVATE, rematch_of=match_id)
            except MarketDataUnavailable as error:
                return failure(str(error))
            self._start_background()
            return {"ok": True}

    def trade(self, sid, payload):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            if not isinstance(payload, dict):
                return failure("Ogiltig handelsförfrågan.")
            action = payload.get("action")
            if not isinstance(action, str) or action not in TRADE_FIELDS:
                return failure("Okänd handelsåtgärd.")
            if payload.keys() != TRADE_FIELDS[action] | {"action", "matchId", "seq"}:
                return failure("Ogiltiga fält i handelsförfrågan.")

            user_id = connection.user_id
            live = self._live_for(user_id)
            if not live or live.game.id != payload["matchId"]:
                return failure("Matchen är inte aktiv.")
            if isinstance(live.game, PredictionMatch):
                return failure("Handel är inte tillgänglig i Ritduell.")
            now = self.clock()
            self._advance_match(live, now)
            if live.game.status != "active":
                return failure("Matchen är inte aktiv.")

            expected = live.next_seq[user_id]
            seq = payload["seq"]
            if type(seq) is not int or seq != expected:
                self._send_state(live, user_id, now, sid)
                return failure("Handelsförfrågan är redan behandlad eller ur ordning.")
            live.next_seq[user_id] = expected + 1
            try:
                outcome = live.game.act(user_id, action, payload, now)
            except RuleError as error:
                self._send_state(live, user_id, now)
                return failure(str(error))
            self._broadcast_state(live, now)
            if live.game.status == "finished":
                self._finish(live, now)
            return {"ok": True, **outcome}

    def prediction_submit(self, sid, payload):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            if not isinstance(payload, dict) or payload.keys() != {"matchId", "round", "moveBps"}:
                return failure("Ogiltig prognosförfrågan.")

            user_id = connection.user_id
            practice = self._practices.get(user_id)
            if practice and practice.id == payload["matchId"]:
                try:
                    practice.submit(payload["round"], payload["moveBps"])
                except RuleError as error:
                    self._send_practice(practice, self.clock(), sid=sid)
                    return failure(str(error))
                self._send_practice(practice, self.clock())
                return {"ok": True}

            live = self._live_for(user_id)
            if not live or live.game.id != payload["matchId"] or not isinstance(live.game, PredictionMatch):
                return failure("Du har ingen aktiv ritduell.")
            now = self.clock()
            self._advance_match(live, now)
            if live.game.status != "active":
                return failure("Matchen är inte aktiv.")

            try:
                live.game.submit(user_id, payload["round"], payload["moveBps"], now)
            except RuleError as error:
                self._send_state(live, user_id, now, sid)
                return failure(str(error))
            self._broadcast_state(live, now)
            return {"ok": True}

    def prediction_practice_start(self, sid, payload=None):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            if payload not in (None, {}):
                return failure("Ogiltig övningsförfrågan.")
            user_id = connection.user_id
            now = self.clock()
            live = self._live_for(user_id)
            if live:
                self._send_state(live, user_id, now, sid)
                return failure("Avsluta din pågående match först.")
            self._prune_practices(now)
            practice = self._practices.get(user_id)
            if practice:
                self._send_practice(practice, now, sid=sid)
                return {"ok": True}

            user = db.session.get(User, user_id)
            if user is None:
                return failure("Kontot finns inte längre.")
            self._leave_private(user_id, now)
            self.queue.pop(user_id, None)
            self._results.pop(user_id, None)
            practice = PredictionPractice(uuid4().hex, user_id, user.username, now)
            self._practices[user_id] = practice
            self._send_practice(practice, now)
            return {"ok": True}

    def prediction_practice_next(self, sid, payload):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            if not isinstance(payload, dict) or payload.keys() != {"matchId", "round"}:
                return failure("Ogiltig övningsförfrågan.")

            user_id = connection.user_id
            now = self.clock()
            practice = self._practices.get(user_id)
            if not practice:
                cached = self._results.get(user_id)
                if cached and cached[0] > now:
                    result = cached[1]
                    if (
                        result["mode"] == PRACTICE_MODE
                        and result["id"] == payload["matchId"]
                        and type(payload["round"]) is int
                        and result["roundsPlayed"] == payload["round"]
                    ):
                        self._emit_user("match_result", result, user_id, sid=sid)
                        return {"ok": True}
                return failure("Du har ingen aktiv övning.")
            if practice.id != payload["matchId"]:
                return failure("Förfrågan gäller en annan övning.")
            try:
                completed = practice.next_round(payload["round"])
            except RuleError as error:
                self._send_practice(practice, now, sid=sid)
                return failure(str(error))
            if completed:
                result = practice.result(now)
                self._practices.pop(user_id)
                self._results[user_id] = (now + RESULT_RETENTION, result)
                self._emit_user("match_result", result, user_id)
            else:
                self._send_practice(practice, now)
            return {"ok": True}

    def prediction_practice_leave(self, sid, payload):
        with self._lock:
            connection = self._connections.get(sid)
            if not connection:
                return failure("Logga in igen.")
            if not isinstance(payload, dict) or payload.keys() != {"matchId"}:
                return failure("Ogiltig övningsförfrågan.")
            user_id = connection.user_id
            practice = self._practices.get(user_id)
            if practice and practice.id != payload["matchId"]:
                return failure("Förfrågan gäller en annan övning.")
            self._drop_practice(user_id)
            return {"ok": True}

    def _send_practice(self, practice, now, *, sid=None):
        self._emit_user("match_state", practice.public(now), practice.user_id, sid=sid)

    def _drop_practice(self, user_id):
        practice = self._practices.pop(user_id, None)
        if practice:
            self._emit_user("prediction_practice_ended", {"id": practice.id}, user_id)

    def _prune_practices(self, now):
        for user_id, practice in tuple(self._practices.items()):
            if practice.reconnect_until is not None and practice.reconnect_until <= now:
                self._practices.pop(user_id)

    def pump(self):
        with self.app.app_context(), self._lock:
            now = self.clock()
            for live in list(self.matches.values()):
                self._advance_match(live, now)
            self._match_queue(now)
            if int(now) != self._queue_reported:
                self._queue_reported = int(now)
                self._prune_practices(now)
                for user_id in self.queue:
                    self._send_queue(user_id, now)
                self._expire_private(now)
                self._results = {
                    user_id: result for user_id, result in self._results.items() if result[0] > now
                }

    def _start_background(self):
        if self.app.config["MATCH_BACKGROUND"] and not self._running and self._has_background_work():
            self._running = True
            self.socketio.start_background_task(self._background_loop)

    def _has_background_work(self):
        return bool(self.queue or self.matches or self._private_invitations or self._private_rematches)

    def _background_loop(self):
        while True:
            try:
                self.pump()
            except SQLAlchemyError:
                self.app.logger.exception("Databasfel vid uppdatering av Stock Fight.")
                self.socketio.sleep(1)
            with self._lock:
                if not self._has_background_work():
                    self._running = False
                    return
            self.socketio.sleep(0.1)

    def _match_queue(self, now):
        for first in tuple(self.queue.values()):
            if first.user_id not in self.queue:
                continue
            for second in tuple(self.queue.values()):
                if first.user_id == second.user_id or first.mode != second.mode:
                    continue
                radius = min(search_radius(now - first.joined), search_radius(now - second.joined))
                if abs(first.elo - second.elo) <= radius:
                    self._create_ranked_match(first, second)
                    break

    def _create_ranked_match(self, first, second):
        players = {first.user_id: first.name, second.user_id: second.name}
        mode = PREDICTION if first.mode == PREDICTION.key else self.mode
        try:
            self._create_match(players, mode)
        except MarketDataUnavailable as error:
            for user_id in players:
                self.queue.pop(user_id, None)
                self._send_queue(user_id, self.clock(), error=str(error))

    def _create_match(self, players, mode, *, bot=None, rematch_of=None):
        is_prediction = mode.key == PREDICTION.key
        remaining_bars = MAX_ROUNDS if is_prediction else ceil(mode.scenario_seconds / self.tick_seconds)
        required_bars = self.preview_count + remaining_bars
        scenario = self.provider.choose(required_bars=required_bars, preview_count=self.preview_count)
        match_id = uuid4().hex
        now = self.clock()
        if is_prediction:
            game = PredictionMatch(match_id, players, scenario, now, countdown=self.countdown)
            next_seq = {}
        else:
            participants = {**players, BOT_USER_ID: "Bot"} if bot is not None else players
            game = Match(
                match_id, participants, scenario, now,
                tick_seconds=self.tick_seconds, countdown=self.countdown, mode=mode,
            )
            next_seq = dict.fromkeys(players, 1)
        started_at = datetime.now(UTC) + timedelta(seconds=self.countdown)
        live = LiveMatch(game, started_at, next_seq, bot=bot, rematch_of=rematch_of)
        self.matches[game.id] = live
        for user_id in players:
            self._drop_practice(user_id)
            self._leave_private(user_id, now)
            self.queue.pop(user_id, None)
            self._results.pop(user_id, None)
            self._match_by_user[user_id] = game.id
            for sid in self._sids.get(user_id, ()):
                self.socketio.server.enter_room(sid, game.id)
        self._broadcast_state(live, now)

    def _advance_match(self, live, now):
        changed = live.game.advance(now)
        if live.bot is not None and live.bot.act(live.game, BOT_USER_ID, now):
            changed = True
        if changed:
            self._broadcast_state(live, now)
        if live.game.status == "finished" and now >= live.retry_after:
            self._finish(live, now)

    def _finish(self, live, now):
        game = live.game
        ratings = {}
        if game.mode.key in (RANKED.key, PREDICTION.key):
            ended_at = live.started_at + timedelta(seconds=game.duration)
            try:
                ratings = save_match(game, live.started_at, ended_at)
            except SQLAlchemyError:
                db.session.rollback()
                live.retry_after = now + 1
                self.app.logger.exception("Kunde inte spara match %s. Försöker igen.", game.id)
                return
        elif live.bot is not None:
            elo = live.bot.elo
            ratings = {user_id: {"eloBefore": elo, "eloAfter": elo} for user_id in live.next_seq}

        expires_at = now + RESULT_RETENTION
        if game.mode.key == PRIVATE.key:
            players = {user_id: player.name for user_id, player in game.players.items()}
            self._private_rematches[game.id] = PrivateRematch(players, expires_at)

        scenario = game.scenario
        for user_id in game.players:
            if user_id == BOT_USER_ID:
                continue
            outcome = "draw" if game.winner_id is None else "win" if game.winner_id == user_id else "lose"
            result = {
                **game.summary(user_id),
                **ratings.get(user_id, {}),
                "id": game.id,
                "mode": game.mode.key,
                "outcome": outcome,
                "duration": game.duration,
                "symbol": scenario.symbol,
                "name": scenario.name,
                "market": scenario.market,
                "interval": scenario.interval,
                "synthetic": scenario.synthetic,
                "periodStart": scenario.bars[0].timestamp.isoformat(),
                "periodEnd": scenario.bars[game.revealed_count - 1].timestamp.isoformat(),
            }
            self._results[user_id] = (expires_at, result)
            self._emit_user("match_result", result, user_id)
            self._match_by_user.pop(user_id, None)
        if game.mode.key == PRIVATE.key:
            for user_id in game.players:
                self._send_private(user_id, now)
        self.socketio.server.close_room(game.id, namespace="/")
        self.matches.pop(game.id, None)

    @staticmethod
    def _new_private_code():
        return "".join(choice(PRIVATE_CODE_ALPHABET) for _ in range(PRIVATE_CODE_LENGTH))

    def _private_rematch_for(self, user_id, now):
        previous = self._results.get(user_id)
        if previous is None or previous[0] <= now:
            return None, None
        match_id = previous[1]["id"]
        rematch = self._private_rematches.get(match_id)
        if rematch is None or rematch.expires_at <= now:
            return None, None
        return match_id, rematch

    def _send_private(self, user_id, now, *, sid=None):
        invitation = self._private_invitations.get(user_id)
        invitation_state = None
        if invitation is not None and invitation.expires_at > now:
            invitation_state = {"code": invitation.code, "remaining": ceil(invitation.expires_at - now)}
        match_id, rematch = self._private_rematch_for(user_id, now)
        rematch_state = None
        if rematch is not None:
            opponent_id = next(player_id for player_id in rematch.players if player_id != user_id)
            rematch_state = {
                "matchId": match_id,
                "selfAccepted": user_id in rematch.accepted,
                "opponentAccepted": opponent_id in rematch.accepted,
                "available": opponent_id in self._sids,
                "remaining": ceil(rematch.expires_at - now),
            }
        self._emit_user("private_state", {"invitation": invitation_state, "rematch": rematch_state}, user_id, sid=sid)

    def _notify_private_peer(self, user_id, now):
        _, rematch = self._private_rematch_for(user_id, now)
        if rematch is not None:
            opponent_id = next(player_id for player_id in rematch.players if player_id != user_id)
            self._send_private(opponent_id, now)

    def _leave_private(self, user_id, now):
        invitation = self._private_invitations.pop(user_id, None)
        match_id, rematch = self._private_rematch_for(user_id, now)
        if rematch is not None:
            self._private_rematches.pop(match_id)
            for player_id in rematch.players:
                self._send_private(player_id, now)
        elif invitation is not None:
            self._send_private(user_id, now)

    def _expire_private(self, now):
        affected_users = set()
        for user_id, invitation in tuple(self._private_invitations.items()):
            if invitation.expires_at <= now:
                self._private_invitations.pop(user_id)
                affected_users.add(user_id)
        for match_id, rematch in tuple(self._private_rematches.items()):
            if rematch.expires_at <= now:
                self._private_rematches.pop(match_id)
                affected_users.update(rematch.players)
        for user_id in affected_users:
            self._send_private(user_id, now)

    def _live_for(self, user_id):
        return self.matches.get(self._match_by_user.get(user_id))

    def _send_state(self, live, user_id, now, sid=None):
        state = live.game.public(user_id, now)
        if user_id in live.next_seq:
            state["nextSeq"] = live.next_seq[user_id]
        if live.bot is not None:
            state["opponent"]["elo"] = live.bot.elo
        self._emit_user("match_state", state, user_id, sid=sid)

    def _broadcast_state(self, live, now):
        for user_id in live.game.players:
            if user_id != BOT_USER_ID:
                self._send_state(live, user_id, now)

    def _send_queue(self, user_id, now, *, sid=None, error=None):
        entry = self.queue.get(user_id)
        waited = now - entry.joined if entry else 0
        state = {"queued": entry is not None, "waited": int(waited), "radius": search_radius(waited)}
        if entry is not None:
            state["mode"] = entry.mode
        if error:
            state["error"] = error
        self._emit_user("queue_state", state, user_id, sid=sid)

    def _emit_user(self, event, payload, user_id, sid=None):
        targets = (sid,) if sid is not None else self._sids.get(user_id, ())
        for target in targets:
            self.socketio.emit(event, payload, to=target)


def failure(message):
    return {"ok": False, "error": message}


def install_handlers(socketio):
    def service():
        return current_app.extensions["match_service"]

    @socketio.on("connect")
    def on_connect(auth=None):
        user_id = session.get("user_id")
        token = session.get("csrf")
        if (
            not isinstance(auth, dict)
            or not token_matches(token, auth.get("csrfToken"))
            or user_id is None
            or db.session.get(User, user_id) is None
        ):
            return False
        service().connect(request.sid, user_id, token)

    @socketio.on("disconnect")
    def on_disconnect(reason=None):
        service().disconnect(request.sid)

    @socketio.on("queue_join")
    def on_queue_join(payload=None):
        return service().queue_join(request.sid, payload)

    @socketio.on("queue_leave")
    def on_queue_leave(payload=None):
        return service().queue_leave(request.sid)

    @socketio.on("bot_start")
    def on_bot_start(payload=None):
        return service().bot_start(request.sid)

    @socketio.on("private_create")
    def on_private_create(payload=None):
        return service().private_create(request.sid, payload)

    @socketio.on("private_join")
    def on_private_join(payload=None):
        return service().private_join(request.sid, payload)

    @socketio.on("private_cancel")
    def on_private_cancel(payload=None):
        return service().private_cancel(request.sid, payload)

    @socketio.on("private_rematch")
    def on_private_rematch(payload=None):
        return service().private_rematch(request.sid, payload)

    @socketio.on("trade")
    def on_trade(payload=None):
        return service().trade(request.sid, payload)

    @socketio.on("prediction_submit")
    def on_prediction_submit(payload=None):
        return service().prediction_submit(request.sid, payload)

    @socketio.on("prediction_practice_start")
    def on_prediction_practice_start(payload=None):
        return service().prediction_practice_start(request.sid, payload)

    @socketio.on("prediction_practice_next")
    def on_prediction_practice_next(payload=None):
        return service().prediction_practice_next(request.sid, payload)

    @socketio.on("prediction_practice_leave")
    def on_prediction_practice_leave(payload=None):
        return service().prediction_practice_leave(request.sid, payload)
