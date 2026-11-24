import pytest

from stockfight import socketio
from stockfight.campaign_http import COMPANY_NAMESPACE
from test_multiplayer import advance, game, join_both, post, register
from test_private import create_invitation


def company_socket(app, http, token=None):
    if token is None:
        token = http.get("/api/me").json["csrfToken"]
    return socketio.test_client(
        app, flask_test_client=http, namespace=COMPANY_NAMESPACE, auth={"csrfToken": token},
    )


def emit_company(client, event, payload):
    return client.emit(event, payload, namespace=COMPANY_NAMESPACE, callback=True)


def company_messages(client):
    return [
        event["args"][0] for event in client.get_received(COMPANY_NAMESPACE)
        if event["name"] == "company_chat_message"
    ]


def test_public_chat_requires_a_valid_session_and_revokes_it_at_logout(game):
    app, _ = game
    first = register(app, "FirstCompany")
    second = register(app, "SecondCompany")
    assert not company_socket(app, app.test_client()).is_connected(COMPANY_NAMESPACE)
    assert not company_socket(app, first.http, "invalid").is_connected(COMPANY_NAMESPACE)

    sender = company_socket(app, first.http)
    listener = company_socket(app, second.http)
    assert sender.is_connected(COMPANY_NAMESPACE) and listener.is_connected(COMPANY_NAMESPACE)
    assert emit_company(sender, "company_chat_send", {"text": "Hej"})["error"] == "chat_unavailable"
    assert emit_company(sender, "company_chat_history", {}) == {"ok": True, "messages": []}
    assert emit_company(sender, "company_chat_send", {"text": "du är en hora"})["ok"]
    assert company_messages(listener) == []

    initial, = emit_company(listener, "company_chat_history", {})["messages"]
    assert (initial["userId"], initial["name"], initial["text"]) == (first.id, "FirstCompany", "du är en ****")
    assert company_messages(sender) == [initial]

    assert post(first.http, "/api/logout", {}).status_code == 200
    assert not sender.is_connected(COMPANY_NAMESPACE)
    assert listener.is_connected(COMPANY_NAMESPACE)
    assert emit_company(listener, "company_chat_history", {})["messages"] == [initial]


def test_public_chat_rejects_invalid_messages_and_limits_spam_per_account(game):
    app, _ = game
    first = register(app, "ChatSender")
    second = register(app, "ChatReceiver")
    sender = company_socket(app, first.http)
    another_tab = company_socket(app, first.http)
    listener = company_socket(app, second.http)
    for client in (sender, another_tab, listener):
        assert emit_company(client, "company_chat_history", {})["ok"]

    for payload in ({}, {"text": []}, {"text": " \t "}, {"text": "a" * 1000}, {"text": "Hej", "name": "Annat namn"}):
        response = emit_company(sender, "company_chat_send", payload)
        assert not response["ok"] and response["error"] == "chat_invalid"

    response = emit_company(sender, "company_chat_send", {"text": "Se https://example.com"})
    assert not response["ok"] and response["error"] == "chat_links"
    assert company_messages(listener) == []

    for index in range(5):
        client = sender if index % 2 == 0 else another_tab
        assert emit_company(client, "company_chat_send", {"text": f"Hej {index}"})["ok"]
    assert len(company_messages(listener)) == 5
    for client in (sender, another_tab):
        assert emit_company(client, "company_chat_send", {"text": "Hej igen"})["error"] == "chat_rate_limited"

    assert emit_company(listener, "company_chat_send", {"text": "En annan spelare"})["ok"]
    advance(game, 11)
    assert emit_company(sender, "company_chat_send", {"text": "Hej igen"})["ok"]


def test_public_chat_retains_only_the_latest_fifty_messages(game):
    app, _ = game
    first = register(app, "ChatHistory")
    sender = company_socket(app, first.http)
    assert emit_company(sender, "company_chat_history", {})["ok"]

    for index in range(52):
        advance(game, 11)
        assert emit_company(sender, "company_chat_send", {"text": f"Rad {index}"})["ok"]

    messages = emit_company(sender, "company_chat_history", {})["messages"]
    assert [message["text"] for message in messages] == [f"Rad {index}" for index in range(2, 52)]
    assert len({message["id"] for message in messages}) == len(messages)


