import os
import eventlet
import eventlet.hubs

from simpleutil.utils.systemutils.posix.inotify import api as inotify
from simpleutil.utils.systemutils.posix.inotify import event

from simpleutil.automaton import machines
from simpleutil.automaton import runners

hub = eventlet.hubs.get_hub()

TIMEOUT = object()
MODIFY = object()


# stat
UNDEFINED = 'undefined'
FINISHING = 'finishing'
FINISHED = 'finished'
ERROR = 'error'
# event
START = 'start'
OK = 'ok'
NOT_OK = 'not_ok'
OVER = 'over'


BLOCK = 4096
MAX_COUTN_OF_BLOCK = 3


class LastRowsN(object):

    # event
    NOT_ENOUGH = 'unenough'
    ENOUGH = 'enough'
    SEEKED = 'seeked'
    # stat
    SEEK = 'seek'
    READ = 'read'

    def __init__(self, fobj, rows):

        self.fobj = fobj
        self.rows = rows
        self.fobj.seek(0, os.SEEK_END)
        self.max_pos = fobj.tell()
        if self.max_pos == 0:
            raise RuntimeError('file is empty')
        self.last_pos = self.max_pos
        self._buffer = ''
        self.readed = 0
        self.runner = runners.FiniteRunner(self._automaton(), detail=False)

    def _automaton(self):
        m = machines.FiniteMachine()

        m.add_state(UNDEFINED)
        m.add_state(self.SEEK)
        m.add_state(self.READ)
        m.add_state(FINISHING)
        m.add_state(FINISHED, terminal=True)
        m.default_start_state = UNDEFINED

        m.add_transition(UNDEFINED, self.SEEK, START)
        m.add_transition(self.SEEK, self.READ, self.SEEKED)
        m.add_transition(self.SEEK, FINISHING, self.ENOUGH)
        m.add_transition(self.READ, self.SEEK, self.NOT_ENOUGH)
        m.add_transition(self.READ, FINISHING, self.ENOUGH)
        m.add_transition(FINISHING, FINISHED, OVER)

        m.add_reaction(self.SEEK, START, self._seek_back)
        m.add_reaction(self.SEEK, self.NOT_ENOUGH, self._seek_back)
        m.add_reaction(self.READ, self.SEEKED, self._read)
        m.add_reaction(FINISHING, self.ENOUGH, self._finish)

        return m

    def _read(self):
        self._buffer = self.fobj.read(BLOCK).replace('\r', '') + self._buffer
        self.readed += BLOCK
        self.fobj.seek(-BLOCK, os.SEEK_CUR)
        if self._buffer.count('\n') > self.rows:
            return self.ENOUGH
        if self.readed >= BLOCK*MAX_COUTN_OF_BLOCK:
            return self.ENOUGH
        return self.NOT_ENOUGH

    def _finish(self):
        buffer_list = self._buffer.split('\n')
        if len(buffer_list) > self.rows:
            buffer_list = buffer_list[-self.rows:]
        self._buffer = '\n'.join(buffer_list)
        return OVER

    def _seek_back(self):
        read_pos = BLOCK
        if self.last_pos < read_pos:
            read_pos = self.last_pos
            self.fobj.seek(0)
            self._buffer = self.fobj.read(read_pos).replace('\r', '') + self._buffer
            self.fobj.seek(0)
            self.last_pos = 0
            self.readed += read_pos
            return self.ENOUGH
        self.fobj.seek(-read_pos, os.SEEK_CUR)
        self.last_pos = self.fobj.tell()
        return self.SEEKED

    def getbuffer(self):
        self.runner.run(START)
        return self._buffer


