#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions having to do with sending emails.

This module provides the :class:`nti.mailer.interfaces.ITemplatedMailer` interface.
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import warnings

from premailer import transform

from pyramid.path import caller_package

from pyramid.renderers import render
from pyramid.renderers import get_renderer

from pyramid.threadlocal import get_current_request

from pyramid_mailer.message import Message

from six import string_types

from zope import component
from zope import interface

from zope.dottedname import resolve as dottedname
# Because zope.i18n is a package, importing a name defined in its
# __init__.py can be tricky.
import zope.i18n
from zope.i18n.interfaces import IUserPreferredLanguages


from nti.mailer.interfaces import IVERP
from nti.mailer.interfaces import IMailer
from nti.mailer.interfaces import IMailDelivery
from nti.mailer.interfaces import IMailerPolicy
from nti.mailer.interfaces import ITemplatedMailer
from nti.mailer.interfaces import IEmailAddressable
from nti.mailer.interfaces import IPrincipalEmailValidation
from nti.mailer.interfaces import IMailerTemplateArgsUtility

from nti.mailer._compat import is_nonstr_iter

from nti.mailer import _verp as default_verp

logger = __import__('logging').getLogger(__name__)
translate = zope.i18n.translate

@interface.implementer(IMailerPolicy)
class _DefaultMailerPolicy(object):
    """
    Returns the default answers we want to use if there is
    no component implementing IMailerPolicy that can be found.
    """

    def get_default_sender(self):
        """There is no default sender."""
        return None


default_mailer_policy = _DefaultMailerPolicy()


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

_marker = object()

