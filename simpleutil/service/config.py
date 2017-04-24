from simpleutil.config import cfg
from simpleutil.log import log

CONF = cfg.CONF


DEFALUT_OPTIONS = [
    cfg.StrOpt('state_path',
               default='/var/run/goperation',
               help="Where to store Goperation state files. "
                    "This directory must be writable by the agent. "),
    ]


def set_default_for_default_log_levels(extra_log_level_defaults):

    log.register_options(CONF)
    log.set_defaults(default_log_levels=log.get_default_log_levels() + extra_log_level_defaults)

def configure(conf=None):
    if conf is None:
        conf = CONF

    for option in DEFALUT_OPTIONS:
        conf.register_opt(option)

