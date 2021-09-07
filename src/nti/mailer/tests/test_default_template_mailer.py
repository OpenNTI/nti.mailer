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

from zope.testing.cleanup import CleanUp

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


@interface.implementer(IBrowserRequest)
class Request(object):
    response = None
    application_url = 'foo'

    def __init__(self):
        self.annotations = {}
        self.context = None


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


class _User(object):
    def __init__(self, username):
        self.username = username


class _Profile(object):
    def __init__(self, realname):
        self.realname = realname


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
                             context=_NotGiven,
                             reply_to=_NotGiven):

        user = user or _User('the_user')
        profile = profile or _Profile(u'Mickey Mouse')
        token_url = 'url_to_verify_email'

        kwargs = {}
        if context is not _NotGiven:
            kwargs['context'] = context
        if reply_to is not _NotGiven:
            kwargs['reply_to'] = reply_to

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

        if str is not bytes: # pragma: no cover
            # There's a bug in the 'always' simple filter on Python 2:
            # It doesn't properly clear the stacklevel cache,
            # so if we've emitted this warning by calling self._create_simple_email
            # before, we don't catch that warning.
            self.assertEqual(len(warns), 1)
            self.assertIn('Mismatch between the explicit', str(warns[0].message))

    def test_create_email_reply_to(self):
        msg = self._create_simple_email(Request())
        assert_that(msg.extra_headers, is_({}))
        msg = self._create_simple_email(Request(), reply_to='foo@bar.com')
        assert_that(msg.extra_headers, is_({'Reply-To': 'foo@bar.com'}))


