import os

import akismet

from ckan.lib.celery_app import celery
from ckan.plugins import toolkit as t

def load_config(ckan_ini_filepath):
    import paste.deploy
    config_abs_path = os.path.abspath(ckan_ini_filepath)
    conf = paste.deploy.appconfig('config:' + config_abs_path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
                                             conf.local_conf)

def register_translator():
    # Register a translator in this thread so that
    # the _() functions in logic layer can work
    from paste.registry import Registry
    from pylons import translator
    from ckan.lib.cli import MockTranslator

    global registry
    global translator_obj

    registry = Registry()
    registry.prepare()
    translator_obj = MockTranslator()
    registry.register(translator, translator_obj)


@celery.task(name="issues.check_spam_comment")
def check_spam_comment(comment_id, ckan_ini_filepath=None,
                                             user_ip=None, user_agent=None):
    load_config(ckan_ini_filepath or '/var/ckan/ckan.ini')
    register_translator()

    import ckan.model as model

    username = t.get_action('get_site_user')(
        {'ignore_auth': True}, {})['name']
    ctx = {
        'user': username,
        'model': model,
        'session': model.Session
    }
    data = {'id': comment_id}
    comment = t.get_action('issue_comment_show')(ctx, data)

    is_spam = check_spam(comment['comment'], comment['user']['name'],
                                           user_ip, user_agent)

    print "SPAM CHECK: {}".format(is_spam)
    if is_spam:
        username = t.get_action('get_site_user')({'ignore_auth': True}, {})['name']
        report = t.get_action('issue_comment_report')
        report({'user': username}, data)


@celery.task(name="issues.check_spam_issue")
def check_spam_issue(dataset_id, issue_number, ckan_ini_filepath=None,
                                      user_ip=None, user_agent=None):
    load_config(ckan_ini_filepath or '/var/ckan/ckan.ini')
    register_translator()

    import ckan.model as model

    username = t.get_action('get_site_user')({'ignore_auth': True}, {})['name']
    ctx = {
        'user': username,
        'model': model,
        'session': model.Session
    }

    data = {'issue_number': issue_number, 'dataset_id': dataset_id, 'include_reports': False}
    issue = t.get_action('issue_show')(ctx, data)
    is_spam = check_spam(issue['description'], issue['user']['name'], user_ip, user_agent)
    print "SPAM CHECK: {}".format(is_spam)

    if is_spam:
        username = t.get_action('get_site_user')({'ignore_auth': True}, {})['name']
        report = t.get_action('issue_report')
        report({'user': username}, data)


def check_spam(comment, author, user_ip=None, user_agent=None):
    import logging
    from pylons import config

    apikey = config.get('ckanext.issues.akismet.key', '')
    if not apikey:
        return False

    print "User:", author, user_ip, user_agent

    log = logging.getLogger(__file__)
    log.info('Checking comment for spam')

    api = akismet.Akismet(apikey)
    if not api.verify_key():
        log.warning("Akismet API key is not verified")
        return False

    return api.comment_check(comment, {'comment_author': author, 'user_ip': user_ip or '', 'user_agent': user_agent or ''})
