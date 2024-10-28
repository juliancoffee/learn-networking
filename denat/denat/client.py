from __future__ import annotations

from typing import Optional, Literal

import enum
import random
import copy
import time
import socket
import select
import sys
import tomllib
import itertools
import logging
from .t import assert_never_seq, unreachable

# utils
logging.basicConfig()
logger = logging.getLogger(__name__)

Addr = tuple[str, int]
def timeout_recv(
    s: socket.socket,
    *,
    timeout: Optional[float] = None,
    buff_len: int = 1000,
) -> Optional[tuple[bytes, Addr]]:
    ok_read, _, _ = select.select([s], [], [], timeout)
    if ok_read:
        s = ok_read[0]
        msg, addr = s.recvfrom(buff_len)
        return msg, addr
    else:
        return None
# end of utils

# ReUDP
class TickResult(enum.Enum):
    # handshake
    GotInitAck = enum.auto()
    GotInitSyn = enum.auto()
    # messages
    GotMsg = enum.auto()
    GotAck = enum.auto()
    # meta
    DupOrEarly = enum.auto()
    Timeout = enum.auto()

HandleResult = Literal[
        TickResult.GotInitSyn,
        TickResult.GotInitAck,
        TickResult.GotMsg,
        TickResult.GotAck,
        TickResult.DupOrEarly,
    ]

def register(stats: Stats, res: HandleResult) -> None:
    match res:
        case TickResult.GotInitSyn | TickResult.GotInitAck:
            stats.meta()
        case TickResult.GotMsg | TickResult.GotAck:
            stats.got()
        case TickResult.DupOrEarly:
            stats.other()

