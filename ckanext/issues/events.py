import uuid

from pylons import config

from sqlalchemy import event
from ckanext.issues.model import Issue, IssueComment
from ckan.lib.celery_app import celery

def user_ip():
    from pylons import request
    return request.environ.get("X_FORWARDED_FOR",
                                               request.environ["REMOTE_ADDR"])
def user_agent():
    from pylons import request
    return request.environ.get("HTTP_USER_AGENT","")

def receive_after_issue_insert(mapper, connection, target):
    # Trigger a background spam check if we have the appropriate
    # configuration in place.
    if not config.get('ckanext.issues.akismet.key'):
        return

    args = [target.dataset_id,
                target.number,
                None,
                user_ip(),
                user_agent()]

    celery.send_task("issues.check_spam_issue",
                args=args,
                task_id=str(uuid.uuid4()),
                queue='priority')

def receive_after_comment_insert(mapper, connection, target):
    # Trigger a background spam check if we have the appropriate
    # configuration in place.
    if not config.get('ckanext.issues.akismet.key'):
        return

    args = [target.id,
                None,
                user_ip(),
                user_agent()]

    celery.send_task("issues.check_spam_comment",
                args=args,
                task_id=str(uuid.uuid4()),
                queue='priority')


event.listen(Issue, 'after_insert', receive_after_issue_insert)
event.listen(IssueComment, 'after_insert', receive_after_comment_insert)