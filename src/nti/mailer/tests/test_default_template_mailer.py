#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
import unittest

import fudge


from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string

from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown

from pyramid.interfaces import IRendererFactory

from pyramid_mailer.interfaces import IMailer

from pyramid_mailer.mailer import DummyMailer as _DummyMailer

from repoze.sendmail.interfaces import IMailDelivery

from zope import component

from zope import interface

from zope.i18n.interfaces import IUserPreferredLanguages
from zope.i18nmessageid import MessageFactory
from zope.publisher.interfaces.browser import IBrowserRequest

from zope.security.interfaces import IPrincipal

from nti.app.pyramid_zope import z3c_zpt

from nti.mailer._compat import parseaddr
from nti.mailer._default_template_mailer import _pyramid_message_to_message
from nti.mailer._default_template_mailer import create_simple_html_text_email

from nti.mailer.interfaces import IEmailAddressable
from nti.mailer.interfaces import EmailAddressablePrincipal
from nti.mailer.interfaces import IPrincipalEmailValidation

MSG_DOMAIN = u'nti.mailer.tests'
_ = MessageFactory(MSG_DOMAIN)

class ITestMailDelivery(IMailer, IMailDelivery):
    pass

class TestMailDelivery(_DummyMailer):

    default_sender = 'no-reply@nextthought.com'

    def send(self, fromaddr, toaddr, message):
        __traceback_info__ = fromaddr, toaddr
        self.queue.append(message)
        # compat with pyramid_mailer messages
        message.subject = message.get('Subject')
        payload = message.get_payload()
        message.body = payload[0].get_payload()
        if len(payload) > 1:
            message.html = payload[1].get_payload()


@interface.implementer(IBrowserRequest)
class Request(object):
    response = None
    application_url = 'foo'

    def __init__(self):
        self.annotations = {}
        self.context = None

    def get(self, key, default=None):
        return default

@interface.implementer(IUserPreferredLanguages)
class TestPreferredLanguages(object):

    def __init__(self, context):
        self.context = context

    def getPreferredLanguages(self):
        return ('test', 'en')

class PyramidMailerLayer(object):

    request = None

    @classmethod
    def setUp(cls):
        import nti.mailer
        from zope.configuration import xmlconfig
        from zope.i18n.testmessagecatalog import TestMessageFallbackDomain

        cls.config = psetUp(registry=component.getGlobalSiteManager(),
                            request=cls.request,
                            hook_zca=True)
        cls.config.setup_registry()
        cls.config.include('pyramid_chameleon')
        cls.config.include('pyramid_mako')
        component.provideUtility(z3c_zpt.renderer_factory,
                                 IRendererFactory,
                                 name=".pt")
        cls._mailer = mailer = TestMailDelivery()
        component.provideUtility(mailer, ITestMailDelivery)

        # Provide a ITranslationDomain that knows about the 'test' language
        cls.i18n_domain = TestMessageFallbackDomain(MSG_DOMAIN)

        component.provideUtility(cls.i18n_domain, name=cls.i18n_domain.domain)
        # Configure the default INegotiator
        xmlconfig.file('configure.zcml', nti.mailer)
        # Add an adapter for our Request to IUserPreferredLanguages, as used
        # by the default INegotiator
        component.provideAdapter(TestPreferredLanguages, (Request,))

    @classmethod
    def tearDown(cls):
        from zope.testing import cleanup
        cleanup.cleanUp() # Clear the site manager
        ptearDown() # unhook ZCA

        cls._mailer = None

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        # Must implement
        pass

@interface.implementer(IPrincipalEmailValidation)
class TestEmailAddressablePrincipal(EmailAddressablePrincipal):

    def __init__(self, user, is_valid=True, *args, **kwargs):
        super(TestEmailAddressablePrincipal, self).__init__(user, *args, **kwargs)
        self.is_valid = is_valid

    def is_valid_email(self):
        return self.is_valid


_NotGiven = object()

