#from functools import wraps, partial

from .addition_tools import _save_json_get_request, _save_json_iter_pages_get_request
from urllib.parse import quote as _quote
from .constants import (
    mangalib_api_link as _mangalib_api_link,
    NOTIF_TYPE_ALL    as _NOTIF_TYPE_ALL,
    READ_TYPE_UNREAD  as _READ_TYPE_UNREAD,
    SITE_RANOBELIB    as _SITE_RANOBELIB,
    SITE_USER         as _SITE_USER,
    SITE_HENTAILIB    as _SITE_HENTAILIB,
    SITE_SLASHLIB     as _SITE_SLASHLIB,
    SITE_MANGALIB     as _SITE_MANGALIB,
    SITE_PEOPLE       as _SITE_PEOPLE,
    SITE_ANIMELIB     as _SITE_ANIMELIB,
    SITE_TEAM         as _SITE_TEAM,
    SITE_FRANCHISE    as _SITE_FRANCHISE,
)
import httpx as _httpx
from .novelTypes import (
    Franchise    as _Franchise,
    Manga        as _Manga,
    Ranobe       as _Ranobe,
    User         as _User,
    Anime        as _Anime,
    Notification as _Notification,
    Hentai       as _Hentai,
    Slash        as _Slash,
    People       as _People,
    Team         as _Team,
)
from .errors import UnauthorisedError as _UnauthorisedError
from .models import MeModel           as _MeModel

# from typing import TypeAlias

# FileLike: TypeAlias = str


