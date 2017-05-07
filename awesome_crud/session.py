class BaseSession(object):
    def __init__(self, app_config):
        self.app_config = app_config

    def __call__(self, node, request, url_params, flags):
        request = self.load(request)
        response = node()
        response = self.store(request, response)
        return response

    def store(self, request, response):
        raise NotImplementedError()

    def load(self, request):
        raise NotImplementedError()


class NoSession(BaseSession):
    def store(self, request, response):
        return response

    def load(self, request):
        request.session = {}
        return request


class CookieSession(BaseSession):
    def load(self, request):
        request.session = request.cookies.mixed()
        return request

    def store(self, request, response):
        for key, value in request.session.iteritems():
            response.set_cookie(key, value)
        return response
