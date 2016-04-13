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
    registry = Registry()
    registry.prepare()
    global translator_obj
    translator_obj = MockTranslator()
    registry.register(translator, translator_obj)

@celery.task(name="issues.check_spam_comment")
def check_spam_comment(comment_id, ckan_ini_filepath=None, user_ip=None, user_agent=None):
    pass
    #check_spam(comment_text, 'viagra-test-123',  ckan_ini_filepath, user_ip, user_agent)

@celery.task(name="issues.check_spam_issue")
def check_spam_issue(dataset_id, issue_number, ckan_ini_filepath=None, user_ip=None, user_agent=None):
    data = {'issue_number': issue_number, 'dataset_id': dataset_id}
    issue = t.get_action('issue_show')({}, data)
    is_spam = check_spam(issue['description'], issue['user']['name'], ckan_ini_filepath, user_ip, user_agent)

    if is_spam:
        username = t.get_action('get_site_user')({'ignore_auth': True}, {})['name']
        report = t.get_action('issue_report')
        report({'user': username}, data)


def check_spam(comment, author, ckan_ini_filepath=None, user_ip=None, user_agent=None):
    import logging
    from pylons import config

    # Load a CKAN instance if we have been given a path to a .ini file
    if ckan_ini_filepath:
        load_config(ckan_ini_filepath)
        register_translator()

    apikey = config.get('ckanext.issues.akismet.key', '')
    if not apikey:
        return False

    log = logging.getLogger(__file__)
    log.info('Checking comment for spam')

    api = akismet.Akismet(apikey)
    if not api.verify_key():
        log.warning("Akismet API key is not verified")
        return

    return api.comment_check(comment, {'comment_author': author, 'user_ip': user_ip or '', 'user_agent': user_agent or ''})
