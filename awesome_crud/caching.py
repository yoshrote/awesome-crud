import hashlib

from webob.exc import HTTPNotModified


class BaseCaching(object):
    def __init__(self, app_config):
        self.app_config = app_config

    def __call__(self, node, request, url_params, flags):
        response = self.lookup(request, node, url_params)
        if response:
            return response
        response = node()
        response = self.store(request, response)
        return response

    def lookup(self, request, node, url_params):
        raise NotImplementedError()

    def store(self, request, response):
        raise NotImplementedError()


class NoCaching(BaseCaching):
    def lookup(self, request, node, url_params):
        return None

    def store(self, request, response):
        return None


class RedisEtagCache(BaseCaching):
    def __init__(self, app_config):
        super(RedisEtagCache, self).__init__(app_config)
        self.cache = app_config['caching']['connection']
        self.format = "{}:{{}}".format(app_config['caching']['prefix']).format

    def lookup(self, request, node, url_params):
        if request.method != 'GET' or url_params.get(node.NAME) is None:
            return None

        etag = self.cache.get(self.format(request.path_info))
        if etag and etag in request.if_match:
            raise HTTPNotModified()
        else:
            return None

    @staticmethod
    def generate_hash(response):
        return hashlib.sha512(response).hexdigest()

    def store(self, request, response):
        self.cache.set(
            self.format(request.path_info),
            self.generate_hash(response.text)
        )
