typedef struct {
    uint_fast64_t numerator;
    uint_fast64_t denominator;
} UnsignedFraction;

/*
 * If the denominator is zero, the fraction is unchanged and false is returned.
 * Otherwise, the fraction is simplified and true is returned.
 */
static bool simplify_unsigned_fraction(UnsignedFraction *frac);
