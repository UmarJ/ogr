import os
import unittest

import pytest

from requre.storage import PersistentObjectStorage

from ogr import PagureService
from ogr.abstract import PRStatus, IssueStatus
from ogr.exceptions import PagureAPIException, OgrException

DATA_DIR = "test_data"
PERSISTENT_DATA_PREFIX = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), DATA_DIR
)


class PagureTests(unittest.TestCase):
    def setUp(self):
        self.token = os.environ.get("PAGURE_TOKEN")
        test_name = self.id() or "all"
        self.persistent_data_file = os.path.join(
            PERSISTENT_DATA_PREFIX, f"test_pagure_data_{test_name}.yaml"
        )

        PersistentObjectStorage().storage_file = self.persistent_data_file

        if PersistentObjectStorage().is_write_mode and (not self.token):
            raise EnvironmentError("please set PAGURE_TOKEN env variables")

        self.service = PagureService(token=self.token, instance_url="https://pagure.io")
        self._user = None
        self._ogr_project = None
        self._ogr_fork = None

    @property
    def user(self):
        if not self._user:
            self._user = self.service.user.get_username()
        return self._user

    @property
    def ogr_project(self):
        if not self._ogr_project:
            self._ogr_project = self.service.get_project(
                namespace=None, repo="ogr-tests"
            )
        return self._ogr_project

    @property
    def ogr_fork(self):
        if not self._ogr_fork:
            self._ogr_fork = self.service.get_project(
                namespace=None, repo="ogr-tests", username=self.user, is_fork=True
            )
        return self._ogr_fork

    def tearDown(self):
        PersistentObjectStorage().dump()


class Comments(PagureTests):
    def test_pr_comments(self):
        pr_comments = self.ogr_project.get_pr_comments(pr_id=4)
        assert pr_comments
        print(pr_comments[0].comment, pr_comments[1].comment, pr_comments[2].comment)
        assert len(pr_comments) == 3
        assert pr_comments[0].comment.endswith("1")

    def test_pr_comments_reversed(self):
        pr_comments = self.ogr_project.get_pr_comments(pr_id=4, reverse=True)
        assert pr_comments
        assert len(pr_comments) == 3
        assert pr_comments[2].comment.endswith("1")

    def test_pr_comments_filter(self):
        pr_comments = self.ogr_project.get_pr_comments(pr_id=4, filter_regex="1")
        assert pr_comments
        assert len(pr_comments) == 1
        assert pr_comments[0].comment == "PR comment 1"

        pr_comments = self.ogr_project.get_pr_comments(
            pr_id=4, filter_regex="PR comment [0-9]*"
        )
        assert pr_comments
        assert len(pr_comments) == 2
        assert pr_comments[0].comment.endswith("1")

    def test_pr_comments_search(self):
        comment_match = self.ogr_project.search_in_pr(pr_id=1, filter_regex="New")
        assert comment_match
        print(comment_match)
        assert comment_match[0] == "New"

        comment_match = self.ogr_project.search_in_pr(
            pr_id=1, filter_regex="Pull-Request has been merged by [a-z]*"
        )
        print(comment_match)
        assert comment_match
        assert comment_match[0].startswith("Pull")


class GenericCommands(PagureTests):
    def test_description(self):
        description = self.ogr_project.get_description()
        assert description.startswith("Testing repository for python-ogr package")

    def test_branches(self):
        branches = self.ogr_project.get_branches()
        assert branches
        assert set(branches) == {"master"}

    def test_get_releases(self):
        releases = self.ogr_project.get_releases()
        assert len(releases) == 0

    def test_git_urls(self):
        urls = self.ogr_project.get_git_urls()
        assert urls
        assert len(urls) == 2
        assert "git" in urls
        assert "ssh" in urls
        assert urls["git"] == "https://pagure.io/ogr-tests.git"
        assert urls["ssh"].endswith("ssh://git@pagure.io/ogr-tests.git")

    def test_username(self):
        # changed to check just lenght, because it is based who regenerated data files
        assert len(self.service.user.get_username()) > 3

    def test_get_file(self):
        file_content = self.ogr_project.get_file_content("README.rst")
        assert file_content
        assert isinstance(file_content, str)
        assert "This is a testing repo" in file_content

    def test_nonexisting_file(self):
        with self.assertRaises(Exception) as _:
            self.ogr_project.get_file_content(".blablabla_nonexisting_file")

    def test_parent_project(self):
        assert self.ogr_fork.parent.namespace is None
        assert self.ogr_fork.parent.repo == "ogr-tests"

    def test_commit_statuses(self):
        flags = self.ogr_project.get_commit_statuses(
            commit="d87466de81c72231906a6597758f37f28830bb71"
        )
        assert isinstance(flags, list)
        assert len(flags) == 0

    def test_get_owners(self):
        owners = self.ogr_fork.get_owners()
        assert [self.user] == owners

    def test_pr_permissions(self):
        owners = self.ogr_project.who_can_merge_pr()
        assert "lachmanfrantisek" in owners
        assert self.ogr_project.can_merge_pr("lachmanfrantisek")

    def test_get_web_url(self):
        url = self.ogr_project.get_web_url()
        assert url == "https://pagure.io/ogr-tests"

    def test_full_repo_name(self):
        assert self.ogr_project.full_repo_name == "ogr-tests"
        assert (
            self.service.get_project(namespace="mbi", repo="ansible").full_repo_name
            == "mbi/ansible"
        )

        # test forks
        assert self.ogr_fork.full_repo_name == f"fork/{self.user}/ogr-tests"
        assert (
            self.service.get_project(
                namespace="Fedora-Infra",
                repo="ansible",
                username=self.user,
                is_fork=True,
            ).full_repo_name
            == f"fork/{self.user}/Fedora-Infra/ansible"
        )


