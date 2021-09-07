#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
import os

from tempfile import mkdtemp

import unittest

import email

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_length
from hamcrest import none

import fudge


from repoze.sendmail.delivery import QueuedMailDelivery
from repoze.sendmail.maildir import Maildir

from repoze.sendmail.tests.test_delivery import _makeMailerStub

from nti.mailer.queue import SESMailer
from nti.mailer.queue import MailerWatcher

# pylint:disable=line-too-long
MSG_STRING = 'MIME-Version: 1.0\nFrom: NextThought <no-reply+70108544275840.qhjWPQ@nextthought.com>\nSubject: Welcome to NextThought\nTo: test.user@nextthought.com\nMessage-Id: <20140528152113.23368.67989.repoze.sendmail@nextthought.com>\nDate: Wed, 28 May 2014 15:21:13 -0000\nContent-Type: multipart/alternative;\n boundary="===============3015559400140931547=="\n\n--===============3015559400140931547==\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nContent-Disposition: inline\n\nHi=20Test=20User!\n\nThank=20you=20for=20creating=20your=20new=20account=20and=20welcome=20to=20=\nNextThought!\n\nUsername:=2070108544275840\nLog=20in=20at:=20https://alpha.nextthought.com\n\nNextThought=20offers=20interactive=20content=20and=20rich=20features=20to=\n=20make\nlearning=20both=20social=20and=20personal.=20Explore=20the=20NextThought=20=\nHelp=20Center\nin=20your=20Library=20to=20get=20started=20and=20learn=20more=20about=20the=\n=20exciting\ninteractive=20features=20NextThought=20has=20to=20offer.\n\nSincerely,\nNextThought\n\nIf=20you=20feel=20this=20email=20was=20sent=20in=20error,=20or=20this=20acc=\nount=20was=20created\nwithout=20your=20consent,=20you=20may=20email=20us=20at=20support@nextthoug=\nht.com.\n\n--===============3015559400140931547==\nContent-Type: text/html; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: quoted-printable\nContent-Disposition: inline\n\n<!DOCTYPE=20html=20PUBLIC=20"-//W3C//DTD=20XHTML=201.0=20Strict//EN"\n=09=20"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n<html=20xmlns=3D"http://www.w3.org/1999/xhtml">\n=09<head>\n=09=09<meta=20http-equiv=3D"content-type"=20content=3D"text/html;=20charset=\n=3Dutf-8"=20/>\n=09=09<title>Welcome=20To=20NextThought</title>\n=09=09<style>\n=09=09=09#green-bar=20{\n=09=09=09background-color:=20#89be3c;\n=09=09=09width:=20100%;\n=09=09=09height:=205px;\n=09=09=09margin-left:=20-30px;\n=09=09=09padding-right:=2040px;\n=09=09=09}\n=09=09=09#logo-bar=20{\n=09=09=09margin-top:=2020px;\n=09=09=09margin-bottom:=2030px;\n=09=09=09}\n=09=09=09body=20{\n=09=09=09margin-left:=2030px;\n=09=09=09margin-right:=200px;\n=09=09=09font-family:=20Helvetica,=20Arial,=20sans-serif;\n=09=09=09font-size:=2014pt;\n=09=09=09line-height:=2020pt;\n=09=09=09color:=20#757474;\n=09=09=09}\n=09=09=09.normal-text=20{\n=09=09=09margin-left:=2030px;\n=09=09=09margin-right:=200px;\n=09=09=09font-family:=20Helvetica,=20Arial,=20sans-serif;\n=09=09=09font-size:=2014pt;\n=09=09=09line-height:=2020pt;\n=09=09=09color:=20#757474;\n=09=09=09}\n=09=09=09a=20{\n=09=09=09text-decoration:=20none;\n=09=09=09color:=20#3fb3f6;\n=09=09=09}\n=09=09=09.tterm,=20strong=20{\n=09=09=09font-weight:=20bold;\n=09=09=09color:=20#494949;\n=09=09=09}\n=09=09=09.tterm-color=20{\n=09=09=09font-weight:=20bold;\n=09=09=09color:=20#3fb3f6;\n=09=09=09}\n=09=09=09h1,=20h2,=20h3,=20h4,=20h5,=20h6=20{\n=09=09=09font-weight:=20bold;\n=09=09=09font-family:=20Helvetica,=20Arial,=20sans-serif;\n=09=09=09color:=20#757474;\n=09=09=09margin-left:=2030px;\n=09=09=09}\n=09=09=09h1=20{\n=09=09=09font-size:=2016pt;\n=09=09=09}\n=09=09=09h2=20{\n=09=09=09font-size:=2014pt;\n=09=09=09}\n=09=09=09body=20p=20{\n=09=09=09margin-right:=2030px;\n=09=09=09margin-left:=2030px;\n=09=09=09font-family:=20Helvetica,=20Arial,=20sans-serif;\n=09=09=09font-size:=2014pt;\n=09=09=09line-height:=2020pt;\n=09=09=09color:=20#757474;\n=09=09=09}\n=09=09=09.pnormal-text=20{\n=09=09=09margin-left:=2030px;\n=09=09=09margin-right:=2030px;\n=09=09=09font-family:=20Helvetica,=20Arial,=20sans-serif;\n=09=09=09font-size:=2014pt;\n=09=09=09line-height:=2020pt;\n=09=09=09color:=20#757474;\n=09=09=09}\n=09=09</style>\n=09</head>\n=09<body>\n=09=09<div>\n=09=09=09<div=20id=3D"green-bar"=20style=3D"background-color:=20#89be3c;=20=\nwidth:=20100%;=20height:=205px;=20margin-left:=20-30px;=20padding-right:=20=\n40px;"></div>\n=09=09=09<div=20id=3D"logo-bar">\n=09=09=09=09<img=20src=3D"https://d2ixlfeu83tci.cloudfront.net/images/email=\n_logo.png"=20width=3D"177"=20height=3D"25"=20alt=3D"NextThought=20Logo"=20/>\n=09=09=09</div>\n=09=09=09\n=09=09=09\n=09=09=09\n=09=09=09\n=09=09</div>\n=09=09<p>Hi=20<span=20class=3D"realname=20tterm">Test=20User</span>!</p>\n\n=09=09<p>Thank=20you=20for=20creating=20your=20new=20account=20and=20welcom=\ne=20to=20NextThought!</p>\n\n=09=09<p>\n=09=09=09<strong>Username:</strong>=20<span=20class=3D"tterm-color">7010854=\n4275840</span>=20<br=20/>\n=09=09=09<strong>Log=20in=20at:</strong>=20<a=20href=3D"https://alpha.nextt=\nhought.com">https://alpha.nextthought.com</a>\n=09=09</p>\n=09=09<p>NextThought=20offers=20interactive=20content=20and=20rich=20featur=\nes=20to=20make=20learning=20both=20social=20and=20personal.=20Explore=20the=\n=20NextThought=20Help=20Center=20in=20your=20Library=20to=20get=20started=\n=20and=20learn=20more=20about=20the=20exciting=20interactive=20features=20N=\nextThought=20has=20to=20offer.</p>\n\n=09=09<p>\n=09=09=09<span>Sincerely,</span><br=20/>\n=09=09=09NextThought\n=09=09</p>\n\n=09=09<p=20style=3D"font-size:=20smaller">\n=09=09=09<span>If=20you=20feel=20this=20email=20was=20sent=20in=20error,=20=\nor=20this=20account=20was=20created=20without=20your=20consent,=20you=20may=\n=20email=20us=20at=20<a=20href=3D"mailto:mailto:support@nextthought.com">su=\npport@nextthought.com</a></span>\n=09=09</p>\n\n=09</body>\n</html>\n\n--===============3015559400140931547==--\n'

