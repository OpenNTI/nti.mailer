#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Processors for :mod:`repoze.sendmail`, intended as a drop-in replacement
for the ``qp`` command line, using Amazon SES.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent

import os

import time

from zope import interface

import smtplib

from email.message import Message

import boto.ses
from boto.ses.exceptions import SESAddressBlacklistedError

from repoze.sendmail.encoding import encode_message

from repoze.sendmail.interfaces import IMailer

from repoze.sendmail.maildir import Maildir

from repoze.sendmail.queue import ConsoleApp as _ConsoleApp
from repoze.sendmail.queue import QueueProcessor

from zope.cachedescriptors.property import Lazy


@interface.implementer(IMailer)
class SESMailer(object):
    """
    This object does not handle throttling or quata actions;
    see also :mod:`nti.app.bulkemail.process`.
    """

    def __init__(self, region='us-east-1'):
        self.region=region

    @Lazy
    def sesconn(self):
        conn = boto.ses.connect_to_region(self.region)
        assert conn
        return conn

    def close(self):
        # Close it if we have it, but don't connect trying to close
        try:
            _sesconn = self.__dict__.pop('sesconn')
            _sesconn.close()
        except KeyError:
            pass

    def send(self, fromaddr, toaddrs, message):
        if not isinstance(message, Message):  # pragma: no cover
            raise ValueError('Message must be instance of email.message.Message')

        message = encode_message(message)

        # Send the mail using SES, transforming SESError and known
        # subclasses into something the SMTP-based queue processor knows
        # how to deal with.
        # NOTE: now that we're here, we have the opportunity to de-VERP
        # the fromaddr found in the message, but still use the VERP form
        # in the fromaddr we pass to SES. In this way we can handle bounces
        # with the recipient none-the-wiser. See also :mod:`nti.app.bulkemail.process`
        # NOTE: Each recipient (To, CC, BCC) counts as a distinct message
        # for purposes of the quota limits. There are a maximum of
        # 50 dests per address. (http://docs.aws.amazon.com/ses/latest/APIReference/API_SendRawEmail.html)
        # NOTE: It is recommended to send an email to individuals:
        # http://docs.aws.amazon.com/ses/latest/DeveloperGuide/sending-email.html
        # "When you send an email to multiple recipients (recipients
        # are "To", "CC", and "BCC" addresses) and the call to Amazon
        # SES fails, the entire email is rejected and none of the
        # recipients will receive the intended email. We therefore
        # recommend that you send an email to one recipient at a time."

        # QQQ: The docs for SendRawEmail say that destinations is not required,
        # so how does that interact with what's in the message body?
        # Boto will accept either a string, a list of strings, or None
        try:
            self.sesconn.send_raw_email(message, fromaddr, toaddrs)
        except SESAddressBlacklistedError:
            # A permanent error, cause the processor
            # to ditch the message
            raise smtplib.SMTPResponseException(553, 'Blacklisted address')


import argparse
import sys
import logging

class ConsoleApp(_ConsoleApp):

    def __init__(self, argv=None):  # pylint: disable=unused-argument
        if argv is None:
            argv = sys.argv
        # Bypass the superclass, don't try to construct an SMTP mailer
        self.script_name = argv[0]
        self._process_args(argv[1:])
        self.mailer = SESMailer()
        getattr(self.mailer, 'sesconn')


class MailerProcess(object):
    """
    A mailer processor that dumps the queue on a provided interval.
    """

    _exit = False
    
    def __init__(self, mailer_factory, queue_path, sleep_seconds=120):  # pylint: disable=unused-argument
        self.mailer_factory = mailer_factory
        self.sleep_seconds = sleep_seconds
        self.queue_path = queue_path
        self.mail_dir = Maildir(self.queue_path, create=True)

    def _maildir_factory(self, *args, **kwargs):
        return self.mail_dir

    def _do_process_queue(self):
        mailer = self.mailer_factory()
        assert mailer
        try:               
            processor = QueueProcessor(mailer,
                                       self.queue_path, # Note this gets ignored by the Maildir factory we send
                                       Maildir=self._maildir_factory)
            logger.info('Processing messages %s' % (processor.maildir.path))
            processor.send_messages()
        finally:
            try:
                mailer.close()
            except AttributeError:
                pass
            mailer = None

    def run(self):
        while not self._exit:
            self._do_process_queue()
            logger.debug('Going to sleep for %i seconds' % (self.sleep_seconds))
            time.sleep(self.sleep_seconds)

class MailerWatcher(MailerProcess):
    """
    A Mailer processor that watches for changes in the mail directory
    using gevent stat watchers.
    """
    watcher = None
    debouncer = None
    debouncer_count = 0

    max_process_frequency_seconds = 10

    def __init__(self, *args, **kwargs):
        super(MailerWatcher, self).__init__(*args, **kwargs)
        hub = gevent.get_hub()
        to_watch = os.path.join(self.queue_path, str('new'))
        self.watcher = hub.loop.stat(to_watch)

    def _start_watching(self):
        assert self.watcher
        logger.debug('Starting watcher for MailDir %s', self.watcher.path)
        self.watcher.start(self._stat_change_observed)

    def _stop_watching(self):
        assert self.watcher
        logger.debug('Stopping watcher for MailDir %s', self.watcher.path)
        self.watcher.stop()

    def _do_process_queue(self):
        # The path we are watching has been modified
        #self._stop_watching()
        super(MailerWatcher, self)._do_process_queue()
        #self._start_watching()

    def _youve_got_mail(self):
        # We've detected we have mail. We want to debounce
        # this so we aren't going crazy. Process the queue at most ever
        # self.max_process_frequency_seconds
        # We use a gevent timer to accomplish this.

        hub = gevent.get_hub()
        if self.debouncer is None:
            self.debouncer = hub.loop.timer(self.max_process_frequency_seconds)

        def _timer_fired(self):
            self.debouncer.stop()
            self.debouncer = None
            if self.debouncer_count > 0:
                self.debouncer_count = 0
                self._youve_got_mail()

        if self.debouncer.active is False:
            self.debouncer_count = 0
            self.debouncer.start(_timer_fired, self)
            logger.info('Processing mail queue. Queue processing paused for %i seconds', self.max_process_frequency_seconds)
            self._do_process_queue()
        else:
            self.debouncer_count += 1
            logger.debug('Deferring queue processing because it was run recently')
            

    def _stat_change_observed(self):
        # On certain file systems we will see stat changes
        # for access times which we don't care about. We really
        # only care about modified times ``st_mtime``
        if self.watcher.prev.st_mtime != self.watcher.attr.st_mtime:
            logger.debug('Maildir watcher detected "st_mtime" change')
            self._youve_got_mail()

    def run(self):
        # Process once initially in case we have things in the queue already
        self._do_process_queue()

        # Note we don't call start watching because _do_process_queue handles that
        self._start_watching()
        gevent.get_hub().join()

def run_process():  # pragma NO COVERAGE
    logging.basicConfig(stream=sys.stderr, format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Run a process that processes the mail queue on some interval')
    parser.add_argument('queue_path', help='The path to the maildir', action='store')
    parser.add_argument('-r', '--sesregion', help='The SES region to connect to.')
    arguments = parser.parse_args()
    
    _mailer_factory = SESMailer if not arguments.sesregion else (lambda: SESMailer(arguments.sesregion))
    
    app = MailerWatcher(_mailer_factory, arguments.queue_path)
    app.run()

def run_console():  # pragma NO COVERAGE
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    app = ConsoleApp()
    app.main()


if __name__ == "__main__":  # pragma NO COVERAGE
    run_console()
