import copy
import time


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
        """Restart timer"""
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
        ms_passed = ns_passed / (10**6)
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
        ms_passed = (time.time_ns() - self.start) / (10**6)
        print(f"time:\n\t{ms_passed} miliseconds")
