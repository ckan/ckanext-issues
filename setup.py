from setuptools import setup, find_packages

version = '0.3'

setup(
	name='ckanext-issues',
	version=version,
	description='CKAN Extension providing Issues (Task/Todos/...)',
	classifiers=[],
	keywords='',
	author='CKAN Project',
	author_email='info@okfn.org',
	url='',
	license='mit',
    packages=find_packages(exclude=['tests']),
    namespace_packages=['ckanext', 'ckanext.issues'],
    package_data = {'ckanext.issues' : ['public/ckanext-issues/*.js',
                                      'public/ckanext-issues/css/*.css',
                                      'public/ckanext-issues/images/*.png',
                                      'templates/*.html']},
	include_package_data=True,
	zip_safe=False,
	install_requires=[
        'enum34',
        'akismet==0.2.0',
    ],
	entry_points=\
	"""
    [ckan.plugins]
	issues=ckanext.issues.plugin:IssuesPlugin

    [paste.paster_command]
    issues = ckanext.issues.commands:Issues

    [ckan.celery_task]
    tasks=ckanext.issues.celery_import:task_imports
	""",
)
