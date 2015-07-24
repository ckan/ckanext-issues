from sqlalchemy import types, Table, ForeignKey, Column, UniqueConstraint
from sqlalchemy.orm import relation, backref, class_mapper

from ckan.model import domain_object, meta


class Report(domain_object.DomainObject):

    def __init__(self, user_id, parent_id):
        self.user_id = user_id
        self.parent_id = parent_id

    @classmethod
    def get_reports(cls, session, parent_id):
        return session.query(cls).filter(
            cls.parent_id == parent_id)

    @classmethod
    def get_reports_for_user(cls, session, user_id, parent_id):
        return session.query(cls).filter(
            cls.parent_id == parent_id
        ).filter(cls.user_id == user_id)


def define_report_tables(models):
    '''Creates the Report tables and mapping classes for them.

    This is the same pattern as table_per_related in the sqlchemy docs. It will
    create a new table called {original_table}_report for each model in models
    and create an associated mapping class under the the original class as
    OriginalModel.Report. The table will contain a foreign key to the model
    passed in and a user_id column (with no foreign key currently as we don't
    generally encourage foreign keys to core tables in extensions).

    e.g for Issue, a new table called 'issue_report' is created and is mapped
    to a class called Issue.Report based on the Report class above.
    '''
    report_tables = []
    for model_ in models:
        mapped_class = class_mapper(model_)
        table_name = mapped_class.mapped_table.fullname
        report_table = Table(
            '{0}_report'.format(table_name),
            meta.metadata,
            Column('id', types.Integer, primary_key=True, autoincrement=True),
            Column('user_id', types.Unicode, nullable=False),
            Column(
                'parent_id',
                types.Integer,
                ForeignKey('{0}.id'.format(table_name), ondelete='CASCADE'),
                nullable=False, index=True),
            UniqueConstraint('user_id', 'parent_id'.format(table_name)),
        )

        ReportClass = type('{0}Report'.format(model_.__name__), (Report,), {})
        model_.Report = ReportClass

        meta.mapper(
            ReportClass,
            report_table,
            properties={
                table_name: relation(
                    model_,
                    backref=backref('abuse_reports'),
                    primaryjoin=report_table.c.parent_id == model_.id
                ),
            }
        )
        report_tables.append(report_table)
    return report_tables
