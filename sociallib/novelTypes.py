from typing import (
    Any       as _Any,
    Literal   as _Literal,
    TypeAlias as _TypeAlias,
)

import httpx as _httpx

from sociallib.errors import UnknownApiError as _UnknownApiError

from .addition_tools import (
    Chapter        as _Chapter,
    ChapterContent as _ChapterContent,
    fullname       as _fullname,
    _save_json_get_request,
    _save_json_iter_pages_get_request,
)
from .constants import (
    SITE_HENTAILIB    as _SITE_HENTAILIB,
    SITE_MANGALIB     as _SITE_MANGALIB,
    SITE_RANOBELIB    as _SITE_RANOBELIB,
    SITE_SLASHLIB     as _SITE_SLASHLIB,
    mangalib_api_link as _mangalib_api_link,
)

from .models import (
    AniChapterModel   as _AniChapterModel,
    AnimeModel        as _AnimeModel,
    BranchModel       as _BranchModel,
    CollectionModel   as _CollectionModel,
    CoversModel       as _CoversModel,
    EpisodeModel      as _EpisodeModel,
    FranchiseModel    as _FranchiseModel,
    MeModel           as _MeModel,
    NotificationModel as _NotificationModel,
    NovelModel        as _NovelModel,
    PeopleModel       as _PeopleModel,
    RanobeModel       as _RanobeModel,
    TeamModel         as _TeamModel,
    UserModel         as _UserModel,
)

InfoAlias: _TypeAlias = _Literal["background"] | _Literal["eng_name"] | _Literal["otherNames"] | _Literal["summary"] | _Literal["releaseDate"] | _Literal["type_id"] | _Literal["caution"] | _Literal["views"] | _Literal["close_view"] | _Literal["rate_avg"] | _Literal["rate"] | _Literal["genres"] | _Literal["tags"] | _Literal["teams"] | _Literal["user"] | _Literal["franchise"] | _Literal["authors"] | _Literal["publisher"] | _Literal["userRating"] | _Literal["moderated"] | _Literal["metadata"] | _Literal["metadata.count"] | _Literal["metadata.close_comments"] | _Literal["manga_status_id"] | _Literal["chap_count"] | _Literal["status_id"] | _Literal["artists"] | _Literal["format"]

