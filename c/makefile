CC=clang
CFLAGS=-std=c17 -Wall -Wextra -pedantic

all:
	@echo "hi, run individual target"

build/tcp_listener: tcp_listener.c
	@echo ">> building"
	mkdir -p build/
	$(CC) $(CFLAGS) tcp_listener.c -o build/tcp_listener

tcp_listener: build/tcp_listener
	@echo ">> running"
	@./build/tcp_listener

build/tcp_client: tcp_client.c
	@echo ">> building"
	mkdir -p build/
	$(CC) $(CFLAGS) tcp_client.c -o build/tcp_client

tcp_client: build/tcp_client
	@echo ">> running"
	@./build/tcp_client

clean:
	rm -rf build/*
