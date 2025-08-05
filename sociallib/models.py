from pydantic import (
    BaseModel as _BaseModel,
    model_validator as _model_validator
)

from datetime import (
    datetime as _datetime,
    UTC as _UTC,
    timedelta as _timedelta
)
import re as _re

from .errors import UnknownApiError as _UnknownApiError


utctimepattern = _re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).(\d{6})Z")


def UTCTimeModel(utcstring: str):
    if utcstring[0] != "-":
        r = utctimepattern.match(utcstring)
        if r:
            return _datetime(*map(lambda x: int(x), r.groups()), tzinfo=_UTC)
        else:
            raise _UnknownApiError(f"{utcstring} is not compatible with UTCTimeModel", 18)
    else:
        return _datetime(1970, 1, 1) - _datetime.strptime(
            utcstring[3:], "%Y-%m-%dT%H:%M:%S.%fZ"
        )


class CoverModel(_BaseModel):
    filename: str | None
    thumbnail: str
    default: str
    md: str


class ACoverModel(CoverModel):
    orig: str


class CoversModel(_BaseModel):
    id: int
    cover: ACoverModel | CoverModel
    info: str
    order: int

    @_model_validator(mode="before")
    def covervalidate(values: dict):  # type:ignore
        if "orig" in (c := values["cover"]):
            values["cover"] = ACoverModel(**c)
        else:
            values["cover"] = CoverModel(**c)
        return values



class TeamModel(_BaseModel):
    id: int
    slug: str
    slug_url: str
    model: str
    name: str
    cover: CoverModel


class VotesModel(_BaseModel):
    up: int
    down: int
    user: None  #! He causes error


class MiniUserModel(_BaseModel):
    username: str
    id: int


class IdLabelModel(_BaseModel):
    id: int
    label: str


class BranchModel(_BaseModel):
    id: int
    branch_id: int | None
    created_at: _datetime
    teams: list[TeamModel]
    user: MiniUserModel
    moderation: IdLabelModel | None

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        if not values.get("moderation"):
            values["moderation"] = None
        ca = values["created_at"]
        if ca:
            values["created_at"] = UTCTimeModel(ca)
        return values


class IdLabelAbbrModel(_BaseModel):
    id: str
    label: str
    abbr: None


class RatingModel(_BaseModel):
    average: str
    averageFormated: str
    votes: int
    votesFormated: str
    user: int


class AvatarModel(_BaseModel):
    filename: str | None
    url: str


class MeModel(_BaseModel):
    id: int
    username: str
    avatar: AvatarModel
    last_online_at: _datetime
    teams: list[TeamModel]
    permissions: list  #
    roles: list  #
    metadata: dict[str, dict[str, str]]

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        values.update(values.pop("data"))
        ca = values["last_online_at"]
        if ca:
            values["last_online_at"] = UTCTimeModel(ca)
        return values


class SubscrptionModel(_BaseModel):
    is_subscribed: bool
    source_type: str
    source_id: int
    relation: None


class ImageModel(_BaseModel):
    id: int
    image: str
    slug: int
    external: int
    chunks: int
    chapter_id: int
    created_at: _datetime
    updated_at: _datetime | _timedelta  # "-000001-11-30T00:00:00.000000Z"
    height: int
    width: int
    url: str
    ratio: str  # float

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        for times in ["updated_at", "created_at"]:
            ca = values[times]
            if ca:
                values[times] = UTCTimeModel(ca)
        return values


class ContentModel(_BaseModel):
    number: str
    id: int
    volume: str
    name: str | None
    branch_id: int | None

    type: str


class MangaContentModel(ContentModel):
    pages: list[ImageModel]


class ChapterModel(_BaseModel):
    id: int
    index: int
    item_number: int
    number: str
    volume: str
    number_secondary: str
    name: str | None
    branches_count: int
    branches: list[BranchModel]
