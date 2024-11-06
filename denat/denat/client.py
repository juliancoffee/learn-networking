from __future__ import annotations

import itertools
import logging
import random
import socket
import sys
import tomllib
from typing import Optional

from .net import Addr, prepare_socket
from .reudp import ReUDP

# utils
logging.basicConfig()
logger = logging.getLogger(__name__)

def game_loop(
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

    game_loop(
        s,
        our_id,
        peer_id,
        remote,
    )


if __name__ == "__main__":
    main()
