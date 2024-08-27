"""
Implements a simple chat-like interface to the server

Enter the message to receive response.

Required variables:
    - SERVER_HOST, server's host to connect to.

Optional variabes:
    - PORT, port to connect to. Default is 8000.

Protocol details:
    Each message, be it from client or to the client should first send a size
    header three-byte long. For example, "014" for the message that contains 14
    bytes.
"""
from typing import Optional

import socket
import sys
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

if __name__ == "__main__":
    # AF_INET for IPv4 and SOCK_STREAM for TCP
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = os.environ.get("SERVER_HOST", "localhost")
    port = os.environ.get("PORT", 8000)

    try:
        s.connect((host, port))
    except ConnectionRefusedError as e:
        print("Couldn't connect (probably because the server hasn't started)")
        print(f"\t{e}")
        sys.exit(1)

    print(f"connected to the server as {s.getsockname()}")
    while True:
        # ping-pong just in case
        send_msg(s, "PING")
        if (x := receive_msg(s)) != "PONG":
            print(f"Server doesn't respond with PONG, but instead with {x!r}")
            sys.exit(1)

        # send input to the server
        msg = input("> ")
        send_msg(s, msg)
        if msg == "END":
            print("bye")
            sys.exit(0)

        # receive response
        res = receive_msg(s)
        print(f"[ {res}")
