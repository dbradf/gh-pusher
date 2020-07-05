# gh-pusher

A tool to push changes to a gh-pages branch.

## Install

<TBD>

## Usage

```
$ gh-pusher --help
Usage: gh-pusher [OPTIONS]

  Publish documentation changes to a github changes branch.

  Move a directory of built documentation from the build directory to  the
  base on the repository on the target github pages branch. If there are any
  changes to the documention, they will be added in a commit under the same
  author and commit message as the last commit message on the active branch.

Options:
  --target-branch TEXT  Branch to publish documentation.
  --build-dir PATH      Directory containing documentation to publish.
                        [required]

  --git-binary PATH     Path to git binary.
  --repo-base PATH      Path to base of repository.
  --help                Show this message and exit.
```
