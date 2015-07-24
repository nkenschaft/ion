# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import requests
from requests_oauthlib import OAuth1
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.template.loader import get_template
from intranet import settings
from ..users.models import User

logger = logging.getLogger(__name__)


def email_send(text_template, html_template, data, subject, emails, headers=None):
    """
        Send an HTML/Plaintext email with the following fields.

        text_template: URL to a Django template for the text email's contents
        html_template: URL to a Django tempalte for the HTML email's contents
        data: The context to pass to the templates
        subject: The subject of the email
        emails: The addresses to send the email to
        headers: A dict of additional headers to send to the message

    """

    text = get_template(text_template)
    html = get_template(html_template)
    text_content = text.render(data)
    html_content = html.render(data)
    subject = settings.EMAIL_SUBJECT_PREFIX + subject
    headers = {} if headers is None else headers
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_FROM, emails, headers=headers)
    msg.attach_alternative(html_content, "text/html")
    logger.debug(msg)
    msg.send()

    return msg


def request_announcement_email(request, form, obj):
    """
        Send an announcement request email

        form: The announcement request form
        obj: The announcement request object

    """

    logger.debug(form.data)
    teacher_ids = form.data["teachers_requested"]
    if type(teacher_ids) != list:
        teacher_ids = [teacher_ids]
    logger.debug(teacher_ids)
    teachers = User.objects.filter(id__in=teacher_ids)
    logger.debug(teachers)

    subject = "News Post Confirmation Request from {}".format(request.user.full_name)
    emails = []
    for teacher in teachers:
        emails.append(teacher.tj_email)
    logger.debug(emails)
    base_url = request.build_absolute_uri(reverse('index'))
    data = {
        "teachers": teachers,
        "user": request.user,
        "formdata": form.data,
        "info_link": request.build_absolute_uri(reverse("approve_announcement", args=[obj.id])),
        "base_url": base_url
    }
    email_send("announcements/emails/teacher_approve.txt", 
               "announcements/emails/teacher_approve.html",
               data, subject, emails)


def admin_request_announcement_email(request, form, obj):
    """
        Send an admin announcement request email

        form: The announcement request form
        obj: The announcement request object

    """

    subject = "News Post Approval Needed ({})".format(obj.title)
    emails = [settings.APPROVAL_EMAIL]
    base_url = requets.build_absolute_uri(reverse('index'))
    data = {
        "req": obj,
        "formdata": form.data,
        "info_link": request.build_absolute_uri(reverse("admin_approve_announcement", args=[obj.id])),
        "base_url": base_url
    }
    email_send("announcements/emails/admin_approve.txt", 
               "announcements/emails/admin_approve.html",
               data, subject, emails)

def announcement_posted_email(request, obj):
    """
        Send a notification posted email

        obj: The announcement object
    """

    if settings.EMAIL_ANNOUNCEMENTS:
        subject = "News: {}".format(obj.title)
        users = User.objects.filter(receive_news_emails=True)
        send_groups = obj.groups.all()
        emails = []
        users_send = []
        for u in users:
            if len(send_groups) == 0:
                # no groups, public.
                em = u.emails[0] if u.emails and len(u.emails) >= 1 else u.tj_email
                if em:
                    emails.append(em)
                users_send.append(u)
            else:
                # specific to a group
                user_groups = u.groups.all()
                if any(i in send_groups for i in user_groups):
                    # group intersection exists
                    em = u.emails[0] if u.emails and len(u.emails) >= 1 else u.tj_email
                    if em:
                        emails.append(em)
                    users_send.append(u)


        logger.debug(users_send)
        logger.debug(emails)

        base_url = requets.build_absolute_uri(reverse('index'))
        url = request.build_absolute_uri(reverse('view_announcement', args=[obj.id]))
        data = {
            "announcement": obj,
            "link": url,
            "base_url": base_url
        }
    else:
        logger.debug("Emailing announcements disabled")


def announcement_posted_twitter(request, obj):
    if obj.groups.count() == 0 and settings.TWITTER_KEYS:
        logger.debug("Publicly available")
        title = obj.title
        title = title.replace("&nbsp;", " ")
        url = request.build_absolute_uri(reverse('view_announcement', args=[obj.id]))
        if len(title) <= 100:
            content = re.sub('<[^>]*>', '', obj.content)
            content = content.replace("&nbsp;", " ")
            content_len = 139 - (len(title) + 2 + 3 + 3 + 22)
            text = "{}: {}... - {}".format(title, content[:content_len], url)
        else:
            text = "{}... - {}".format(title[:110], url)
        logger.debug("Posting tweet: {}".format(text))

        resp = notify_twitter(text)
        respobj = json.loads(resp)

        if respobj and "id" in respobj:
            messages.success(request, "Posted tweet: {}".format(text))
            messages.success(request, "https://twitter.com/tjintranet/status/{}".format(respobj["id"]))
        else:
            messages.error(request, resp)
            logger.debug(resp)
            logger.debug(respobj)
    else:
        logger.debug("Not posting to Twitter")


def notify_twitter(status):
    url = 'https://api.twitter.com/1.1/statuses/update.json'

    cfg = settings.TWITTER_KEYS

    if not cfg:
        return False

    auth = OAuth1(cfg["consumer_key"],
                 cfg["consumer_secret"],
                 cfg["access_token_key"],
                 cfg["access_token_secret"])

    data = {
        "status": status
    }

    req = requests.post(url, data=data, auth=auth)

    return req.text