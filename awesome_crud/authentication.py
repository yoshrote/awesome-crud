class BaseAuthentication(object):
    def __init__(self, app_config):
        self.app_config = app_config

    def __call__(self, node, request, url_params, flags):
        request = self.identify(request)
        response = node()
        return response

    def identify(self, request):
        raise NotImplementedError('identify')


class PassthoughAuthentication(BaseAuthentication):
    def identify(self, request):
        """
        Look at session headers to evaluate who this is and assign the user
        object to the request itself
        """
        request.user = None
        return request


class BasicAuthentication(BaseAuthentication):
    def identify(self, request):
        """
        Look at session headers to evaluate who this is and assign the user
        object to the request itself
        """
        auth_type, _, auth_value = request.headers.\
            get('Authorization', '').partition(' ')

        request.user = None
        return request