class Ranobe:
    def __init__(
        self,
        session: _httpx.AsyncClient,
        rawdata: dict = {},
        auth_token=None,
        model=None,
        print_warnings=True,
    ):
        self.session = session
        self.beriar: dict[str, str] | None = auth_token
        if model:
            self.model = model
        elif rawdata != {}:
            try:
                self.model = _RanobeModel(**rawdata)
            except Exception as e:
                if type(e).__name__ == "ValidationError":
                    self.model = _NovelModel(**rawdata)
                else:
                    raise
        elif print_warnings:
            print(f"WARNING: model is not defined!")
        self.last_chapters: None | list[_Chapter] = None
        self.last_addition_info: dict[str, _Any] = rawdata

    async def recover_model(self, slug_url: str, use_auth: bool = False):
        resp = (await _save_json_get_request(
                    f"{_mangalib_api_link}api/manga/{slug_url}?{'&'.join(map(lambda x: 'fields[]=' + x, ['releaseDate', 'rate']))}", self.session, headers={} if not use_auth else self.beriar
                ))["data"]
        self.__init__(
            self.session,
            resp,
            self.beriar,
        )
        return self

    async def chapter(self, volume: int, number: int, translator_id: int | str | None = None):
        return _ChapterContent(
            (
                await _save_json_get_request(
                    "{}api/manga/{}/chapter?{}number={}&volume={}".format(
                        _mangalib_api_link,
                        self.model.slug_url,
                        "" if translator_id is None else f"branch_id={translator_id}&",
                        number,
                        volume,
                    ),
                    self.session,
                    headers=self.beriar,
                )
            )["data"]
        )

    async def chapters(self):
        chapters = await _save_json_get_request(
            f"{_mangalib_api_link}api/manga/{self.model.slug_url}/chapters", self.session, self.beriar
        )
        chapters = list(
            map(
                lambda x: _Chapter(
                    x, self.model.slug_url, self.session, auth_token=self.beriar
                ),
                chapters["data"],
            )
        )
        self.last_chapters = chapters
        return chapters

    async def translators_branches(self, chapters_indexes: slice = slice(0, None)) -> list[_BranchModel]:
        if (x := self.last_chapters) is None:
            chapters = (await self.chapters())[chapters_indexes]
        else:
            chapters = x[chapters_indexes]
        all_branches: list[int] = []
        all_transl: list[_BranchModel] = []
        for e in chapters:
            for teambr in e.model.branches:
                if teambr.branch_id not in all_branches:
                    all_branches.append(teambr.branch_id)
                    all_transl.append(teambr)
        return all_transl

    async def addition_info(
        self,
        infs: list[InfoAlias] = [
            "background",
            "eng_name",
            "otherNames",
            "summary",
            "releaseDate",
            "type_id",
            "caution",
            "views",
            "close_view",
            "rate_avg",
            "rate",
            "genres",
            "tags",
            "teams",
            "user",
            "franchise",
            "authors",
            "publisher",
            "userRating",
            "moderated",
            "metadata",
            "metadata.count",
            "metadata.close_comments",
            "manga_status_id",
            "chap_count",
            "status_id",
            "artists",
            "format",
        ],
        use_cached_data = True,
        auth = False
    ):
        if use_cached_data:
            true_infs = []
            for e in infs:
                if e not in self.last_addition_info:
                    true_infs.append(e)
        else:
            true_infs = infs
        if len(true_infs) or not use_cached_data:
            resp = (await _save_json_get_request(
                _mangalib_api_link
                + f"api/manga/{self.model.slug_url}?{'&'.join(map(lambda x: "fields[]=" + x, true_infs))}",
                self.session,
                headers = self.beriar if auth else {}
            ))["data"]
            self.last_addition_info.update(resp)
            return resp
        if len(infs) == 0:
            return self.last_addition_info
        else:
            return {k: self.last_addition_info[k]
                    for k in infs}

    async def covers(self):
        return list(map(lambda x: _CoversModel(**x), (await _save_json_get_request(f"{_mangalib_api_link}api/manga/{self.model.slug_url}/covers", self.session))["data"]))

    async def similar(self):
        return await _save_json_get_request(
            _mangalib_api_link + f"api/manga/{self.model.slug_url}/similar", self.session
        )

    def __repr__(self) -> str:
        return f"<{_fullname(self)} object: slug_url={self.model.slug_url}>"


