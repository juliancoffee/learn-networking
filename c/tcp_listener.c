#include <stdio.h>
#include <string.h>

//#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>

void fill_addr(struct addrinfo *res, char *dst, int dst_len) {
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
    struct sockaddr_in *addr = (struct sockaddr_in *)res->ai_addr;

    inet_ntop(
            res->ai_family,
            &(addr->sin_addr),
            dst,
            dst_len
    );
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
    unsigned short port = ntohs(((struct sockaddr_in *)res->ai_addr)->sin_port);

    int sockfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (sockfd < 0) {
        fprintf(stderr, "socket() errored\n");
        return 1;
    }

    int bind_status = bind(sockfd, res->ai_addr, res->ai_addrlen);
    if (bind_status < 0) {
        fprintf(stderr, "bind() errored\n");
        return 1;
    }

    char addr_str_buff[INET_ADDRSTRLEN];
    fill_addr(res, addr_str_buff, sizeof addr_str_buff);
    printf("bind to %s:%d\n", addr_str_buff, port);
}
