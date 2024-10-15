#include <stdio.h>
#include <string.h>

int main(void) {
    size_t len = strlen("hi");
    printf("len of \"hi\" is: %lu\n", len);
    // -> 2 (god I was affraid it would print 3, with null terminator)
}
