"""Command line tool for pushing to github pages."""
from glob import glob
import os
import shutil
from typing import Callable, NamedTuple, Any, Dict

import click
from plumbum import local

SEP = ":"


class CommitMetaData(NamedTuple):
    """Details about a commit."""

    author: str
    email: str
    message: str

    @classmethod
    def from_git_history(cls, commit_str: str) -> "CommitMetaData":
        """
        Create commit history metadata from the given string.

        :param commit_str: String containing commit metadata.
        :return: CommitMetaData based on given string.
        """
        (author, email, *message) = commit_str.split(SEP)
        return cls(author=author, email=email, message=SEP.join(message))

    def author_string(self) -> str:
        """Get a string describing the author."""
        return f"{self.author} <{self.email}>"


class GitService(object):
    """Service to handle git interactions."""

    def __init__(self, git: Any) -> None:
        """
        Create a new GitService.

        :param git: Git command object.
        """
        self.git = git

    def get_last_commit(self) -> CommitMetaData:
        """Get the commit metadata for the last commit."""
        format = SEP.join([r"%an", r"%ae", r"%s"])
        output = self.git("log", "-n", "1", f'--pretty=format:"{format}"')
        return CommitMetaData.from_git_history(output.strip('"'))

    def git_changes_exist(self) -> bool:
        """Determine if the current directory has any git changes."""
        output = self.git("status", "--short")
        return len(output.strip()) > 0

    def switch_branch(self, branch: str) -> None:
        """
        Switch to the specified branch.

        :param branch: Branch to switch to.
        """
        self.git("checkout", branch)

    def commit_all_files(self, commit_data: CommitMetaData) -> None:
        """
        Commit all files with the given commit metadata.

        :param commit_data: Meta data to use for the commit.
        """
        self.git("add", ".")
        self.git("commit", "-m", commit_data.message, f"--author={commit_data.author_string()}")

    def push_branch(self, branch: str) -> None:
        """
        Push changes on the branch to the origin.

        :param branch: Branch to push.
        """
        self.git("push", "origin", branch)

    def get_active_branch(self) -> str:
        """Get the active branch."""
        return self.git("rev-parse", "--abbrev-ref", "HEAD").strip()


class FileService(object):
    """Service to orchestra file operations."""

    def __init__(self, shutil: Any, globber: Callable, path_ops: Any, file_ops: Any) -> None:
        """
        Create a new FileService.

        :param shutil: shell utilities.
        :param globber: Function to glob directories.
        :param path_ops: Function to operate on paths.
        """
        self.shutil = shutil
        self.globber = globber
        self.path_ops = path_ops
        self.file_ops = file_ops

    def remove(self, target: str) -> None:
        """
        Remove the given file if it exists.

        :param target: File or directory to remove.
        """
        if self.path_ops.exists(target):
            if self.path_ops.isfile(target):
                self.file_ops.remove(target)
            else:
                self.shutil.rmtree(target)

    def move_files(self, parent_dir: str, target_dir: str) -> None:
        """
        Move files under the one directory to another directory.

        :param parent_dir: Path to directory containing files to move.
        :param target_dir: Path to directory to move files to.
        """
        files = self.globber(f"{parent_dir}/*")
        for f in files:
            target_file = f"{target_dir}/{self.path_ops.basename(f)}"
            self.remove(target_file)
            self.shutil.move(f, target_dir)


class GhPushService(object):
    """Service to orchestrate pushing to gh pages."""

    def __init__(self, git_service: GitService, file_service: FileService) -> None:
        """
        Create a new github push service.

        :param git_service: Git service.
        :param file_service: File service.
        """
        self.git_service = git_service
        self.file_service = file_service

    def push_changes(self, repo_base: str, build_dir: str, target_branch: str) -> None:
        """
        Move changes to root of repo, commit them and publish them.

        :param repo_base: Path to base of git repository.
        :param build_dir: Path to directory containing changes to publish.
        :param target_branch: Name of branch to publish to.
        """
        with local.cwd(repo_base):
            active_branch = self.git_service.get_active_branch()
            commit_data = self.git_service.get_last_commit()
            self.git_service.switch_branch(target_branch)

            self.file_service.move_files(build_dir, ".")
            if self.git_service.git_changes_exist():
                self.git_service.commit_all_files(commit_data)
                self.git_service.push_branch(target_branch)

            self.git_service.switch_branch(active_branch)


@click.command()
@click.option("--target-branch", default="gh-pages", help="Branch to publish documentation.")
@click.option(
    "--build-dir",
    type=click.Path(exists=True),
    required=True,
    help="Directory containing documentation to publish.",
)
@click.option("--git-binary", type=click.Path(exists=True), help="Path to git binary.")
@click.option(
    "--repo-base", type=click.Path(exists=True), default=".", help="Path to base of repository."
)
def gh_push(**options: Dict[str, Any]) -> None:
    """
    Publish documentation changes to a github changes branch.

    Move a directory of built documentation from the build directory to 
    the base on the repository on the target github pages branch. If there
    are any changes to the documention, they will be added in a commit under
    the same author and commit message as the last commit message on the active
    branch. 
    """
    target_branch = str(options["target_branch"])
    build_dir = os.path.expanduser(str(options["build_dir"]))
    repo_base = os.path.expanduser(str(options["repo_base"]))
    git_binary = options["git_binary"] or local.which("git")
    git = local[git_binary]

    git_service = GitService(git)
    file_service = FileService(shutil, glob, os.path, os)
    gh_push_service = GhPushService(git_service, file_service)

    gh_push_service.push_changes(repo_base, build_dir, target_branch)
