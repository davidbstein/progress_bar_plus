from progress_bar_plus import pbar
import time


# TODO: test that this does the right thing in jupyter, slurm nodes, TTY, pipes, and file redirects...
# TODO: test different run conditions...
for i in pbar(range(10)):
  time.sleep(1)