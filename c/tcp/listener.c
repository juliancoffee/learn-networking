#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <unistd.h>
#include <sys/errno.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>

#include "common.h"

/*
 * handles the client request
 *
 * the protocol is similar to one in Python's program, but it's one-shot
 * you connect, make a request, get a response, it's over, almost like HTTP
 *
 * also, instead of all caps, we will do reverse, because why not?
 */
void swap_chars(char *a, char *b) {
    char tmp = *a;
    *a = *b;
    *b = tmp;
}

void rev_string_inplace(char *string, size_t len) {
    size_t stop = len / 2;

    for (size_t i = 0; i < stop; i++) {
        char *first = &string[i];
        char *last = &string[len - i - 1];
        swap_chars(first, last);
    }
}

void handle_client(int sockfd) {
    printf("* hi from handler process\n");

    char *msg_buff = proto_recv(sockfd);
    printf("<> the message is (%s)\n", msg_buff);

    // reverse and send back
    rev_string_inplace(msg_buff, strlen(msg_buff));
    printf("<> the reversed message is (%s)\n", msg_buff);
    proto_send(sockfd, msg_buff);

    // shut down the connection
    shutdown(sockfd, SHUT_RDWR);

    // free the buff
    free(msg_buff);
}

#define PORT "8000"
#define HOST "localhost"

int main(void) {
    printf("hi, i'm the server!\n");

    struct addrinfo hints;
    /*
     * again, I don't know why this works
     *
     * like, on assembly level of whatever, yeah, the byte is (probably) the
     * smallest "chunk" of data you can address, and if it's not true, then
     * compiler/headers/libc for this platform would be adjusted accordingly
     *
     * is it ok to just access random bits and bytes of a structure?
     * well, idk, I guess?
     * smart people probably know what they are doing.
     *
     * `man getaddrinfo` specifies this in examples as well
     */
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;

    struct addrinfo *res;
    if (getaddrinfo(HOST, PORT, &hints, &res) != 0) {
        fprintf(stderr, "getaddrinfo() errored\n");
        return 1;
    }

    int sockfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (sockfd < 0) {
        fprintf(stderr, "socket() errored\n");
        return 1;
    }

    int yes = 1;
    if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes) < 0) {
        fprintf(stderr, "setsockopt() errored\n");
        return 1;
    }

    if (bind(sockfd, res->ai_addr, res->ai_addrlen) < 0) {
        int err_status = errno;
        fprintf(stderr, "bind() errored\n");
        // in theory, this shouldn't happen after previous call, but who knows
        if (err_status == EADDRINUSE) {
            fprintf(stderr, "address in use\n");
        }
        return 1;
    }

    char *host_port = get_host_port_ipv4(res->ai_addr);
    printf("bind to %s\n", host_port);
    free(host_port);

    // signal that you're ready to accept connections
    const int backlog = 10;
    // god this is much easier compared to stuff before
    if (listen(sockfd, backlog) < 0) {
        fprintf(stderr, "listen() errored\n");
        return 1;
    }
    printf("listening...\n");

    for (;;) {
        printf("accepting...\n");

        struct sockaddr_in client_addr;
        socklen_t addr_len = (socklen_t) sizeof client_addr;
        int client_sockfd = accept(
                sockfd,
                (struct sockaddr *)&client_addr,
                &addr_len
        );

        if (client_sockfd < 0) {
            fprintf(stderr, "accept() errored\n");
            return 1;
        }

        char *host_port = get_host_port_ipv4((struct sockaddr *)&client_addr);
        printf("got client from %s\n", host_port);
        free(host_port);

        // handle client
        handle_client(client_sockfd);

        // free
        close(client_sockfd);
    }

    /*
     * won't get cleaned if any of errors happen because the code simply won't
     * run to this point, just saying
     *
     * but in this case we 'return 1' out of the program, so the "destructor"
     * shall probably run some way or another by OS for us
     */
    freeaddrinfo(res);
}
