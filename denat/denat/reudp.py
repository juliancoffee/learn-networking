from __future__ import annotations

import enum
import itertools
import logging
import random
import socket
import time
from typing import Literal, Optional, Self

from .net import (
    Addr,
    disconnect,
    first_peer_fetch,
    parse_server_msg,
    timeout_recv,
    try_to_reconnect,
)
from .stats import Stats
from .t import assert_never_seq, unreachable

logger = logging.getLogger(__name__)


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
    """Re_liable_UDP object to use with deNAT

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

    def __enter__(self) -> Self:
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
        return f"init_syn:{self.init_x}".encode()

    @staticmethod
    def init_ack_msg(init_y: int) -> bytes:
        return f"init_ack:{init_y}".encode()

    @staticmethod
    def packed_msg(i: int, msg: str) -> bytes:
        return f"msg:{i}:{msg}".encode()

    @staticmethod
    def ack_msg(i: int) -> bytes:
        return f"ack:{i}".encode()

    def try_resend_lost(self, *, timeout=0.1) -> int:
        to_resend = []
        for i, (_, time_sent, is_done) in self.sent.items():
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
        data = payload.decode("utf-8").split(":")
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
                        | TickResult.DupOrEarly
                    ):
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
