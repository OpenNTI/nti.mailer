# -*- coding: utf-8 -*-
"""
Tests for interfaces.py.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

class AbstractPrincipal(object):
    id = 'id'
    email = 'sjohnson@nextthought.com'

    def __conform__(self, iface):
        return self


class TestEmailAddressablePrincipal(unittest.TestCase):

    def _makeOne(self, context):
        from nti.mailer.interfaces import EmailAddressablePrincipal
        return EmailAddressablePrincipal(context)

    def test_copies_title(self):
        class Context(AbstractPrincipal):
            id = 'id'
            title = 'MyTitle'

        prin = self._makeOne(Context())
        self.assertIs(prin.id, Context.id)
        self.assertIs(prin.email, Context.email)
        self.assertIs(prin.title, Context.title)
        self.assertIsNone(prin.description)

    def test_copies_description(self):
        class Context(AbstractPrincipal):
            id = 'id'
            description = 'MyDesc'

        prin = self._makeOne(Context())
        self.assertIs(prin.id, Context.id)
        self.assertIs(prin.email, Context.email)
        self.assertIs(prin.description, Context.description)
        self.assertIsNone(prin.title)

    def test_str_repr(self):
        prin = self._makeOne(AbstractPrincipal())
        expected = 'Principal(id/sjohnson@nextthought.com)'
        self.assertEqual(str(prin), expected)
        self.assertEqual(repr(prin), expected)