"""
created_at: str
expired_at: None
expired_type: int
publish_at: None
teams: list
moderated: IdLabelModel
likes_count: int
is_liked: bool
is_viewed: bool
manga_id: int
model: str
slug: int
branch_id: str | None

type: str
pages: list
"""


class PlayerVideoQualityModel(_BaseModel):
    href: str
    quality: int
    bitrate: int


class PlayerVideoModel(_BaseModel):
    id: int
    quality: list[PlayerVideoQualityModel]


class PlayerSubtitleModel(_BaseModel):
    id: int
    format: str
    name: str
    filename: str
    src: str


class StatsModel(_BaseModel):
    value: int
    formated: str
    short: str
    label: str
    tag: str


class NovelModel(_BaseModel):
    id: int
    name: str
    rus_name: str
    eng_name: str | None
    slug: str
    slug_url: str
    cover: CoverModel
    ageRestriction: dict[str, int | str]
    site: int
    type: IdLabelModel
    model: str
    status: IdLabelModel
    releaseDateString: str


class AverUserModel(_BaseModel):
    id: int
    username: str
    avatar: AvatarModel
    last_online_at: _datetime | None

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        ca = values["last_online_at"]
        if ca:
            values["last_online_at"] = UTCTimeModel(ca)
        return values


class BlockItemsModel(_BaseModel):
    item_type: str
    item_id: int
    comment: str
    related: NovelModel


class CollectionPreviewBlockModel(_BaseModel):
    collections_id: int
    uuid: str
    name: str
    items: list[BlockItemsModel]


class CollectionModel(_BaseModel):
    description: dict | None
    attachments: list | None = None  #
    user: None | AverUserModel = None  #
    subscription: None | SubscrptionModel = None  #
    blocks: None | list[CollectionPreviewBlockModel] = None  #

    id: int
    model: str
    name: str
    type: str
    views: int
    favorites_count: int
    items_count: int
    comments_count: int
    votes: VotesModel
    user_id: int
    site_id: int
    created_at: _datetime
    updated_at: _datetime
    spoiler: bool
    interactive: bool
    adult: bool
    previews: None | list[CoverModel] = None  #

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        # error doing
        stop = False
        if "attachments" in values and (x := values["attachments"]) != []:
            print(f"CollectionPreviewModel: attachments = {x}, type = {type(x)}")
            stop = True
        if stop:
            from os import _exit
            _exit(0)
        for e in ["description",
                  "attachments",
                  "user",
                  "subscription",
                  "blocks"]:
            if e not in values:
                values[e] = None

        for times in ["updated_at", "created_at"]:
            ca = values[times]
            if ca:
                values[times] = UTCTimeModel(ca)
        return values


class PlayerTeamModel(TeamModel):
    stats: list[StatsModel]


class TimecodeModel(_BaseModel):
    type: str
    _from: str  # 22:23
    to: str  # 10:05

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        values["_from"] = values.pop("from")
        return values


class PlayerModel(_BaseModel):
    id: int
    episode_id: int
    player: str
    translation_type: IdLabelModel
    team: PlayerTeamModel
    created_at: _datetime
    views: int
    timecode: list[TimecodeModel] | None
    subtitles: list[PlayerSubtitleModel] | None
    video: PlayerVideoModel | None

    src: str

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        for name in ["src", "video", "subtitles", "timecode"]:
            if name not in values:
                values[name] = None  #!
        ca = values["created_at"]
        if ca:
            values["created_at"] = UTCTimeModel(ca)
        return values


class PeopleModel(_BaseModel):
    id: int
    slug: str
    slug_url: str
    model: str
    name: str
    rus_name: str | None
    alt_name: str | None
    cover: CoverModel
    subscription: SubscrptionModel
    confirmed: bool
    user_id: int
    titles_count_details: dict[str, int]
    stats: list[StatsModel]


class FranchiseModel(_BaseModel):
    id: int
    slug: str
    slug_url: str
    model: str
    name: str
    alt_name: str
    subscription: SubscrptionModel
    stats: list[StatsModel]
    titles_count_details: dict[str, int]