class TestFunctions(CleanUp, unittest.TestCase):

    def test_get_renderer_spec_and_package_no_colon_no_slash_no_package(self):
        from nti.mailer import tests
        from .._default_template_mailer import _get_renderer_spec_and_package

        template, package = _get_renderer_spec_and_package('no_colon', '.txt',
                                                           level=2)
        assert_that(template, is_('templates/no_colon.txt'))
        assert_that(package, is_(tests))

    def test_get_renderer_spec_and_package_no_colon_no_package(self):
        from nti.mailer import tests
        from .._default_template_mailer import _get_renderer_spec_and_package

        template, package = _get_renderer_spec_and_package('subdir/no_colon', '.txt',
                                                           level=2)
        assert_that(template, is_('subdir/no_colon.txt'))
        assert_that(package, is_(tests))

    @fudge.patch('nti.mailer._default_template_mailer.get_renderer')
    def test__get_renderer(self, fake_get_renderer):
        from nti.mailer import tests
        from .._default_template_mailer import _get_renderer
        fake_get_renderer.expects_call().calls(lambda *args, **kwargs: (args, kwargs))

        args, kwargs = _get_renderer('no_colon', '.txt', level=2)
        assert_that(args, is_(('templates/no_colon.txt',)))
        assert_that(kwargs, is_({'package': tests}))

    @fudge.patch('nti.mailer._default_template_mailer._get_renderer')
    def test_do_html_text_templates_exist(self, fake__get_renderer):
        from .._default_template_mailer import do_html_text_templates_exist
        class MyException(Exception):
            pass

        def _get_renderer(base_template, extension, package=None, level=3):
            if extension in ('.pt', '.good'):
                return
            if extension == '.mako':
                # Unexpected case should propagate
                raise MyException
            # Expected case should return false.
            raise ValueError
        fake__get_renderer.expects_call().calls(_get_renderer)
        # This will raise ValueError on the second one
        result = do_html_text_templates_exist('base_template')
        self.assertFalse(result)

        with self.assertRaises(MyException):
            do_html_text_templates_exist('base_template', '.mako')

        result = do_html_text_templates_exist('base_template', '.good')
        self.assertTrue(result)

    def test_create_no_subject(self):
        result = create_simple_html_text_email(
            'base_template',
            subject=None,
            recipients=('foo@bar.com')
        )
        assert_that(result, is_(none()))

    def test__make_template_args_calls_all_IMailerTemplateArgsUtility(self):
        from ..interfaces import IMailerTemplateArgsUtility
        from .._default_template_mailer import _make_template_args
        the_request = object()

        # Note that we have to use different keys, because
        # the order in which these are called is not specified
        class A(object):
            def get_template_args(self, request):
                assert request is the_request
                return {'A': 1}

        class B(object):
            def get_template_args(self, request):
                assert request is the_request
                return {'B': 2}

        # unnamed
        component.provideUtility(A(), IMailerTemplateArgsUtility)
        # named
        component.provideUtility(B(), IMailerTemplateArgsUtility, u'B')

        template_args = {"C": 3}
        template_args_copy = template_args.copy()
        result = _make_template_args(
            the_request,
            self,
            '.txt',
            '.txt',
            template_args
        )

        # Got a new instance
        self.assertIsNot(result, template_args)
        # template args was left unchanged
        assert_that(template_args, is_(template_args_copy))
        assert_that(result, is_({
            'context': self,
            'A': 1,
            'B': 2,
            'C': 3
        }))

    def test__get_from_address_not_found(self):
        from .._default_template_mailer import _get_from_address

        with self.assertRaises(RuntimeError) as exc:
            _get_from_address(pyramid_mail_message=None, recipients=(), request=None)

        assert_that(exc.exception.args, is_(('No one to send mail from',)))

    def test__send_mail_with_IMailDelivery(self):
        from .._default_template_mailer import _send_mail

        class MailDelivery(object):
            sender = to = email_message = None
            def send(self, *args):
                self.sender, self.to, self.email_message = args

        class MockPyramidMailMessage(object):
            sender = 'from@nextthought.com'
            send_to = 'to@nextthought.com'
            email_message = object()

            def to_message(self):
                return self.email_message

        delivery = MailDelivery()
        component.provideUtility(delivery, IMailDelivery)

        _send_mail(MockPyramidMailMessage())

        # Verp gets applied to the sender, which inserts a default
        # realname if there is no IMailerPolicy
        self.assertEqual(delivery.sender, 'NextThought <%s>' % MockPyramidMailMessage.sender)
        self.assertIs(delivery.to, MockPyramidMailMessage.send_to)
        self.assertIs(delivery.email_message, MockPyramidMailMessage.email_message)

        # If there is no IMailDelivery, but the IMailer has a `queue_delivery`,
        # it gets used instead.
        result = component.getSiteManager().unregisterUtility(delivery, IMailDelivery)
        self.assertTrue(result)

        class Mailer(object):
            def __init__(self):
                self.queue_delivery = MailDelivery()

        mailer = Mailer()
        delivery = mailer.queue_delivery
        component.provideUtility(mailer, IMailer)

        _send_mail(MockPyramidMailMessage())
        self.assertEqual(delivery.sender, 'NextThought <%s>' % MockPyramidMailMessage.sender)
        self.assertIs(delivery.to, MockPyramidMailMessage.send_to)
        self.assertIs(delivery.email_message, MockPyramidMailMessage.email_message)

    def test__send_mail_with_IMailer(self):
        from .._default_template_mailer import _send_mail

        class Mailer(object):
            msg = None
            def send_to_queue(self, msg):
                self.msg = msg

        mailer = Mailer()
        component.provideUtility(mailer, IMailer)

        # We don't need to utilize much of this at all, but
        # the 'sender' does get mutated.
        class MockPyramidMailMessage(object):
            sender = 'from@nextthought.com'
            email_message = object()

            def to_message(self):
                return self.email_message

        pyramid_mail_message = MockPyramidMailMessage()
        _send_mail(pyramid_mail_message)

        assert_that(mailer.msg, is_(pyramid_mail_message))
        assert_that(pyramid_mail_message.sender, is_(
            'NextThought <%s>' % MockPyramidMailMessage.sender))

    def test__send_mail_with_nothing(self):
        from .._default_template_mailer import _send_mail
        class MockPyramidMailMessage(object):
            sender = 'from@nextthought.com'

            def to_message(self):
                return 42

        # The sender still gets mutated...
        pyramid_mail_message = MockPyramidMailMessage()
        with self.assertRaises(RuntimeError) as exc:
            _send_mail(pyramid_mail_message)

        assert_that(exc.exception.args, is_(('No way to deliver message',)))
        assert_that(pyramid_mail_message.sender, is_(
            'NextThought <%s>' % MockPyramidMailMessage.sender))

    def test_queue_simple_html_text_email_message_factory_deprecated(self):
        # The message_factory is deprecated.
        import warnings
        from .._default_template_mailer import queue_simple_html_text_email

        class MockPyramidMailMessage(object):
            sender = 'from@nextthought.com'
            def to_message(self):
                return self

        def message_factory(*_args, **_kwargs):
            return MockPyramidMailMessage()

        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            with self.assertRaises(RuntimeError) as exc:
                queue_simple_html_text_email(message_factory=message_factory)

        assert_that(exc.exception.args, is_(('No way to deliver message',)))
        self.assertEqual(len(warns), 1)
        assert_that(warns[0].message.args,
                    is_(('The message_factory argument is deprecated.',)))

    def test_queue_simple_html_text_email_message_factory_return_none(self):
        import warnings
        from .._default_template_mailer import queue_simple_html_text_email

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            result = queue_simple_html_text_email(message_factory=lambda *_args, **_kw: None)

        assert_that(result, is_(none()))
