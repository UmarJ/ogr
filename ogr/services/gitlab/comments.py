# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import Union

from gitlab.v4.objects import ProjectIssueNote, ProjectMergeRequestNote

from ogr.abstract import IssueComment, PRComment


# TODO: Keep reference to (ogr's) Issue/PR


class GitlabCommentParser:
    def _from_raw_comment(
        self, raw_comment: Union[ProjectIssueNote, ProjectMergeRequestNote]
    ) -> None:
        self.__raw_comment = raw_comment
        self.comment = raw_comment.body
        self.author = raw_comment.author["username"]
        self.created = raw_comment.created_at
        self.edited = raw_comment.updated_at


class GitlabIssueComment(GitlabCommentParser, IssueComment):
    def __str__(self) -> str:
        return "Gitlab" + super().__str__()


class GitlabPRComment(GitlabCommentParser, PRComment):
    def __str__(self) -> str:
        return "Gitlab" + super().__str__()
