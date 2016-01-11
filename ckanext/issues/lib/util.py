import ckanext.issues.model as issue_model
import ckan.model as model


def issue_count(package):
    return issue_model.Issue.get_issue_count_for_package(package['id'])

def issue_comment_count(issue):
    return issue_model.IssueComment.get_comment_count_for_issue(issue['id'])

def issue_comments(issue):
    return issue_model.IssueComment.get_comments_for_issue(issue['id'])


def _issue_query(org, resolved_required=False, days=None):
    r = "NOT" if resolved_required else ""
    e = ""
    if days:
        e = "AND extract(epoch from (now() - created)) > (82600 * {days})"\
            .format(days=days)

    q = """
        SELECT count(id)
        FROM "issue"
        WHERE {r} resolved is NULL
          {extra}
          AND package_id in (
            SELECT table_id
            FROM member
            WHERE group_id='{gid}'
              AND table_name='package'
              AND state='active'
          );
    """.format(gid=org.id, r=r, extra=e)

    return q

def old_unresolved(org, days=30):
    q = _issue_query(org, False, days=days)
    return model.Session.execute(q).scalar()

def resolved_count_for_organization(org):
    q = _issue_query(org, False)
    return model.Session.execute(q).scalar()

def unresolved_count_for_organization(org):
    q = _issue_query(org, True)
    return model.Session.execute(q).scalar()
