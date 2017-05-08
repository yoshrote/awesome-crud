"""
Small framework for creating RESTful apps.

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


Response guide: https://i.stack.imgur.com/whhD1.png

# Routing
When the `Application` receives a request it uses it's `Router` to traverse
to the correct `Node`. The `Node` will pass
the request and any data extracted form the URL to the relevant controller.
The controller then calls the corresponding method on the `BaseDAO` instance
to handle any querying and persistence operations and returns something which
can be transformed into a `webob.Response` object.

## Tree routing
The `Router` uses the resource names extracted to navigate the
`Application.RESOURCE_TREE` to find the correct `Node`.

## Flat routing
The final resource name extracted from the URL will determine
the correct `Node` in the `Application.RESOURCE_MAP`.

# Ideas
Use BodyMan as the request.registry
Order Authentication/Authorization/Cache layer hooks

"""
from __future__ import unicode_literals
import logging
from functools import partial

from webob.dec import wsgify
from webob.exc import HTTPException

from .router import Router
from .request import AwesomeRequest
from .authentication import PassthoughAuthentication
from .authorization import PassthoughAuthorization
from .caching import NoCaching
from .session import NoSession


LOG = logging.getLogger(__name__)


class Application(object):
    RESOURCE_TREE = None
    ROOT = None
    Router = Router
    Authentication = PassthoughAuthentication
    Authorization = PassthoughAuthorization
    Caching = NoCaching
    Session = NoSession

    def __init__(self, app_config):
        self.router = self.Router(self.ROOT, self.RESOURCE_TREE)
        self.app_config = app_config
        self.authorization = self.Authorization(app_config)
        self.authentication = self.Authentication(app_config)
        self.session = self.Session(app_config)
        self.caching = self.Caching(app_config)

    @wsgify(RequestClass=AwesomeRequest)
    def __call__(self, request):
        request.registry = self.app_config

        try:
            node, url_params, flags = self.router.route(request)
        except HTTPException as exc:
            return exc

        func = self.wrap_up(request, node, url_params, flags, layers=[
            self.session, self.authentication, self.authorization, self.caching
        ])
        return func()

    @staticmethod
    def wrap_up(request, node, url_params, flags, layers=None):
        layers = reversed(layers or [])
        base = partial(node, request, url_params, **flags)
        for layer in layers:
            base = partial(layer, base, request, url_params, flags)
        return base

__all__ = ['Application']
