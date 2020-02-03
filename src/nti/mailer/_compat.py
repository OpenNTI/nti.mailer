#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

try:
    from email.utils import parseaddr # PY3
    from email.utils import formataddr  # PY3
except ImportError:  # pragma: no cover
    from rfc822 import parseaddr # PY2
    from rfc822 import dump_address_pair as formataddr # PY2