class Manga(Ranobe): pass
class Hentai(Manga): pass
class Slash(Hentai): pass
class Anime:
    def __init__(
        self,
        session: _httpx.AsyncClient,
        rawdata: dict = {},
        auth_token=None,
        model=None,
    ) -> None:
        self.session = session
        self.beriar: dict[str, str] | None = auth_token
        self.last_chapters: list[_AniChapterModel] | None = None
        if model:
            self.model = model
        elif rawdata != {}:
            self.model = _AnimeModel(**rawdata)

    async def recover_model(self, slug_url: str):
        self.__init__(
            self.session,
            (
                await _save_json_get_request(
                    f"{_mangalib_api_link}api/manga/{slug_url}", self.session
                )
            )["data"],
            self.beriar,
        )
        return self

    async def chapters(self) -> list[_AniChapterModel]:
        self.last_chapters = list(
            map(
                lambda x: _AniChapterModel(**x),
                (
                    await _save_json_get_request(
                        _mangalib_api_link
                        + f"api/episodes?anime_id={self.model.slug_url}",
                        self.session,
                    )
                )["data"],
            )
        )
        return self.last_chapters

    async def episode(self, episode_id):
        return _EpisodeModel(
            **(
                await _save_json_get_request(
                    _mangalib_api_link + f"api/episodes/{episode_id}", self.session
                )
            )["data"]
        )

    async def stats(self):
        return await _save_json_get_request(
            _mangalib_api_link
            + f"api/anime/{self.model.slug_url}/stats?bookmarks=true&rating=true",
            self.session,
        )

    async def similar(self):
        return await _save_json_get_request(
            _mangalib_api_link + f"api/anime/{self.model.slug_url}/similar", self.session
        )

    async def relations(self):
        return await _save_json_get_request(
            _mangalib_api_link + f"api/anime/{self.model.slug_url}/relations",
            self.session,
        )

    async def comments(self, page_min=1, page_max=1):
        return await _save_json_iter_pages_get_request(
            _mangalib_api_link
            + "api/comments?page={}"
            + f"&post_id={self.model.id}&post_type=anime&sort_by=id&sort_type=desc",
            self.session,
            lambda x: not x["mata"]["has_next_page"],
            page_min=page_min,
            page_max=page_max,
        )

    async def sticky_comments(self):
        return await _save_json_get_request(
            _mangalib_api_link
            + f"api/comments/sticky?post_id={self.model.id}&post_type=anime",
            self.session,
        )

    async def reviews(self, page_min=1, page_max=1):
        return await _save_json_iter_pages_get_request(
            _mangalib_api_link
            + "api/reviews?page={}"
            + f"&reviewable_id={self.model.id}&reviewable_type=anime&sort_by=newest",
            self.session,
            lambda x: x["links"]["next"] is None,
            page_min=page_min,
            page_max=page_max,
        )

    async def addition_info(
        self,
        infs=[
            "background",
            "eng_name",
            "otherNames",
            "summary",
            "releaseDate",
            "type_id",
            "caution",
            "views",
            "close_view",
            "rate_avg",
            "rate",
            "genres",
            "tags",
            "teams",
            "user",
            "franchise",
            "authors",
            "publisher",
            "userRating",
            "moderated",
            "metadata",
            "metadata.count",
            "metadata.close_comments",
            "anime_status_id",
            "time",
            "episodes",
            "episodes_count",
            "episodesSchedule",
        ],
    ):
        return await _save_json_get_request(
            _mangalib_api_link
            + f"api/anime/{self.model.slug_url}?{'&'.join(map(lambda x: "fields[]=" + x, infs))}",
            self.session,
        )

    def __repr__(self) -> str:
        return f"<{_fullname(self)} object: slug_url={self.model.id}>"


class Collection:
    def __init__(self, session: _httpx.AsyncClient, rawdata: dict):
        self.session = session
        self.model = _CollectionModel(**rawdata)

    async def collectioncontent(self, id: int, process_function_novels=True):
        collection = _CollectionModel(
            **(
                await _save_json_get_request(
                    _mangalib_api_link + f"api/collections/{id}", self.session
                )
            )["data"]
        )
        if process_function_novels:
            for e in collection.blocks:
                for e1 in e.items:
                    related = e1.related
                    e1.related = site_models_by_number[related.site](
                        session=self.session, model=related
                    )
        return collection

    def __repr__(self) -> str:
        return f"<{_fullname(self)} object: slug_url={self.model.id}>"


