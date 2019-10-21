#!/Sr/bin/env python
# -*- coding: utf-8 -*-
"""
Mailing interfaces.

This package is based upon both :mod:`pyramid_mailer` and :mod:`repoze.sendmail`,
but the relevant parts are re-exported from this package.

.. $Id$
"""

from __future__ import print_function, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.schema import NativeStringLine

from zope.security.interfaces import IPrincipal

try:
    from pyramid_mailer.interfaces import IMailer
except ImportError:
    class IMailer(interface.Interface):
        pass
IMailer = IMailer  # [re]export, primarily for testing

try:
    from repoze.sendmail.interfaces import IMailDelivery
except ImportError:
    class IMailDelivery(interface.Interface):
        transaction_manager = interface.Attribute(u"The transaction manager to use.")

        def send(fromaddr, toaddrs, message):
            pass
IMailDelivery = IMailDelivery  # [re]export, primarily for testing

from nti.schema.field import TextLine
# pylint:disable=I0011,E0213


class IEmailAddressable(interface.Interface):
    """
    Something containing an email address. Commonly, when
    the object containing the email address represents a \"user\"
    of the system, it should also be adaptable to :class:`zope.security.interfaces.IPrincipal`.

    See :class:`.EmailAddressablePrincipal` for a simple serialization-safe
    example.
    """

    email = interface.Attribute(u"The email address to send to")


@interface.implementer(IEmailAddressable,
                       IPrincipal)
class EmailAddressablePrincipal(object):
    """
    An implementation of both :class:`IEmailAddressable`
    and :class:`IPrincipal` that combines both interfaces
    from something (a context) that is adaptable to both. Use this
    when the weight of the context is undesirable, such as during
    serialization (pickling), or when concurrency is a factor.

    This object copies the attributes from both interfaces into
    itself at construction time.
    """

    # These two attributes of IPrincipal aren't required
    title = None
    description = None

    def __init__(self, context):
        self.email = IEmailAddressable(context).email

        prin = IPrincipal(context)
        self.id = prin.id

        for name in 'title', 'description':
            prin_val = getattr(prin, name, None)
            if prin_val is not None:
                setattr(self, str(name), prin_val)

    def __str__(self):
        return str('Principal(%s/%s)' % (self.id, self.email))

    __repr__ = __str__


class ITemplatedMailer(interface.Interface):
    """
    An object, typically registered as a utility,
    that can handle putting together an email (having both
    text and HTML parts) by rendering templates.
    """

    def queue_simple_html_text_email(base_template,
                                     subject='',
                                     request=None,
                                     recipients=(),
                                     bcc=(),
                                     template_args=None,
                                     attachments=(),
                                     package=None,
                                     text_template_extension='.txt'):
        """
        Transactionally queues an email for sending. The email has both a
        plain text and an HTML version.

        :keyword recipients: A sequence of RFC822 email addresses as strings,
                or objects that can be adapted to an :class:`.IEmailAddressable`
                object. If no recipients are given, this does nothing. If any
                recipients are not strings, then if they cannot be adapted to
                :class:`.IEmailAddressable` or if the ``email`` attribute of the
                adapted object is false (none, empty) they will silently be dropped
                from the list. Objects that are :class:`.IEmailAddressable` should also
                (optionally) be able to become :class:`zope.security.interfaces.IPrincipal`
                by adaptation; this may permit us to construct a better (e.g., VERP)
                message.
        :keyword bcc: As for recipients.
        :keyword text_template_extension: The filename extension for the plain text template. Valid
                values are ".txt" for Chameleon templates (this is the
                default and preferred version) and ".mak" for Mako
                templates. Note that if you use Mako, the usual
                ``context`` argument is renamed to ``nti_context``, as
                ``context`` is a reserved word in Mako (this may change in the future).
        :keyword package: If given, and the template is not an absolute
                asset spec, then the template will be interpreted relative to this
                package (and its templates/ subdirectory if no subdirectory is specified).
                If no package is given, the package of the caller of this function is used.

        :return: The :class:`pyramid_mailer.message.Message` we sent, if we sent one,
                otherwise None.
        """

    def create_simple_html_text_email(base_template,
                                      subject='',
                                      request=None,
                                      recipients=(),
                                      template_args=None,
                                      attachments=(),
                                      package=None,
                                      bcc=(),
                                      text_template_extension='.txt'):
        """
        The same arguments and return types as :meth:`queue_simple_html_text_email`,
        but without the actual transactional delivery.
        """

    def do_html_text_templates_exist(base_template,
                                     text_template_extension='.txt',
                                     package=None):
        """
        A preflight method for checking if templates exist. Returns a True value
        if they do.
        """


