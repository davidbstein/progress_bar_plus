import time
from datetime import timedelta
import traceback
import atexit
import asyncio
import weakref
import os
import sys
import logging
import logging.config
from pathlib import Path

def get_slurm_state():
  return {
    k: v
    for k, v in os.environ.items()
    if "SLURM" in k
  }

def is_in_slurm():
  state = get_slurm_state()
  job_name = state.get("SLURM_JOB_NAME")
  if not job_name:
    return False
  if job_name == "sys/dashboard/sys/jupyterlab":
    return False
  return True

def is_in_jupyter():
  try:
    from IPython import get_ipython
    return get_ipython().__class__.__name__ == 'ZMQInteractiveShell'
  except ImportError:
    return False

_dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
logger = logging.config.fileConfig(_dir_path / "default_config.conf")

if is_in_jupyter():
  from ipywidgets import HTML
  import ipywidgets
  logger = logging.getLogger('notebookLogger')
elif is_in_slurm():
  logger = logging.getLogger('slurmLogger')
else:
  logger = logging.getLogger('scriptLogger')

_SETTINGS = {
  "interactive_debounce": 0.1, # if running in an interactive terminal or jupyter
  "script_debounce": 60, # if running on a SLURM node
}

def is_redirected():
  # todo: windows is different.
  return not is_in_jupyter() and not sys.stdout.isatty()

def get_caller():
  try:
    assert False
  except Exception as e:
    import traceback
    tb = traceback.extract_stack()
    if len(tb) < 3:
      return None
    return tb[-3]

def _format_time(seconds):
  if seconds < 2:
    return f"{seconds:07.4f}s"
  elif seconds < 60:
    return f"0:{seconds:05.2f}"
  elif seconds < 3600:
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes)}:{int(seconds):02d}"
  elif seconds < 86400:  # less than a day
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
  else:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(days)}d, {int(hours)}:{int(minutes):02d}:{int(seconds):02d}"


def _compute_estimates(pbar):
  now = time.time()
  time_elapsed = now - pbar.start_time
  if pbar.n == 0:
    return {
      "time_elapsed": time_elapsed,
      "time_per_iteration": 0,
      "time_remaining": 0,
      "iter_per_second": 0,
    }
  time_per_iteration = time_elapsed / pbar.n
  if pbar.total:
    time_remaining = (pbar.total - pbar.n) * time_per_iteration
  else:
    time_remaining = 0
  return {
    "time_elapsed": _format_time(time_elapsed),
    "time_per_iteration": _format_time(time_per_iteration),
    "time_remaining": _format_time(time_remaining),
    "iter_per_second": 1 / time_per_iteration,
  }

def _pbar_html(perc, status, width="300px"):
  color = {
    "running": "var(--jp-brand-color1)",
    "error": "var(--jp-error-color1)",
    "done": "var(--jp-success-color1)",
    "stopped": "var(--jp-warn-color1)",
  }.get(status, "var(--jp-warn-color1)")
  return f"""
    <div style="width: {width}; height: 1.5em; background: var(--jp-layout-color2); position: relative;">
      <div style="left: 0; right: {100-100*perc}%; top:0; bottom:0; background-color: {color}; position: absolute;"></div>
    </div>
  """

def _render_html(pbar):
  status = "running"
  e = _compute_estimates(pbar)
  time_str = f"{e['time_elapsed']}"[:10]
  error_extra = ""
  if pbar.finished:
    status = "done"
  elif pbar.stopped:
    status = "stopped"
  if pbar.error:
    status = "error"
    error_extra = f"<pre style='color:red'>{pbar.error}</pre>"
  if pbar.total:
    percentage = (pbar.n / pbar.total) * 100
    perc = f"{percentage:.1f}%"
    progress_bar = _pbar_html(pbar.n/pbar.total, status)
    counts = f"{pbar.n}/{pbar.total}"
    if status == "running":
      time_str += f"<{e['time_remaining']}"
  else:
    perc = ""
    progress_bar = ""
    progress_bar = _pbar_html(1, status, width="40px")
    counts = f"{pbar.n}"
  if e['iter_per_second'] >= 1:
    iter_str = f"{e['iter_per_second']:.2f}it/s"
  else:
    iter_str = f"{e['time_per_iteration']}s/it"
  time_string = f"[{time_str},\t{iter_str}]"
  elemstyle = f"white-space: nowrap;"
  return f"""
    <div style="display:flex; flex-direction:column;">
    </style>
      <div style="display:flex; gap:1em; align-items: center;">
        <div style='{elemstyle}'>{pbar.desc}</div>
        <div style='{elemstyle}; width: 5em;'>{perc}</div>
        <div style='{elemstyle}'>{progress_bar}</div>
        <div style='{elemstyle}'>{counts}</div>
        <div style='{elemstyle}'>{time_string}</div>
        <div style='{elemstyle}'>{status}</div>
      </div>
      {error_extra}
    </div>
  """

