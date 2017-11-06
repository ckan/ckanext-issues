import traceback
import pylons
from pylons import config
from logging import getLogger
import ckan.model as model
import ckan.lib.helpers as h
import ckan.plugins.toolkit as toolkit
from ckan.lib.base import render
from ckan.logic import action
from ckan.lib.mailer import mail_recipient
import threading

log = getLogger(__name__)

role_mapper ={'Admin':'admin','Editor':'reader'}

def notify_create_reopen(context,issue):

  notify(context,issue,"issues/email/issue_create_reopen.txt")

def notify_close(context,issue):

  notify(context,issue,"issues/email/issue_close.txt")

def notify_delete(context,issue):

  notify(context,issue,"issues/email/issue_delete.txt")


def notify(context,issue,email_template):

  notify_admin = toolkit.asbool(config.get("ckanext.issues.notify_admin", False))
  notify_owner = toolkit.asbool(config.get("ckanext.issues.notify_owner", False))
  if not notify_admin and not notify_owner:
      return

  user_obj = model.User.get(issue.user_id)
  dataset = model.Package.get(issue.dataset_id)

  extra_vars = {
      'issue': issue,
      'title': dataset.title,
      'username': user_obj.name,
      'email': user_obj.email,
      'site_url': h.url_for(
          controller='ckanext.issues.controller:IssueController',
          action='show',
          id=issue.id,
          package_id=issue.dataset_id,
          qualified=True
      )
  }

  if notify_owner:
    contact_name = dataset.author or dataset.maintainer
    contact_email =  dataset.author_email or dataset.maintainer_email

    email_msg = render(email_template,extra_vars=extra_vars)
    send_email(contact_name,contact_email,email_msg)

  if notify_admin:

      # retrieve organization's admins (or the role specified on ckanext.issues.minimun_role_required) to notify
      organization = action.get.organization_show(context,data_dict={'id':dataset.owner_org})
      minimun_role_required = config.get("ckanext.issues.minimun_role_required", "Anonymous")

      for user in organization['users']:

        if user['capacity'] == role_mapper[minimun_role_required] and user['activity_streams_email_notifications']:

          admin_user = model.User.get(user['id'])
          admin_name = admin_user.name
          admin_email = admin_user.email

          if admin_email != contact_email:
            email_msg = render(email_template,extra_vars=extra_vars)
            send_email(admin_name,admin_email,email_msg)

def send_email(contact_name,contact_email,email_msg):

  log.debug("send_email to %s %s",contact_name,contact_email)

  headers = {}
  # if cc_email:
  #     headers['CC'] = cc_email

  try:

    mail_recipient(contact_name, contact_email,"Dataset issue",email_msg, headers=headers)

  except Exception:

    traceback.print_exc()
    log.error('Failed to send an email message for issue notification')
