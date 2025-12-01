import time


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
  if seconds == 0:
    return "0s"
  elif seconds < .1:
    return f"0:{seconds:07.4f}s"
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


def _compute_time_per_iter(pbar):
  estimates = []
  updates = [v for v in pbar._update_tracker if v[0] > 0]
  # per N updates
  if len(updates) >= 2:
    u1_ts, u1_n = min(pbar._update_tracker)
    u2_ts, u2_n = max(pbar._update_tracker)
    if u2_ts - u1_ts:
      estimates.append((u2_ts - u1_ts)/(u2_n - u1_n))
  # in last minute
  timed_diff_ts = pbar.last_update - pbar._timed_tracker[0][0]
  timed_diff_n = pbar.n - pbar._timed_tracker[0][1]
  if timed_diff_ts > 0 and timed_diff_n > 5:
    estimates.append(timed_diff_ts/timed_diff_n)
  time_elapsed = pbar.last_update - pbar.start_time
  # over full run
  estimates.append(time_elapsed / pbar.n)
  to_ret = sum(estimates) / len(estimates)
  return to_ret

def _compute_estimates(pbar):
  now = time.time()
  time_elapsed = pbar.last_update - pbar.start_time
  if pbar.n == 0:
    return {
      "time_elapsed": _format_time(0),
      "time_per_iteration": 0,
      "time_remaining": 0,
      "iter_per_second": 0,
    }
  time_per_iteration = _compute_time_per_iter(pbar)
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