class ReUDP:
    """ Re_liable_UDP object to use with deNAT

    Guarantees:
        - All messages will be delivered.
        - Message should arrive in order.
    """

    def __init__(
        self,
        s: socket.socket,
        our_id: str,
        peer_id: str,
        remote: Addr,
    ) -> None:
        # init data
        self.remote = remote
        self.our_id = our_id
        self.peer_id = peer_id

        # consts
        self.init_x = random.randint(0, 100)

        # switches
        self.s = s
        self.peer = self.first_peer_fetch()
        self.us_ok = False
        self.end = False

        # state
        self.reconnects = 0
        self.stats = Stats()

        self.last_received_id = -1
        self.received: dict[int, str] = {}
        self.read_queue: list[tuple[str, Addr]] = []

        self.last_sent_id = itertools.count()
        self.sent: dict[int, tuple[str, float, bool]] = {}

        # start a handshake
        init_syn = self.syn_msg()
        self.raw_send(init_syn)


    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.end = True
        # exit from the remote server mapping
        # NOTE: using UDP, packet may or may not be delivered
        disconnect(self.s, self.our_id, self.peer_id, self.remote)

        # try to ensure that all the messages are sent at the end
        # won't work if our peer is disconnected first, of course
        for _ in range(10):
            self.handle_messages(timeout=0.05)
            if self.try_resend_lost(timeout=0.05) == 0:
                break

        # print stats, because why not :3
        self.stats.print_results()

    def first_peer_fetch(self) -> Addr:
        return first_peer_fetch(
            self.s,
            self.our_id,
            self.peer_id,
            self.remote,
        )

    def try_to_reconnect(self) -> None:
        if self.end:
            return

        self.reconnects += 1
        if self.reconnects > 5:
            raise RuntimeError("i'm tired")

        logger.error("<> connection has failed, trying to reconnect")
        self.s = try_to_reconnect(
            self.s,
            self.our_id,
            self.peer_id,
            self.remote,
        )

    def raw_send(self, msg: bytes) -> None:
        logger.debug(f"-> {msg!r}")
        self.s.sendto(msg, self.peer)

    def raw_get(self, *, timeout: float = 0.15) -> Optional[tuple[bytes, Addr]]:
        if (res := timeout_recv(self.s, timeout=timeout)) is not None:
            data, addr = res
            logger.debug(f"<- {data!r}")
            return res
        else:
            return None

    def syn_msg(self) -> bytes:
        return f"init_syn:{self.init_x}".encode('utf-8')

    @staticmethod
    def init_ack_msg(init_y: int) -> bytes:
        return f"init_ack:{init_y}".encode('utf-8')

    @staticmethod
    def packed_msg(i: int, msg: str) -> bytes:
        return f"msg:{i}:{msg}".encode('utf-8')

    @staticmethod
    def ack_msg(i: int) -> bytes:
        return f"ack:{i}".encode('utf-8')

    def try_resend_lost(self, *, timeout = 0.1) -> int:
        to_resend = []
        for (i, (_, time_sent, is_done)) in self.sent.items():
            if is_done:
                continue
            if time.monotonic() - time_sent < timeout:
                continue
            to_resend.append(i)

        for i in to_resend:
            msg, _, _ = self.sent[i]
            self.raw_send(self.packed_msg(i, msg))
            self.sent[i] = msg, time.monotonic(), False

        return len(to_resend)

    def handle_remote(self, payload: bytes) -> None:
        _, peer = parse_server_msg(payload)
        logger.debug(f"new peer: {peer}")
        self.peer = peer

    def handle_peer(self, payload: bytes) -> HandleResult:
        data = payload.decode('utf-8').split(":")
        match data:
            case ["init_ack", x_str] if int(x_str) == self.init_x:
                self.us_ok = True

                return TickResult.GotInitAck
            case ["init_syn", y_str]:
                init_ack = self.init_ack_msg(int(y_str))
                self.raw_send(init_ack)

                return TickResult.GotInitSyn
            case ["msg", msg_id_str, msg]:
                msg_id = int(msg_id_str)

                expected_id = self.last_received_id + 1
                if msg_id > expected_id:
                    # no ack for you sommry, you're too early
                    #
                    # realistically speaking, we could have a queue for early
                    # birds, so that you don't need to resend the message, but
                    # idk, let's see how it will work without it
                    return TickResult.DupOrEarly

                # otherwise, acknowledge
                ack = self.ack_msg(msg_id)
                self.raw_send(ack)

                # oh, you've arrived, we expected you
                if msg_id not in self.received:
                    self.received[msg_id] = msg
                    self.last_received_id = msg_id

                    # should we store addr in read_queue? probably not
                    # but hell, I don't want to think about it right now
                    self.read_queue.append((msg, self.peer))
                    return TickResult.GotMsg
                else:
                    return TickResult.DupOrEarly
            case ["ack", msg_id_str]:
                msg_id = int(msg_id_str)
                match self.sent.get(msg_id, None):
                    case None:
                        # sending ack to the message we haven't sent is the
                        # error on the other side
                        #
                        # i'll leave a breakpoint just in case, but if it was
                        # a "real" program, we'd probably ignore it, because
                        # that's not our responsibility
                        breakpoint()
                        unreachable()
                    case sent_msg, sent_time, acked:
                        if not acked:
                            self.sent[msg_id] = sent_msg, sent_time, True

                            return TickResult.GotAck
                        else:
                            return TickResult.DupOrEarly
                    case rest:
                        breakpoint()
                        assert_never_seq(rest)
            case _:
                breakpoint()
                raise RuntimeError(f"unexpected message: {payload!r}")


    def handle_messages(self, *, timeout: float = 0.15) -> Optional[TickResult]:
        if (res := self.raw_get(timeout=timeout)) is not None:
            payload, addr = res
            if addr == self.remote:
                self.handle_remote(payload)
                self.stats.remote()
                return None
            elif addr == self.peer:
                ret = self.handle_peer(payload)
                register(self.stats, ret)

                match ret:
                    case TickResult.GotAck | TickResult.GotMsg:
                        return ret
                    case (
                        TickResult.GotInitSyn
                        | TickResult.GotInitAck
                        | TickResult.DupOrEarly):
                        return None
                    case rest:
                        assert_never_seq(rest)
            else:
                logger.error(f"unknown {addr}: {payload!r}")
                self.stats.other()
                return None
        else:
            # NOTE: there's a high chance that this won't fire if
            # we didn't receive any "init_ack", because the packet got lost,
            # but then we receive other packets, even while being in
            # `not self.us_ok`
            #
            # who cares though?
            #
            # counter-point, if we don't care, do we really need this stuff?
            #
            # my thinking is that it's needed in TCP, because you have
            # connect()/accept() step so that's why they need this
            #
            # we don't have it, and frankly our connection lifecycle is more
            # dependent on deNAT reliability than on connect/close
            if not self.us_ok:
                init_syn = self.syn_msg()
                self.raw_send(init_syn)
            self.stats.miss()
            return None

    def tick(self, *, attempts: int = 10) -> TickResult:
        for _ in range(attempts):
            ret = self.handle_messages()
            self.try_resend_lost()
            if ret is not None:
                return ret
        else:
            self.try_to_reconnect()

            return TickResult.Timeout

    def get(self) -> Optional[tuple[str, Addr]]:
        if self.read_queue:
            return self.read_queue.pop(0)
        else:
            return None

    def get_blocking(self) -> tuple[str, Addr]:
        if self.read_queue:
            return self.read_queue.pop(0)
        else:
            # poll until receive the message
            while self.tick() != TickResult.GotMsg:
                pass
            res = self.get()
            if res is None:
                breakpoint()
                raise RuntimeError("got none")
            else:
                return res

    def send(self, msg: str) -> None:
        i = next(self.last_sent_id)

        self.raw_send(self.packed_msg(i, msg))
        self.sent[i] = msg, time.monotonic(), False

