# -*- coding: UTF-8 -*-
import sys

import webob.dec
import webob.exc

from simpleutil.log import log
from simpleutil.serialization import jsonutils

LOG = log.getLogger(__name__)

DEFAULT_CONTENT_TYPE = 'application/json'
STREAM_CONTENT_TYPE = 'application/octet-stream'

deserializers = {
    DEFAULT_CONTENT_TYPE: jsonutils.loads,
    STREAM_CONTENT_TYPE: lambda x: x
}

serializers = {
    DEFAULT_CONTENT_TYPE: jsonutils.dump_as_bytes,
    STREAM_CONTENT_TYPE: lambda x: x
}

default_serializer = serializers[DEFAULT_CONTENT_TYPE]

class NotFaultsExcpetion(Exception):
    pass


def controller_return_response(controller, faults=None, action_status=None):
    """Represents an API entity resource and the associated serialization and
    deserialization logic
    """
    action_status = action_status or dict(create=201, delete=204)
    faults = faults or {}
    # 已知错误
    konwn_exceptions = faults.keys() if faults else (NotFaultsExcpetion, )
    # @webob.dec.wsgify(RequestClass=Request)
    @webob.dec.wsgify
    def resource(req):
        # wsgi.Router的_dispatch通过match找到contorler
        # 在调用contorler(req)
        # 这里就是被调用的那个contorler
        match = req.environ['wsgiorg.routing_args'][1]
        args = match.copy()
        # 弹出的controller是当前闭包
        args.pop('controller', None)
        args.pop('format', None)
        action = args.pop('action', '__call__')
        # 默认content_type
        try:
            content_type = req.content_type
            # content_type = DEFAULT_CONTENT_TYPE
            deserializer = deserializers[content_type]
            serializer = serializers[content_type]
        except KeyError:
            body = default_serializer({'msg': 'can not find %s content_type serializer' % req.content_type})
            kwargs = {'body': body, 'content_type': DEFAULT_CONTENT_TYPE}
            raise webob.exc.HTTPInternalServerError(**kwargs)
        try:
            if req.body:
                args['body'] = deserializer(req.body)['body']
            # controller是自由变量
            # 这个controller是外部传入的controller
            method = getattr(controller, action)
            print action, args
            result = method(req, **args)
        except konwn_exceptions as e:
            mapped_exc = faults[e.__class__]
            if 400 <= mapped_exc.code < 500:
                LOG.info('%(action)s failed (client error): %(exc)s',
                         {'action': action, 'exc': e})
            else:
                LOG.exception('%s failed', action)
            body = default_serializer({'msg': e.message})
            kwargs = {'body': body, 'content_type': DEFAULT_CONTENT_TYPE}
            raise mapped_exc(**kwargs)
        except webob.exc.HTTPException as e:
            type_, value, tb = sys.exc_info()
            if hasattr(e, 'code') and 400 <= e.code < 500:
                msg = '%(action)s failed (client error): %(exc)s', {'action': action, 'exc': e}
                LOG.info(msg)
            else:
                msg = '%s failed', action
                LOG.exception(msg)
            msg = 'webob HTTPException %s', msg
            value.body = default_serializer({'msg': msg})
            value.content_type = DEFAULT_CONTENT_TYPE
            # value是Response对象
            return value
        except NotImplementedError as e:
            body = default_serializer({'msg': 'NotImplementedError %s' % e.message})
            kwargs = {'body': body, 'content_type': DEFAULT_CONTENT_TYPE}
            raise webob.exc.HTTPNotImplemented(**kwargs)
        except Exception:
            # NOTE(jkoelker) Everything else is 500
            LOG.exception('%s failed', action)
            # Do not expose details of 500 error to clients.
            msg = 'Request Failed: internal server error while ' \
                  'processing your request.'
            body = default_serializer({'msg': msg})
            kwargs = {'body': body, 'content_type': DEFAULT_CONTENT_TYPE}
            raise webob.exc.HTTPInternalServerError(**kwargs)
        status = action_status.get(action, 200)
        body = serializer(result)
        # NOTE(jkoelker) Comply with RFC2616 section 9.7
        if status == 204:
            body = None
        # 返回对象是Response实例
        # response的时候直接调用这个Response实例的__call__方法
        # environ是req.environ
        # 这里的start_response是eventlet.wsgi.handle_one_response中的闭包start_response
        # 这里模拟的是neutron里的写法
        # keyston的controller不会通过闭包返回Response类
        # keyston的controller会直接返回文本
        # 当返回文本对象的时候会先通过req.Response类生成Response实例
        # 再调用__call__方法
        # 有必要会设置req.Response类指向一个继承webob.Response的类
        return webob.Response(request=req, status=status,
                              content_type=content_type,
                              body=body)
    # 返回闭包
    return resource
