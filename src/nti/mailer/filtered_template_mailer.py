#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mailers that somehow filter their arguments before
actually creating or queuing mail.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.mailer.interfaces import ITemplatedMailer

logger = __import__('logging').getLogger(__name__)


def _get_current_request():
    try:
        from pyramid.threadlocal import get_current_request
        return get_current_request()
    except ImportError:
        return None


@interface.implementer(ITemplatedMailer)
class _BaseFilteredMailer(object):

    @property
    def _default_mailer(self):
        # We look up the utility by name, because we expect
        # to be registered in sub-sites to override the main utility.
        # (Note that we use query here because zope.component arguably has
        # a bug in accessing new random attributes DURING ZCML TIME so registrations
        # are unreliable)
        return component.queryUtility(ITemplatedMailer, name='default')

    def __getattr__(self, name):
        return getattr(self._default_mailer, name)

BaseFilteredMailer = _BaseFilteredMailer
