#include <stdio.h>
#include <string.h>

//#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>

void fill_addr_ipv4(
    struct sockaddr *ai_addr,
    char *dst,
    int dst_len
) {
    /*
     * look, this simply shouldn't work
     *
     * but everyone uses it, because it works
     * and the reason why it works is probably because
     * everyone uses it
     *
     * addrinfo->ai_addr is sockaddr, which is a "generic" struct that is
     * (kind of) large enough to work with both sockaddr_in and sockaddr_in6
     *
     * which is why you can cast them back and forth, as long as it's the right
     * address family.
     *
     * cough-cough
     * I asked ChatGPT and he said something about "well, but POSIX" and
     * "common initial sequence"
     * end of cough-cough
     *
     * Common Initial Sequence is kinda exists, but requires unions.
     * And also, while you can access them in a (probably) safe way, Common
     * Initial Sequence doesn't change aliasing rules, so in some cases,
     * compiler still can bite you.
     */
    struct sockaddr_in *addr = (struct sockaddr_in *)ai_addr;

    inet_ntop(
            AF_INET,
            &(addr->sin_addr),
            dst,
            dst_len
    );
}

unsigned short get_port_ipv4(struct sockaddr *ai_addr) {
    /*
     * getaddrinfo() returns port in a network-order endiannes, live with it
     */
    unsigned short port = ntohs(((struct sockaddr_in *)ai_addr)->sin_port);
    return port;
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

    if (bind(sockfd, res->ai_addr, res->ai_addrlen) < 0) {
        fprintf(stderr, "bind() errored\n");
        return 1;
    }

    char addr_str_buff[INET_ADDRSTRLEN];
    fill_addr_ipv4(res->ai_addr, addr_str_buff, sizeof addr_str_buff);
    unsigned short port = get_port_ipv4(res->ai_addr);
    printf("bind to %s:%d\n", addr_str_buff, port);

    // signal that you're ready to accept connections
    const int backlog = 10;
    // god this is much easier compared to stuff before
    if (listen(sockfd, backlog) < 0) {
        fprintf(stderr, "listen() errored\n");
    }
    printf("listening...\n");

    for (;;) {
        struct sockaddr_in client_addr;
        socklen_t addr_len = (socklen_t) sizeof client_addr;
        int client_sockfd = accept(
                sockfd,
                (struct sockaddr *)&client_addr,
                &addr_len
        );

        char client_addr_str_buff[INET_ADDRSTRLEN];
        fill_addr_ipv4(
                (struct sockaddr *)&client_addr,
                client_addr_str_buff,
                sizeof client_addr_str_buff
        );
        unsigned short port = get_port_ipv4((struct sockaddr *)&client_addr);
        printf("got client from %s:%d\n", addr_str_buff, port);

        // handle it
        (void)client_sockfd;
    }

    // won't get cleaned if any of errors happen, just saying
    freeaddrinfo(res);
}
