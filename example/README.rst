Example
=======

|example.c|_ is the C source code file.

|example.h|_ is a public header, automatically generated with::

    autoheaders example.c > example.h

|example.priv.h|_ is a private header (meant to be included only by
``example.c``), automatically generated with::

    autoheaders -p example.c > example.priv.h

.. |example.c| replace:: **example.c**
.. _example.c: example.c

.. |example.h| replace:: **example.h**
.. _example.h: example.h

.. |example.priv.h| replace:: **example.priv.h**
.. _example.priv.h: example.priv.h
