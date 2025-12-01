import time

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
    "iter_per_second": 1/time_per_iteration,
  }
