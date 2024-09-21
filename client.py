from typing import Optional

import random
import copy
import time
import socket
import select
import sys
import tomllib
import itertools

# utils
Addr = tuple[str, int]
def timeout_recv(
    s: socket.socket,
    timeout: Optional[float] = None
) -> Optional[tuple[bytes, Addr]]:
    ok_read, _, _ = select.select([s], [], [], timeout)
    if ok_read:
        s = ok_read[0]
        msg, addr = s.recvfrom(100)
        return msg, addr
    else:
        return None
# end of utils

def make_peer_req(
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote: Addr,
) -> None:
    req = f"JOIN#{our_id}@{peer_id}"
    s.sendto(req.encode('utf-8'), remote)

def parse_addr(addr_string: str) -> Addr:
    host, port_string = addr_string.split(":")
    port = int(port_string)

    return host, port

def parse_server_msg(msg: bytes) -> tuple[Addr, Addr]:
    our_addr_string, peer_addr_string = msg.decode("utf-8").split(";")
    our = parse_addr(our_addr_string)
    peer = parse_addr(peer_addr_string)

    return our, peer

def same_line_print(i: int, msg: str, *args, **kwargs) -> None:
    # padding in case msg len changes
    padding = " " * 10
    if i == 0:
        print(f"{msg}" + padding, *args, **kwargs)
    else:
        to_prev_line = "\x1b[1A"
        print(f"{to_prev_line}{msg}" + padding, *args, **kwargs)

def first_peer_fetch(
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote: Addr,
) -> tuple[str, int]:

    server_msg = None
    for i in itertools.count():
        # declare that we exist
        make_peer_req(s, our_id, peer_id, remote)
        numbering = '' if i == 0 else f'#{i + 1}'
        same_line_print(i, f"<> requesting the connection {numbering}")

        # check the mailbox
        if (res := timeout_recv(s, 2)) is not None:
            msg, sender_addr = res
            # if the message from server, we got it
            if sender_addr == remote:
                server_msg = msg
                break

    if server_msg is None:
        raise RuntimeError("couldn't get the server message")

    # parse server message
    our, peer = parse_server_msg(server_msg)

    # print response
    print(f"<> server says we are {our[0]}:{our[1]}")
    print(f"<> server says our peer is {peer[0]}:{peer[1]}")

    # finally return response
    return peer

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



def prepare_socket(port: Optional[int] = None) -> socket.socket:
    if port is None:
        try:
            port = int(sys.argv[1])
            print(f"<> using src port: {port}")
        except (ValueError, IndexError):
            port = 9_990
            print("<warn> couldn't get the src port from arguments."
                  f" Using default src port: {port}")

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


class Stats:
    def __init__(self):
        # counters
        self.miss_counter = 0
        self.got_counter = 0
        self.other_counter = 0

        # failure counters
        self.err_clock = 0
        self.ok_clock = 0

        # start time
        self.start = time.time_ns()

        # used for periodics
        self.last = None
        self.ns = 0.0

    def miss(self):
        self.miss_counter += 1

        self.err_clock += 1

    def got(self):
        self.got_counter += 1

        self.ok_clock += 1
        self.err_clock = 0

    def other(self):
        self.other_counter += 1

    def failed_enough(self, err_limit: int) -> bool:
        if self.err_clock >= err_limit:
            self.err_clock = 0
            return True
        else:
            return False

    def good_enough(self, ok_limit: int) -> bool:
        if self.ok_clock >= ok_limit:
            self.ok_clock = 0
            return True
        else:
            return False

    def print_step(self):
        if self.last is None:
            miss = self.miss_counter
            got = self.got_counter
            other = self.other_counter
            ns_passed = time.time_ns() - self.start
        else:
            miss = self.miss_counter - self.last.miss_counter
            got = self.got_counter - self.last.got_counter
            other = self.other_counter - self.last.other_counter
            ns_passed = time.time_ns() - self.last.ns

        print(f"miss/got/other: {miss}/{got}/{other}")
        ms_passed = ns_passed / (10 ** 6)
        print(f"time: {ms_passed} milliseconds")

        self.last = copy.deepcopy(self)
        self.last.ns = time.time_ns()

    def print_results(self):
        print("Total stats")
        print("===========")
        print(f"miss:\n\t{self.miss_counter}")
        print(f"got:\n\t{self.got_counter}")
        print(f"other:\n\t{self.other_counter}")
        ms_passed = (time.time_ns() - self.start) / (10 ** 6)
        print(f"time:\n\t{ms_passed} miliseconds")