class EpisodeModel(_BaseModel):
    id: int
    model: str
    name: str
    number: str
    number_secondary: str
    season: str
    status: IdLabelAbbrModel
    anime_id: int
    created_at: _datetime
    players: list[PlayerModel]
    type: str

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        ca = values["created_at"]
        if ca:
            values["created_at"] = UTCTimeModel(ca)
        return values


class UserModel(AverUserModel):
    created_at: _datetime

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        for times in ["last_online_at", "created_at"]:
            ca = values[times]
            if ca:
                values[times] = UTCTimeModel(ca)
        return values


class RanobeModel(NovelModel):
    releaseDate: str | None  # must be "", "2019", "2015, 2016"
    rating: RatingModel


class AnimeModel(RanobeModel):
    shiki_rate: None


class AniChapterModel(_BaseModel):
    id: int
    model: str
    name: str
    number: str
    number_secondary: str
    season: str
    status: IdLabelAbbrModel
    anime_id: int
    created_at: _datetime
    item_number: int
    type: str

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        ca = values["created_at"]
        if ca:
            values["created_at"] = UTCTimeModel(ca)
        return values


class MangaModel(RanobeModel):  #
    pass


class NotificationDataMediaModel(_BaseModel):
    id: int
    name: str
    rus_name: str
    eng_name: str
    model: str
    slug: str
    slug_url: str
    cover: CoverModel
    site: int


class NotificationUserModel(_BaseModel):
    id: int
    username: str
    avatar: AvatarModel


class NotificationTeamModel(_BaseModel):
    id: int
    slug: str
    slug_url: str
    model: str
    name: str
    cover: dict
    vk: str | None
    discord: str | None

    @_model_validator(mode="before")
    def missingvalidate(values: dict):  # type:ignore
        for k in ["discord", "vk"]:
            if k not in values.keys():
                values[k] = None
        return values


class NotificationChapterModel(_BaseModel):
    id: int
    model: str
    volume: str
    number: str
    name: str
    branch_id: int | None
    manga_id: int | None
    expired_at: _datetime | None

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        ca = values["expired_at"]
        if ca:
            values["created_at"] = UTCTimeModel(ca)
        return values


class NotificationDataItemModel(_BaseModel):
    id: int
    slug: str
    slug_url: str
    model: str
    name: str
    rus_name: str | None
    cover: CoverModel

    @_model_validator(mode="before")
    def missingvalidate(values: dict):  # type:ignore
        for k in ["rus_name"]:
            if k not in values.keys():
                values[k] = None
        return values


class NotificationDataModel1(_BaseModel):
    user: NotificationUserModel
    chapter: NotificationChapterModel
    media: NotificationDataMediaModel
    teams: list[TeamModel]
    is_new: bool


class NotificationDataModel2(_BaseModel):
    user: NotificationUserModel
    media: NotificationDataMediaModel
    teams: list[TeamModel]
    is_new: bool
    count: int


class NotificationDataModel3(_BaseModel):
    item: NotificationDataItemModel
    media: NotificationDataMediaModel
    subscription_type: str
    is_new: bool


def NotificationDataModel(values: dict):
    keys = set(values.keys())
    for m in [
            NotificationDataModel1,
            NotificationDataModel2,
            NotificationDataModel3
            ]:
        if set(m.model_fields.keys()) == keys:
            return m(**values)
    else:
        raise _UnknownApiError(f"NotificationDataModel keys do not match known keys {values}", 567)


class NotificationModel(_BaseModel):
    id: int
    type: str
    category: str
    data: NotificationDataModel1 | NotificationDataModel2 | NotificationDataModel3
    content: dict
    created_at: _datetime

    @_model_validator(mode="before")
    def utcvalidate(values: dict):  # type:ignore
        ca = values["created_at"]
        if ca:
            values["created_at"] = UTCTimeModel(ca)
        values["data"] = NotificationDataModel(values["data"])
        return values

