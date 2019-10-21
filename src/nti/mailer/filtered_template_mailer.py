#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mailers that somehow filter their arguments before
actually creating or queuing mail.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import rfc822

from zope import component
from zope import interface

from nti.mailer.interfaces import ITemplatedMailer
from nti.mailer.interfaces import IEmailAddressable

from nti.mailer._default_template_mailer import _as_recipient_list

from nti.securitypolicy.utils import is_impersonating


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


class NextThoughtOnlyMailer(_BaseFilteredMailer):
    """
    This mailer ensures we only send email to nextthought.com
    addresses. It should only be registered in \"testing\" sites.
    """

    def _transform_recipient(self, addr):
        # support IEmailAddressable. We lose
        # VERP, but that's alright
        addr = getattr(IEmailAddressable(addr, addr), 'email', addr)
        if addr.endswith('@nextthought.com'):
            return addr

        realname, addr = rfc822.parseaddr(addr)
        # XXX This blows up if we get a malformed
        # email address
        local, _ = addr.split('@')
        addr = 'dummy.email+' + local + '@nextthought.com'
        return rfc822.dump_address_pair((realname, addr))

    def _should_send_to_addr(self, addr):
        return True

    def create_simple_html_text_email(self,
                                      base_template,
                                      subject='',
                                      request=None,
                                      recipients=(),
                                      template_args=None,
                                      attachments=(),
                                      package=None,
                                      bcc=(),
                                      text_template_extension='.txt',
                                      **kwargs):
        # Implementation wise, we know that all activity
        # gets directed through this method, so we only need to filter
        # here.
        bcc = _as_recipient_list(bcc) or ()
        recipients = _as_recipient_list(recipients)
        filtered_recip = [self._transform_recipient(a) for a in recipients]
        filtered_recip = [
            a for a in filtered_recip if self._should_send_to_addr(a)]

        filtered_bcc = [self._transform_recipient(a) for a in bcc]
        filtered_bcc = [
            a for a in filtered_bcc if self._should_send_to_addr(a)]

        if '_level' in kwargs:
            kwargs['_level'] = kwargs['_level'] + 1
        else:
            kwargs['_level'] = 4

        mailer = self._default_mailer
        return mailer.create_simple_html_text_email(base_template,
                                                    subject=subject,
                                                    request=request,
                                                    recipients=filtered_recip,
                                                    template_args=template_args,
                                                    attachments=attachments,
                                                    bcc=filtered_bcc,
                                                    package=package,
                                                    text_template_extension=text_template_extension,
                                                    **kwargs)


class ImpersonatedMailer(NextThoughtOnlyMailer):
    """
    This mailer, which is suitable for registration everywhere,
    takes into account the impersonation status of the current request.
    If the request is impersonated, then non `@nextthought.com` addresses
    are intercepted, otherwise mail is sent normally.

    .. note:: This is tied to the implementation of :func:`nti.appserver.logon.impersonate_user`
    """

    def create_simple_html_text_email(self,
                                      base_template,
                                      subject='',
                                      request=None,
                                      recipients=(),
                                      template_args=None,
                                      bcc=None,
                                      attachments=(),
                                      package=None,
                                      text_template_extension='.txt',
                                      **kwargs):
        _request = request
        if _request is None \
                or not hasattr(_request, 'environ'):  # In case we're zope proxied?
            _request = _get_current_request()

        if is_impersonating(_request):
            # This is how we know we are impersonated. In this case,
            # we want to filter everything. (see nti.appserver.logon)
            # Hmm, maybe we want to redirect to the impersonating user?
            # That would couple us pretty tightly to the DS though right now
            # since we don't have an principal directory utility
            mailer = super(ImpersonatedMailer,
                           self).create_simple_html_text_email
        else:
            # Not impersonating, no need to filter
            mailer = self._default_mailer.create_simple_html_text_email

        if '_level' in kwargs:
            kwargs['_level'] = kwargs['_level'] + 1
        else:
            kwargs['_level'] = 4

        return mailer(base_template,
                      subject=subject,
                      request=request,
                      recipients=recipients,
                      template_args=template_args,
                      attachments=attachments,
                      package=package,
                      bcc=bcc,
                      text_template_extension=text_template_extension,
                      **kwargs)
