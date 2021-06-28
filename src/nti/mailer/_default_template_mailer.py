#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions having to do with sending emails.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from premailer import transform

from pyramid.compat import is_nonstr_iter

from pyramid.path import caller_package

from pyramid.renderers import render
from pyramid.renderers import get_renderer

from pyramid.threadlocal import get_current_request

from pyramid_mailer.message import Message

from six import string_types

from zope import component
from zope import interface

from zope.dottedname import resolve as dottedname

from nti.mailer.interfaces import IVERP
from nti.mailer.interfaces import IMailer
from nti.mailer.interfaces import IMailDelivery
from nti.mailer.interfaces import IMailerPolicy
from nti.mailer.interfaces import ITemplatedMailer
from nti.mailer.interfaces import IEmailAddressable
from nti.mailer.interfaces import IPrincipalEmailValidation
from nti.mailer.interfaces import IMailerTemplateArgsUtility

logger = __import__('logging').getLogger(__name__)


def _get_renderer_spec_and_package(base_template,
                                   extension,
                                   package=None,
                                   level=3):
    if isinstance(package, string_types):
        package = dottedname.resolve(package)

    # Did they give us a package, either in the name or as an argument?
    # If not, we need to get the right package
    if ':' not in base_template and package is None:
        # 2 would be our caller, aka this module.
        package = caller_package(level)
    # Do we need to look in a subdirectory?
    if ':' not in base_template and '/' not in base_template:
        base_template = 'templates/' + base_template

    return base_template + extension, package


def _get_renderer(base_template,
                  extension,
                  package=None,
                  level=3):
    """
    Given a template name, find a renderer for it.
    For template name, we accept either a relative or absolute
    asset spec. If the spec is relative, it can be 'naked', in which
    case it is assummed to be in the templates sub directory.

    This *must* only be called from this module due to assumptions
    about the call tree.
    """

    template, package = _get_renderer_spec_and_package(base_template,
                                                       extension,
                                                       package=package,
                                                       level=level + 1)

    return get_renderer(template, package=package)


def do_html_text_templates_exist(base_template,
                                 text_template_extension='.txt',
                                 package=None,
                                 _level=3):
    """
    A preflight method for checking if templates exist. Returns a True value
    if they do.
    """
    try:
        _get_renderer(base_template, '.pt', package=package, level=_level)
        _get_renderer(base_template, text_template_extension,
                      package=package, level=_level)
    except ValueError:
        # Pyramid raises this if the template doesn't exist
        return False
    return True


def _as_recipient_list(recipients):
    # XXX: Perhaps we should enforce a certain kwarg to ensure we always get
    # users here. We definitely prefer it since we can enforce we do not send
    # to bounced addresses. In some cases, we only have raw email addresses.
    # Currently, we'll just ignore those users with invalid addresses.
    result = []
    if recipients:
        # accept a raw string
        recipients = recipients if is_nonstr_iter(recipients) else [recipients]
        for recipient in recipients:
            # If we have a principal object, explicitly check if `is_valid_email`.
            email_validation = IPrincipalEmailValidation(recipient, None)
            if      email_validation is not None \
                and not email_validation.is_valid_email():
                continue
            # Convert any IEmailAddressable into their email, and strip
            # empty strings
            recipient = getattr(IEmailAddressable(recipient, recipient), 'email', recipient)
            if isinstance(recipient, string_types) and recipient:
                result.append(recipient)
    return result

as_recipient_list = _as_recipient_list

