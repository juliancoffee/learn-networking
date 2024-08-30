CC=clang
CFLAGS=-std=c17 -Wall -Wextra -pedantic

all:
	@echo "hi, run individual target"

build/listener: listener.c common.c common.h
	@echo ">> building"
	mkdir -p build/
	$(CC) $(CFLAGS) listener.c common.c -o build/listener

server: build/listener
	@echo ">> running"
	@./build/listener

build/client: client.c
	@echo ">> building"
	mkdir -p build/
	$(CC) $(CFLAGS) client.c -o build/client

client: build/client
	@echo ">> running"
	@./build/client

build/test: test.c makefile
	@echo ">> building"
	mkdir -p build/
	$(CC) $(CFLAGS) test.c -o build/test

test: build/test
	@echo ">> running"
	@./build/test

clean:
	rm -rf build/*
