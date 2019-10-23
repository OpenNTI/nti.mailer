#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string

from zope import interface

from zope.publisher.interfaces.browser import IBrowserRequest

from zope.security.interfaces import IPrincipal

from nti.mailer._default_template_mailer import _pyramid_message_to_message
from nti.mailer._default_template_mailer import create_simple_html_text_email

from nti.mailer.interfaces import IEmailAddressable
from nti.mailer.interfaces import EmailAddressablePrincipal
from nti.mailer.interfaces import IPrincipalEmailValidation

from nti.app.testing.layers  import AppLayerTest


@interface.implementer(IPrincipalEmailValidation)
class TestEmailAddressablePrincipal(EmailAddressablePrincipal):

	def __init__(self, user, is_valid=True, *args, **kwargs):
		super(TestEmailAddressablePrincipal, self).__init__(user, *args, **kwargs)
		self.is_valid = is_valid

	def is_valid_email(self):
		return self.is_valid


@interface.implementer(IBrowserRequest)
class Request(object):
	context = None
	response = None
	application_url = 'foo'

	def __init__(self):
		self.annotations = {}

	def get(self, key, default=None):
		return default


class TestEmail(AppLayerTest):

	def test_create_mail_message_with_non_ascii_name_and_string_bcc(self):
		class User(object):
			username = 'the_user'

		class Profile(object):
			# Note the umlaut e
			realname = 'Suzë Schwartz'

		user = User()
		profile = Profile()
		request = Request()
		request.context = user

		token_url = 'url_to_verify_email'
		msg = create_simple_html_text_email('new_user_created',
											subject='Hi there',
											recipients=['jason.madden@nextthought.com'],
											bcc='foo@bar.com',
											template_args={'user': user,
														   'profile': profile,
														   'context': user,
														   'href': token_url,
														   'support_email': 'support_email' },
											package='nti.appserver',
											request=request)
		assert_that(msg, is_(not_none()))

		base_msg = _pyramid_message_to_message(msg, ['jason.madden@nextthought.com'], None)

		base_msg_string = str(base_msg)
		# quoted-prinatble encoding of iso-8859-1 value of umlaut-e
		assert_that(base_msg_string, contains_string('Hi=20Suz=EB=20Schwartz'))

		# Because we can't get to IPrincial, no VERP info
		assert_that(msg.sender, is_('"NextThought" <no-reply@nextthought.com>'))

		#
		assert_that(msg, has_property('bcc', ['foo@bar.com']))

	def test_create_email_with_verp(self):

		@interface.implementer(IPrincipal, IEmailAddressable)
		class User(object):
			username = 'the_user'
			id = 'the_user'
			email = 'thomas.stockdale@nextthought.com'  # this address encodes badly to simple base64

		class Profile(object):
			realname = 'Suzë Schwartz'

		user = User()
		profile = Profile()
		request = Request()
		request.context = user

		token_url = 'url_to_verify_email'
		msg = create_simple_html_text_email('new_user_created',
											subject='Hi there',
											recipients=[TestEmailAddressablePrincipal(user, is_valid=True)],
											template_args={'user': user,
														   'profile': profile,
														   'context': user,
														   'href': token_url,
														   'support_email': 'support_email' },
											package='nti.appserver',
											request=request)
		assert_that(msg, is_(not_none()))
		# import pyramid_mailer
		# from pyramid_mailer.interfaces import IMailer
		# from zope import component
		# mailer = pyramid_mailer.Mailer.from_settings( {'mail.queue_path': '/tmp/ds_maildir', 'mail.default_sender': 'no-reply@nextthought.com' } )
		# component.provideUtility( mailer, IMailer )
		# component.provideUtility(mailer.queue_delivery)
		# from .._default_template_mailer import _send_mail
		# _send_mail(msg, [user], None)
		# import transaction
		# transaction.commit()

		_pyramid_message_to_message(msg, [user], None)

		# we can get to IPrincipal, so we have VERP
		# The first part will be predictable, the rest won't
		assert_that(msg.sender, contains_string('"NextThought" <no-reply+'))

		# Test invalid
		invalid_user = TestEmailAddressablePrincipal(user, is_valid=False)
		msg = create_simple_html_text_email('new_user_created',
											subject='Hi there',
											recipients=[invalid_user],
											template_args={'user': user,
														'profile': profile,
														'context': user,
														'href': token_url,
														'support_email': 'support_email' },
											package='nti.appserver',
											request=request)
		assert_that(msg, none())


