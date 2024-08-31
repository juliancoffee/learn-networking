#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include <errno.h>

#include <netdb.h>
#include <netinet/ip_icmp.h>
#include <sys/socket.h>
#include <arpa/inet.h>

#include <unistd.h>
#include "common.h"

void print_hex(char *buff, size_t len) {
    for (size_t i = 0; i < len; i++) {
        if (i < len - 1) {
            printf("%#x:", (unsigned char)buff[i]);
        } else {
            printf("%#x", (unsigned char)buff[i]);
        }
    }
    printf("\n");
}

#define BUFF_SIZE 8192

int main(void) {
    printf("ready to sniff...\n");
    int fd = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    if (fd < 0) {
        fprintf(stderr, "socket() errored\n");
        perror("socket");
        return 1;
    }

    // snif
    char buffer[BUFF_SIZE];
    for (;;) {
        memset(buffer, 0, BUFF_SIZE);
        int res = read(fd, buffer, BUFF_SIZE);
        if (res < 0) {
            fprintf(stderr, "read() errored\n");
            perror("read");
            break;
        }


        // \x1b[32m...\x1b[0m
        //
        // coloring magic, should work everywhere nowadays
        // but almost guaranteed to work on *nix systems
        printf(
            "\x1b[32m <> Caught icmp packet (len=%d):\x1b[0m\n",
            res
        );

        printf("<ip header> raw\n");
        struct ip *ip = (struct ip *)buffer;
        size_t ip_header_size = ip->ip_hl * 4;
        print_hex(buffer, ip_header_size);
        printf("<ip header> parsed\n");
        printf("ip_hl: %d\n", ip->ip_hl);
        printf("ip_v: %d\n", ip->ip_v);
        printf("ip_tos: %d\n", ip->ip_tos);
        printf("ip_len: %d\n", ip->ip_len);
        printf("ip_id: %d\n", ip->ip_id);
        printf("ip_off: %d\n", ip->ip_off);
        printf("ip_ttl: %d\n", ip->ip_ttl);
        printf("ip_p: %d\n", ip->ip_p);
        printf("ip_sum: %d\n", ip->ip_sum);

        char addr_str_buff[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &ip->ip_src, addr_str_buff, sizeof addr_str_buff);
        printf("ip_src: %s\n", addr_str_buff);

        memset(addr_str_buff, 0, sizeof addr_str_buff);
        inet_ntop(AF_INET, &ip->ip_dst, addr_str_buff, sizeof addr_str_buff);
        printf("ip_dst: %s\n", addr_str_buff);

        printf("<icmp header> raw\n");
        struct icmp *icmp = (struct icmp *)(buffer + ip_header_size);
        size_t icmp_header_size = 8;
        print_hex(buffer + ip_header_size, icmp_header_size);
        printf("<icmp header> parsed\n");
        printf("icmp_type: %d\n", icmp->icmp_type);
        printf("icmp_code: %d\n", icmp->icmp_code);
        printf("icmp_cksum: %d\n", icmp->icmp_cksum);

        if (icmp->icmp_type == ICMP_ECHOREPLY) {
            /*
             * https://www.rfc-editor.org/rfc/rfc792.txt
             *
             * says that for echo reply, it's always identifier and sequence
             * number
             */
            // idk what icmp_id is, and even what endianness it is
            // RFC says that it's an identifier in matching echos and replies
            printf("icmp_id: %d\n", ntohs(icmp->icmp_id));
            printf("icmp_seq: %d\n", ntohs(icmp->icmp_seq));
        } else {
            printf("rest: ");
            print_hex(((char *)icmp) + 4, 4);
        }

        printf("<icmp payload>\n");
        print_hex(buffer + 20 + 8, res - 20 - 8);
    }
}