MSG_BYTES = MSG_STRING if isinstance(MSG_STRING, bytes) else MSG_STRING.encode('ascii')

class TestMailer(unittest.TestCase):

    def setUp(self):
        super(TestMailer, self).setUp()
        self.message = email.message_from_string(MSG_STRING)

    def test_region(self):
        # Defaults to us-east-1
        mailer = SESMailer()

        assert_that(mailer.client.meta.endpoint_url, is_('https://email.us-east-1.amazonaws.com'))

        mailer = SESMailer('us-west-2')
        assert_that(mailer.client.meta.endpoint_url, is_('https://email.us-west-2.amazonaws.com'))

        mailer = SESMailer('bad-region')
        # XXX: Mocking this out because if you have .boto credentials
        # set up, this actually tries to connect, which (a) takes
        # awhile if there's no response and (b) could expose you to
        # hijacking of credentials
        class MyException(Exception):
            pass
        def call(*args):
            raise MyException

        mailer.client._make_api_call = call
        with self.assertRaises(MyException):
            mailer.client.get_send_quota()

    def test_send(self):
        mailer = SESMailer()

        send_kwargs = {}

        def send_raw_email(*_args, **kwargs):
            send_kwargs.update(kwargs)

        mailer.client = fudge.Fake('SESClient')
        mailer.client.provides('send_raw_email').calls(send_raw_email)

        mailer.send('from', ('to',), self.message)

        encoded_msg_sent = send_kwargs['RawMessage']['Data']
        sent_msg_str = (
            encoded_msg_sent.decode('ascii')
            if not isinstance(encoded_msg_sent, str)
            else encoded_msg_sent
        )
        # In order to get reasonable error messages, we want to do a line-wise
        # comparison. Moreover, Python 3 and Python 2 produce slightly different
        # line breaks and spacing. This is the case in headers: Python 3
        # likes to add extra line breaks if a header value is too long (so we
        # shortened the Message-Id value to avoid that); Python 2 did that for the
        # Content-Type header, but for whatever reason Python 3 re-combines that
        # line.
        self.maxDiff = None
        def prep_lines(msg_str):
            msg_str = msg_str.replace('\n boundary=', ' boundary=')
            result = [
                x.strip()
                for x in msg_str.splitlines()
            ]
            return result
        self.assertEqual(prep_lines(sent_msg_str), prep_lines(MSG_STRING))


