""" Read client.py for more """
from typing import Optional

import socket
import os

SIZE_HEADER_SIZE = 3

def send_msg(s: socket.socket, msg: str) -> None:
    message_bytes = msg.encode("utf-8")
    size = len(message_bytes)
    s.sendall(f"{size:0>{SIZE_HEADER_SIZE}}".encode("utf-8"))
    s.sendall(message_bytes)

def receive_msg(s: socket.socket) -> Optional[str]:
    size_header = s.recv(SIZE_HEADER_SIZE)
    if size_header == b'':
        return None
    else:
        # this might panic if the server doesn't conform to the protocol, but
        # we're ok with that
        size = int(size_header)

        # It's possible that recv returns less data than specified especially
        # with really long messages. afaik the max length of a TCP packet is 65535
        # bytes.
        # Additional reasons might include network lag, or smth like that.
        left = size
        buffer = b''
        while len(buffer) < size:
            res = s.recv(left)
            buffer += res
            left -= len(res)

        return buffer.decode("utf-8")

# in theory, this should use threads or be re-implemented with async
# i don't care though
# that's just a simple experiment
#
# note though that this means it will block until the client is disconnected
def handle_connection(client: socket.socket, addr: tuple[str, int]) -> None:
    hostname, port = addr
    print(f"new client has connected: ({hostname}:{port})")
    while True:
        if (x := receive_msg(client)) == "PING":
            send_msg(client, "PONG")
        else:
            print(f"client didn't send ping first, but {x!r}")
            client.shutdown(socket.RDWR)
            return

        msg = receive_msg(client)
        if msg is None:
            print(f"client sent an empty message or disconnected")
            client.shutdown(socket.RDWR)
            return

        if msg == "END":
            print(f"client {hostname}:{port} has disconnected")
            client.shutdown(socket.RDWR)
            return

        caps = msg.upper()
        send_msg(client, caps)

def serve(s: socket.socket) -> None:
    host = os.environ.get("SERVER_HOST", "localhost")
    port = os.environ.get("PORT", 8000)
    s.bind((host, port))
    s.listen()

    while True:
        client, client_addr = s.accept()
        with client:
            handle_connection(client, client_addr)

if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with s:
        serve(s)
