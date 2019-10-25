#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import raises
from hamcrest import calling
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not
from hamcrest import none
from hamcrest import has_length

import fudge

from nose.tools import assert_raises

import os

from tempfile import mkdtemp

import unittest

import email

from boto.ses.exceptions import SESAddressBlacklistedError

from repoze.sendmail.delivery import QueuedMailDelivery
from repoze.sendmail.maildir import Maildir

from repoze.sendmail.tests.test_delivery import _makeMailerStub

from smtplib import SMTPResponseException

from nti.mailer.queue import SESMailer
from nti.mailer.queue import MailerWatcher

MSG_STRING = 'MIME-Version: 1.0\nFrom: NextThought <no-reply+70108544275840.qhjWPQ@nextthought.com>\nSubject: Welcome to NextThought\nTo: test.user@nextthought.com\nMessage-Id: <20140528152113.23368.67989.repoze.sendmail@aux1-ou.internal.nextthought.com>\nDate: Wed, 28 May 2014 15:21:13 -0000\nContent-Type: multipart/alternative;\n boundary="===============3015559400140931547=="\n\n--===============3015559400140931547==\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nContent-Disposition: inline\n\nHi=20Test=20User!\n\nThank=20you=20for=20creating=20your=20new=20account=20and=20welcome=20to=20=\nNextThought!\n\nUsername:=2070108544275840\nLog=20in=20at:=20https://alpha.nextthought.com\n\nNextThought=20offers=20interactive=20content=20and=20rich=20features=20to=\n=20make\nlearning=20both=20social=20and=20personal.=20Explore=20the=20NextThought=20=\nHelp=20Center\nin=20your=20Library=20to=20get=20started=20and=20learn=20more=20about=20the=\n=20exciting\ninteractive=20features=20NextThought=20has=20to=20offer.\n\nSincerely,\nNextThought\n\nIf=20you=20feel=20this=20email=20was=20sent=20in=20error,=20or=20this=20acc=\nount=20was=20created\nwithout=20your=20consent,=20you=20may=20email=20us=20at=20support@nextthoug=\nht.com.\n\n--===============3015559400140931547==\nContent-Type: text/html; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nContent-Disposition: inline\n\n<!DOCTYPE=20html=20PUBLIC=20"-//W3C//DTD=20XHTML=201.0=20Strict//EN"\n=09=20"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n<html=20xmlns=3D"http://www.w3.org/1999/xhtml">\n=09<head>\n=09=09<meta=20http-equiv=3D"content-type"=20content=3D"text/html;=20charset=\n=3Dutf-8"=20/>\n=09=09<title>Welcome=20To=20NextThought</title>\n=09=09<style>\n=09=09=09#green-bar=20{\n=09=09=09background-color:=20#89be3c;\n=09=09=09width:=20100%;\n=09=09=09height:=205px;\n=09=09=09margin-left:=20-30px;\n=09=09=09padding-right:=2040px;\n=09=09=09}\n=09=09=09#logo-bar=20{\n=09=09=09margin-top:=2020px;\n=09=09=09margin-bottom:=2030px;\n=09=09=09}\n=09=09=09body=20{\n=09=09=09margin-left:=2030px;\n=09=09=09margin-right:=200px;\n=09=09=09font-family:=20Helvetica,=20Arial,=20sans-serif;\n=09=09=09font-size:=2014pt;\n=09=09=09line-height:=2020pt;\n=09=09=09color:=20#757474;\n=09=09=09}\n=09=09=09.normal-text=20{\n=09=09=09margin-left:=2030px;\n=09=09=09margin-right:=200px;\n=09=09=09font-family:=20Helvetica,=20Arial,=20sans-serif;\n=09=09=09font-size:=2014pt;\n=09=09=09line-height:=2020pt;\n=09=09=09color:=20#757474;\n=09=09=09}\n=09=09=09a=20{\n=09=09=09text-decoration:=20none;\n=09=09=09color:=20#3fb3f6;\n=09=09=09}\n=09=09=09.tterm,=20strong=20{\n=09=09=09font-weight:=20bold;\n=09=09=09color:=20#494949;\n=09=09=09}\n=09=09=09.tterm-color=20{\n=09=09=09font-weight:=20bold;\n=09=09=09color:=20#3fb3f6;\n=09=09=09}\n=09=09=09h1,=20h2,=20h3,=20h4,=20h5,=20h6=20{\n=09=09=09font-weight:=20bold;\n=09=09=09font-family:=20Helvetica,=20Arial,=20sans-serif;\n=09=09=09color:=20#757474;\n=09=09=09margin-left:=2030px;\n=09=09=09}\n=09=09=09h1=20{\n=09=09=09font-size:=2016pt;\n=09=09=09}\n=09=09=09h2=20{\n=09=09=09font-size:=2014pt;\n=09=09=09}\n=09=09=09body=20p=20{\n=09=09=09margin-right:=2030px;\n=09=09=09margin-left:=2030px;\n=09=09=09font-family:=20Helvetica,=20Arial,=20sans-serif;\n=09=09=09font-size:=2014pt;\n=09=09=09line-height:=2020pt;\n=09=09=09color:=20#757474;\n=09=09=09}\n=09=09=09.pnormal-text=20{\n=09=09=09margin-left:=2030px;\n=09=09=09margin-right:=2030px;\n=09=09=09font-family:=20Helvetica,=20Arial,=20sans-serif;\n=09=09=09font-size:=2014pt;\n=09=09=09line-height:=2020pt;\n=09=09=09color:=20#757474;\n=09=09=09}\n=09=09</style>\n=09</head>\n=09<body>\n=09=09<div>\n=09=09=09<div=20id=3D"green-bar"=20style=3D"background-color:=20#89be3c;=20=\nwidth:=20100%;=20height:=205px;=20margin-left:=20-30px;=20padding-right:=20=\n40px;"></div>\n=09=09=09<div=20id=3D"logo-bar">\n=09=09=09=09<img=20src=3D"https://d2ixlfeu83tci.cloudfront.net/images/email=\n_logo.png"=20width=3D"177"=20height=3D"25"=20alt=3D"NextThought=20Logo"=20/>\n=09=09=09</div>\n=09=09=09\n=09=09=09\n=09=09=09\n=09=09=09\n=09=09</div>\n=09=09<p>Hi=20<span=20class=3D"realname=20tterm">Test=20User</span>!</p>\n\n=09=09<p>Thank=20you=20for=20creating=20your=20new=20account=20and=20welcom=\ne=20to=20NextThought!</p>\n\n=09=09<p>\n=09=09=09<strong>Username:</strong>=20<span=20class=3D"tterm-color">7010854=\n4275840</span>=20<br=20/>\n=09=09=09<strong>Log=20in=20at:</strong>=20<a=20href=3D"https://alpha.nextt=\nhought.com">https://alpha.nextthought.com</a>\n=09=09</p>\n=09=09<p>NextThought=20offers=20interactive=20content=20and=20rich=20featur=\nes=20to=20make=20learning=20both=20social=20and=20personal.=20Explore=20the=\n=20NextThought=20Help=20Center=20in=20your=20Library=20to=20get=20started=\n=20and=20learn=20more=20about=20the=20exciting=20interactive=20features=20N=\nextThought=20has=20to=20offer.</p>\n\n=09=09<p>\n=09=09=09<span>Sincerely,</span><br=20/>\n=09=09=09NextThought\n=09=09</p>\n\n=09=09<p=20style=3D"font-size:=20smaller">\n=09=09=09<span>If=20you=20feel=20this=20email=20was=20sent=20in=20error,=20=\nor=20this=20account=20was=20created=20without=20your=20consent,=20you=20may=\n=20email=20us=20at=20<a=20href=3D"mailto:mailto:support@nextthought.com">su=\npport@nextthought.com</a></span>\n=09=09</p>\n\n=09</body>\n</html>\n\n--===============3015559400140931547==--\n'

