import json
from simpleutil.utils import jsonutils


RESPONESCHEMA = {
    'type': 'object',
    'required': ['agent_id', 'agent_time', 'resultcode'],
    'properties':
        {
            'agent_id': {'type': 'integer', 'minimum': 0},                                   # agent id
            'agent_time': {'type': 'integer', 'minimum': 0},                                 # agent respone time
            'resultcode': {'type': 'integer', 'minimum': -127, 'maxmum': 127},               # resultcode
            'result': {'type': 'string'},                                                    # result message
            'details': {'type': 'array', 'minItems': 1,                                      # details for rpc
                        'items': {'type': 'object',
                                  'required': ['detail_id', 'resultcode', 'result'],
                                  'properties': {
                                      'detail_id': {'type': 'integer', 'minimum': 0},
                                      'resultcode': {'type': 'integer', 'minimum': -127, 'maxmum': 127},
                                      'result': {'oneOf': [{'type': 'string'}, {'type': 'object'}]}
                                  }
                                  }
                        }
        }
}


x = {'agent_time': 1511616056, 'expire': 60, 'result': 'Get status from 127.0.0.1 success',
     'details': [{'resultcode': 0, 'detail_id': 0,
                  'result': {'frozen': False, 'endpoint': 'gopcdn', 'locked': 0, 'entitys': 0}}],
     'resultcode': 0, 'agent_id': 1}


print jsonutils.schema_validate(x, RESPONESCHEMA)


CDN = 'gopcdn'

ENABLE = 1
DISENABLE = 0

ANY = 0
ANDROID = 1
IOS = 2

EntityTypeMap = {IOS: 'ios',
                 ANDROID: 'android',
                 ANY: 'any'}

InvertEntityTypeMap = dict([(v, k) for k, v in EntityTypeMap.iteritems()])


CREATESCHEMA = {
    'type': 'object',
    'required': ['endpoint', 'etype'],
    'properties':
        {
            'endpoint':  {'type': 'string', 'description': 'provide cdn resource for this endpoint'},
            'etype': {'oneOf': [{'type': 'string', 'enum': InvertEntityTypeMap.keys()},
                                {'type': 'integer', 'enum': EntityTypeMap.keys()}],
                      'description': 'entity type, ios,android'},
            'impl': {'type': 'string', 'description': 'impl type, svn git nfs'},
            'uri': {'type': 'string', 'description': 'impl checkout uri'},
            'version': {'type': 'string'},
            'timeout': {'type': 'integer', 'minimum': 10, 'maxmum': 3600,
                        'description': 'impl checkout timeout'},
            'auth': {'type': 'object'},
            'cdnhost': {'type': 'object',
                        'required': ['hostname'],
                        'properties': {'hostname': {'type': 'string'},
                                       'listen': {'type': 'integer', 'minimum': 1, 'maxmum': 65535},
                                       'charset': {'type': 'string'},
                                       }},
        }
}


jsonutils.schema_validate({'endpoint': 'a', 'etype': 'ios'}, CREATESCHEMA)