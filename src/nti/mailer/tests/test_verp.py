#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import contains
from hamcrest import assert_that

import fudge
import unittest

from nti.mailer._compat import parseaddr

from nti.mailer._verp import verp_from_recipients
from nti.mailer._verp import principal_ids_from_verp

from nti.mailer.interfaces import EmailAddressablePrincipal


class TestVerp(unittest.TestCase):

        def test_pids_from_verp_email(self):
                fromaddr = 'no-reply+kaley.white%40nextthought.com.PFgX7A@nextthought.com'
                pids = principal_ids_from_verp(fromaddr, default_key='alpha.nextthought.com')
                assert_that(pids, contains('kaley.white@nextthought.com'))

                # With label
                fromaddr = 'no-reply+label+label2+kaley.white%40nextthought.com.PFgX7A@nextthought.com'
                pids = principal_ids_from_verp(fromaddr, default_key='alpha.nextthought.com')
                assert_that(pids, contains('kaley.white@nextthought.com'))

                # With '+' in principal
                fromaddr = 'no-reply+label+foo%2B%2B%2B.PXAYJg@nextthought.com'
                pids = principal_ids_from_verp(fromaddr, default_key='alpha.nextthought.com')
                assert_that(pids, contains('foo+++'))

                pids = principal_ids_from_verp(fromaddr)
                assert_that(pids, is_(()))

        @fudge.patch('nti.mailer._verp._get_default_sender',
                                 'nti.mailer._verp._get_signer_secret')
        def test_verp_from_recipients_in_site_uses_default_sender_realname(self, mock_find, mock_secret):
                mock_find.is_callable().returns('Janux <janux@ou.edu>')
                mock_secret.is_callable().returns('abc123')

                prin = EmailAddressablePrincipal.__new__(EmailAddressablePrincipal)
                prin.email = 'foo@bar.com'
                prin.id = 'foo'

                addr = verp_from_recipients('no-reply@nextthought.com',
                                                                        (prin,),
                                                                        default_key='alpha.nextthought.com')

                name, email = parseaddr(addr)

                assert_that(name, is_('Janux'))
                assert_that(email, is_('no-reply+foo.UGQXuA@nextthought.com'))

                pids = principal_ids_from_verp(addr, default_key='alpha.nextthought.com')
                assert_that(pids, contains(prin.id))

                # Test with label already; principal with '+' chars.
                prin.id = 'foo+++'
                addr = verp_from_recipients('no-reply+label+label2@nextthought.com',
                                                                        (prin,),
                                                                        default_key='alpha.nextthought.com')

                name, email = parseaddr(addr)

                assert_that(name, is_('Janux'))
                assert_that(email, is_('no-reply+label+label2+foo%2B%2B%2B.ULoYGw@nextthought.com'))

                pids = principal_ids_from_verp(addr, default_key='alpha.nextthought.com')
                assert_that(pids, contains(prin.id))

                # If more than one prin, no verp
                prin2 = EmailAddressablePrincipal.__new__(EmailAddressablePrincipal)
                prin2.email = 'foo2@bar.com'
                prin2.id = 'foo2'

                prin.id = 'foo+++'
                addr = verp_from_recipients('no-reply+label+label2@nextthought.com',
                                                                        (prin, prin2),
                                                                        default_key='alpha.nextthought.com')

                name, email = parseaddr(addr)

                assert_that(name, is_('Janux'))
                assert_that(email, is_('no-reply+label+label2@nextthought.com'))

