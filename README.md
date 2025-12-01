
# `progress-bar-plus` 

`progress-bar-plus` is a lightweight, tqdm-style progress bar. `pbar` provides stable time estimates, clean output when redirected to a logfile, and smooth multi-bar rendering in terminals.

I made it to deal with a few classes of edge-case situations where `tqdm` didn't meeting my needs. Namely: nested loops, redirected stdout, heterogeneous execution contexts, and iterators with variable speed. It shines in multi-node and multi-process pipelines with more than one iterator running at once, Especially when parts of the pipeline may restart or resume from cache and skip a bunch of items or stop early. It is intended to be indistinguishable from `tqdm` in normal usage, but development remains to reach that point.

## Features

* Automatic detection of execution environment (terminal, notebook, redirected logs, batch nodes)
* Clean rendering in Jupyter
* Multiple progress bars updating simultaneously in a single terminal without flicker or overlap.
* Informative default labels based on the calling script, function, and line number
  * When applicable: also includes information about SLURM job and node by default
* Stable ETA estimates even when iteration speed changes significantly
* Near-drop-in replacement for `tqdm`

## Contributing

Pull requests, issues, and collaborators welcome!

## Installation

```
pip install progress-bar-plus
```

Requires Python 3.8 or newer.

## Basic Usage

```
from progress_bar_plus import pbar
import time

for i in pbar(range(3)):
  for j in pbar(range(200)):
    time.sleep(0.0001 * j)
```

## Manual Usage

```
from progress_bar_plus import ProgressBar
import time

p = ProgressBar(total=100, desc="Training")
for _ in range(100):
  p.update()
  time.sleep(0.01)
p.close()
```
