#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
import contextlib

from hamcrest import is_
from hamcrest import contains_exactly as contains
from hamcrest import assert_that

import fudge
import unittest

from zope import component
from zope import interface

from zc.displayname.interfaces import IDisplayNameGenerator

from nti.mailer._compat import parseaddr

from nti.mailer._verp import verp_from_recipients
from nti.mailer._verp import principal_ids_from_verp

from nti.mailer.interfaces import EmailAddressablePrincipal


def _make_displayname_adapter(display_name):

    @interface.implementer(IDisplayNameGenerator)
    class StaticDisplayNameAdapter(object):

        def __init__(self, _site, _request):
            pass

        def __call__(self):
            return display_name

    return StaticDisplayNameAdapter


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

                prin = self.email_addr_principal('foo', 'foo@bar.com')

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
                prin2 = self.email_addr_principal('foo2', 'foo2@bar.com')

                addr = verp_from_recipients('no-reply+label+label2@nextthought.com',
                                                                        (prin, prin2),
                                                                        default_key='alpha.nextthought.com')

                name, email = parseaddr(addr)

                assert_that(name, is_('Janux'))
                assert_that(email, is_('no-reply+label+label2@nextthought.com'))

        def email_addr_principal(self, principal_id, email_address):
                prin = EmailAddressablePrincipal.__new__(EmailAddressablePrincipal)
                prin.email = '%s' % email_address
                prin.id = principal_id
                return prin

        @fudge.patch('nti.mailer._verp._get_default_sender',
                     'nti.mailer._verp._get_signer_secret',
                     'nti.mailer._verp.get_current_request')
        def test_verp_from_recipients_no_default_sender_realname(self,
                                                                 mock_find,
                                                                 mock_secret,
                                                                 get_current_request):
                """
                If there's no realname for the default sender, use the
                brand name as a fallback.
                """
                mock_find.is_callable().returns('janux@ou.edu')
                mock_secret.is_callable().returns('abc123')
                request = fudge.Fake('Request')

                # We'll pass it in the first time through, so this shouldn't
                # be called
                get_current_request.is_callable().returns(request).times_called(0)

                # If we have a IDisplayNameGenerator registered for the current site
                # we'll use that for the real name
                displayname_adapter = _make_displayname_adapter("Brand XYZ")
                with provide_adapter(displayname_adapter,
                                     required=(object, object),
                                     provided=IDisplayNameGenerator):

                    # Explicitly provide request
                    prin = self.email_addr_principal('foo', 'foo@bar.com')
                    addr = verp_from_recipients('no-reply@nextthought.com',
                                                (prin,),
                                                default_key='alpha.nextthought.com',
                                                request=request)

                    name, email = parseaddr(addr)

                    assert_that(name, is_('Brand XYZ'))
                    assert_that(email, is_('no-reply+foo.UGQXuA@nextthought.com'))

                    # Use current request implicitly
                    get_current_request.times_called(1)
                    addr = verp_from_recipients('no-reply@nextthought.com',
                                                (prin,),
                                                default_key='alpha.nextthought.com')

                    name, email = parseaddr(addr)

                    assert_that(name, is_('Brand XYZ'))
                    assert_that(email, is_('no-reply+foo.UGQXuA@nextthought.com'))

                # But if we don't have an IDisplayNameGenerator, we default to NextThought
                prin = self.email_addr_principal('foo', 'foo@bar.com')
                addr = verp_from_recipients('no-reply@nextthought.com',
                                            (prin,),
                                            default_key='alpha.nextthought.com',
                                            request=request)

                name, email = parseaddr(addr)

                assert_that(name, is_('NextThought'))
                assert_that(email, is_('no-reply+foo.UGQXuA@nextthought.com'))


@contextlib.contextmanager
def provide_adapter(adapter, **kwargs):
    gsm = component.getGlobalSiteManager()
    gsm.registerAdapter(adapter, **kwargs)
    try:
        yield
    finally:
        gsm.unregisterAdapter(adapter, **kwargs)