# end of ReUDP

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
        logger.info(f"<> requesting the connection #{i + 1}")

        # check the mailbox
        if (res := timeout_recv(s, timeout=2)) is not None:
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
    logger.info(f"<> server says we are {our[0]}:{our[1]}")
    logger.info(f"<> server says our peer is {peer[0]}:{peer[1]}")

    # finally return response
    return peer

def disconnect(
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote: Addr,
) -> None:
    req = f"EXIT#{our_id}@{peer_id}"
    s.sendto(req.encode('utf-8'), remote)
    logger.info("<> requested exit")


def prepare_socket(port: Optional[int] = None) -> socket.socket:
    if port is None:
        try:
            port = int(sys.argv[1])
            logger.info(f"<> using src port: {port}")
        except (ValueError, IndexError):
            port = 9_990
            logger.warning("<> couldn't get the src port from arguments."
                  f" Using default src port: {port}")

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        try:
            host = "0.0.0.0"
            logger.info(f"<> binding to {host}:{port}")
            s.bind((host, port))
            break
        except OSError as e:
            if e.errno == 48:
                logger.error(f"<err> {port=} is taken, trying the next one")
                port += 1
            else:
                raise e
    return s


class Stats:
    def __init__(self):
        # counters
        self.miss_counter = 0
        self.got_counter = 0
        self.remote_counter = 0
        self.meta_counter = 0
        self.other_counter = 0

        # failure counters
        self.err_clock = 0
        self.ok_clock = 0

        # start time
        self.start = time.time_ns()

        # used for periodics
        self.last = None
        self.ns = 0.0

    def reset(self):
        """ Restart timer """
        self.start = time.time_ns()

        self.last = None
        self.ns = 0.0

    def miss(self):
        self.miss_counter += 1

        self.err_clock += 1

    def got(self):
        self.got_counter += 1

        self.ok_clock += 1
        self.err_clock = 0

    def meta(self):
        self.meta_counter += 1

        self.ok_clock += 1
        self.err_clock = 0

    def remote(self):
        self.remote_counter += 1

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
            remote = self.remote_counter
            ns_passed = time.time_ns() - self.start
        else:
            miss = self.miss_counter - self.last.miss_counter
            got = self.got_counter - self.last.got_counter
            other = self.other_counter - self.last.other_counter
            remote = self.remote_counter - self.last.remote_counter
            ns_passed = time.time_ns() - self.last.ns

        print(f"miss/got/other/remote: {miss}/{got}/{other}/{remote}")
        ms_passed = ns_passed / (10 ** 6)
        print(f"time: {ms_passed} milliseconds")

        self.last = copy.deepcopy(self)
        self.last.ns = time.time_ns()

    def print_results(self):
        print("Total stats")
        print("===========")
        print(f"miss:\n\t{self.miss_counter}")
        print(f"got:\n\t{self.got_counter}")
        print(f"remote:\n\t{self.remote_counter}")
        print(f"meta:\n\t{self.meta_counter}")
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
    #
    # hint: the lower is the cap, the higher is the chance
    if random.random() >= 0.60:
        _, port = s.getsockname()
        s = prepare_socket(port + 1)
    # send peer request anyway though
    make_peer_req(s, our_id, peer_id, remote)
    return s

