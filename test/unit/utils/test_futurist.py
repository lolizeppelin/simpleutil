import eventlet
eventlet.monkey_patch(os=False, thread=False)


from simpleutil.utils import futurist

executor = futurist.GreenThreadPoolExecutor()


def sleep_func():
    print 'sleep start'
    eventlet.sleep(10)
    print 'sleep end'
    return 'success'


fut = executor.submit(sleep_func)
try:
    print fut.result(1)
except Exception as e:
    print 'success get', e.__class__.__name__
    print 'try cancel function'
    import eventlet.hubs
    hub = eventlet.hubs.get_hub()
    t = hub.schedule_call_global(1, fut.cancel)
    eventlet.sleep(0)
    try:
        ret = fut.result()
    except futurist.CancelledError as e:
        print 'success get', e.__class__.__name__
        print e.message
    else:
        print ret, type(ret)
        raise RuntimeError('can not cancel')
else:
    raise RuntimeError('result timeout test fail')



print 'all test success'