class Team:
    def __init__(self, session: _httpx.AsyncClient, rawdata: dict, auth_token=None):
        self.session = session
        self.beriar = auth_token
        self.model = _TeamModel(**rawdata)  #!

    async def reload_model(self, slug_url: str):
        resp = (await _save_json_get_request(
            f"https://api.mangalib.me/api/teams/{slug_url}", self.session
        ))["data"]
        self.__init__(self.session, resp, self.beriar)
        return self

    async def users(self):
        return await _save_json_get_request(f"https://api2.mangalib.me/api/teams/{self.model.slug_url}/users", self.session)

    async def is_my_favorite(self):
        return await _save_json_get_request(f"https://api2.mangalib.me/api/fovorites/team/{self.model.id}", self.session, self.beriar)

    async def novels(
        self, site=_SITE_RANOBELIB
    ) -> list[Anime | Hentai | Manga | Ranobe | Slash]:
        novels = list(
            map(
                lambda x: site_models_by_number[x["site"]](self.session, x),
                await _save_json_iter_pages_get_request(
                    "https://api2.mangalib.me/api/manga?page={}&fields[]=rate&fields[]=rate_avg&fields[]=releaseDate&fields[]=userBookmark"
                    + f"&site_id[]={site}&target_id={self.model.id}&target_model={self.model.model}&target_id={self.model.id}&target_model=team",
                    self.session,
                    lambda x: not x["links"]["next"],
                ),
            )
        )
        if site == _SITE_SLASHLIB or site == _SITE_HENTAILIB:
            for e in novels:
                e.beriar = self.beriar
        return novels

    def __repr__(self) -> str:
        return f"<{_fullname(self)} object: slug_url={self.model.slug_url}>"


class People:
    def __init__(self, session: _httpx.AsyncClient, rawdata: dict | None = None, auth_token=None):
        self.session = session
        self.beriar = auth_token
        if rawdata:
            self.model = _PeopleModel(**rawdata)
        else:
            self.model = None

    async def reload_model(self, slug_url: str):
        resp = await _save_json_get_request(
            f"https://api.mangalib.me/api/people/{slug_url}", self.session
        )
        if resp["dsc"] != "":
            raise Exception("Please report this: dsc=" + resp["dsc"])
        self.__init__(self.session, resp, self.beriar)
        return self

    async def novels(
        self, site=_SITE_RANOBELIB, auth = False
    ) -> list[Anime | Hentai | Manga | Ranobe | Slash]:
        novels = list(
            map(
                lambda x: site_models_by_number[x["site"]](self.session, x),
                await _save_json_iter_pages_get_request(
                    "https://api.mangalib.me/api/manga?page={}&fields[]=rate&fields[]=rate_avg&fields[]=releaseDate&fields[]=userBookmark"
                    + f"&site_id[]={site}&target_id={self.model.id}&target_model={self.model.model}",
                    self.session,
                    lambda x: not x["links"]["next"],
                    headers = {} if not auth else self.beriar
                ),
            )
        )
        if site == _SITE_SLASHLIB or site == _SITE_HENTAILIB:
            for e in novels:
                e.beriar = self.beriar
        return novels

    def __repr__(self) -> str:
        return f"<{_fullname(self)} object: slug_url={self.model.slug_url}>"


class Franchise:
    def __init__(self, session: _httpx.AsyncClient, rawdata: dict, auth_token=None):
        self.session = session
        self.beriar = auth_token
        self.model = _FranchiseModel(**rawdata)

    async def reload_model(self):
        resp = await _save_json_get_request(
            f"https://api.mangalib.me/api/franchise/{self.model.slug_url}", self.session
        )
        self.__init__(self.session, resp, self.beriar)
        return self

    async def novels(
        self, site=_SITE_RANOBELIB
    ) -> list[Anime | Hentai | Manga | Ranobe | Slash]:
        return list(
            map(
                lambda x: site_models_by_number[x["site"]](self.session, x),
                await _save_json_iter_pages_get_request(
                    "https://api.mangalib.me/api/manga?page={}&fields[]=rate&fields[]=rate_avg&fields[]=userBookmark"
                    + f"&site_id[]={site}&target_id={self.model.id}&target_model={self.model.model}",
                    self.session,
                    lambda x: not x["links"]["next"],
                ),
            )
        )

    def __repr__(self) -> str:
        return f"<{_fullname(self)} object: slug_url={self.model.slug_url}>"