class TailWithF(object):

    PREPAREING = 'prepareing'
    PAUSEING = 'pauseing'
    OUTPUTING = 'outputing'
    NROWS = 'nrows'

    interval = 5

    def __init__(self, path,
                 output, pause=None,
                 rows=20):
        self.path = path
        self.file = open(path, 'r')
        self.inotifer = inotify.Notifier(path)
        self.inotifer.start()
        self.output = output
        self.pause = pause
        self.rows = rows
        self._stoped = True
        self.modify = False
        self.buffer = ''
        self.runner = None
        self.callback = None

    def _automaton(self):
        if self.runner is None:
            m = machines.FiniteMachine()

            m.add_state(UNDEFINED)
            m.add_state(self.NROWS)
            m.add_state(self.PREPAREING)
            m.add_state(self.OUTPUTING)
            m.add_state(self.PAUSEING)
            m.add_state(FINISHING)
            m.add_state(FINISHED, terminal=True)
            m.default_start_state = UNDEFINED

            m.add_transition(UNDEFINED, self.NROWS, START)
            m.add_transition(self.NROWS, self.OUTPUTING, OK)
            m.add_transition(self.PREPAREING, self.OUTPUTING, OK)
            m.add_transition(self.OUTPUTING, self.PAUSEING, OK)
            m.add_transition(self.PAUSEING, self.PREPAREING, OK)
            m.add_transition(self.PREPAREING, FINISHING, NOT_OK)
            m.add_transition(self.OUTPUTING, FINISHING, NOT_OK)
            m.add_transition(self.PAUSEING, FINISHING, NOT_OK)
            m.add_transition(FINISHING, FINISHED, OVER)

            m.add_reaction(self.NROWS, START, self.n_rows)
            m.add_reaction(self.PREPAREING, OK, self.prepare_func)
            m.add_reaction(self.OUTPUTING, OK, self.output_func)
            m.add_reaction(self.PAUSEING, OK, self.pause_func)
            m.add_reaction(FINISHING, NOT_OK, self.close_func)

            self.runner = runners.FiniteRunner(m, detail=False)

    def prepare_func(self):
        if self.modify:
            try:
                self.buffer = self.file.read(BLOCK)
            except (OSError, IOError):
                return NOT_OK
            pos = self.file.tell()
            last_post = os.path.getsize(self.path)
            if pos == last_post:
                self.modify = False
            # file delete some line !!!
            elif pos > last_post:
                return NOT_OK
            return OK
        else:
            self.callback = eventlet.getcurrent().switch
            timer = hub.schedule_call_global(self.interval, self.callback, TIMEOUT)
            if hub.switch() is not TIMEOUT:
                timer.cancel()
            self.callback = None
        return OK

    def output_func(self):
        if self.buffer:
            try:
                self.output(self.buffer.replace('\r', ''))
                self.buffer = ''
            except:
                return NOT_OK
        return OK

    def pause_func(self):
        try:
            if self.pause:
                self.pause()
        except:
            return NOT_OK
        return OK

    def close_func(self):
        self.stop()
        return OVER

    def n_rows(self):
        if self.rows <= 0:
            self.file.seek(0, os.SEEK_END)
            return OK
        before = os.path.getsize(self.path)
        if before < 1:
            return OK
        reader = LastRowsN(self.file, self.rows)
        self.buffer = reader.getbuffer()
        after = os.path.getsize(self.path)
        diff = after - before
        if diff:
            if diff < 0:
                return NOT_OK
            self.modify = True
        self.file.seek(reader.max_pos)
        return OK

    def event_notify(self, events):
        # event is a mask set
        if events:
            events.clear()
            if not self.modify:
                self.modify = True
                if self.callback:
                    hub.schedule_call_global(0, self.callback, MODIFY)

    def start(self, threadpool):
        if self._stoped:
            self.inotifer.add_watch(event.IN_MODIFY)
            self._automaton()
            threadpool.add_thread(self.runner.run, START)
            threadpool.add_thread(self.inotifer.loop, self.event_notify)
            self._stoped = False

    def stop(self):
        if not self._stoped:
            self._stoped = True
            self.runner.shutoff()
            eventlet.sleep(self.inotifer.interval)
            if self.callback:
                hub.schedule_call_global(0, self.callback, MODIFY)
            self.inotifer.close()
            self.file.close()
