from typing import Optional

import time
import socket
import select
import sys
import tomllib

def fetch_peer_addr(
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote_host: str,
    remote_port: int,
) -> tuple[str, int]:
    req = f"JOIN#{our_id}@{peer_id}"
    s.sendto(req.encode('utf-8'), (remote_host, remote_port))

    print("<> send a message, fetching the response")

    while True:
        msg, sender_addr = s.recvfrom(100)
        if sender_addr == (remote_host, remote_port):
            server_msg = msg
            break
    our_addr_string, peer_addr_string = server_msg.decode("utf-8").split(";")

    our_host, our_port_string = our_addr_string.split(":")
    our_port = int(our_port_string)
    print(f"<> server says we are {our_host}:{our_port}")

    peer_host, peer_port_string = peer_addr_string.split(":")
    peer_port = int(peer_port_string)
    print(f"<> server says our peer is {peer_host}:{peer_port}")
    return (peer_host, peer_port)

def disconnect(
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote_host: str,
    remote_port: int,
) -> None:
    req = f"EXIT#{our_id}@{peer_id}"
    s.sendto(req.encode('utf-8'), (remote_host, remote_port))
    print("<> requested exit")

def hi_peer(s, peer_host, peer_port, dbg: bool = True):
    s.sendto(f"hi peer on {peer_host}".encode("utf-8"), (peer_host, peer_port))
    if dbg:
        print(f"<> said hello to peer")

def check_peer(s, dbg: bool=True):
    msg, addr = s.recvfrom(100)
    if dbg:
        print(f"<> got message from our peer on {addr}")
        print(f"<> {msg!r} our peer said")


def prepare_socket(port: Optional[int] = None) -> socket.socket:
    if port is None:
        try:
            port = int(sys.argv[1])
            print(f"<> using src port: {port}")
        except (ValueError, IndexError):
            port = 9_990
            print("<err> couldn't get the src port from arguments")
            print(f"<> using default src port: {port}")

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        try:
            host = "0.0.0.0"
            print(f"<> binding to {host}:{port}")
            s.bind((host, port))
            break
        except OSError as e:
            if e.errno == 48:
                print(f"<err> {port=} is taken, trying the next one")
                port += 1
            else:
                raise e
    return s


def main_loop(
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote_host: str,
    remote_port: int,
) -> None:
    peer_host, peer_port = fetch_peer_addr(
        s,
        our_id,
        peer_id,
        remote_host,
        remote_port,
    )
    print("<> starting the main loop")

    miss = 0
    got = 0

    now = time.time_ns()
    for i in range(50):
        if i == 0:
            print(f"<{i}th iteration>    ")
        else:
            print(f"\x1b[1A<{i}th iteration>    ")
        # repeat
        hi_peer(s, peer_host, peer_port, dbg=False)
        # anybody there?
        ok_read, ok_write, errs = select.select([s], [], [], 0.15)
        if ok_read:
            got += 1
            check_peer(ok_read[0], dbg=False)
        else:
            miss += 1

    print(f"{miss=}")
    print(f"{got=}")
    print(f"total time: {(time.time_ns() - now) / (10 ** 6)} miliseconds")


def main() -> None:
    try:
        with open("config.toml", "rb") as f:
            data = tomllib.load(f)

        remote_host = data["remote_host"]
        remote_port = int(data["remote_port"])

        our_id = data["our_id"]
        if len(sys.argv) >= 3:
            our_id = sys.argv[2]
            print(f"<> rewrite our_id with {our_id}")

        peer_id = data["peer_id"]
        if len(sys.argv) >= 4:
            peer_id = sys.argv[3]
            print(f"<> rewrite peer_id with {peer_id}")

    except Exception as e:
        print("couldn't read the config.toml")
        print(f"{e=}")
        sys.exit(1)

    s = prepare_socket()
    print(f"<> good, ready to connect to {remote_host}:{remote_port}")

    try:
        main_loop(
            s,
            our_id,
            peer_id,
            remote_host,
            remote_port,
        )
    finally:
        disconnect(
            s,
            our_id,
            peer_id,
            remote_host,
            remote_port,
        )

if __name__ == "__main__":
    main()
