#include <stdio.h>
#include <stdint.h>

#define byte(val, n) ((uint8_t *)&(val))[(n)]

struct u8_doubled {
    uint8_t x;
    uint8_t y;
};

struct u16_doubled {
    uint16_t x;
    uint16_t y;
};

int main(void) {
    printf("hi there\n");

    uint16_t x = 0x1234;
    printf("%0x:%0x\n", byte(x, 0), byte(x, 1));
    // -> 34:12

    uint32_t x1 = 0x12345678;
    printf("%0x:%0x:%0x:%0x\n",
        byte(x1, 0),
        byte(x1, 1),
        byte(x1, 2),
        byte(x1, 3)
    );
    // -> 78:56:34:12


    struct u8_doubled x2 = {.x = 0x12, .y = 0x34};
    printf("%0x:%0x\n", byte(x2, 0), byte(x2, 1));
    // -> 12:34 (as expected, or not expected?)

    struct u16_doubled x3 = {.x = 0x1234, .y = 0x5678};
    printf("%0x:%0x:%0x:%0x\n",
        byte(x3, 0),
        byte(x3, 1),
        byte(x3, 2),
        byte(x3, 3)
    );
    // -> 34:12:78:56 (the same as above)
}