class TestMailer(unittest.TestCase):

	def setUp(self):
		super(TestMailer, self).setUp()
		self.message = email.message_from_string(MSG_STRING)

	@fudge.test
	def test_ses_raises(self):
		mailer = SESMailer()
		fake_sesconn = fudge.Fake()
		exc = SESAddressBlacklistedError('404', 'reason')
		fake_sesconn.expects('send_raw_email').raises(exc)

		mailer.sesconn = fake_sesconn

		assert_that(calling(mailer.send).with_args('from', ('to',), self.message),
					raises(SMTPResponseException))

        def test_ses_close(self):
                mailer = SESMailer()
                conn = mailer.sesconn

                # We have a connection
                assert_that(conn._connection, is_not(none()))

                mailer.close()

                # No connection after closing
                assert_that(conn._connection, is_(none()))

        def test_region(self):
                # Defaults to us-east-1
                mailer = SESMailer()

                assert_that(mailer.sesconn._connection[0], is_('email.us-east-1.amazonaws.com'))

                mailer = SESMailer('us-west-2')
                assert_that(mailer.sesconn._connection[0], is_('email.us-west-2.amazonaws.com'))

                mailer = SESMailer('bad-region')
                with assert_raises(AssertionError):
                        getattr(mailer, 'sesconn')

class TestMailerWatcher(unittest.TestCase):

        def setUp(self):
                self.dir = mkdtemp()
                self.queue_dir = os.path.join(self.dir, str("queue"))
                self.delivery = QueuedMailDelivery(self.queue_dir)
                self.maildir = Maildir(self.queue_dir, True)
                self.mailer = _makeMailerStub()

        def test_delivery(self):
                from email.message import Message
                from_addr = "foo@bar.foo"
                to_addr = "bar@foo.bar"
                message = Message()
                message['Subject'] = 'Pants'
                message.set_payload('Nice pants, mister!')

                import transaction
                transaction.manager.begin()
                self.delivery.send(from_addr, to_addr, message)
                self.delivery.send(from_addr, to_addr, message)
                transaction.manager.commit()

                assert_that(tuple(self.maildir), has_length(2))

                def _mailer_factory():
                        return self.mailer
                
                watcher = MailerWatcher(_mailer_factory, self.queue_dir)
                watcher.run(seconds=.1)

                assert_that(tuple(self.maildir), has_length(0))

                

                

                