def _make_template_args(
        request,
        context,
        extension,
        text_template_extension,
        existing_template_args
):
    # Mako gets bitchy if 'context' comes in as an argument, but
    # that's what Chameleon wants. To simplify things, we handle that
    # for our callers. They just want to use 'context'.
    # This should be fixed with 1.0a2
    the_context_name = (
        'nti_context'
        if extension == text_template_extension and text_template_extension != '.txt'
        else 'context'
    )
    result = {}
    result[the_context_name] = context
    result.update(existing_template_args)

    # Because the "correct" name for the context variable cannot be known
    # by the ``IMailerTemplateArgsUtility``, they should not attempt to
    # set it. Thus, we are always correct using our *context* value we
    # discovered above, except in the mismatch case.
    if the_context_name == 'nti_context' and 'context' in existing_template_args:
        result[the_context_name] = existing_template_args['context']
        del result['context']
    for args_utility in component.getAllUtilitiesRegisteredFor(IMailerTemplateArgsUtility):
        result.update(args_utility.get_template_args(request))
    return result


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
                                  context=_marker,
                                  _level=3):
    """
    Create a :class:`pyramid_mailer.message.Message` by rendering
    the pair of templates to create a text and html part.

    :keyword str text_template_extension:
        The filename extension for the plain text template. Valid
        values are ".txt" for Chameleon templates (this is the default
        and preferred version) and ".mak" for Mako templates. Note
        that if you use Mako, the usual ``context`` argument is
        renamed to ``nti_context``, as ``context`` is a reserved word
        in Mako.
    :keyword package:
        If given, and the template is not an absolute asset spec, then
        the template will be interpreted relative to this package (and
        its templates/ subdirectory if no subdirectory is specified).
        If no package is given, the package of the caller of this
        function is used.

    .. versionchanged:: 0.0.1
        Now, if the *subject* is a :class:`zope.i18nmessageid.Message`, it will
        be translated.
    .. versionchanged:: 0.0.1
        Added the *context* argument. If this argument is not supplied, the
        value of ``request.context`` will be used. As a last resort, ``template_args['context']
        will be used. (If both *context* or ``request.context`` and a template argument value
        are given, they should be the same object.)
    """

    recipients = _as_recipient_list(recipients)

    if not recipients:
        logger.info("Refusing to attempt to send email with no recipients")
        return None
    if not subject:
        logger.info("Refusing to attempt to send email with no subject")
        return None

    request = request if request is not None else get_current_request()

    if context is _marker and request is not None:
        try:
            context = request.context
        except AttributeError:
            pass

    template_args = template_args or {}
    if context is _marker:
        context = template_args.get('context', None)

    assert context is not _marker
    template_args.setdefault('context', context)

    if (
            'context' in template_args
            and context is not None
            and context is not template_args['context']
    ):
        warnings.warn(
            "Mismatch between the explicit context and the template_args context. "
            "In the future this might be an error. Currently, one will be used for translation "
            "and one will be used in the template.",
            stacklevel=2
        )

    cc = _as_recipient_list(cc)
    bcc = _as_recipient_list(bcc)
    # If the *context* is None, and no ``target_language`` is provided, the
    # translate utility won't try to negotiate a language. In that case, we
    # try to use the request as the context.
    # See nti.app.pyramid_zope.i18n for details on negotiation: In summary,
    # the default INegotiator from zope.i18n.negotiator adapts the context to
    # IUserPreferredLanguages and then tries to find one of those in the catalog.
    # We have registrations that turn the request into an IUserPreferredLanguages
    # based on the Accept headers.
    #
    # (Determining the context is all subject to change.)
    try:
        subject = translate(subject, context=context if context is not None else request)
    except TypeError as ex:
        if (
                context is not None
                and len(ex.args) >= 3
                and ex.args[2] == IUserPreferredLanguages
        ):
            # We tried to use the *context* argument, but there is no adapter for it.
            # fallback to using the request.
            logger.info("Failed to find adapter to translate the subject %r: %s",
                        subject, ex)
            subject = translate(subject, context=request)
        else: # pragma: no cover
            raise

    def do_render(pkg):
        # XXX: Factor this out to a testable function.
        # The primary difficulty is the assumed `level` parameter.
        specs_and_packages = [_get_renderer_spec_and_package(base_template,
                                                             extension,
                                                             package=pkg,
                                                             level=_level + 1) + (extension,)
                              for extension in ('.pt', text_template_extension)]

        return [render(spec,
                       _make_template_args(request, context,
                                           extension, text_template_extension,
                                           template_args),
                       request=request,
                       package=pkg)
                for spec, pkg, extension in specs_and_packages]

    try:
        html_body, text_body = do_render(package)
    except ValueError: # pragma: no cover
        # This is just to handle the case where the
        # site specifies a package, but wants to use
        # a default template in some cases. This is kind of a
        # scary case.
        # XXX: Is it even used? It's not tested. We should probably
        # raise a deprecation warning.
        if package is None:
            raise
        # Ok, let's try to find the package.
        logger.warning(
            "Failed to find template %r for package %s; trying default",
            base_template, package
        )
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

    :return: The :class:`pyramid_mailer.message.Message` we sent.
    """

    kwargs = dict(kwargs)
    if '_level' not in kwargs:
        kwargs['_level'] = 4
    message_factory = kwargs.pop('message_factory', create_simple_html_text_email)
    if message_factory is not create_simple_html_text_email:
        warnings.warn("The message_factory argument is deprecated.", stacklevel=2)
    message = message_factory(*args, **kwargs)
    # There are cases where this will be none (bounced email handling, missing
    # subject - error?). In at least the bounced email case, we want to avoid
    # sending the email and erroring.
    if message is None:
        return None
    return _send_mail(message,
                      recipients=kwargs.get('recipients', ()),
                      request=kwargs.get('request'))


def _compute_from(*args, **kwargs):
    verp = component.queryUtility(IVERP, default=default_verp)
    return verp.verp_from_recipients(*args, **kwargs)


def _get_from_address(pyramid_mail_message, recipients, request):
    """
    Get a valid `From`/`Sender`/`Return-Path` address. This field is required and
    must be from a verified email address (e.g. @nextthought.com).
    """
    fromaddr = getattr(pyramid_mail_message, 'sender', None)

    if not fromaddr:
        # Can we get a site policy for the current site?
        # It would be the unnamed IComponents
        policy = component.queryUtility(IMailerPolicy, default=default_mailer_policy)
        fromaddr = policy.get_default_sender()
    if not fromaddr:
        pyramidmailer = component.queryUtility(IMailer)
        fromaddr = getattr(pyramidmailer, 'default_sender', None)

    if not fromaddr:
        raise RuntimeError("No one to send mail from")

    result = _compute_from(fromaddr,
                           recipients,
                           request if request is not None else get_current_request())
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
    assert pyramid_mail_message is not None
    pyramidmailer = component.queryUtility(IMailer)

    # XXX: We'd like to call this only on the one branch
    # that actually needs it, but sadly it has a side-effect of
    # mutating the ``pyramid_mail_message`` in place.
    # This isn't a very cheap operation, so hopefully the first branch
    # is the common one.
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
    return pyramid_mail_message

interface.moduleProvides(ITemplatedMailer)