def _draw_term_progress_bar(perc, status='running', num_chars=30):
  bar_width = num_chars * perc
  fill_chars = {
    "running": "█ ",
    "error": "▚░",
    "done": "█ ",
    "stopped": "▒░",
  }.get(status, "▓░")
  full_chars = int(bar_width)
  partial_char_width = bar_width - full_chars
  partial_char = ' ▏▎▍▌▋▊▉'[int(partial_char_width*8)]
  empty_chars = num_chars - full_chars - 1
  return f"{fill_chars[0] * full_chars}{partial_char}{fill_chars[1]*empty_chars}"

def _render_text(pbar):
  status = "running"
  e = _compute_estimates(pbar)
  time_str = f"{e['time_elapsed']}"
  error_extra = ""
  if pbar.finished:
    status = "done"
  elif pbar.stopped:
    status = "stopped"
  if pbar.error:
    status = "error"
    error_extra = f"\n{pbar.error}"
  if pbar.total:
    percentage = (pbar.n / pbar.total) * 100
    progress_bar = _draw_term_progress_bar(pbar.n/pbar.total, status)
    progress_str = f"{percentage:.1f}% |{progress_bar}|"
    counts = f"{pbar.n}/{pbar.total}"
    if status == "running":
      time_str += f"<{e['time_remaining']}"
  else:
    percentage = 0
    progress_str = f""
    counts = f"{pbar.n}"
  if e['iter_per_second'] >= 1:
    iter_str = f"{e['iter_per_second']:.2f}it/s"
  else:
    iter_str = f"{e['time_per_iteration']}s/it"
  time_string = f"{time_str:9} {iter_str}"
  return f"({status}) {progress_str} {counts}it [{time_string}] {pbar.desc} {error_extra}"


class ProgressBar:
  def __init__(self, iterable=None, total=None, force_script_mode=False, force_interactive_mode=False, debounce_rate=None, desc=""):
    self.force_update_on_exit = True
    self.stopped = False
    self.iterable = iterable
    if total:
      self.total = total
    elif hasattr(iterable, '__len__'):
      self.total=len(iterable)
    else:
      self.total = None
    self.n = 0
    self.desc = desc
    caller = get_caller()
    if caller and not self.desc:
      self.desc = f"{caller.filename.split('/')[-1]}:{caller.lineno}({caller.name})"
    self.start_time = time.time()
    self.started = False
    self.last_update = 0
    self.finished = False
    self.error = None
    self.notebook_mode = is_in_jupyter() and not force_script_mode and not force_interactive_mode
    self.interative_mode = not is_in_slurm() and not is_redirected() and not force_script_mode
    if self.notebook_mode:
      self.debounce_rate = _SETTINGS['interactive_debounce']
      self.render_target = weakref.proxy(HTML(value=_render_html(self)))
      display(self.render_target)
    elif self.interative_mode:
      self.debounce_rate = _SETTINGS['interactive_debounce']
      print(self.desc, end='', flush=True)
    else:
      self.debounce_rate = _SETTINGS['script_debounce']
    if debounce_rate:
      self.debounce_rate = debounce_rate
    atexit.register(self._force_update)
    self._finalizer = weakref.finalize(self, self._finalize)
    self._event_loop = asyncio.get_event_loop()

  def reset(self):
    self.n = 0
    self._do_render()

  def _force_update(self):
    if self.force_update_on_exit:
      self._do_render(force=True)

  def _finalize(self):
    if not self.finished and not self.error:
      self.error = "Interrupted"
    self._force_update()

  def update(self, n=1):
    self.n += n
    self._render()

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

  def _do_render(self, force=False):
    if self.notebook_mode:
      self.render_target.value = _render_html(self)
    else:
      state_string = _render_text(self)
      if not self.interative_mode:
        if self.finished or self.error:
          end = "\n"
        else:
          end = "\r"
        print(state_string, end=end)
      else:
        logger.info(state_string)
    self.last_update = time.time()
    if self.finished:
      del(self)

  def close(self):
    self.stopped = True
    self._do_render()
    del self._event_loop

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
progress_bar = ProgressBar
