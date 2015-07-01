import factory
import ckanext.issues.model

class Issue(factory.Factory):
    '''A factory class for creating issues.'''

    # This is the class that this Factory will create and return
    # instances of.
    FACTORY_FOR = ckanext.issues.model.Issue

    # These are the default params that will be used to create new
    # organizations.
    type = 'organization'
    is_organization = True

    title = 'Test Organization'
    description = 'Just another test organization.'
    image_url = 'http://placekitten.com/g/200/100'

    # Generate a different group name param for each user that gets created.
    name = factory.Sequence(lambda n: 'test_org_{n}'.format(n=n))

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': _get_action_user_name(kwargs)}

        group_dict = helpers.call_action('organization_create',
                                         context=context,
                                         **kwargs)
        return group_dict

