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
                                      'result': {'anyOf': [{'type': 'string'}, {'type': 'object'}]}}
                                  }
                        }
        }
}


x = {'agent_time': 1511616056, 'expire': 60, 'result': 'Get status from 127.0.0.1 success',
     'details': [{'resultcode': 0, 'detail_id': 0,
                  'result': {'frozen': False, 'endpoint': 'gopcdn', 'locked': 0, 'entitys': 0}}],
     'resultcode': 0, 'agent_id': 1}


print jsonutils.schema_validate(x, RESPONESCHEMA)
