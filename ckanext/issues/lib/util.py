import ckanext.issues.model as issue_model
import ckan.model as model


def issue_count(package):
  return model.Session.query(issue_model.Issue)\
    .filter(issue_model.Issue.package_id==package.id).count()

def issue_comment_count(issue):
  return issue_model.IssueComment.get_comment_count(issue)

def issue_comments(issue):
  return issue_model.IssueComment.get_comments(issue)


def _issue_query(publisher, resolved_required=False, days=None):
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
    """.format(gid=publisher.id, r=r,extra=e)

    return q

def old_unresolved(publisher, days=30):
    q = _issue_query(publisher, False, days=days)
    return model.Session.execute(q).scalar()

def resolved_count_for_publisher(publisher):
    q = _issue_query(publisher, False)
    return model.Session.execute(q).scalar()

def unresolved_count_for_publisher(publisher):
    q = _issue_query(publisher, True)
    return model.Session.execute(q).scalar()
