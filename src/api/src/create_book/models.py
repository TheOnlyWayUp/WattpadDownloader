from typing import List, Optional, TypedDict


class CopyrightData(TypedDict):
    name: str
    statement: str
    freedoms: str
    printing: str
    image_url: Optional[str]


class Language(TypedDict):
    name: str


class User(TypedDict):
    username: str
    avatar: str
    description: str


class Part(TypedDict):
    id: int
    title: str


class Story(TypedDict):
    id: str
    title: str
    createDate: str
    modifyDate: str
    language: Language
    user: User
    description: str
    cover: str
    completed: bool
    tags: List[str]
    mature: bool
    url: str
    parts: List[Part]
    isPaywalled: bool
    copyright: int