class TestLoopingMailerProcess(unittest.TestCase):

    def setUp(self):
        self.dir = mkdtemp()
        self.queue_dir = os.path.join(self.dir, "queue")
        self.delivery = QueuedMailDelivery(self.queue_dir)
        self.maildir = Maildir(self.queue_dir, True)
        self.mailer = _makeMailerStub()
        self.queued_count = 0

    def _getFUT(self):
        from nti.mailer.queue import LoopingMailerProcess
        class FUT(LoopingMailerProcess):
            def _sleep_after_run(self, _seconds):
                self._exit = True

        return FUT

    def _makeOne(self):
        result = self._getFUT()(lambda: self.mailer, self.queue_dir)
        self.addCleanup(result.close)
        return result

    def _runOnce(self, proc):
        proc.run()

    def _queue_two_messages(self):
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
        self.queued_count += 2
        transaction.manager.commit()

        assert_that(tuple(self.maildir), has_length(2))

    def test_delivery_messages_already_present(self):
        self._queue_two_messages()
        watcher = self._makeOne()
        self._runOnce(watcher)
        assert_that(tuple(self.maildir), has_length(0))


class TestMailerWatcher(TestLoopingMailerProcess):

    def _getFUT(self):
        # This makes a one-shot object
        class FUT(MailerWatcher):
            # The timer that's started with this timeout will
            # keep the loop alive. So keep it short.
            max_process_frequency_seconds = 0.1
            test_queue_proc_count = 0
            test_timer_fired_count = 0
            test_one_shot = True

            def _youve_got_mail(self):
                super(FUT, self)._youve_got_mail()
                # Deterministically close this down now so the event
                # loop can exit, but only after we've actually
                # processed something (this prevents hardcoding some
                # timeout to wait for the watcher to fire) If this is
                # messed up, the test will hang or fail.
                if self.test_one_shot:
                    self.close()
            def _do_process_queue(self):
                self.test_queue_proc_count += 1
                super(FUT, self)._do_process_queue()
            def _timer_fired(self):
                self.test_timer_fired_count += 1
                super(FUT, self)._timer_fired()

        return FUT

    def _runOnce(self, proc):
        proc.run(seconds=0.1)

    def test_delivery_messages_arrive_while_waiting(self):
        import gevent
        # Next time we yield to the hub, this will get called.
        def q():
            # Sleep in case our stat watcher has
            # very poor mtime resolution; we don't want a false
            # negative in our detection. For libuv watchers,
            # 0.5 seems to be enough. But for libev watchers on GHA,
            # we need a full second. Do this ahead of time, non-blocking,
            # so the stat watcher has a chance to get a before-time
            gevent.sleep(0.5)
            self._queue_two_messages()


        gevent.spawn(q)

        # Some systems are very slow to detect changes. Notably,
        # libev on Darwin (macOS 10.15.7 on APFS) can take several
        # seconds to observe the change (5 -- 7); libuv finds it
        # very quickly, usually.
        mailer = self._makeOne()

        assert_that(self.queued_count, is_(0))
        mailer.run()
        assert_that(self.queued_count, is_(2))
        # Ran twice: Once for the call to run(), once for the
        # watcher.
        assert_that(mailer.test_queue_proc_count, is_(2))
        assert_that(tuple(self.maildir), has_length(0))
        self.assertFalse(mailer.watcher.active)
        assert_that(mailer.debouncer, is_(none()))
        assert_that(mailer.debouncer_count, is_(0))

    def test_debouncer_basic(self):
        # This isn't a very functional test, it doesn't prove
        # much beyond the code as written interacts roughly as
        # expected.
        import gevent
        mailer = self._makeOne()
        mailer.test_one_shot = False
        mailer._youve_got_mail()
        self.assertTrue(mailer.debouncer.active)
        assert_that(mailer.debouncer_count, is_(0))
        assert_that(mailer.test_queue_proc_count, is_(1))
        orig_debouncer = mailer.debouncer

        # Now imagine we get mail before the timer fires.
        # It doesn't process the mail
        mailer._youve_got_mail()
        assert_that(mailer.debouncer_count, is_(1))
        assert_that(mailer.test_queue_proc_count, is_(1))
        assert_that(mailer.test_timer_fired_count, is_(0))
        self.assertIs(mailer.debouncer, orig_debouncer)

        # Now let the timer fire
        while mailer.test_timer_fired_count == 0:
            gevent.sleep(0.01)

        # The debouncer count reset, as did the debouncer instance
        assert_that(mailer.debouncer_count, is_(0))
        self.assertIsNot(mailer.debouncer, orig_debouncer)
        # The queue was processed again
        assert_that(mailer.test_queue_proc_count, is_(2))
        assert_that(mailer.test_timer_fired_count, is_(1))



