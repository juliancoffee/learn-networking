import socket
import os

def handle_connection(client: socket.socket) -> None:
    raise NotImplementedError

if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = os.environ["SERVER_HOST"]
    port = os.environ.get("PORT", 8000)
    s.bind((host, port))
    s.listen()

    while True:
        client, _client_addr = s.accept()
        handle_connection(client)
