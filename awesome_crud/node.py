from __future__ import unicode_literals
import logging

from webob import Response
from webob.exc import (
    HTTPNotFound,
    HTTPMethodNotAllowed,
    HTTPNotImplemented,
)

from .router import Router

LOG = logging.getLogger(__name__)


class BaseController(object):
    KNOWN_VERBS = ('GET', 'DELETE', 'OPTIONS', 'PATCH', 'POST', 'PUT')

    def __init__(self, context):
        self.dispatch = {
            'OPTIONS': self.options
        }
        self.context = context

    def __call__(self, request, url_params):
        if request.method not in self.KNOWN_VERBS:
            raise HTTPNotImplemented()

        try:
            func = self.dispatch[request.method]
        except KeyError:
            LOG.info(self.__class__.__name__)
            LOG.info('%s not in %s', request.method, self.dispatch.keys())
            raise HTTPMethodNotAllowed()
        else:
            return func(request, url_params)

    def options(self, request, url_params):
        LOG.info('options')
        resp = Response()
        resp.allow = sorted(self.dispatch.keys())
        return resp


class ResourceController(BaseController):
    def __init__(self, context):
        super(ResourceController, self).__init__(context)
        self.dispatch.update({
            'GET': self.query,
            'POST': self.create,
        })

    def create(self, request, url_params):
        LOG.info('create')
        resource = self.context(request.registry).create(
            url_params, request.deserialize_body
        )

        response = request.serialized_response(resource)
        response.status = 201
        response.headers['Location'] = Router.reverse(
            request, self.context, resource
        )
        return response

    def query(self, request, url_params):
        LOG.info('query')
        return self.context(request.registry).query(
            url_params,
            request.GET
        )


class InstanceController(BaseController):
    def __init__(self, context):
        super(InstanceController, self).__init__(context)
        self.dispatch.update({
            'DELETE': self.delete,
            'GET': self.get,
            'PATCH': self.patch,
            'PUT': self.update,
        })

    def update(self, request, url_params):
        LOG.info('update')
        resource = self.context(request.registry).update(
            url_params, request.deserialize_body
        )
        response = request.serialized_response(resource)
        response.status = 200
        return response

    def patch(self, request, url_params):
        LOG.info('patch')
        resource = self.context(request.registry).patch(
            url_params, request.deserialize_body
        )
        response = request.serialized_response(resource)
        response.status = 200
        return response

    def delete(self, request, url_params):
        LOG.info('delete')
        self.context(request.registry).delete(url_params)
        return Response(status=204)

    def get(self, request, url_params):
        LOG.info('get')
        resource = self.context(request.registry).get(
            url_params
        )
        response = request.serialized_response(resource)
        response.status = 200
        return response


class BulkController(BaseController):
    def __init__(self, context):
        super(BulkController, self).__init__(context)
        self.dispatch.update({
            'DELETE': self.delete,
            'PATCH': self.patch,
            'POST': self.create,
            'PUT': self.update,
        })

    def create(self, request, url_params):
        LOG.info('bulk_create')
        return self.context(request.registry).bulk_create(
            url_params, request.deserialize_body
        )

    def update(self, request, url_params):
        LOG.info('bulk_update')
        return self.context(request.registry).bulk_update(
            url_params, request.deserialize_body
        )

    def patch(self, request, url_params):
        LOG.info('bulk_patch')
        return self.context(request.registry).bulk_patch(
            url_params, request.deserialize_body
        )

    def delete(self, request, url_params):
        LOG.info('bulk_delete')
        return self.context(request.registry).bulk_delete(
            url_params, request.deserialize_body
        )


class Node(object):
    # class to manage accessing object
    CONTEXT = None

    # shims
    BulkController = BulkController
    ResourceController = ResourceController
    InstanceController = InstanceController

    def __init__(self, resource_tree):
        self.resource_tree = resource_tree
        self.bulk_controller = self.BulkController(self.CONTEXT)
        self.resource_controller = self.ResourceController(self.CONTEXT)
        self.instance_controller = self.InstanceController(self.CONTEXT)

    def __call__(self, request, url_params, bulk=False):
        LOG.debug('request: %s', request.deserialize_body)
        LOG.debug('url_params: %s', url_params)
        LOG.debug('bulk: %s', bulk)
        if url_params.get(self.CONTEXT.NAME) is None and bulk:
            return self.wrap(
                request,
                self.bulk_controller(request, url_params)
            )
        elif url_params.get(self.CONTEXT.NAME) is None:
            return self.wrap(
                request,
                self.resource_controller(request, url_params)
            )
        elif bulk:
            raise HTTPNotFound(
                detail="Can't bulk operate on a resource instance"
            )
        else:
            return self.wrap(
                request,
                self.instance_controller(request, url_params)
            )

    def wrap(self, request, response):
        if isinstance(response, Response):
            return response

        if isinstance(response, unicode):
            resp = Response(
                content_type=bytes(request.serialized_mime_type),
                charset=bytes(request.serialized_charset)
            )
            resp.text = response
        else:
            resp = request.serialized_response(response)

        resp.status = 200
        return resp

    def __getitem__(self, key):
        return self.resource_tree[key]
