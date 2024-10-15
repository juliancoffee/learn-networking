#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <netdb.h>

#include "common.h"

#define PORT "8000"
#define HOST "localhost"

int main(int argc, char **argv) {
    printf("hi, i'm the client!\n");

    if (argc != 2) {
        fprintf(stderr, "please run with the message you want to send\n");
        return 1;
    }
    if (strlen(argv[1]) == 0) {
        fprintf(stderr, "please message can't be empty\n");
        return 1;
    }

    struct addrinfo hints;
    memset(&hints, 0, sizeof hints);
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

    if (connect(sockfd, res->ai_addr, res->ai_addrlen) < 0) {
        fprintf(stderr, "connect() errored\n");
        return 1;
    }

    char *host_port = get_host_port_ipv4(res->ai_addr);
    printf("connected to %s\n", host_port);
    free(host_port);

    printf("<> your message is: (%s)\n", argv[1]);
    proto_send(sockfd, argv[1]);
    char *response = proto_recv(sockfd);
    printf("<> result is: (%s)\n", response);
    free(response);
}