def establish_connection2(
    stats: Stats,
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote: Addr,
) -> tuple[socket.socket, Addr]:
    """ Try to establish a connection

    It's possible that portion of this protocol will leak to the next
    stage, so you'll need to handle potential syn() from the peer.
    """
    def syn_msg(rand_x: int) -> bytes:
        return f"init_syn:{rand_x}".encode('utf-8')
    def ack_msg(y: int) -> bytes:
        return f"init_ack:{y}".encode('utf-8')

    logger.info("<> initiating connection")
    peer = first_peer_fetch(s, our_id, peer_id, remote)
    stats.reset()

    us_ok = False
    them_maybe_ok = False

    # send first syn to the peer
    init_x = random.randint(0, 100)
    s.sendto(syn_msg(init_x), peer)

    # start the main stage
    while (not us_ok) or (not them_maybe_ok):
        if stats.failed_enough(50):
            logger.error("can't establish connection, I give up")
            sys.exit(1)

        if stats.failed_enough(10):
            s = try_to_reconnect(s, our_id, peer_id, remote)

        if (res := timeout_recv(s, timeout=0.15)) is not None:
            msg, addr = res
            if addr != peer:
                if addr == remote:
                    _, peer = parse_server_msg(msg)
                    logger.debug(f"new peer: {peer}")
                    stats.remote()
                else:
                    stats.other()
                    # idk what to do in this case
                    # it's possible that our peer will decide to change
                    # its port and they'll get the response from remote server
                    # and send the message to us sooner than we'll get the
                    # message from the remote
                    #
                    # but I think this situation will fix itself in the end
                    breakpoint()
                continue

            data = msg.decode('utf-8').split(":")
            match data:
                case ["init_ack", x_str] if int(x_str) == init_x:
                    us_ok = True
                case ["init_syn", y_str]:
                    y = int(y_str)
                    s.sendto(ack_msg(y), peer)
                    them_maybe_ok = True
                case _:
                    breakpoint()
        else:
            stats.miss()
            if not us_ok:
                s.sendto(syn_msg(init_x), peer)

    logger.info("<> connection is probably stable")
    return s, peer

def main_loop2(
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote: Addr,
) -> None:
    def we_won(our_pick: str, their_pick: str) -> Optional[bool]:
        if our_pick == their_pick:
            return None
        else:
            match (our_pick, their_pick):
                case ["rock", "scissors"]:
                    return True
                case ["paper", "rock"]:
                    return True
                case ["scissors", "paper"]:
                    return True
                case _:
                    return False


    def next_pick(turn: int) -> str:
        pick = random.choice(["paper", "rock", "scissors"])
        print(f"<*> on turn {turn} we picked: {pick}")
        return pick

    with ReUDP(s, our_id, peer_id, remote) as tunnel:
        for game in range(5):
            print(f"<> it's a {game+1}th game")
            for turn in itertools.count():
                pick = next_pick(turn)
                tunnel.send(pick)
                their_pick, addr = tunnel.get_blocking()
                print(f"<_> on turn {turn} they picked: {their_pick}")
                if (won := we_won(pick, their_pick)) is not None:
                    if won:
                        print("we won!")
                    else:
                        print("we lost :(")
                    break

def main() -> None:
    logger.setLevel(logging.INFO)
    try:
        with open("config.toml", "rb") as f:
            data = tomllib.load(f)

        remote_host = data["remote_host"]
        remote_port = int(data["remote_port"])
        remote = (remote_host, remote_port)

        our_id = data["our_id"]
        if len(sys.argv) >= 3:
            our_id = sys.argv[2]
            logger.info(f"<> rewrite our_id with {our_id}")

        peer_id = data["peer_id"]
        if len(sys.argv) >= 4:
            peer_id = sys.argv[3]
            logger.info(f"<> rewrite peer_id with {peer_id}")

    except Exception as e:
        logger.error("couldn't read the config.toml")
        logger.error(f"{e=}")
        sys.exit(1)

    s = prepare_socket()
    logger.info(f"<> good, ready to connect to {remote_host}:{remote_port}")

    main_loop2(
        s,
        our_id,
        peer_id,
        remote,
    )

if __name__ == "__main__":
    main()
