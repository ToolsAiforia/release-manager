from datetime import datetime

from pydantic import BaseModel, Field


class RepoInfo(BaseModel):
    name: str
    path: str
    current_branch: str
    has_uncommitted: bool


class TagInfo(BaseModel):
    name: str
    commit_hash: str
    date: datetime
    is_release: bool = False


class CommitInfo(BaseModel):
    hash: str
    short_hash: str
    message: str
    author: str
    date: datetime
    linear_keys: list[str] = Field(default_factory=list)


class RepoSelection(BaseModel):
    repo_name: str
    from_tag: str
    to_tag: str


class RepoReport(BaseModel):
    repo_name: str
    from_tag: str
    to_tag: str
    commits: list[CommitInfo] = Field(default_factory=list)
    linear_keys: list[str] = Field(default_factory=list)


class ReleaseReport(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.now)
    root_dir: str
    repos: list[RepoReport] = Field(default_factory=list)
    all_linear_keys: list[str] = Field(default_factory=list)
