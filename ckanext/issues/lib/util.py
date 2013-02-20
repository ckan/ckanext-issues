import ckanext.issues.model as issue_model
import ckan.model as model

def issue_count(package):
  return model.Session.query(issue_model.Issue)\
    .filter(issue_model.Issue.package_id==package.id).count()

def resolved_count_for_publisher(publisher):
    q = """
        SELECT count(id)
        FROM "issue"
        WHERE resolved is NULL
          AND package_id in (
            SELECT table_id
            FROM member
            WHERE group_id='{gid}'
              AND table_name='package'
              AND state='active'
          );
    """.format(gid=publisher.id)

    return model.Session.execute(q).scalar()


def unresolved_count_for_publisher(publisher):
    q = """
        SELECT count(id)
        FROM "issue"
        WHERE NOT resolved is NULL
          AND package_id in (
            SELECT table_id
            FROM member
            WHERE group_id='{gid}'
              AND table_name='package'
              AND state='active'
          );
    """.format(gid=publisher.id)

    return model.Session.execute(q).scalar()
