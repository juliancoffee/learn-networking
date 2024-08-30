#include <sys/socket.h>
#include <stdio.h>
#include <string.h>
#include <netdb.h>
#include <arpa/inet.h>

unsigned short get_port_ipv4(struct sockaddr *ai_addr) {
    /*
     * getaddrinfo() returns port in a network-order endiannes, live with it
     */
    unsigned short port = ntohs(((struct sockaddr_in *)ai_addr)->sin_port);
    return port;
}

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

// returns "host:port"
// don't forget to free the result
char *get_host_port_ipv4(struct sockaddr *ai_addr) {
    char addr_str_buff[INET_ADDRSTRLEN];
    fill_addr_ipv4(ai_addr, addr_str_buff, sizeof addr_str_buff);

    unsigned short port = get_port_ipv4(ai_addr);
    char *res;
    asprintf(&res, "%s:%d", addr_str_buff, port);
    return res;
}

int recvall(int sockfd, char *buff, size_t len, int flags) {
    size_t left = len;
    size_t read = 0;
    while (read < len) {
        int got = recv(sockfd, buff + read, left, flags);
        if (got == 0) {
            return read;
        }
        if (got < 0) {
            return got;
        }
        read += got;
        left -= got;
    }

    return read;
}

int sendall(int sockfd, char *buff, size_t len, int flags) {
    size_t left = len;
    size_t wrote = 0;
    while (wrote < len) {
        int got = send(sockfd, buff + wrote, left, flags);
        if (got == 0) {
            return wrote;
        }
        if (got < 0) {
            return got;
        }
        wrote += got;
        left -= got;
    }

    return wrote;
}
