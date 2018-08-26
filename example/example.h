#ifndef EXAMPLE_H
#define EXAMPLE_H

// The types defined in stdint.h are used in public structs and function
// declarations, so we need to place the "#include" here to ensure that
// stdint.h is included in the header.
#include <stdint.h>

// Similarly, "bool" is used in the declaration of the public function
// simplify_fraction(), so the "#include" must be here.
//
// However, even though fprintf() is used in the body of a public function,
// stdio.h doesn't need to be included here, because nothing it declares
// is used in a public function *declaration* or struct. If "FILE *" were
// the type of a public function parameter, though, then stdio.h would need
// to be included here.
#include <stdbool.h>

typedef struct {
    int_fast64_t numerator;
    int_fast64_t denominator;
} Fraction;

/*
 * If the denominator is zero, the fraction is unchanged and false is returned.
 * Otherwise, the fraction is simplified and true is returned. If the fraction
 * is negative, only the numerator will be negative after calling this
 * function. If the numerator is zero, the denominator will be set to one.
 */
bool simplify_fraction(Fraction *frac);

/*
 * Tries to simplify the fraction. If the denominator is zero, an error message
 * is displayed and abort() is called.
 */
void simplify_fraction_or_abort(Fraction *frac);

#endif
