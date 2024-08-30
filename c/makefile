CC=clang
CFLAGS=-std=c17 -Wall -Wextra -pedantic

all:
	@echo "hi, run individual target"

build/tcp_listener: tcp_listener.c
	@echo ">> building"
	mkdir -p build/
	$(CC) $(CFLAGS) tcp_listener.c -o build/tcp_listener

server_tcp: build/tcp_listener
	@echo ">> running"
	@./build/tcp_listener

build/tcp_client: tcp_client.c
	@echo ">> building"
	mkdir -p build/
	$(CC) $(CFLAGS) tcp_client.c -o build/tcp_client

tcp_client: build/tcp_client
	@echo ">> running"
	@./build/tcp_client

build/test: test.c makefile
	@echo ">> building"
	mkdir -p build/
	$(CC) $(CFLAGS) test.c -o build/test

test: build/test
	@echo ">> running"
	@./build/test

clean:
	rm -rf build/*