class Service(PagureTests):
    def test_project_create(self):
        """
        Remove https://pagure.io/$USERNAME/new-ogr-testing-repo before data regeneration
        """
        name = "new-ogr-testing-repo"
        project = self.service.get_project(repo=name, namespace=None)
        assert not project.exists()

        new_project = self.service.project_create(repo=name)
        assert new_project.exists()
        assert new_project.repo == name

        project = self.service.get_project(repo=name, namespace=None)
        assert project.exists()

    def test_project_create_in_the_group(self):
        """
        Remove https://pagure.io/packit-service/new-ogr-testing-repo-in-the-group
        before data regeneration
        """
        name = "new-ogr-testing-repo-in-the-group"
        namespace = "packit-service"
        project = self.service.get_project(repo=name, namespace=namespace)
        assert not project.exists()

        new_project = self.service.project_create(repo=name, namespace=namespace)
        assert new_project.exists()
        assert new_project.repo == name

        project = self.service.get_project(repo=name, namespace=namespace)
        assert project.exists()

    def test_project_create_invalid_namespace(self):
        name = "new-ogr-testing-repo"
        namespace = "nonexisting"

        with pytest.raises(OgrException):
            self.service.project_create(repo=name, namespace=namespace)
        project = self.service.get_project(repo=name, namespace=namespace)
        assert not project.exists()


class Issues(PagureTests):
    def test_issue_list(self):
        issue_list = self.ogr_project.get_issue_list()
        assert isinstance(issue_list, list)

        issue_list = self.ogr_project.get_issue_list(status=IssueStatus.all)
        assert issue_list
        assert len(issue_list) >= 2


class PullRequests(PagureTests):
    def test_pr_create(self):
        pr = self.ogr_fork.pr_create(
            title="Testing PR",
            body="Body of the testing PR.",
            target_branch="master",
            source_branch="master",
        )
        assert pr.title == "Testing PR"
        assert pr.description == "Body of the testing PR."
        assert pr.target_branch == "master"
        assert pr.source_branch == "master"
        assert pr.status == PRStatus.open

    def test_pr_list(self):
        pr_list_default = self.ogr_project.get_pr_list()
        assert isinstance(pr_list_default, list)

        pr_list = self.ogr_project.get_pr_list(status=PRStatus.all)
        assert pr_list
        assert len(pr_list) >= 2

        assert len(pr_list_default) < len(pr_list)

    def test_pr_info(self):
        pr_info = self.ogr_project.get_pr_info(pr_id=1)
        assert pr_info
        assert pr_info.title.startswith("Add README file")
        assert pr_info.status == PRStatus.merged


class Forks(PagureTests):
    def test_fork(self):
        assert self.ogr_fork.exists()
        assert self.ogr_fork.is_fork
        fork_description = self.ogr_fork.get_description()
        assert fork_description
        a = self.ogr_fork.parent
        assert a
        is_forked = a.is_forked()
        assert is_forked and isinstance(is_forked, bool)
        fork = a.get_fork(create=False)
        assert fork
        assert fork.is_fork
        urls = fork.get_git_urls()
        assert "{username}" not in urls["ssh"]

    def test_nonexisting_fork(self):
        ogr_project_non_existing_fork = self.service.get_project(
            namespace=None,
            repo="ogr-tests",
            username="qwertzuiopasdfghjkl",
            is_fork=True,
        )
        assert not ogr_project_non_existing_fork.exists()
        with self.assertRaises(PagureAPIException) as ex:
            ogr_project_non_existing_fork.get_description()
        assert "Project not found" in ex.exception.pagure_error

    def test_fork_property(self):
        fork = self.ogr_project.get_fork()
        assert fork
        assert fork.get_description()

    def test_create_fork(self):
        """
        Remove your fork of ogr-tests https://pagure.io/fork/$USER/ogr-tests
        before regeneration data.
        But other tests needs to have already existed user fork.
        So regenerate data for other tests, remove  data file for this test
        and regenerate it again.
        """
        not_existing_fork = self.ogr_project.get_fork(create=False)
        assert not not_existing_fork
        assert not self.ogr_project.is_forked()

        old_forks = self.ogr_project.service.user.get_forks()

        self.ogr_project.fork_create()

        assert self.ogr_project.get_fork().exists()
        assert self.ogr_project.is_forked()

        new_forks = self.ogr_project.service.user.get_forks()
        assert len(old_forks) == len(new_forks) - 1