def create_simple_html_text_email(base_template,
                                  subject='',
                                  request=None,
                                  recipients=(),
                                  template_args=None,
                                  reply_to=None,
                                  attachments=(),
                                  package=None,
                                  cc=(),
                                  bcc=(),
                                  text_template_extension='.txt',
                                  _level=3):
    """
    Create a :class:`pyramid_mailer.message.Message` by rendering
    the pair of templates to create a text and html part.

    :keyword text_template_extension: The filename extension for the plain text template. Valid values
            are ".txt" for Chameleon templates (this is the default and preferred version) and ".mak" for
            Mako templates. Note that if you use Mako, the usual ``context`` argument is renamed to ``nti_context``,
            as ``context`` is a reserved word in Mako.
    :keyword package: If given, and the template is not an absolute
            asset spec, then the template will be interpreted relative to this
            package (and its templates/ subdirectory if no subdirectory is specified).
            If no package is given, the package of the caller of this function is used.
    """

    recipients = _as_recipient_list(recipients)

    if not recipients:
        logger.info("Refusing to attempt to send email with no recipients")
        return
    if not subject:
        # Should the subject already be localized or should we do that?
        logger.info("Refusing to attempt to send email with no subject")
        return

    if request is None:
        request = get_current_request()

    cc = _as_recipient_list(cc)
    bcc = _as_recipient_list(bcc)

    def make_args(extension):
        # Mako gets bitchy if 'context' comes in as an argument, but
        # that's what Chameleon wants. To simplify things, we handle that
        # for our callers. They just want to use 'context'.
        # This should be fixed with 1.0a2
        the_context_name = 'nti_context' if extension == text_template_extension and text_template_extension != '.txt' else 'context'
        result = {}
        if request:
            result[the_context_name] = getattr(request, 'context', None)
        if template_args:
            result.update(template_args)

        if the_context_name == 'nti_context' and 'context' in template_args:
            result[the_context_name] = template_args['context']
            del result['context']
        for args_utility in component.getAllUtilitiesRegisteredFor(IMailerTemplateArgsUtility):
            result.update(args_utility.get_template_args(request))
        return result

    def do_render(pkg):
        specs_and_packages = [_get_renderer_spec_and_package(base_template,
                                                             extension,
                                                             package=pkg,
                                                             level=_level + 1) + (extension,)
                              for extension in ('.pt', text_template_extension)]

        return [render(spec,
                       make_args(extension),
                       request=request,
                       package=pkg)
                for spec, pkg, extension in specs_and_packages]

    try:
        html_body, text_body = do_render(package)
    except ValueError as e:
        # This is just to handle the case where the
        # site specifies a package, but wants to use
        # a default template in some cases.
        if package is None:
            raise e
        # Ok, let's try to find the package.
        html_body, text_body = do_render(None)

    # Email clients do not handle CSS well unless it's inlined.
    # This can be expensive (~.4s per email) if users interactively
    # trigger large numbers of emails. In that case, the email is
    # probably better off created with inlined styles.
    html_body = transform(html_body)

    # PageTemplates (Chameleon and Z3c.pt) produce Unicode strings.
    # Under python2, at least, the text templates (Chameleon alone) produces byte objects,
    # (JAM: TODO: Can we make it stay in the unicode realm? Pyramid config?)
    # (JAM: TODO: Not sure about what Mako does?)
    # apparently encoded as UTF-8, which is not ideal. This either is
    # a bug itself (we shouldn't pass non-ascii values as text/plain)
    # or triggers a bug in pyramid mailer when it tries to figure out the encoding,
    # leading to a UnicodeError.
    # The fix is to supply the charset parameter we want to encode as;
    # Or we could decode it ourself, which lets us use the optimal encoding
    # pyramid_mailer picks...we ignore errors
    # here to make sure that we can send /something/
    if isinstance(text_body, bytes):
        text_body = text_body.decode('utf-8', 'replace')

    # JAM: Why are we quoted-printable encoding? That produces much bigger
    # output...whether we do it like this, or simply pass in the unicode
    # strings, we get quoted-printable. We would pass Attachments if we
    # wanted to specify the charset (see above)
    # message = Message( subject=subject,
    # 				   recipients=recipients,
    # 				   body=Attachment(data=text_body, disposition='inline',
    # 								   content_type='text/plain',
    # 								   transfer_encoding='quoted-printable'),
    # 				   html=Attachment(data=html_body, disposition='inline',
    # 								   content_type='text/html',
    # 								   transfer_encoding='quoted-printable') )
    message = Message(subject=subject,
                      recipients=recipients,
                      body=text_body,
                      html=html_body,
                      cc=cc,
                      bcc=bcc,
                      attachments=attachments)

    if reply_to:
        message.extra_headers['Reply-To'] = reply_to

    return message