class TestEmail(unittest.TestCase):

    layer = PyramidMailerLayer

    @fudge.patch('nti.mailer._verp._brand_name')
    def test_create_mail_message_with_non_ascii_name_and_string_bcc(self, brand_name):
        brand_name.is_callable().returns(None)

        class User(object):
            username = 'the_user'

        class Profile(object):
            # Note the umlaut e
            realname = u'Suzë Schwartz'

        user = User()
        profile = Profile()
        request = Request()
        request.context = user

        token_url = 'url_to_verify_email'
        msg = create_simple_html_text_email('tests/templates/test_new_user_created',
                            subject='Hi there',
                            recipients=['jason.madden@nextthought.com'],
                            bcc='foo@bar.com',
                            template_args={'user': user,
                                           'profile': profile,
                                           'context': user,
                                           'href': token_url,
                                           'support_email': 'support_email' },
                            package='nti.mailer',
                            text_template_extension=".mak",
                            request=request)
        assert_that(msg, is_(not_none()))

        base_msg = _pyramid_message_to_message(msg, ['jason.madden@nextthought.com'], None)

        base_msg_string = str(base_msg)
        # quoted-prinatble encoding of iso-8859-1 value of umlaut-e
        assert_that(base_msg_string, contains_string('Hi=20Suz=EB=20Schwartz'))

        # Because we can't get to IPrincial, no VERP info
        name, email = parseaddr(msg.sender)
        assert_that(name, is_('NextThought'))
        assert_that(email, is_('no-reply@nextthought.com'))

        #
        assert_that(msg, has_property('bcc', ['foo@bar.com']))

    @fudge.patch('nti.mailer._verp._brand_name')
    def test_create_email_with_verp(self, brand_name):
        brand_name.is_callable().returns(None)

        @interface.implementer(IPrincipal, IEmailAddressable)
        class User(object):
            username = 'the_user'
            id = 'the_user'
            # this address encodes badly to simple base64
            # XXX: What?
            email = 'thomas.stockdale@nextthought.com'

        class Profile(object):
            realname = u'Suzë Schwartz'

        user = User()
        profile = Profile()
        request = Request()
        request.context = user

        token_url = 'url_to_verify_email'
        msg = create_simple_html_text_email('tests/templates/test_new_user_created',
                            subject='Hi there',
                            recipients=[TestEmailAddressablePrincipal(user, is_valid=True)],
                            template_args={'user': user,
                                           'profile': profile,
                                           'context': user,
                                           'href': token_url,
                                           'support_email': 'support_email' },
                            package='nti.mailer',
                            request=request)
        assert_that(msg, is_(not_none()))
        # import pyramid_mailer
        # from pyramid_mailer.interfaces import IMailer
        # from zope import component
        # mailer = pyramid_mailer.Mailer.from_settings(
        #    {'mail.queue_path': '/tmp/ds_maildir',
        #     'mail.default_sender': 'no-reply@nextthought.com'
        #  } )
        # component.provideUtility( mailer, IMailer )
        # component.provideUtility(mailer.queue_delivery)
        # from .._default_template_mailer import _send_mail
        # _send_mail(msg, [user], None)
        # import transaction
        # transaction.commit()

        _pyramid_message_to_message(msg, [user], None)

        # we can get to IPrincipal, so we have VERP
        # The first part will be predictable, the rest won't
        name, email = parseaddr(msg.sender)
        assert_that(name, is_('NextThought'))
        assert_that(email, contains_string('no-reply+'))

        # Test invalid
        invalid_user = TestEmailAddressablePrincipal(user, is_valid=False)
        msg = create_simple_html_text_email('tests/templates/test_new_user_created',
                            subject='Hi there',
                            recipients=[invalid_user],
                            template_args={'user': user,
                                           'profile': profile,
                                           'context': user,
                                           'href': token_url,
                                           'support_email': 'support_email' },
                            package='nti.mailer',
                            request=request)
        assert_that(msg, none())

    @fudge.patch('nti.mailer._verp._brand_name')
    def test_create_email_with_mako(self, brand_name):
        brand_name.is_callable().returns(None)

        user = _User('the_user')
        request = Request()
        request.context = user

        msg = self._create_simple_email(request,
                                        text_template_extension=".mak",
                                        user=user)
        assert_that(msg, is_(not_none()))

    @fudge.patch('nti.mailer._verp._brand_name')
    def test_create_email_no_request_context(self, brand_name):
        brand_name.is_callable().returns(None)

        request = Request()
        del request.context
        assert not hasattr(request, 'context')
        msg = self._create_simple_email(request,
                                        text_template_extension=".mak")
        assert_that(msg, is_(not_none()))

    def _create_simple_email(self,
                             request,
                             user=None,
                             profile=None,
                             text_template_extension=".txt",
                             subject=u'Hi there',
                             context=_NotGiven):

        user = user or _User('the_user')
        profile = profile or _Profile(u'Mickey Mouse')
        token_url = 'url_to_verify_email'

        kwargs = {}
        if context is not _NotGiven:
            kwargs['context'] = context

        msg = create_simple_html_text_email(
            'tests/templates/test_new_user_created',
            subject=subject,
            recipients=['jason.madden@nextthought.com'],
            template_args={'user': user,
                           'profile': profile,
                           'context': user,
                           'href': token_url,
                           'support_email': 'support_email'},
            package='nti.mailer',
            text_template_extension=text_template_extension,
            request=request,
            **kwargs)
        return msg

    def test_create_email_localizes_subject(self):
        import warnings

        request = Request()
        subject = _(u'Hi there')
        # If we don't provide a `context` object, by default
        # the ``translate`` function won't try to negotiate a language;
        # creating the message works around that by using the `request` as the context.
        msg = self._create_simple_email(request, subject=subject)
        assert_that(msg.subject, is_(u'[[nti.mailer.tests][Hi there]]'))

        # We can be explicit about that
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            msg = self._create_simple_email(request, subject=subject, context=request)
        assert_that(msg.subject, is_(u'[[nti.mailer.tests][Hi there]]'))

        # If we *do* provide a context, but there is no
        # IUserPreferredLanguages available for the context, we
        # fallback to using the request for translation. This can either
        # be in the ``request.context``, or the ``context`` argument
        request.context = self
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            msg = self._create_simple_email(request, subject=subject)
        assert_that(msg.subject, is_(u'[[nti.mailer.tests][Hi there]]'))

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            msg = self._create_simple_email(request, subject=subject, context=request)
        assert_that(msg.subject, is_(u'[[nti.mailer.tests][Hi there]]'))

    def test_warning_about_mismatch_of_context(self):
        # If we pass a context argument we get the warning because the
        # function always puts ``context=User()`` in the arguments.
        import warnings
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            self._create_simple_email(Request(), context=self)


        self.assertEqual(len(warns), 1)
        self.assertIn('Mismatch between the explicit', str(warns[0].message))

class _User(object):
    def __init__(self, username):
        self.username = username


class _Profile(object):
    def __init__(self, realname):
        self.realname = realname
