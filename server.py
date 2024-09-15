from typing import Optional, Never

import select
import socket
import sys


# pair of addresses
Addr = tuple[str, int]

class Entry:
    """ Class representing mapping entry

    Conceptually maps a pair of ids to a pair of addresses.
    """
    def __init__(
        self,
        ids: tuple[str, str],
        addrs: tuple[Addr, Optional[Addr]]
    ) -> None:
        self._a = (ids[0], addrs[0])
        self._b = (ids[1], addrs[1])

    def _is_direct(self, ids: tuple[str, str]) -> bool:
        id1, id2 = ids

        return self._a[0] == id1 and self._b[0] == id2

    def _is_reverse(self, ids: tuple[str, str]) -> bool:
        id1, id2 = ids

        return self._a[0] == id2 and self._b[0] == id1

    def corresponds(self, ids: tuple[str, str]) -> bool:
        """ Check whether the entry corresponds to id pair
        """

        return self._is_direct(ids) or self._is_reverse(ids)

    def addr_of(self, ident: str) -> Optional[Addr]:
        """ Get the addr of identifier if any """
        if self._a[0] == ident:
            return self._a[1]
        elif self._b[0] == ident:
            return self._b[1]
        else:
            raise AttributeError

    def set_addr_of(self, ident: str, addr: Addr) -> None:
        """ Set the addr for identifier """
        if self._a[0] == ident:
            self._a = (self._a[0], addr)
        elif self._b[0] == ident:
            self._b = (self._b[0], addr)
        else:
            raise AttributeError

    def get_full_pair(
            self,
            ids: tuple[str, str],
        ) -> Optional[tuple[Addr, Addr]]:
        """ Return full addr pair if possible """
        if self._b[1] is None:
            return None

        assert (first := self.addr_of(ids[0])) is not None
        assert (second := self.addr_of(ids[1])) is not None

        return first, second

class Mapping:
    def __init__(self) -> None:
        self.mapping: list[Entry] = []

    def register(
            self,
            ids: tuple[str, str],
            our_addr: Addr,
    ) -> Entry:
        entry = self.find_entry(ids)
        if entry is None:
            entry = Entry(ids, (our_addr, None))
            self.mapping.append(entry)
        else:
            id1, id2 = ids
            entry.set_addr_of(id1, our_addr)

        return entry

    def find_entry(self, ids: tuple[str, str]) -> Optional[Entry]:
        for entry in self.mapping:
            if entry.corresponds(ids):
                return entry
        else:
            return None

    def remove_entry(self, ids: tuple[str, str]):
        to_remove = None
        for i, entry in enumerate(self.mapping):
            if entry.corresponds(ids):
                to_remove = i
                break

        if to_remove is not None:
            self.mapping.pop(to_remove)



def addrs_to_string(addr_a: Addr, addr_b: Addr) -> str:
    def addr_to_string(addr: Addr) -> str:
        host, port = addr
        return ":".join((host, str(port)))

    return ";".join((addr_to_string(addr_a), addr_to_string(addr_b)))


def handle_join(s: socket.socket, mapping: Mapping, our_addr: Addr, msg: str):
    our_id, their_id = msg.split("@")
    id_pair = our_id, their_id

    if mapping.find_entry(id_pair) is None:
        print(f"<> registered new mapping: {our_id} @ {their_id}")
        mapping.register(id_pair, our_addr)
    else:
        entry = mapping.register(id_pair, our_addr)

        addr_pair = entry.get_full_pair(id_pair)
        if addr_pair is None:
            print(f"<> another hit to {our_id} @ {their_id}")
            print("<> but the mapping is incomplete")
            return

        our_addr, their_addr = addr_pair
        s.sendto(
            addrs_to_string(our_addr, their_addr).encode('utf-8'),
            our_addr
        )
        s.sendto(
            addrs_to_string(their_addr, our_addr).encode('utf-8'),
            their_addr
        )
        print(f"<> send their addresses to both: {our_id} @ {their_id}")

def handle_exit(mapping: Mapping, msg: str):
    our_id, their_id = msg.split("@")
    id_pair = our_id, their_id

    mapping.remove_entry(id_pair)


def loop() -> Never:
    try:
        port = int(sys.argv[1])
        print(f"<> using port: {port}")
    except (ValueError, IndexError):
        port = 11_111
        print("<err> couldn't get the port")
        print(f"<> using default port: {port}")

    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("0.0.0.0", port))
    print("<> bound and ready to receive messages")

    mapping = Mapping()
    while True:
        ok_read, ok_write, errs = select.select([server], [], [])
        if ok_read:
            s: socket.socket = ok_read[0]
            msg_bytes, our_addr = s.recvfrom(100)
            payload = msg_bytes.decode('utf-8')

            print(f"<> [{our_addr}]: {payload}")

            cmd, msg = payload.split("#")
            if cmd == "JOIN":
                handle_join(s, mapping, our_addr, msg)
            elif cmd == "EXIT":
                handle_exit(mapping, msg)

if __name__ == "__main__":
    loop()
