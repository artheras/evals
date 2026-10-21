#ifndef DEBOUNCE_H
#define DEBOUNCE_H

#define DEBOUNCE_SAMPLES 5

typedef struct {
    int stable;
    int count;
} debounce_t;

void debounce_init(debounce_t *d, int initial);
int debounce_sample(debounce_t *d, int raw);

#endif
