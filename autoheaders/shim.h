/*
 * To the extent possible under law, the author(s) have dedicated all
 * copyright and neighboring rights to this software to the public domain
 * worldwide. This software is distributed without any warranty. See
 * <http://creativecommons.org/publicdomain/zero/1.0/> for a copy of the
 * CC0 Public Domain Dedication.
 */

typedef int __builtin_va_list;

#define __FUNCTION__ ""
#define __PRETTY_FUNCTION__ ""
#define __alignof(...) 0
#define __alignof__(...) 0
#define __asm(...)
#define __asm__(...)
#define __attribute(...)
#define __attribute__(...)
#define __builtin_offsetof(...) 0
#define __builtin_va_arg(...) 0
#define __complex _Complex
#define __complex__ _Complex
#define __const const
#define __extension
#define __extension__
#define __imag _Imaginary
#define __imag__ _Imaginary
#define __inline inline
#define __inline__ inline
#define __label
#define __label__
#define __null ((void *)0)
#define __null__ ((void *)0)
#define __real
#define __real__
#define __restrict restrict
#define __restrict__ restrict
#define __signed signed
#define __signed__ signed
#define __thread
#define __thread__
#define __typeof(...) int
#define __typeof__(...) int
#define __volatile volatile
#define __volatile__ volatile

// pycparser doesn't support all of C11 yet.
#define _Alignas(...)
#define _Alignof(...) 0
#define _Atomic
#define _Generic(...) 0
#define _Noreturn
#define _Static_assert(...)
#define _Thread_local