class TestFunctions(unittest.TestCase):

    def test_stat_modified_time(self):
        from nti.mailer.queue import _stat_modified_time
        class Watcher1(object):
            st_mtime = 42

        assert_that(_stat_modified_time(Watcher1()), is_(42))

        class Watcher2(object):
            class st_mtim(object):
                tv_sec = 36
                tv_nsec = 24

        assert_that(_stat_modified_time(Watcher2()), is_((36, 24)))

    def test_stat_watcher_modified(self):
        from nti.mailer.queue import _stat_watcher_modified
        class Watcher(object):
            class prev(object):
                st_mtime = 42
            class attr(object):
                st_mtime = 42

        self.assertFalse(_stat_watcher_modified(Watcher()))

        Watcher.prev.st_mtime = 36
        self.assertTrue(_stat_watcher_modified(Watcher()))

    def test_log_level_for_verbosity(self):
        import logging
        from nti.mailer.queue import _log_level_for_verbosity as FUT
        assert_that(FUT(-1), is_(logging.ERROR))
        assert_that(FUT(0), is_(logging.ERROR))
        assert_that(FUT(1), is_(logging.WARN))
        assert_that(FUT(2), is_(logging.INFO))
        assert_that(FUT(3), is_(logging.DEBUG))
        assert_that(FUT(4), is_(logging.DEBUG))
        assert_that(FUT(5), is_(logging.DEBUG))
        assert_that(FUT(6), is_(logging.DEBUG))

class TestConsoleApp(unittest.TestCase):

    def test_construct(self):
        from nti.mailer.queue import ConsoleApp
        import tempfile
        args = ['console', tempfile.gettempdir()]
        app = ConsoleApp(args)
        assert_that(app.mailer, is_(SESMailer))
