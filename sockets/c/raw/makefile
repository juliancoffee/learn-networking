CC=clang
CFLAGS=-std=c17 -Wall -Wextra -pedantic -g

build/snif: sniffer.c ../tcp/common.c ../tcp/common.h
	@echo ">> building"
	mkdir -p build/
	$(CC) $(CFLAGS) sniffer.c ../tcp/common.c \
		-I ../tcp \
		-o build/snif

snif: build/snif
	@echo ">> running"
	sudo ./build/snif

build/ping: ping.c ../tcp/common.c ../tcp/common.h
	@echo ">> building"
	mkdir -p build/
	$(CC) $(CFLAGS) ping.c ../tcp/common.c \
		-I ../tcp \
		-o build/ping

ping: build/ping
	@echo ">> running"
	sudo ./build/ping

clean:
	mkdir -p build/
	rm build/*
