import itertools
import logging
import random
import select
import socket
import sys
from typing import Optional

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


def make_peer_req(
    s: socket.socket,
    our_id: str,
    peer_id: str,
    remote: Addr,
) -> None:
    req = f"JOIN#{our_id}@{peer_id}"
    s.sendto(req.encode("utf-8"), remote)


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
    s.sendto(req.encode("utf-8"), remote)
    logger.info("<> requested exit")


def prepare_socket(port: Optional[int] = None) -> socket.socket:
    if port is None:
        try:
            port = int(sys.argv[1])
            logger.info(f"<> using src port: {port}")
        except (ValueError, IndexError):
            port = 9_990
            logger.warning(
                "<> couldn't get the src port from arguments."
                f" Using default src port: {port}"
            )

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


def try_to_reconnect(
    s: socket.socket, our_id: str, peer_id: str, remote: Addr
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
