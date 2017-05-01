"""
Create:         POST    /
Get:            GET     /<id>
Update:         PUT     /<id>
Partial Update: PATCH   /<id>
Delete:         DELETE  /<id>
Bulk Create:    POST    /_bulk
    Body: [<obj1>, <obj2>, ..., <objN>]
Bulk Update:    PUT     /_bulk
    Body: [<obj1>, <obj2>, ..., <objN>]
Bulk Patch:     PATCH   /_bulk
    Body: [<obj1>, <obj2>, ..., <objN>]
Bulk Delete:    DELETE  /_bulk
    Body: [<id1>, <id2>, ..., <idN>]
Query:          GET     /
    Params:     default     options
        order:  asc         desc|asc
        offset: 0
        limit:  None
"""
from __future__ import unicode_literals
import json
import logging

from collections import OrderedDict

from webob import Request, Response
from webob.dec import wsgify
from webob.exc import (
    HTTPBadRequest,
    HTTPException,
    HTTPNotFound,
    HTTPMethodNotAllowed,
    HTTPNotImplemented,
)

LOG = logging.getLogger(__name__)

class BaseController(object):
    def __init__(self, context):
        self.dispatch = {
            'OPTIONS': self.options
        }
        self.context = context

    def __call__(self, request, url_params):
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
        return self.context(request).create(url_params)

    def query(self, request, url_params):
        return self.context(request).query(
            url_params,
            order=request.GET.get('order', 'asc'),
            offset=int(request.GET.get('offset') or 0),
            limit=(
                int(request.GET.get('limit'))
                if request.GET.get('limit')
                else None))


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
        return self.context(request).update(url_params)

    def patch(self, request, url_params):
        LOG.info('patch')
        return self.context(request).patch(url_params)

    def delete(self, request, url_params):
        LOG.info('delete')
        return self.context(request).delete(url_params)

    def get(self, request, url_params):
        LOG.info('get')
        return self.context(request).get(url_params)


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
        return self.context(request).bulk_create(url_params)

    def update(self, request, url_params):
        LOG.info('bulk_update')
        return self.context(request).bulk_update(url_params)

    def patch(self, request, url_params):
        LOG.info('bulk_patch')
        return self.context(request).bulk_patch(url_params)

    def delete(self, request, url_params):
        LOG.info('bulk_delete')
        return self.context(request).bulk_delete(url_params)


class Router(object):
    BULK_ROUTE = '_bulk'

    def __init__(self, root, resource_tree):
        self.resource_tree = resource_tree
        self.root = root

    @staticmethod
    def pairwise(iterable):
        pair = []
        for i, obj in enumerate(iterable):
            if i % 2 == 1:
                pair.append(obj)
                yield tuple(pair)
                pair = []
            else:
                pair.append(obj)
        if pair:
            pair.append(None)
            yield tuple(pair)

    def route(self, request):
        path = request.path_info.split('/')
        if path[0] == '':
            path = path[1:]

        if not path and self.root:
            return self.root(request)
        elif not path:
            raise HTTPNotFound()

        bulk = False
        url_params = OrderedDict()
        LOG.debug("route pairs: %s", list(self.pairwise(path)))
        node = self.resource_tree
        for resource_name, id_ in self.pairwise(path):
            # get controller
            try:
                node = node[resource_name]
            except KeyError:
                raise HTTPNotFound()

            # parse url_params
            if id_ == self.BULK_ROUTE:
                bulk = True
            elif id_ is not None:
                url_params[resource_name] = id_

        return node(request, url_params, bulk=bulk)


class Node(object):
    # class to manage accessing object
    CONTEXT = None

    def __init__(self, resource_tree):
        self.resource_tree = resource_tree
        self.bulk_controller = BulkController(self.CONTEXT)
        self.resource_controller = ResourceController(self.CONTEXT)
        self.instance_controller = InstanceController(self.CONTEXT)

    def __call__(self, request, url_params, bulk=False):
    	LOG.debug('request: %s', request.params)
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
        resp = Response(
            content_type=bytes(request.serialized_mime_type),
            charset=bytes(request.serialized_charset)
        )

        if isinstance(response, unicode):
            resp.text = response
        else:
            resp.text = request.serializer.dumps(response).decode(
                request.serialized_charset
            )

        return resp

    def __getitem__(self, key):
        return self.resource_tree[key]


class BaseDAO(object):
    # routing and parameter key
    NAME = None

    def __init__(self, request):
        self.request = request

    @staticmethod
    def serialize_body(request):
        body = request.body if request.body else request.serialized_empty
        try:
            return request.serializer.loads(body)
        except ValueError:
            raise HTTPBadRequest(detail='could not serialize body')

    def create(self, body):
        raise HTTPNotImplemented()

    def query(self, body, order='asc', offset=0, limit=None):
        raise HTTPNotImplemented()

    def update(self, body):
        raise HTTPNotImplemented()

    def patch(self, body):
        raise HTTPNotImplemented()

    def delete(self, body):
        raise HTTPNotImplemented()

    def get(self, body):
        raise HTTPNotImplemented()

    def bulk_create(self, body):
        raise HTTPNotImplemented()

    def bulk_update(self, body):
        raise HTTPNotImplemented()

    def bulk_patch(self, body):
        raise HTTPNotImplemented()

    def bulk_delete(self, body):
        raise HTTPNotImplemented()


class AwesomeRequest(Request):
    @property
    def serializer(self):
        return self.registry['serialization']['serializer']

    @property
    def serialized_mime_type(self):
        return self.registry['serialization']['mime']

    @property
    def serialized_charset(self):
        return self.registry['serialization']['charset']

    @property
    def serialized_empty(self):
        return self.registry['serialization']['empty']

class Application(object):
    RESOURCE_TREE = None
    ROOT = None

    def __init__(self, app_config):
        self.router = Router(self.ROOT, self.RESOURCE_TREE)
        self.app_config = app_config

    @wsgify(RequestClass=AwesomeRequest)
    def __call__(self, request):
        request.registry = self.app_config
        try:
            return self.router.route(request)
        except HTTPException as exc:
            return exc