def test_duel_chat_is_private_and_remains_available_until_results_expire(game):
    app, _ = game
    first, second = join_both(game)
    match_id = first.state()["id"]
    spectator = register(app, "ChatSpectator")
    other_match = register(app, "OtherMatch")
    assert spectator.emit("spectate_join", {"matchId": match_id})["ok"]
    assert other_match.emit("bot_start")["ok"]
    other_id = other_match.state()["id"]
    room = {"matchId": match_id}

    for outsider in (spectator, other_match):
        assert not outsider.emit("duel_chat_history", room)["ok"]
        assert not outsider.emit("duel_chat_send", {**room, "preset": "ez"})["ok"]
    assert not first.emit("duel_chat_history", {"matchId": other_id})["ok"]
    assert first.emit("duel_chat_history", room) == {"ok": True, "messages": []}
    assert second.emit("duel_chat_history", room) == {"ok": True, "messages": []}

    assert not first.emit("duel_chat_send", {**room, "preset": "my own message"})["ok"]
    assert not first.emit("duel_chat_send", {**room, "preset": "ez", "text": "spoofed"})["ok"]
    assert first.emit("duel_chat_send", {**room, "preset": "ez"})["ok"]
    message, = second.events("duel_chat_message")
    assert message["matchId"] == match_id and message["userId"] == first.id
    assert (message["name"], message["preset"], message["text"]) == ("BullPlayer", "ez", "EZ")
    assert first.events("duel_chat_message") == [message]
    assert not spectator.events("duel_chat_message")
    assert not other_match.events("duel_chat_message")

    second.socket.disconnect()
    second.connect()
    assert second.emit("duel_chat_history", room)["messages"] == [message]

    advance(game, 130)
    result, = first.events("match_result")
    assert result["id"] == match_id
    assert second.emit("duel_chat_send", {**room, "preset": "thumbs_up"})["ok"]
    emoji, = first.events("duel_chat_message")
    assert (emoji["userId"], emoji["kind"], emoji["text"]) == (second.id, "emoji", "👍")
    assert first.emit("duel_chat_history", room)["messages"] == [message, emoji]
    advance(game, 901)
    assert not first.emit("duel_chat_history", room)["ok"]
    assert not second.emit("duel_chat_send", {**room, "preset": "ez"})["ok"]


@pytest.mark.parametrize("mode", ["private", "prediction", "bot"])
def test_preset_chat_is_available_in_other_duels(game, mode):
    app, _ = game
    first = register(app, "FirstDuelist")
    if mode == "bot":
        assert first.emit("bot_start")["ok"]
        receiver = first
    else:
        receiver = register(app, "SecondDuelist")
        if mode == "private":
            assert receiver.emit("private_join", {"code": create_invitation(first)})["ok"]
        else:
            assert first.emit("queue_join", {"mode": "prediction"})["ok"]
            assert receiver.emit("queue_join", {"mode": "prediction"})["ok"]

    state = first.state()
    room = {"matchId": state["id"]}
    assert state["mode"] == mode
    assert receiver.emit("duel_chat_history", room)["ok"]
    preset = "ez" if mode == "bot" else "gg"
    assert first.emit("duel_chat_send", {**room, "preset": preset})["ok"]
    messages = receiver.events("duel_chat_message")
    assert any(
        message["preset"] == preset and message["userId"] == first.id
        for message in messages
    )
    if mode == "bot":
        assert any(message["userId"] == state["opponent"]["id"] and message["kind"] == "emoji"
                   for message in messages)


def test_duel_chat_limits_spam_without_blocking_the_other_player(game):
    first, second = join_both(game)
    room = {"matchId": first.state()["id"]}
    assert first.emit("duel_chat_history", room)["ok"]
    assert second.emit("duel_chat_history", room)["ok"]

    for preset in ("gg", "gl", "wave", "fire", "laugh"):
        assert first.emit("duel_chat_send", {**room, "preset": preset})["ok"]
    blocked = first.emit("duel_chat_send", {**room, "preset": "ez"})
    assert not blocked["ok"] and blocked["error"] == "chat_rate_limited"
    assert len(second.events("duel_chat_message")) == 5

    assert second.emit("duel_chat_send", {**room, "preset": "ez"})["ok"]
    advance(game, 11)
    assert first.emit("duel_chat_send", {**room, "preset": "ez"})["ok"]


def test_solo_practice_does_not_create_a_duel_chat_room(game):
    app, _ = game
    player = register(app, "SoloLearner")
    assert player.emit("prediction_practice_start")["ok"]
    room = {"matchId": player.state()["id"]}
    assert not player.emit("duel_chat_history", room)["ok"]
    assert not player.emit("duel_chat_send", {**room, "preset": "ez"})["ok"]
