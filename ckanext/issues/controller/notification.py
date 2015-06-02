import traceback
from pylons import config
from logging import getLogger
import ckan.model as model
import ckan.lib.helpers as h
from ckan.lib.base import render
from ckan.logic import action
from ckan.lib.mailer import mail_recipient
from genshi.template.text import NewTextTemplate

log = getLogger(__name__)

role_mapper ={'Admin':'admin','Editor':'reader'}

def notify_create_reopen(context,issue):

    notify(context,issue,"issues/email/issue_create_reopen.txt")

def notify_delete_close(context,issue):

    notify(context,issue,"issues/email/issue_delete_close.txt")

def notify(context,issue,email_template):

    notify_admin = config.get("ckanext.issues.notify_admin", False)
    notify_owner = config.get("ckanext.issues.notify_owner", False)
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
            action='issue_page',
            package_id=dataset.name,
            qualified=True
        )
    }

    if notify_owner:
        contact_name = dataset.author or dataset.maintainer
        contact_email =  dataset.author_email or dataset.maintainer_email
        send_email(contact_name,contact_email,extra_vars,email_template)

    if notify_admin:

        # retrieve organization's admins (or the role specified on ckanext.issues.minimun_role_required) to notify
        user_roles = action.get.roles_show(context,data_dict={'domain_object':dataset.owner_org})
        minimun_role_required = config.get("ckanext.issues.minimun_role_required", "Anonymous")

        for user in user_roles['roles']:
            if user['role'] == role_mapper[minimun_role_required]:

                admin_user = model.User.get(user['user_id'])
                admin_name = admin_user.name
                admin_email = admin_user.email

                send_email(admin_name,admin_email,extra_vars,email_template)

def send_email(contact_name,contact_email,extra_vars,template):

    log.debug("send_email to %s %s",contact_name,contact_email)

    email_msg = render(template,extra_vars=extra_vars,loader_class=NewTextTemplate)

    headers = {}
    # if cc_email:
    #     headers['CC'] = cc_email

    try:

        mail_recipient(contact_name, contact_email,
                       "Dataset issue",
                       email_msg, headers=headers)

        log.debug('Email message for issue notification sent')

    except Exception:
        traceback.print_exc()
        log.error('Failed to send an email message for issue notification')