class IVERP(interface.Interface):
    """
    Amazon SES now supports labels for `sending emails
    <http://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-email-addresses.html>`_,
    making it possible to do `VERP
    <https://en.wikipedia.org/wiki/Variable_envelope_return_path>`_,
    meaning we can directly identify the account we sent to (or even
    type of email) in case of a bounce. This requires using 'labels'
    and modifying the sending address: foo+label@domain.com. Note that
    SES makes no mention of the Sender header, instead putting the
    labels directly in the From line (which is what, for example,
    Facebook does) or in the Return-Path line (which is what trello
    does). However, SES only deals with the Return-Path header if you
    use its `API, not if you use SMTP
    <http://docs.aws.amazon.com/ses/latest/DeveloperGuide/notifications-via-email.html>`_
    """

    def realname_from_recipients(fromaddr, recipients, request=None):
        """
        This function takes a given From address and manipulates it to include
        a default realname, usually based on the current site and possibly
        the recipient list.

        Despite being located in the VERP module, this function does not actually
        do any signing.

        :return: The ``fromaddr``, guaranteed to be in \"Realname <to@example.com>\"
                format.
        """

    def verp_from_recipients(fromaddr, recipients, request=None):
        """
        This function takes a given from address and manipulates it to
        include VERP information that identifies the *accounts* of the
        recipients. For this to work, the recipients must initially be
        passed as things that can be adapted to `IEmailAddressable`
        objects; for those objects that can be adapted, then if they can
        be adapted to :class:`.IPrincipal`, we include the principal ID.

        In addition, if the `fromaddr` does not include a realname,
        adds a default.

        .. note:: We take the request as an argument because at some point
                we may want to include some notion of the sending site,
                although it's probably better to use separate SES/SNS queues
                if possible.

        :param fromaddr: The initial from address, without any labels,
                possibly including a realname portion.

        :return: The ``fromaddr``, manipulated to include a VERP
                label, if possible, identifying the principals related to the
                recipients and/or request.
        """

    def principal_ids_from_verp(fromaddr, request=None):
        """
        Decode the VERP information as encoded in :meth:`verp_from_recipients`,
        returning a sequence of positively-identified principal IDs for the current
        environment, if any.
        """


class IMailerPolicy(interface.Interface):
    """
    Mailer policy utility
    """

    DEFAULT_EMAIL_SENDER = TextLine(title=u'An optional email sender',
                                    description=u'An email address used to send emails to users'
                                                u'such as account creation, both on behalf of this'
                                                u'object as well as from other places. Optional.',
                                    required=False,
                                    default=None)


    NEW_USER_CREATED_EMAIL_TEMPLATE_BASE_NAME = NativeStringLine(title=u'The base template for sending '
                                                                       u'an email to a newly created user.',
                                                                 description=u'The asset spec for a template having both text and'
                                                                             u'HTML versions. If the asset spec is a bare name'
                                                                             u'like "foobar", it is assumed to be located in the'
                                                                             u'``templates`` directory in the package this object'
                                                                             u'is located in. Otherwise, it can be a complete spec'
                                                                             u'such as "the.package:other_dir/foobar"',
                                                                 default='nti.appserver:templates/new_user_created',
                                                                 required=False)

    NEW_USER_CREATED_EMAIL_SUBJECT = TextLine(title=u'The email subject for new user emails.',
                                              required=False,
                                              default=u'Welcome to NextThought')

    NEW_USER_CREATED_BCC = TextLine(title=u'The bcc address for new user emails.',
                                    default=None,
                                    required=False)

    PASSWORD_RESET_EMAIL_TEMPLATE_BASE_NAME = NativeStringLine(title=u'The base template for password reset emails.',
                                                               default='password_reset_email')

    PASSWORD_RESET_EMAIL_SUBJECT = TextLine(title=u'The subject for password reset emails.',
                                            default=u'NextThought Password Reset',
                                            required=False)

    SUPPORT_EMAIL = TextLine(title=u'The support email.',
                             default=u'support@nextthought.com',
                             required=False)

    USERNAME_RECOVERY_EMAIL_TEMPLATE_BASE_NAME = NativeStringLine(title=u'The base template for username recovery emails.',
                                                                  default='username_recovery_email',
                                                                  required=False)

    USERNAME_RECOVERY_EMAIL_SUBJECT = TextLine(title=u'The email subject for username recovery emails.',
                                               default=u'Username Reminder',
                                               required=False)
