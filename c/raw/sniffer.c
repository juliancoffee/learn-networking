#include <stdio.h>
#include <string.h>

#include <errno.h>

#include <netdb.h>
//#include <netinet/in.h>
//#include <netinet/ip.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <netinet/ip_icmp.h>
#include <sys/socket.h>
#include <unistd.h>

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

        struct ip *ip = (struct ip *)buffer;
        struct icmp *icmp = (struct icmp *)(buffer + ip->ip_hl * 4);

        if (icmp->icmp_type == ICMP_ECHO) {
            printf("Caught ICMP Echo Request:\n");
        } else if (icmp->icmp_type == ICMP_ECHOREPLY) {
            printf("Caught ICMP Echo Reply:\n");
        } else {
            printf("Caught ICMP packet, type: %d\n", icmp->icmp_type);
        }

        printf(
            "Caught icmp packet (len=%d):\n",
            res
        );
        printf("ip header\n");
        print_hex(buffer, 20);
        printf("icmp header\n");
        print_hex(buffer + 20, 8);
        printf("icmp payload\n");
        print_hex(buffer + 20 + 8, res - 20 - 8);
    }
}