class LibAccount:
    def __init__(
        self,
        session: _httpx.AsyncClient,
        filename: str | None = None,
        filecontent: dict | None = None,
        check_session_type: bool = True
    ):
        if check_session_type:
            assert hasattr(session, "get")
        self.headers = None
        self.session = session
        self.last_notifications = None
        if filecontent:
            filedict = filecontent
        elif filename:
            with open(filename, "r") as file:
                filedict: dict = eval(file.read())
        else:
            return None
        self.beriar = {"Authorization": filedict.pop("Authorization")}
        filedict["Content-Type"] = "application/json"
        self.headers = filedict

    async def me(self):
        headerscache = self.headers
        if headerscache:
            headerscache.update(self.beriar)
            me: dict = await _save_json_get_request(
                _mangalib_api_link + "api/auth/me",
                self.session,
                headers=headerscache,
                allow_redirects=False,
            )
            try:
                is_authorised: bool = me["data"]["toast"]["type"] != "error"
                error_message: str | None = me["data"]["toast"]["message"]
            except KeyError:
                error_message = None
                is_authorised = True
            return is_authorised, error_message, _User(self.session, model=_MeModel(**me))

    async def notifications_count(self):
        headerscache = self.headers
        if headerscache:
            headerscache.update(self.beriar)
            notifications_count = await _save_json_get_request(
                _mangalib_api_link + "api/notifications/count",
                self.session,
                headers=headerscache,
            )
            return notifications_count

    async def notifications(
        self,
        notif_type=_NOTIF_TYPE_ALL,
        max_pages=1,
        min_pages=1,
        read_type=_READ_TYPE_UNREAD,
        cache_response=False
    ):
        headerscache = self.headers
        if headerscache:
            headerscache.update(self.beriar)
            notifications = list(
                map(
                    lambda x: _Notification(self.session, x, self.beriar),
                    await _save_json_iter_pages_get_request(
                        _mangalib_api_link
                        + f"api/notifications?notification_type={notif_type}"
                        + "&page={}"
                        + f"&read_type={read_type}&sort_type=desc",
                        self.session,
                        lambda x: x["links"]["next"] is None,
                        headers=headerscache,
                        page_max=max_pages,
                        page_min=min_pages,
                    ),
                )
            )
            del headerscache
            if cache_response:
                self.last_notifications = notifications
            return notifications
        else:
            raise _UnauthorisedError("Authentificate before try to get notifications")

    # async def refresh_auth(self):  # he add capcha
    #    pass

    async def search(
        self,
        query: str,
        site=_SITE_RANOBELIB,
        max_pages=1,
        min_pages=1,
        addition_info=["rate_avg", "rate", "releaseDate"],
        auth=False,
        throw_beriar_to_all=False,
    ):
        if len(query) == 1 and (site == _SITE_USER or site == _SITE_PEOPLE):
            raise Exception(f"LibAccount.search_{site}(query) must by more or equal 2")
        search_api_link = _mangalib_api_link
        has_next_page = lambda onesearchdata: not onesearchdata["meta"]["has_next_page"]
        if site != _SITE_USER:
            addition_prompt0 = "&" + "&".join(("fields[]=" + e) for e in addition_info)
        if site == SITE_ANIMELIB:
            parse_class = _Anime
            site_name = "anime"
            has_next_page = lambda x: x["links"]["next"] is None
        elif site == _SITE_MANGALIB:
            parse_class = _Manga
            site_name = "manga"
        elif site == _SITE_SLASHLIB:
            parse_class = _Slash
            site_name = "manga"
        elif site == _SITE_HENTAILIB:
            parse_class = _Hentai
            site_name = "manga"
        elif site == _SITE_RANOBELIB:
            parse_class = _Ranobe
            site_name = "manga"
        elif site == _SITE_USER:
            parse_class = _User
            site_name = site
            addition_prompt0 = "&sort_type=asc&sort_by=id"
            # search_api_link = mangalib_api_link
            has_next_page = lambda onesearchdata: onesearchdata["links"]["next"] is None
        elif site == _SITE_PEOPLE:
            parse_class = _People
            site_name = site
            addition_prompt0 = "&limit=35&sort_by=subscribes_count&sort_type=desc"
            has_next_page = lambda onesearchdata: onesearchdata["links"]["next"] is None
        elif site == SITE_TEAM:
            parse_class = _Team
            site_name = site
            addition_prompt0 = ""
            has_next_page = lambda onesearchdata: onesearchdata["links"]["next"] is None
        elif site == SITE_FRANCHISE:
            parse_class = _Franchise
            site_name = site
            has_next_page = lambda onesearchdata: onesearchdata["links"]["next"] is None
            addition_prompt0 = "&sort_by=name&sort_type=desc"
        else:
            raise Exception(f'LibAccount.search(site="{site}") is unknown')

        addition_prompt = (
            "" if (site == _SITE_USER or site == _SITE_PEOPLE) else f"&site_id[]={site}"
        )
        throw_data = (
            self.beriar
            if throw_beriar_to_all or (site == _SITE_HENTAILIB or site == _SITE_SLASHLIB or site == _SITE_PEOPLE)
            else None
        )
        searchdata = list(
            map(
                lambda x: parse_class(
                    rawdata=x, session=self.session, auth_token=throw_data
                ),
                await _save_json_iter_pages_get_request(
                    search_api_link
                    + f"api/{site_name}?q={_quote(query)}{addition_prompt}"
                    + "&page={}"
                    + addition_prompt0,
                    session=self.session,
                    not_has_next_page_func=has_next_page,
                    page_max=max_pages,
                    page_min=min_pages,
                    headers=self.beriar if auth else None,
                ),
            )
        )
        return searchdata

    async def search_manga(
        self,
        query: str,
        max_pages=1,
        min_pages=1,
        addition_info=["rate_avg", "rate", "releaseDate"],
    ) -> list[_Manga]:
        return await self.search(
            site=_SITE_MANGALIB,
            query=query,
            max_pages=max_pages,
            min_pages=min_pages,
            addition_info=addition_info,
        )

    async def search_ranobe(
        self,
        query: str,
        max_pages=1,
        min_pages=1,
        addition_info=["rate_avg", "rate", "releaseDate"],
    ) -> list[_Ranobe]:
        return await self.search(
            site=_SITE_RANOBELIB,
            query=query,
            max_pages=max_pages,
            min_pages=min_pages,
            addition_info=addition_info,
        )

    async def search_team(
        self,
        query: str,
        max_pages=1,
        min_pages=1,
    ) -> list[_Team]:
        return await self.search(
            site=SITE_TEAM,
            query=query,
            max_pages=max_pages,
            min_pages=min_pages,
            throw_beriar_to_all=True
        )

    async def search_user(
        self,
        query: str,
        max_pages=1,
        min_pages=1,
        addition_info=["rate_avg", "rate", "releaseDate"],
    ) -> list[_User]:
        return await self.search(
            site=_SITE_USER,
            query=query,
            max_pages=max_pages,
            min_pages=min_pages,
            addition_info=addition_info,
        )

    async def search_anime(
        self,
        query: str,
        max_pages=1,
        min_pages=1,
        addition_info=["rate_avg", "rate", "releaseDate"],
    ) -> list[_Anime]:
        return await self.search(
            site=SITE_ANIMELIB,
            query=query,
            max_pages=max_pages,
            min_pages=min_pages,
            addition_info=addition_info,
        )

    async def search_slash(
        self,
        query: str,
        max_pages=1,
        min_pages=1,
        addition_info=["rate_avg", "rate", "releaseDate"],
    ) -> list[_Slash]:
        return await self.search(
            site=_SITE_SLASHLIB,
            query=query,
            max_pages=max_pages,
            min_pages=min_pages,
            addition_info=addition_info,
        )

    async def search_hentai(
        self,
        query: str,
        max_pages=1,
        min_pages=1,
        addition_info=["rate_avg", "rate", "releaseDate"],
    ) -> list[_Hentai]:
        return await self.search(
            site=_SITE_HENTAILIB,
            query=query,
            max_pages=max_pages,
            min_pages=min_pages,
            addition_info=addition_info,
        )

    async def search_people(self, query: str, max_pages=1, min_pages=1) -> list[_People]:
        return await self.search(
            site=_SITE_PEOPLE, query=query, max_pages=max_pages, min_pages=min_pages
        )

    async def search_franchise(
        self, query: str, max_pages=1, min_pages=1, subscriptions=True
    ) -> list[_Franchise]:
        return await self.search(
            site=SITE_FRANCHISE,
            query=query,
            max_pages=max_pages,
            min_pages=min_pages,
            auth=subscriptions,
        )
