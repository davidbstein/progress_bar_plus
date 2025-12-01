import os
import sys
from pathlib import Path
import logging
import logging.config
######################
# Figure out context #
######################

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
HTML = None
if is_in_jupyter():
  from ipywidgets import HTML
  import ipywidgets
  logger = logging.getLogger('notebookLogger')
elif is_in_slurm():
  logger = logging.getLogger('slurmLogger')
else:
  logger = logging.getLogger('scriptLogger')

def is_redirected():
  # todo: windows is different.
  return not is_in_jupyter() and not sys.stdout.isatty()

def get_current_mode():
  if sys.stdout.isatty():
    return "interactive"
  if is_in_jupyter():
    return "notebook"
  if is_redirected():
    return "redirected"
  return "unknown"
