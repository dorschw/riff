
# Riff
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)](https://github.com/charliermarsh/ruff)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)


Ruff + diff = Riff

Run [**Ruff**](https://ruff.rs)⚡, and filter out violations not caused by your branch.
Riff uses `git diff` to detect code lines modified in the current branch, and filters Ruff's output accordingly.
Riff only fails when violations are detected in modified lines.


### Rationale
Ruff doesn't have a baseline feature, so Riff can come handy for enforcing Ruff rules in larger repositories quickly, without having to fix every single existing violation.


## Usage

### Locally
* Run `riff`, followed by Riff arguments (optional, see below), and Ruff arguments (optional, see limitations).
* Running `riff` without arguments will run it in the current directory.
* Riff expects to be run in a repository folder.

### As a pre-commit hook

Copy this to your [`.pre-commit-config`](https://pre-commit.com/#plugins) file
####
```
- repo: https://github.com/dorschw/riff
  hooks:
  - id: riff
    rev: 0.0.284a1
```

To pass other arguments to Riff (and Ruff), add the `args` key, e.g.
```
    args: ["--base-branch=origin/master"]
```

### Arguments
* `always_fail_on`: comma-separated list of Ruff error codes. When detected by Ruff, Riff will consider them as failures, even if they're not in lines modified in the current branch.
* `print_github_annotation`: boolean (default `false`). When set to `true`, will add [GitHub Annotations](https://dailystuff.nl/blog/2023/extending-github-actions-with-annotations), making the violations more visible when reviewing code in GitHub's `Modified Files` tab.
* `base_branch`: string (default `origin/main`). Change to `origin/master` or whatever your base branch is named.
## Limitations
* When using Ruff's `--fix` feature, Ruff will fix everything it is [configured](https://beta.ruff.rs/docs/configuration/) to, regardless of the modified lines. Riff cannot control this behavior.
* Riff cannot _currently_ run Ruff with a `--format` configuration. (see [here](https://github.com/dorschw/riff/issues/9))
