from __future__ import unicode_literals
import logging

from webob import Request, Response
from webob.acceptparse import MIMEAccept
from webob.exc import (
    HTTPBadRequest,
    HTTPNotAcceptable,
    HTTPUnsupportedMediaType,
)

LOG = logging.getLogger(__name__)


class AwesomeRequest(Request):
    @property
    def serializer(self):
        return self.registry['serialization']['serializer']

    @property
    def serialized_mime_type(self):
        output_mime = self.accept.best_match(
            self.registry['serialization'].keys()
        )
        if output_mime is None:
            raise HTTPUnsupportedMediaType()
        else:
            return output_mime

    @property
    def serialized_charset(self):
        return self.registry['serialization']['charset']

    def serialized_response(self, resource):
        output_mime = self.serialized_mime_type

        serializer = self.registry['serialization'][output_mime]

        try:
            response = Response(
                content_type=bytes(output_mime),
                charset=bytes(serializer['charset'])
            )
            response.text = serializer['serializer'].dumps(resource).decode(
                serializer['charset']
            )
            return response
        except ValueError:
            raise HTTPUnsupportedMediaType()

    @property
    def deserialize_body(self):
        input_mime = MIMEAccept(
            ';'.join(self.registry['serialization'].keys())
        )
        if self.content_type not in input_mime:
            raise HTTPNotAcceptable()

        serializer = self.registry['serialization'][self.content_type]

        body = self.body if self.body else serializer['empty']
        try:
            return serializer['serializer'].loads(body)
        except ValueError:
            raise HTTPBadRequest(detail='could not serialize body')
