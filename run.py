import os

from stockfight import create_app, socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(
        app,
        host=os.getenv("STOCK_FIGHT_DEV_HOST", "127.0.0.1"),
        port=int(os.getenv("STOCK_FIGHT_PORT", "8080")),
        allow_unsafe_werkzeug=True,
    )
