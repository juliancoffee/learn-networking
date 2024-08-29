/* I just test all the cursed behaviour in this file.
 *
 * Ideally, until I get a segfault or at least a warning.
 *
 * And yeah, spoiler, zero warnings even with -pedantic.
 * And no segfaults, at least for now.
 */
#include <stdint.h>
#include <string.h>
#include <stdio.h>

struct store_t {
    uint32_t x;
    char pad[5];
};

struct value1_t {
    uint32_t x;
    char y;
    char pad[4];
};

struct value2_t {
    uint32_t x;
    char y;
    char z;
    char k;
    char n;
    char m;
};

int gen(uint8_t version, struct store_t *s) {
    if (version == 1) {
        struct value1_t *v1 = (struct value1_t *)s;
        v1->x = version;
        v1->y = '@';
        memset(v1->pad, 0, sizeof v1->pad);
    } else if (version == 2) {
        struct value2_t *v2 = (struct value2_t *)s;
        v2->x = version;
        v2->y = '@';
        v2->z = '@';
        v2->k = '@';
        v2->n = '@';
        v2->m = '@';
    } else {
        return -1;
    }

    return 0;
}

int main(void) {
    printf("hi\n");

    struct store_t s_uninit;
    printf(">> sizeof store_t: %lu\n", sizeof s_uninit);
    // -> 12 on my machine

    // 8 in ASCII is backspace, btw.
    // but I picked this randomly, I swear
    struct value1_t v = {.x = 5, .y = 8};
    printf(">> sizeof value1_t: %lu\n", sizeof v);
    // -> 12 on my machine
    printf("v:\n x: %d, y: %d, pad: (%s)\n", v.x, v.y, v.pad);

    struct store_t *v_as_s = (struct store_t *)&v;
    printf("v_as_s:\n x: %d, pad: (%s)\n", v_as_s->x, v_as_s->pad);

    struct value1_t *v_as_s_as_v = (struct value1_t *)v_as_s;
    printf(
            "v_as_s_as_v:\n x: %d, y: %d, pad: (%s)\n",
            v_as_s_as_v->x,
            v_as_s_as_v->y,
            v_as_s_as_v->pad
    );

    int *v_as_int = (int *)&v;
    printf("v_as_int:\n %d\n", *v_as_int);
    char *v_as_char = (char *)&v;
    printf("v_as_char:\n %d\n", *v_as_char);

    struct value1_t v_to_memset;
    memset(&v_to_memset, 0, sizeof v_to_memset);
    printf("v_to_memset:\n x: %d, y: %d, pad: (%s)\n",
            v_to_memset.x, v_to_memset.y, v_to_memset.pad);

    struct value2_t v2 = {
        .x = 5,
        .y = '@',
        .z = '@',
        .k = '@',
        .n = '@',
        .m = '@',
    };
    printf(">> sizeof value2_t: %lu\n", sizeof v2);
    // -> 12 on my machine
    printf("v2:\n x: %d, y: %d, z: %d, k: %d, n: %d, m: %d\n",
            v2.x,
            v2.y,
            v2.z,
            v2.k,
            v2.n,
            v2.m
    );
    struct value1_t *v2_as_v1 = (struct value1_t *)&v2;
    printf(
            "v2_as_v1:\n x: %d, y: %d, pad: (%s)\n",
            v2_as_v1->x,
            v2_as_v1->y,
            v2_as_v1->pad
    );
    struct store_t *v2_as_s = (struct store_t *)&v2;
    printf(
            "v2_as_s:\n x: %d, pad: (%s)\n",
            v2_as_s->x,
            v2_as_s->pad
    );

    struct value1_t v1_gen;
    gen(1, (struct store_t *)&v1_gen);
    printf(
            "v1_gen:\n x: %d, y: %d, pad: (%s)\n",
            v1_gen.x,
            v1_gen.y,
            v1_gen.pad
    );
    struct store_t *v1_gen_as_s = (struct store_t *)&v1_gen;
    printf(
            "v1_gen_as_s:\n x: %d, pad: (%s)\n",
            v1_gen_as_s->x,
            v1_gen_as_s->pad
    );

    struct value2_t v2_gen;
    printf("v2_gen_uninit:\n x: %d, y: %d, z: %d, k: %d, n: %d, m: %d\n",
            v2_gen.x,
            v2_gen.y,
            v2_gen.z,
            v2_gen.k,
            v2_gen.n,
            v2_gen.m
    );
    // -> all zeroes
    gen(2, (struct store_t *)&v2_gen);
    printf("v2_gen:\n x: %d, y: %d, z: %d, k: %d, n: %d, m: %d\n",
            v2_gen.x,
            v2_gen.y,
            v2_gen.z,
            v2_gen.k,
            v2_gen.n,
            v2_gen.m
    );
    // -> 2 and then all 64, as expected

    printf("address v2_gen: %zx\n", (size_t)&v2_gen);
    printf("shift x of v2_gen: %lu\n", (size_t)&v2_gen.x - (size_t)&v2_gen);
    // -> 0 as expected
    printf("shift y of v2_gen: %lu\n", (size_t)&v2_gen.y - (size_t)&v2_gen);
    // -> 4 (size of x is 4, so y is right next to it)
    printf("shift z of v2_gen: %lu\n", (size_t)&v2_gen.z - (size_t)&v2_gen);
    // -> 5
    printf("shift k of v2_gen: %lu\n", (size_t)&v2_gen.k - (size_t)&v2_gen);
    // -> 6
    printf("shift n of v2_gen: %lu\n", (size_t)&v2_gen.n - (size_t)&v2_gen);
    // -> 7
    printf("shift m of v2_gen: %lu\n", (size_t)&v2_gen.m - (size_t)&v2_gen);
    // -> 8
    printf("shift for end of v2_gen from v2_gen.m: %lu\n",
            (size_t)(&v2_gen + 1) - (size_t)&v2_gen.m);
    // -> 4, so padding is at the end, I suppose

    struct store_t *v2_gen_as_s = (struct store_t *)&v2_gen;
    printf(
            "v2_gen_as_s:\n x: %d, pad: (%s)\n",
            v2_gen_as_s->x,
            v2_gen_as_s->pad
    );
    // -> honestly, this should segfault, but because v2_gen was all zeroes
    // before initialization, it treats the next byte after pad ends as
    // null-terminator, I suppose
}
