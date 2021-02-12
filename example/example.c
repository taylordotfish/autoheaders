/*
 * To the extent possible under law, the author(s) have dedicated all
 * copyright and related and neighboring rights to this software to the
 * public domain worldwide. This software is distributed without any
 * warranty. See <http://creativecommons.org/publicdomain/zero/1.0/> for
 * a copy of the CC0 Public Domain Dedication.
 */

/*
 * See example.h and example.priv.h for the headers generated from this file.
 */

// The line below causes autoheaders to generate an include guard:
// @guard EXAMPLE_H

// The generated header files themselves should always be included.
#include "example.h"
#include "example.priv.h"

#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>

// assert.h defines the "static_assert" macro, which is used at the top level
// in this file, so we need to ensure that autoheaders includes it during its
// processing. Adding the "@include" comment on the same line achieves this.
#include <assert.h> /* @include */

// Code within this preprocessor conditional will be included in the header.
// This code could be moved to the end of the file and it would still work.
#ifdef HEADER
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
#endif

// Code within this preprocessor conditional will be included in the
// private header. This code could be moved to the end of the file and it would
// still work.
#ifdef PRIVATE_HEADER
    typedef struct {
        uint_fast64_t numerator;
        uint_fast64_t denominator;
    } UnsignedFraction;
#endif

/*
 * If the denominator is zero, the fraction is unchanged and false is returned.
 * Otherwise, the fraction is simplified and true is returned.
 */
static bool simplify_unsigned_fraction(UnsignedFraction *frac) {
    uint_fast64_t numer = frac->numerator;
    uint_fast64_t denom = frac->denominator;
    if (denom == 0) {
        return false;
    }
    if (numer == 0) {
        frac->denominator = 1;
        return true;
    }

    uint_fast64_t *smaller = (numer < denom) ? &numer : &denom;
    for (uint_fast64_t i = 2; i <= *smaller;) {
        if (numer % i == 0 && denom % i == 0) {
            numer /= i;
            denom /= i;
        } else {
            i++;
        }
    }

    frac->numerator = numer;
    frac->denominator = denom;
    return true;
}

/*
 * If the denominator is zero, the fraction is unchanged and false is returned.
 * Otherwise, the fraction is simplified and true is returned. If the fraction
 * is negative, only the numerator will be negative after calling this
 * function. If the numerator is zero, the denominator will be set to one.
 */
bool simplify_fraction(Fraction *frac) {
    bool is_negative = (frac->numerator < 0) != (frac->denominator < 0);
    UnsignedFraction unsigned_frac = {
        .numerator = imaxabs(frac->numerator),
        .denominator = imaxabs(frac->denominator),
    };
    if (!simplify_unsigned_fraction(&unsigned_frac)) {
        return false;
    }
    frac->numerator = (is_negative ? -1 : 1) * unsigned_frac.numerator;
    frac->denominator = unsigned_frac.denominator;
    return true;
}

/*
 * Tries to simplify the fraction. If the denominator is zero, an error message
 * is displayed and abort() is called.
 */
void simplify_fraction_or_abort(Fraction *frac) {
    if (!simplify_fraction(frac)) {
        fprintf(stderr, "Could not simplify fraction: denominator is 0.\n");
        abort();
    }
}
