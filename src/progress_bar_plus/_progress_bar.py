import time
import traceback
import atexit
import asyncio
import weakref
from pathlib import Path

from progress_bar_plus import (
  util,
  renderers,
  context_util,
  )
from progress_bar_plus.context_util import logger

_SETTINGS = {
  "interactive_debounce": 0.1, # if running in an interactive terminal or jupyter
  "script_debounce": 60, # if running on a SLURM node or piping to logs
}
TIME_ESTIMATE_PERIOD=60 #seconds

logger = context_util.logger # must be overwritten at initialization.

####
# Main class
####

def _get_total(pbar, total=None):
  if total:
     return total
  elif hasattr(pbar.iterable, '__len__'):
    return len(pbar.iterable)
  else:
    return None


def _get_default_description(caller):
  source_scriptname = caller.filename.split('/')[-1]
  return f"{source_scriptname}:{caller.lineno}({caller.name})"

def _register_interactive_pbar(registry, pbar):
  for ref in registry:
    if inst := ref():
      inst.tty_target += 1
  registry.append(weakref.ref(pbar))

class ProgressBar:
  def __init__(self, 
    iterable=None, 
    total=None, 
    force_script_mode=False, 
    force_interactive_mode=False, 
    debounce_rate=None, 
    desc="",
    _active_pbars=[],
  ):
    # setup
    self.force_update_on_exit = True
    self.stopped = False
    self.iterable = iterable
    self.total = _get_total(self, total)
    self.n = 0
    _caller = util.get_caller()
    self.desc = desc or _get_default_description(_caller)

    # internal state
    self.start_time = time.time()
    self.started = False
    self.last_update = self.start_time
    self.finished = False
    self.error = None

    # set render and debounce mode
    self.mode = context_util.get_current_mode()
    if self.mode == "interactive":
      self.debounce_rate = _SETTINGS['interactive_debounce']
      self.tty_target = 1
      _register_interactive_pbar(_active_pbars,self)
      print(self.desc, end='\n', flush=True)
    elif self.mode == "notebook":
      self.debounce_rate = _SETTINGS['interactive_debounce']
      self.render_target = weakref.proxy(context_util.HTML())
      display(self.render_target)
    elif self.mode == "redirected":
      self.debounce_rate = _SETTINGS['script_debounce']
    if debounce_rate:
      self.debounce_rate = debounce_rate

    # exit handlers
    atexit.register(self._force_update)
    self._finalizer = weakref.finalize(self, self._finalize)
    self._event_loop = asyncio.get_event_loop()

    self._init_trackers()
    self._do_render()

  def reset(self):
    self.n = 0
    self._do_render()

  def _force_update(self):
    if self.force_update_on_exit:
      self._do_render()

  def _finalize(self):
    if not self.finished and not self.error:
      self.error = "Interrupted"
    self._force_update()

  def _init_trackers(self):
    now = self.last_update
    self._timed_tracker = ((now, 0), (now, 0))
    self._update_tracker = [(now, 0) for _ in range(10)]
    self._update_tracker_idx = 0

  def _update_trackers(self):
    now = self.last_update
    self._update_tracker_idx = (self._update_tracker_idx + 1) % len(self._update_tracker)
    self._update_tracker[self._update_tracker_idx] = (now, self.n)
    two_ago, [oa_time, oa_val] = self._timed_tracker
    if now - oa_time > TIME_ESTIMATE_PERIOD:
      self._timed_tracker = (one_ago, (now, self.n))

  def update(self, n=1):
    self.n += n
    self._render()

  def close(self):
    self.stopped = True
    self._do_render()
    del self._event_loop

  def set_description(self, desc):
    self.desc = desc
    self._render()

  def _render(self):
    current_time = time.time()
    time_since_last_update = current_time - self.last_update
    if time_since_last_update >= self.debounce_rate:
      self._do_render()
    else:
      # Schedule a render for the future if one isn't already scheduled
      if not hasattr(self, '_debounced') or not self._debounced:
        self._debounced = True
        self._schedule_render = weakref.proxy(self._event_loop.create_task(self._schedule_render()))

  async def _schedule_render(self):
    await asyncio.sleep(self.debounce_rate)
    if not self.stopped:
      self._do_render()
    else:
      pass
    self._debounced = False

  def _do_render(self):
    self.last_update = time.time()
    self._update_trackers()
    if self.mode == "notebook":
      html = renderers.render_html(self)
      self._draw_html(html)
    else:
      text = renderers.render_text(self)
      if self.mode == "interactive":
        self._draw_interative_text(text)
      else:
        self._draw_text(text)
    if self.finished:
      del self

  def _draw_html(self, html):
    self.render_target.value = html

  def _draw_interative_text(self, text):
    renderers.tty_move_y(-self.tty_target)
    renderers.tty_clear_line()
    print(text, end="\r")
    renderers.tty_move_y(self.tty_target)
    
  def _draw_text(self, text):
    logger.info(text)

  def __iter__(self):
    try:
      if not self.started:
        self.start_time = time.time()
        self.started = True
      for element in self.iterable:
        yield element
        self.n += 1
        self._render()
      self.finished = True
    except GeneratorExit:
      self.stopped = "Iterator stopped prematurely"
    except:
      self.error = traceback.format_exc()
      raise
    finally:
      self.close()

  def __call__(self, iterable):
    self.iterable = iterable
    self.iterator = iter(iterable)
    self.total = len(iterable) if hasattr(iterable, '__len__') else None
    return self

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.close()

  def __del__(self):
    try:
      logger.debug("Pbar Deleted")
    except:
      pass # sometimes self-references break during deletion.

