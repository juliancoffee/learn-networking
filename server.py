from typing import Optional

import select
import socket
import sys

try:
    port = int(sys.argv[1])
    print(f"<> using port: {port}")
except (ValueError, IndexError):
    port = 11_111
    print("<err> couldn't get the port")
    print(f"<> using default port: {port}")

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", port))
print("<> bound and ready to receive messages")

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
            addrs: tuple[Addr, Optional[Addr]]
    ) -> Entry:
        entry = self.find_entry(ids)
        if entry is None:
            entry = Entry(ids, addrs)
            self.mapping.append(entry)
        return entry

    def find_entry(self, ids: tuple[str, str]) -> Optional[Entry]:
        for entry in self.mapping:
            if entry.corresponds(ids):
                return entry
        else:
            return None

def addrs_to_string(addr_a: Addr, addr_b: Addr) -> str:
    def addr_to_string(addr: Addr) -> str:
        host, port = addr
        return ":".join((host, str(port)))

    return ";".join((addr_to_string(addr_a), addr_to_string(addr_b)))


mapping = Mapping()
while True:
    ok_read, ok_write, errs = select.select([s], [], [])
    if ok_read:
        s = ok_read[0]
        msg_bytes, our_addr = s.recvfrom(100)
        msg = msg_bytes.decode('utf-8')

        print(f"<> [{our_addr}] send us a message. <{msg}> they said")

        our_id, their_id = msg.split("@")
        id_pair = our_id, their_id

        entry = mapping.find_entry(id_pair)
        if entry is None:
            print(f"<> registered new mapping: {our_id} @ {their_id}")
            mapping.register(id_pair, (our_addr, None))
        else:
            assert (addr_pair := entry.get_full_pair(id_pair)) is not None
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
