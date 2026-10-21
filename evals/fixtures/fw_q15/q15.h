#ifndef Q15_H
#define Q15_H

#include <stdint.h>

typedef int16_t q15_t;

q15_t q15_from_double(double x);
q15_t q15_add(q15_t a, q15_t b);
q15_t q15_mul(q15_t a, q15_t b);

#endif
