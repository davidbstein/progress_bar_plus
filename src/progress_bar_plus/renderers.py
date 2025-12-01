from progress_bar_plus import util

def tty_move_y(n=1):
  if n == -1:
    print(f"\x1b[A\r", end='')
  elif n < -1:
    print(f"\x1b[{-n}A\r", end='')
  elif n == 1:
    print(f"\x1b[B\r", end='')
  elif n > 1:
    print(f"\x1b[{n}B\r", end='')
  else:
    pass

def tty_clear_line():
  print("\x1b[K", end='')
## PROCESSING

def _get_status(pbar):
  to_ret = "running"
  if pbar.finished:
    to_ret = "done"
  elif pbar.stopped:
    to_ret = "stopped"
  if pbar.error:
    to_ret = "error"
    if pbar.error == "Interrupted":
      to_ret = "interrupted"
  return to_ret

def _get_progres(pbar):
  if pbar.total:
    return (pbar.n / pbar.total)
  else:
    return None

def _get_iter_str(estimates):
  if estimates['iter_per_second'] >= 1:
    return f"{estimates['iter_per_second']:.2f}it/s"
  else:
    return f"{estimates['time_per_iteration']}/it"

def _process_pbar(pbar):
  estimates = util._compute_estimates(pbar)
  return dict(
    time_str = f"{estimates['time_elapsed']}",
    estimates = util._compute_estimates(pbar),
    iter_str = _get_iter_str(estimates),
    error_extra = "",
    status = _get_status(pbar),
    progress = _get_progres(pbar),
  )


## RENDERING

class Colors:
  """ ANSI color codes """
  BLACK = "\033[0;30m"
  RED = "\033[0;31m"
  GREEN = "\033[0;32m"
  BROWN = "\033[0;33m"
  BLUE = "\033[0;34m"
  PURPLE = "\033[0;35m"
  CYAN = "\033[0;36m"
  LIGHT_GRAY = "\033[0;37m"
  DARK_GRAY = "\033[1;30m"
  LIGHT_RED = "\033[1;31m"
  LIGHT_GREEN = "\033[1;32m"
  YELLOW = "\033[1;33m"
  LIGHT_BLUE = "\033[1;34m"
  LIGHT_PURPLE = "\033[1;35m"
  LIGHT_CYAN = "\033[1;36m"
  LIGHT_WHITE = "\033[1;37m"
  BOLD = "\033[1m"
  FAINT = "\033[2m"
  ITALIC = "\033[3m"
  UNDERLINE = "\033[4m"
  BLINK = "\033[5m"
  NEGATIVE = "\033[7m"
  CROSSED = "\033[9m"
  END = "\033[0m"

def _pbar_html(perc, status='running', width="300px"):
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

def _pbar_text(perc, status='running', num_chars=30):
  bar_width = num_chars * perc
  fill_chars = {
    "running": "█ ",
    "error": "▚░",
    "interrupted": "█░",
    "done": "█ ",
    "stopped": "▒░",
  }.get(status, "▓░")
  color_code = {
    "running": Colors.CYAN,
    "error": Colors.RED,
    "interrupted": Colors.YELLOW,
    "done": Colors.GREEN,
    "stopped": Colors.PURPLE,
  }.get(status, Colors.LIGHT_WHITE)
  full_chars = int(bar_width)
  partial_char_width = bar_width - full_chars
  partial_char = ' ▏▎▍▌▋▊▉'[int(partial_char_width*8)]
  empty_chars = num_chars - full_chars - 1
  if perc == 1:
    partial_char = ''
  return f"{color_code}{fill_chars[0] * full_chars}{partial_char}{Colors.END}{fill_chars[1]*empty_chars}"


## DRAWING

def render_html(pbar):
  info = _process_pbar(pbar)
  progress = info['progress']
  status = info['status']
  time_str = info['time_str']
  iter_str = info['iter_str']
  e = info['estimates']
  error_extra = info['error_extra']
  if pbar.error:
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
    iter_str = f"{e['time_per_iteration']}/it"
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

def render_text(pbar):
  info = _process_pbar(pbar)
  progress = info['progress']
  status = info['status']
  time_str = info['time_str']
  iter_str = info['iter_str']
  e = info['estimates']
  error_extra = info['error_extra']
  if pbar.error:
    error_extra = f"\n{pbar.error}"
  if pbar.total:
    percentage = progress * 100
    progress_bar = _pbar_text(pbar.n/pbar.total, status)
    progress_str = f"{percentage:>5.1f}% |{progress_bar}|"
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
  time_string = f"{time_str:<14} {iter_str:>14}"
  return f"({status:^11}) {progress_str} {counts}it [{time_string}] {pbar.desc} {error_extra}"
