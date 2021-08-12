#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

import sys

from email.utils import parseaddr # PY2.2+
from email.utils import formataddr  # PY2.2+

PY2 = sys.version_info[0] <= 2
PY3 = sys.version_info[0] >= 3

if PY2: # pragma: no cover
    def is_nonstr_iter(v):
        return hasattr(v, '__iter__')
else: # pragma: no cover
    def is_nonstr_iter(v):
        if isinstance(v, str):
            return False
        return hasattr(v, '__iter__')

__all__ = (
    'parseaddr',
    'formataddr',
    'PY2',
    'PY3',
    'is_nonstr_iter',
)
