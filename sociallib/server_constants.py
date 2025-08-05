from typing import (
    Self      as _Self,
    Literal   as _Literal,
    TypeAlias as _TypeAlias,
)
import httpx as _httpx
from .constants import (
    RETRIES_PLUS_ONE  as _RETRIES_PLUS_ONE,
    mangalib_api_link as _mangalib_api_link,
)
from .errors import MaxRetriesReachedError as _MaxRetriesReachedError


Constant: _TypeAlias = _Literal[
    "genres",
    "tags",
    "format",
    "types",
    "scanlateStatus",
    "status",
    "ageRestriction",
    "teamPermissions",
    "teamRoles",
    "teamNoticeReasons",
    "imageServers",
    "videoServers",
    "episodeStatus",
    "players",
    "translationTypes",
    "collectionsType",
    "characterPosition",
    "voiceLanguage",
    "relationTypes",
    "mediaModeratorPermissions",
    "lockedFields",
    "banStatus",
    "genders",
    "blogPlatform",
    "blogType",
    "blogVisibleFor",
    "timestamp",
]

all_constants = list(Constant.__args__)



class ContantsCache:
    __instanse = None

    def __new__(cls, *args, **kwargs) -> _Self:
        if cls.__instanse is None:
            cls.__instanse = super().__new__(cls)
        return cls.__instanse

    def __init__(self) -> None:
        self.last_constants = {}

    async def get_constants(
        self, session: _httpx.AsyncClient, constants: list[Constant]
    ):
        resp = {}
        for e in constants:
            if e in self.last_constants:
                resp[e] = self.last_constants[e]
                constants.remove(e)
        if constants:
            resp.update((await _get_constants(session, constants))["data"])
        self.last_constants.update(resp)
        return resp


async def _get_constants(session: _httpx.AsyncClient, constants: list[Constant]) -> dict:
    count = 0
    while count < _RETRIES_PLUS_ONE:
        try:
            r = (await session.get(f"{_mangalib_api_link}api/constants?{'&'.join(map(lambda constant: 'fields[]=' + constant, constants))}")).json()  # before: https://api.lib.social
        except _httpx.ConnectTimeout:
            count += 1
            continue
        break
    if count == _RETRIES_PLUS_ONE:
        raise _MaxRetriesReachedError(f'Max retry count ({count}) for constants "{constants}"')
    return r  # type: ignore


if __name__ == "__main__":
    import asyncio
    async def main():
        async with _httpx.AsyncClient() as cli:
            return await _get_constants(cli, ["imageServers"])
    print(asyncio.run(main()))

"""--- Output ---
'imageServers': [
{'id': 'main', 'label': 'Первый', 'url': 'https://img2.hentaicdn.org', 'site_ids': [1, 2, 3]},
{'id': 'secondary', 'label': 'Второй', 'url': 'https://img2.hentaicdn.org', 'site_ids': [1, 2, 3]},
{'id': 'compress', 'label': 'Сжатия', 'url': 'https://img3.hentaicdn.org', 'site_ids': [1, 2, 3]},
{'id': 'download', 'label': 'Скачивание', 'url': 'https://img3.hentaicdn.org', 'site_ids': [1, 2, 3]},
{'id': 'crop', 'label': 'Crop pages', 'url': 'https://crops.mangalib.me', 'site_ids': [1, 2, 3]},
{'id': 'main', 'label': 'Первый', 'url': 'https://img2h.imgslib.link', 'site_ids': [4]},
{'id': 'secondary', 'label': 'Второй', 'url': 'https://img3h.hentaicdn.org', 'site_ids': [4]},
{'id': 'compress', 'label': 'Сжатия', 'url': 'https://img3.imglib.info', 'site_ids': [4]},
{'id': 'crop', 'label': 'Crop pages', 'url': 'https://crops.hentailib.me', 'site_ids': [4]}
]

"""