class User:
    def __init__(
        self,
        session: _httpx.AsyncClient,
        rawdata: dict = {},
        auth_token=None,
        model=None,
    ):
        self.session = session
        self.beriar: dict[str, str] | None = auth_token
        if model:
            self.model: _UserModel | _MeModel = model
        else:
            self.model = _UserModel(**rawdata)

    async def stats(self):
        return await _save_json_get_request(
            _mangalib_api_link + f"api/user/{self.model.id}/stats", session=self.session
        )

    async def is_blocked(self):
        return await _save_json_get_request(
            _mangalib_api_link + f"api/ignore/{self.model.id}", self.session, self.beriar
        )

    async def is_friend(self):
        return await _save_json_get_request(
            _mangalib_api_link + f"api/friendship/{self.model.id}",
            self.session,
            self.beriar,
        )

    async def addition_info(
        self,
        req_data: list[str] = [
            "background",
            "roles" "points",
            "ban_info",
            "gender",
            "created_at",
            "about",
            "teams",
        ],
    ):
        return await _save_json_get_request(
            _mangalib_api_link
            + f'api/user/{self.model.id}?{"&".join(map(lambda x: "fields[]=" + x, req_data))}',
            self.session,
        )

    async def bookmarks(self):
        return await _save_json_get_request(
            _mangalib_api_link + f"api/bookmarks/folder/{self.model.id}", self.session
        )

    async def bookmark_info(self, bookmark_index: int, site: str | int = _SITE_MANGALIB, page_max: int = 1, page_min: int = 1):
        return await _save_json_iter_pages_get_request(_mangalib_api_link + "api/bookmarks?page={}&sort_by=name&sort_type=desc" + f"&status={bookmark_index}&user_id={self.model.id}", headers={"Site_Id": str(site)}, session=self.session, not_has_next_page_func=lambda x: x["links"]["next"] is None, page_max=page_max, page_min=page_min)

    async def comments(self, page_min=1, page_max=1):
        return await _save_json_iter_pages_get_request(
            _mangalib_api_link
            + f"api/user/{self.model.id}/comments?"
            + "page={}&sort_by=id&sort_type=desc",
            self.session,
            lambda x: not x["links"]["next"],
            page_min=page_min,
            page_max=page_max,
        )

    async def collections_preview(self, limit=12, subscriptions=0):
        return list(
            map(
                lambda x: Collection(self.session, x),
                await _save_json_iter_pages_get_request(
                    _mangalib_api_link
                    + f"api/collections?limit={limit}"
                    + "&page={}&sort_by=newest&sort_type=desc"
                    + f"&subscriptions={subscriptions}&user_id={self.model.id}",
                    self.session,
                    not_has_next_page_func=lambda x: x["links"]["next"] is None,
                ),
            )
        )

    def __repr__(self) -> str:
        return f'<{_fullname(self)} object: username="{self.model.username}">'


class Notification:
    def __init__(self, session: _httpx.AsyncClient, rawdata: dict, auth_token=None):
        self.session = session
        self.model = _NotificationModel(**rawdata)
        self.beriar = auth_token

    async def mark_read(self):
        c = await _save_json_get_request(_mangalib_api_link + f"api/notifications/{self.model.id}", self.session, self.beriar, function="PUT")
        if c == {"data":{"toast":{"type":"silent","message":"success"}}}:
            return True
        raise _UnknownApiError(f"mark_readed recieves nonnormal response {c} on notification {self}", 558)

    async def mark_delete(self):
        c = await _save_json_get_request(_mangalib_api_link + f"api/notifications/{self.model.id}", self.session, self.beriar, function="DELETE")
        if c == {"data":{"toast":{"type":"silent","message":"success"}}}:
            return True
        raise _UnknownApiError(f"mark_readed recieves nonnormal response {c} on notification {self}", 558)

    def __repr__(self) -> str:
        return f'<{_fullname(self)} object: id="{self.model.id}">'


site_models_by_number = [None, Manga, Slash, Ranobe, Hentai, Anime]
