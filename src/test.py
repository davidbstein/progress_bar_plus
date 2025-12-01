from progress_bar_plus import pbar
import time

def run():
  # TODO: test that this does the right thing in jupyter, slurm nodes, TTY, pipes, and file redirects...
  # TODO: test different run conditions...
  for i in pbar(range(3)):
    for j in pbar(range(4)):
      time.sleep(.2)
    if i > 1:
      break
run()