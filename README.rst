simpleutil
==========


主要代码基于Openstack Mitaka中的oslo_cfg,oslo_log,oslo_util

复制monotonic相关代码到timeutils中减少依赖

复制python-cachetools代码到cachetools中减少依赖,默认计时器改为monotonic

代码瘦身,删除部分兼容python 2、3的代码,支持python2.6+

在lockutils中通过eventlet实现一个优先级锁PriorityLock,作用参考oslo_messaging._drivers.impl_rabbit中的ConnectionLock

在lockutils中通过eventlet实现一个顺序锁OrderedLock,作用参考_OrderedTask中调用的threading.Condition

在uuidutils中实现了一个全局主键生成类,原理类似Snowflake