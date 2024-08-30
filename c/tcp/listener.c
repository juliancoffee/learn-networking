#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <unistd.h>
#include <sys/errno.h>
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

    // one additional byte to store null terminator
    char size_header[5];
    memset(size_header, 0, sizeof size_header);
    recv(sockfd, size_header, 4, 0);

    printf("<> header is (%s)\n", size_header);
    unsigned short size;
    sscanf(size_header, "%04hd", &size);
    printf("<> size is %hd\n", size);

    // one more byte to fill with a null terminator
    size_t msg_buff_size = (size_t)size + 1;
    char *msg_buff = calloc(msg_buff_size, sizeof(char));

    // get the message
    recv(sockfd, msg_buff, (size_t)size, 0);
    printf("<> the message is (%s)\n", msg_buff);

    // reverse and send back
    rev_string_inplace(msg_buff, (size_t)size);
    printf("<> the reversed message is (%s)\n", msg_buff);
    send(sockfd, msg_buff, (size_t)size, 0);

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

    char addr_str_buff[INET_ADDRSTRLEN];
    fill_addr_ipv4(res->ai_addr, addr_str_buff, sizeof addr_str_buff);
    unsigned short port = get_port_ipv4(res->ai_addr);
    printf("bind to %s:%d\n", addr_str_buff, port);

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

        char client_addr_str_buff[INET_ADDRSTRLEN];
        fill_addr_ipv4(
                (struct sockaddr *)&client_addr,
                client_addr_str_buff,
                sizeof client_addr_str_buff
        );
        unsigned short port = get_port_ipv4((struct sockaddr *)&client_addr);
        printf("got client from %s:%d\n", addr_str_buff, port);

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
