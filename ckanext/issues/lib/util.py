
import ckan.model as model

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
