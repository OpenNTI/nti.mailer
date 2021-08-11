#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

import sys

try:
    from email.utils import parseaddr # PY3
    from email.utils import formataddr  # PY3
except ImportError:  # pragma: no cover
    from rfc822 import parseaddr # PY2
    from rfc822 import dump_address_pair as formataddr # PY2

PY2 = sys.version_info[0] <= 2
PY3 = sys.version_info[0] >= 3

if PY2: # pragma: no cover
    def is_nonstr_iter(v):
        return hasattr(v, '__iter__')
else:
    def is_nonstr_iter(v):
        if isinstance(v, str):
            return False
        return hasattr(v, '__iter__')
