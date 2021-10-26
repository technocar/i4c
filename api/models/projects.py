from datetime import datetime
from typing import List, Tuple, Optional, Union, Dict
from pydantic import BaseModel, Field
from models import ProjectStatusEnum, ProjectVersionStatusEnum


class KeyValue(BaseModel):
    key: str
    value: str


class Project(BaseModel):
    name: str
    status: ProjectStatusEnum
    versions: List[str] = Field(..., title="List of versions. Numbers are version numbers others are labels.")
    extra: List[KeyValue]
    created_at: datetime


class ProjectIn(BaseModel):
    name: str
    status: ProjectStatusEnum
    extra: Optional[List[Dict[str, str]]]


class GitFile(BaseModel):
    repo: str
    name: str
    commit: str


class UncFile(BaseModel):
    name: str


class IntFile(BaseModel):
    name: str
    ver: str


class ProjFile(BaseModel):
    savepath: str
    file: Union[GitFile, UncFile, IntFile]


class ProjectVersion(BaseModel):
    ver: int = Field(..., title="Version number.")
    labels: List[str] = Field(..., title="List of labels.")
    status: ProjectVersionStatusEnum
    files: List[ProjFile]


async def get_projects(credentials, name=None, status=None, cre_after=None, cre_before=None, file=None):
    # todo 1: **********
    return []