class PagureProjectTokenCommands(PagureTests):
    def setUp(self):
        self.token = os.environ.get("PAGURE_OGR_TEST_TOKEN")
        test_name = self.id() or "all"
        self.persistent_data_file = os.path.join(
            PERSISTENT_DATA_PREFIX, f"test_pagure_data_{test_name}.yaml"
        )

        PersistentObjectStorage().storage_file = self.persistent_data_file

        if PersistentObjectStorage().is_write_mode and (not self.token):
            raise EnvironmentError("please set PAGURE_OGR_TEST_TOKEN env variables")

        self.service = PagureService(token=self.token, instance_url="https://pagure.io")
        self._user = None
        self._ogr_project = None
        self._ogr_fork = None

    def test_issue_permissions(self):
        owners = self.ogr_project.who_can_close_issue()
        assert "lachmanfrantisek" in owners

        issue = self.ogr_project.get_issue_info(2)
        assert self.ogr_project.can_close_issue("lachmanfrantisek", issue)

    def test_issue_comments(self):
        issue_comments = self.ogr_project._get_all_issue_comments(issue_id=3)
        assert issue_comments
        assert len(issue_comments) == 4
        assert issue_comments[0].comment.startswith("test")
        assert issue_comments[1].comment.startswith("tests")

    def test_issue_info(self):
        issue_info = self.ogr_project.get_issue_info(issue_id=2)
        assert issue_info
        assert issue_info.title.startswith("Test 1")
        assert issue_info.status == IssueStatus.closed

    def test_issue_comments_reversed(self):
        issue_comments = self.ogr_project.get_issue_comments(issue_id=3, reverse=True)
        assert len(issue_comments) == 4
        assert issue_comments[0].comment.startswith("regex")

    def test_issue_comments_regex(self):
        issue_comments = self.ogr_project.get_issue_comments(
            issue_id=3, filter_regex="regex"
        )
        assert len(issue_comments) == 2
        assert issue_comments[0].comment.startswith("let's")

    def test_issue_comments_regex_reversed(self):
        issue_comments = self.ogr_project.get_issue_comments(
            issue_id=3, filter_regex="regex", reverse=True
        )
        assert len(issue_comments) == 2
        assert issue_comments[0].comment.startswith("regex")

    def test_update_pr_info(self):
        pr_info = self.ogr_project.get_pr_info(pr_id=4)
        orig_title = pr_info.title
        orig_description = pr_info.description

        self.ogr_project.update_pr_info(
            pr_id=4, title="changed", description="changed description"
        )
        pr_info = self.ogr_project.get_pr_info(pr_id=4)
        assert pr_info.title == "changed"
        assert pr_info.description == "changed description"

        self.ogr_project.update_pr_info(
            pr_id=4, title=orig_title, description=orig_description
        )
        pr_info = self.ogr_project.get_pr_info(pr_id=4)
        assert pr_info.title == orig_title
        assert pr_info.description == orig_description

    def test_pr_comments_author_regex(self):
        comments = self.ogr_project.get_pr_comments(
            pr_id=4, filter_regex="^regex", author="mfocko"
        )
        assert len(comments) == 1
        assert comments[0].comment.endswith("test")

    def test_pr_comments_author(self):
        comments = self.ogr_project.get_pr_comments(pr_id=4, author="lachmanfrantisek")
        assert len(comments) == 0

    def test_issue_comments_author_regex(self):
        comments = self.ogr_project.get_issue_comments(
            issue_id=3, filter_regex="^test[s]?$", author="mfocko"
        )
        assert len(comments) == 2
        assert comments[0].comment == "test"
        assert comments[1].comment == "tests"

    def test_issue_comments_author(self):
        comments = self.ogr_project.get_issue_comments(
            issue_id=3, author="lachmanfrantisek"
        )
        assert len(comments) == 0