def queue_simple_html_text_email(*args, **kwargs):
    """
    Transactionally queues an email for sending. The email has both a
    plain text and an HTML version.

    :keyword text_template_extension: The filename extension for the plain text template. Valid values
            are ".txt" for Chameleon templates (this is the default and preferred version) and ".mak" for
            Mako templates. Note that if you use Mako, the usual ``context`` argument is renamed to ``nti_context``,
            as ``context`` is a reserved word in Mako.

    :keyword message_factory: A callable, called with the same arguments
            passed to this function to create a
            :class:`pyramid_mailer.message.Message` by rendering the pair
            of templates to create a text and html part.

    :return: The :class:`pyramid_mailer.message.Message` we sent.
    """

    kwargs = dict(kwargs)
    if '_level' not in kwargs:
        kwargs['_level'] = 4
    message_factory = kwargs.pop('message_factory', create_simple_html_text_email)
    message = message_factory(*args, **kwargs)
    # There are cases where this will be none (bounced email handling, missing
    # subject - error?). In at least the bounced email case, we want to avoid
    # sending the email and erroring.
    if message is None:
        return
    return _send_pyramid_mailer_mail(message,
                                     recipients=kwargs.get('recipients'),
                                     request=kwargs.get('request'))


def _send_pyramid_mailer_mail(message, recipients=None, request=None):
    """
    Given a :class:`pyramid_mailer.message.Message`, transactionally deliver
    it to the queue.

    :return: The :class:`pyramid_mailer.message.Message` we sent.
    """
    # The pyramid_mailer.Message class is slightly nicer than the
    # email package messages, if much less powerful. However, it makes the
    # mistake of using different methods for send vs send_to_queue.
    # It is built of top of repoze.sendmail and an IMailer contains two instances
    # of repoze.sendmail.interfaces.IMailDelivery, one for queue and one
    # for immediate, and those objects do the real work and also have a consistent
    # interfaces. It's easy to change the pyramid_mail message into a email
    # message
    _send_mail(pyramid_mail_message=message,
               recipients=recipients, request=request)
    return message


def _compute_from(*args, **kwargs):
    verp = component.queryUtility(IVERP)
    if verp is None:
        from . import _verp
        verp = _verp
    return verp.verp_from_recipients(*args, **kwargs)


def _get_from_address(pyramid_mail_message, recipients, request):
    """
    Get a valid `From`/`Sender`/`Return-Path` address. This field is required and
    must be from a verified email address (e.g. @nextthought.com).
    """
    pyramidmailer = component.queryUtility(IMailer)
    if request is None:
        request = get_current_request()

    fromaddr = getattr(pyramid_mail_message, 'sender', None)

    if not fromaddr:
        # Can we get a site policy for the current site?
        # It would be the unnamed IComponents
        policy = component.queryUtility(IMailerPolicy)
        if policy:
            fromaddr = policy.get_default_sender()
    if not fromaddr:
        fromaddr = getattr(pyramidmailer, 'default_sender', None)

    if not fromaddr:
        raise RuntimeError("No one to send mail from")

    result = _compute_from(fromaddr, recipients, request)
    return result


def _pyramid_message_to_message(pyramid_mail_message, recipients, request):
    """
    Preps a pyramid message for sending, including adjusting its sender if needed.

    :return:
    """
    assert pyramid_mail_message is not None

    fromaddr = _get_from_address(pyramid_mail_message, recipients, request)

    pyramid_mail_message.sender = fromaddr
    # Sadly, as of 2014-05-22, Amazon SES (and some other SMTP relays, actually, if I understand
    # correctly) don't support setting Sender or Return-Path. They get ignored.
    # (At least for SES, this is because it need to set the Return-Path value
    # to something it controls in order to handle stateful retry logic, and delivery
    # to correct bounce queue, etc:
    #	  Return-Path: <000001462444a009-cfdcd8ed-008e-4bee-9ea7-30a47b615e64-000000@amazonses.com>
    # )
    # If this did work, we could leave the From address alone.
    # pyramid_mail_message.extra_headers['Sender'] = fromaddr
    # pyramid_mail_message.extra_headers['Return-Path'] = fromaddr
    message = pyramid_mail_message.to_message()
    return message


def _send_mail(pyramid_mail_message=None, recipients=(), request=None):
    """
    Sends a message transactionally.
    """
    assert pyramid_mail_message is not None
    pyramidmailer = component.queryUtility(IMailer)

    message = _pyramid_message_to_message(
        pyramid_mail_message, recipients, request
    )

    delivery = component.queryUtility(IMailDelivery) \
            or getattr(pyramidmailer, 'queue_delivery', None)
    if delivery:
        delivery.send(pyramid_mail_message.sender,
                      pyramid_mail_message.send_to,
                      message)
    elif pyramidmailer and pyramid_mail_message:
        pyramidmailer.send_to_queue(pyramid_mail_message)
    else:
        raise RuntimeError("No way to deliver message")


interface.moduleProvides(ITemplatedMailer)
