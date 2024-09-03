#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <sys/socket.h>
#include <netinet/ip_icmp.h>
#include <netdb.h>

#include "common.h"

#define SRC_HOST "0.0.0.0"
#define DEST_HOST "google.com"
#define PORT "0"

// as you may guess, it was the first time I wrote anything even remotely
// related to binary arithmetic
void one_complement_add(uint32_t *val, uint16_t adder) {
    *val += adder;

    if (*val > 0xffff) {
        uint32_t leftover = (*val >> 16);
        uint32_t real_val = (*val & 0x0000ffff);

        *val = real_val + leftover;
    }
}

uint16_t checksum(char *data, size_t n_chars) {
    uint32_t sum = 0;
    int counter = 0;

    uint16_t *pairs = (uint16_t *)data;
    while (n_chars > 1) {
        one_complement_add(&sum, pairs[counter]);
        counter += 1;
        n_chars -= 2;
    }

    // if odd, we went early
    if (n_chars == 1) {
        one_complement_add(&sum, data[counter * 2] * 256);
    }

    uint16_t final_sum = (uint16_t)sum;

    // one complement is just invert all the bits
    return ~final_sum;
}

int main(void) {
    printf("hi, i'm pinger!\n");

    int sockfd = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    if (sockfd < 0) {
        fprintf(stderr, "socket() errored\n");
        perror("socket");
        return 1;
    }

    // I do all of this to get res->ai_addr
    struct addrinfo hints;
    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_INET;

    struct addrinfo *res_src = NULL;
    if (getaddrinfo(SRC_HOST, PORT, &hints, &res_src) != 0) {
        fprintf(stderr, "getaddrinfo() errored\n");
        perror("getaddrinfo");
        return 1;
    }

    struct addrinfo *res_dest = NULL;
    if (getaddrinfo(DEST_HOST, PORT, &hints, &res_dest) != 0) {
        fprintf(stderr, "getaddrinfo() errored\n");
        perror("getaddrinfo");
        return 1;
    }

    // allocate buff
    const int total = 40;
    char buff[total];
    memset(buff, 0, sizeof buff);

    size_t offset = 0;
    // form an IP header
    int hincl = 1;
    if (setsockopt(sockfd, IPPROTO_IP, IP_HDRINCL, &hincl, sizeof(hincl)) != 0) {
        fprintf(stderr, "setsockopt() errored\n");
        perror("setsockopt");
        return 1;
    }

    struct ip *ip = (struct ip*)buff + 0;
    // set version (4) and len (5)
    buff[0] = 0x45;
    ip->ip_tos = 0;
    // as (Apple's) man says, ip_len should be in the host byte order
    ip->ip_len = total;
    ip->ip_id = 0;
    ip->ip_off = 0;
    ip->ip_ttl = 64;
    // ICMP = 1
    ip->ip_p = 1;
    // please compute for me
    ip->ip_sum = 0;
    ip->ip_src = ((struct sockaddr_in *)res_src->ai_addr)->sin_addr;
    ip->ip_dst = ((struct sockaddr_in *)res_dest->ai_addr)->sin_addr;

    // wrote ip header (20 bytes)
    offset += 20;

    // form an ICMP header
    struct icmp *icmp = (struct icmp *)(buff + offset);

    // ECHO
    icmp->icmp_type = 8;
    icmp->icmp_code = 0;

    // random id
    srandomdev();
    icmp->icmp_id = htons(random());

    // start from 0
    icmp->icmp_seq = htons(0);

    // checksum
    // fill to zero before calculating everything
    //
    // and no, we can't make kernel to compute this for us :(
    icmp->icmp_cksum = 0;

    // to use with checksum
    const int icmp_data_size = total - offset;

    // wrote icmp header (8 bytes)
    offset += 8;

    // fill payload with increments
    char *payload = buff + offset;
    for (size_t i = 0; i < total - offset; i += 1) {
        payload[i] = (uint8_t)i;
    }

    // checksum should go at the end
    icmp->icmp_cksum = checksum((char *)icmp, icmp_data_size);


    int send_status = sendto(
        sockfd,
        buff,
        sizeof buff,
        0,
        res_dest->ai_addr,
        sizeof(struct sockaddr_in)
    );

    if (send_status < 0) {
        fprintf(stderr, "sendto() errored\n");
        perror("sendto");
        return 1;
    }
}
