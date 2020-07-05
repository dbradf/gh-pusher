"""Unit tests for gh_pusher.py"""
from string import ascii_letters, digits, whitespace
from unittest.mock import MagicMock

from hypothesis import given
import hypothesis.strategies as st

import ghpusher.gh_pusher as under_test

NAME_ALPHABET = list(ascii_letters + digits + whitespace)
MESSAGE_ALPHABET = st.characters(blacklist_characters='"')


class TestCommitMetaData:
    @given(
        st.text(alphabet=NAME_ALPHABET, min_size=1), st.emails(), st.text(min_size=1),
    )
    def test_auther_string(self, author, email, message):
        commit_data = under_test.CommitMetaData(author, email, message)

        assert author in commit_data.author_string()
        assert f"<{email}>" in commit_data.author_string()


def mocked_git_service():
    return under_test.GitService(MagicMock())


class TestGitService:
    @given(
        author=st.text(alphabet=NAME_ALPHABET, min_size=1),
        email=st.emails(),
        message=st.text(alphabet=MESSAGE_ALPHABET, min_size=1),
    )
    def test_get_last_commit(self, author, email, message):
        git_service = mocked_git_service()
        git_service.git.return_value = f"{author}:{email}:{message}"

        commit_data = git_service.get_last_commit()

        assert commit_data.author == author
        assert commit_data.email == email
        assert commit_data.message == message

    def test_git_changes_exist_true(self):
        git_service = mocked_git_service()
        git_service.git.return_value = "some\nfound\nfiles"

        assert git_service.git_changes_exist()

    def test_git_changes_exist_false(self):
        git_service = mocked_git_service()
        git_service.git.return_value = ""

        assert not git_service.git_changes_exist()

    @given(branch=st.text(alphabet=list(ascii_letters), min_size=1))
    def test_switch_branches(self, branch):
        git_service = mocked_git_service()
        git_service.switch_branch(branch)

        git_service.git.assert_called_with("checkout", branch)

    @given(
        author=st.text(alphabet=NAME_ALPHABET, min_size=1),
        email=st.emails(),
        message=st.text(alphabet=MESSAGE_ALPHABET, min_size=1),
    )
    def test_commit_all_files(self, author, email, message):
        git_service = mocked_git_service()
        commit_data = under_test.CommitMetaData(author, email, message)

        git_service.commit_all_files(commit_data)

        git_service.git.assert_any_call("add", ".")
        git_service.git.assert_any_call("commit", "-m", message, f"--author={author} <{email}>")

    @given(branch=st.text(alphabet=list(ascii_letters), min_size=1))
    def test_push_branch(self, branch):
        git_service = mocked_git_service()
        git_service.push_branch(branch)

        git_service.git.assert_called_with("push", "origin", branch)

    @given(branch=st.text(alphabet=list(ascii_letters), min_size=1))
    def test_get_active_branch(self, branch):
        git_service = mocked_git_service()
        git_service.git.return_value = f"{branch}\n\n"

        active_branch = git_service.get_active_branch()

        assert active_branch == branch


def mocked_file_service():
    return under_test.FileService(MagicMock(), MagicMock(), MagicMock(), MagicMock())


class TestFileSerice:
    @given(
        target_dir=st.text(alphabet=list(ascii_letters), min_size=1),
        parent_dir=st.text(alphabet=list(ascii_letters), min_size=1),
        file_list=st.lists(st.text(alphabet=list(ascii_letters), min_size=1)),
    )
    def test_move_files(self, file_list, target_dir, parent_dir):
        file_service = mocked_file_service()

        file_service.path_ops.exists.return_value = False
        file_service.globber.return_value = file_list

        file_service.move_files(parent_dir, target_dir)

        file_service.globber.assert_called_with(f"{parent_dir}/*")
        assert file_service.shutil.move.call_count == len(file_list)
        for f in file_list:
            file_service.shutil.move.assert_any_call(f, target_dir)

    @given(target=st.text(alphabet=list(ascii_letters), min_size=1))
    def test_remove_a_file(self, target):
        file_service = mocked_file_service()

        file_service.path_ops.exists.return_value = True
        file_service.path_ops.isfile.return_value = True

        file_service.remove(target)

        file_service.file_ops.remove.assert_called_with(target)

    @given(target=st.text(alphabet=list(ascii_letters), min_size=1))
    def test_remove_a_directory(self, target):
        file_service = mocked_file_service()

        file_service.path_ops.exists.return_value = True
        file_service.path_ops.isfile.return_value = False

        file_service.remove(target)

        file_service.shutil.rmtree.assert_called_with(target)
