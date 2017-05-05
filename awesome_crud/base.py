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
        return self.context(request.registry).create(url_params, request.deserialize_body)

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
        return self.context(request.registry).update(url_params, request.deserialize_body)

    def patch(self, request, url_params):
        LOG.info('patch')
        return self.context(request.registry).patch(url_params, request.deserialize_body)

    def delete(self, request, url_params):
        LOG.info('delete')
        return self.context(request.registry).delete(url_params)

    def get(self, request, url_params):
        LOG.info('get')
        return self.context(request.registry).get(url_params)


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
        return self.context(request.registry).bulk_create(url_params, request.deserialize_body)

    def update(self, request, url_params):
        LOG.info('bulk_update')
        return self.context(request.registry).bulk_update(url_params, request.deserialize_body)

    def patch(self, request, url_params):
        LOG.info('bulk_patch')
        return self.context(request.registry).bulk_patch(url_params, request.deserialize_body)

    def delete(self, request, url_params):
        LOG.info('bulk_delete')
        return self.context(request.registry).bulk_delete(url_params, request.deserialize_body)


class Router(object):
    BULK_ROUTE = '_bulk'

    def __init__(self, root, resource_tree, navigation='flat'):
        self.resource_tree = resource_tree
        self.root = root

        nav_map = {
            'flat': self._nav_flat,
            'tree': self._nav_tree,
        }
        try:
            self.navigation = nav_map[navigation]
        except KeyError as nav_method:
            raise RuntimeError(
                'Invalid navigation method: {}'.format(nav_method)
            )

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
  
    def _nav_tree(self, path):
        bulk = False
        url_params = OrderedDict()
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
        return node, url_params, bulk

    def _nav_flat(self, path):
        bulk = False
        url_params = OrderedDict()
        for resource_name, id_ in self.pairwise(path):
            # parse url_params
            if id_ == self.BULK_ROUTE:
                bulk = True
            elif id_ is not None:
                url_params[resource_name] = id_

        try:
            node = self.resource_tree[resource_name]
        except KeyError:
            raise HTTPNotFound()

        node
        
        return node, url_params, bulk

    def route(self, request):
        path = request.path_info.split('/')
        if path[0] == '':
            path = path[1:]

        if not path and self.root:
            return self.root(request)
        elif not path:
            raise HTTPNotFound()

        LOG.debug("route pairs: %s", list(self.pairwise(path)))
        node, url_params, bulk = self.navigation(path)

        return node(request, url_params, bulk=bulk)


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

    def __init__(self, registry):
        self.registry = registry

    def create(self, url_params, body):
        raise HTTPNotImplemented()

    def query(self, url_params, query_params):
        raise HTTPNotImplemented()

    def get(self, url_params):
        raise HTTPNotImplemented()

    def delete(self, url_params):
        raise HTTPNotImplemented()

    def update(self, url_params, body):
        raise HTTPNotImplemented()

    def patch(self, url_params, body):
        raise HTTPNotImplemented()

    def bulk_create(self, url_params, body):
        raise HTTPNotImplemented()

    def bulk_update(self, url_params, body):
        raise HTTPNotImplemented()

    def bulk_patch(self, url_params, body):
        raise HTTPNotImplemented()

    def bulk_delete(self, url_params, body):
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

    @property
    def deserialize_body(self):
        body = self.body if self.body else self.serialized_empty
        try:
            return self.serializer.loads(body)
        except ValueError:
            raise HTTPBadRequest(detail='could not serialize body')


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