def try_to_reconnect(
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote: Addr
) -> socket.socket:
    # because both peers probably will try to reconnect
    # add some randomness to the process
    if random.random() >= 0.50:
        _, port = s.getsockname()
        s = prepare_socket(port + 1)
    # send peer request anyway though
    make_peer_req(s, our_id, peer_id, remote)
    return s

def establish_connection(
    stats: Stats,
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote: Addr,
) -> Addr:
    print("<> initiating connection")
    peer = first_peer_fetch(s, our_id, peer_id, remote)

    for i in range(100):
        # if missed to many requests, try to change the port
        if stats.failed_enough(10):
            s = try_to_reconnect(s, our_id, peer_id, remote)

        if stats.good_enough(10):
            print("<> connection is stable")
            return peer

        # ping
        s.sendto(b"ping", peer)

        # check the result
        if (res := timeout_recv(s, 0.15)) is not None:
            msg, addr = res
            if addr == peer:
                stats.got()
            elif addr == remote:
                _, peer = parse_server_msg(msg)
                print(f"new peer: {peer}")
                stats.other()
            else:
                print(f"unknown msg: {msg!r}:{addr}")
                stats.other()
        else:
            stats.miss()


        if (i % 10) == 0 and i != 0:
            stats.print_step()
    else:
        raise RuntimeError("failed to establish connection")

def next_pick(turn: int) -> str:
    pick = random.choice(["paper", "rock", "scissors"])
    print(f"<*> on turn {turn} we picked: {pick}")
    return pick

def play_loop(
    stats: Stats,
    s: socket.socket,
    peer: Addr,
    remote: Addr,
) -> None:
    turn = 0
    pick = next_pick(turn)

    peer_picks: dict[int, str] = {}
    msg_cache: set[bytes] = set()

    while turn < 10:
        our_msg = f"go:{turn}:{pick}".encode('utf-8')
        s.sendto(our_msg, peer)

        while True:
            if (res := timeout_recv(s, 0.15)) is not None:
                msg, addr = res
                if addr == remote:
                    _, peer = parse_server_msg(msg)
                    print(f"new peer: {peer}")
                    stats.other()
                    continue

                if addr != peer:
                    stats.other()
                    print(f"unexpected sender: {addr}, msg: {msg!r}")
                    continue

                data = msg.decode('utf-8').split(":")
                if data[0] == "ping":
                    stats.other()
                    print(f"leftover ping")
                    continue
                elif data[0] == "ack" and int(data[1]) == turn:
                    stats.got()
                    turn += 1
                    pick = next_pick(turn)
                    break
                elif data[0] == "go":
                    peer_turn = int(data[1])
                    if peer_picks.get(peer_turn) is None:
                        stats.got()
                        peer_pick = data[2]
                        peer_picks[peer_turn] = peer_pick
                        print(f"<_> on turn {peer_turn} opponent picked {peer_pick}")
                    else:
                        stats.other()
                    s.sendto(f"ack:{peer_turn}".encode('utf-8'), peer)
                    continue
                else:
                    stats.other()
                    if msg not in msg_cache:
                        msg_cache.add(msg)
                        print(f"unexpected msg: {msg!r}")
                    continue
            else:
                s.sendto(our_msg, peer)
                stats.miss()

def main_loop(
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote: Addr,
) -> None:
    stats = Stats()
    # establish a connection
    try:
        peer = establish_connection(stats, s, our_id, peer_id, remote)
        play_loop(stats, s, peer, remote)
    finally:
        stats.print_results()

def main() -> None:
    try:
        with open("config.toml", "rb") as f:
            data = tomllib.load(f)

        remote_host = data["remote_host"]
        remote_port = int(data["remote_port"])
        remote = (remote_host, remote_port)

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
            remote,
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
