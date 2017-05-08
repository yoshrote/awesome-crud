import logging

LOG = logging.getLogger(__name__)


class BaseAuthorization(object):
    def __init__(self, app_config):
        self.app_config = app_config

    def pre_process(self, request, node, url_params, flags):
        raise NotImplementedError()

    def post_process(self, response, node, url_params, flags):
        raise NotImplementedError()

    def __call__(self, node, request, url_params, flags):
        LOG.info('pre-processing')
        request = self.pre_process(request, node, url_params, flags)
        response = node()
        LOG.info('post-processing')
        response = self.post_process(response, node, url_params, flags)
        return response


class PassthoughAuthorization(BaseAuthorization):
    def pre_process(self, request, node, url_params, flags):
        """
        Look at request.user, request.session and routing info
        to determine if user can make request and filter out
        results which they should not see
        """
        return request

    def post_process(self, response, node, url_params, flags):
        return response
