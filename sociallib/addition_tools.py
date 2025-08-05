import asyncio as _asyncio
import json    as _json
import os      as _os
import shutil  as _shutil
import re      as _re

from typing import (
    Any      as _Any,
    Callable as _Callable,
    Iterable as _Iterable,
    Literal  as _Literal,
    TypeVar  as _TypeVar,
)

import aiofiles as _aiofiles
import httpx    as _httpx

from .constants import (
    RETRIES_PLUS_ONE  as _RETRIES_PLUS_ONE,
    mangalib_api_link as _mangalib_api_link
)
from .errors import (
    FilenameTooBigError    as _FilenameTooBigError,
    MaxRetriesReachedError as _MaxRetriesReachedError,
    ModerationError        as _ModerationError,
    NotFoundError          as _NotFoundError,
    UnauthorisedError      as _UnauthorisedError,
    UnknownApiError        as _UnknownApiError,
    RestrictedError        as _RestrictedError,
)
from .models import (
    BranchModel       as _BranchModel,
    ChapterModel      as _ChapterModel,
    ContentModel      as _ContentModel,
    MangaContentModel as _MangaContentModel,
)
from .server_constants import ContantsCache as _ContantsCache

type__to_extention = {"xml": "html", "doc": "json"}

check_slash = lambda x: x if x[-1] == "/" else (x + "/")

def extract_slug_url(full_url: str) -> str | None:
    match = _re.search(r".*/([^/?]+)", full_url)
    if match:
        return match.group(1)
    else:
        return match

def safe_filename(s: str, max_length: int = 255) -> str:
    """Sanitize a string making it safe to use as a filename.

    This function was based off the limitations outlined here:
    https://en.wikipedia.org/wiki/Filename.

    :param str s:
        A string to make safe for use as a file name.
    :param int max_length:
        The maximum filename character length.
    :rtype: str
    :returns:
        A sanitized string.
    """
    # Characters in range 0-31 (0x00-0x1F) are not allowed in ntfs filenames.
    ntfs_characters = [chr(i) for i in range(31)]
    characters = [
        r'"',
        r"\#",
        r"\$",
        r"\%",
        r"'",
        r"\*",
        #r"\,",
        #r"\.",
        r"\/",
        r"\:",
        r'"',
        r"\;",
        r"\<",
        r"\>",
        r"\?",
        r"\\",
        r"\^",
        r"\|",
        r"\~",
        r"\\\\",
    ]
    pattern = "|".join(ntfs_characters + characters)
    regex = _re.compile(pattern, _re.UNICODE)
    filename = regex.sub("", s)
    return filename[:max_length].rsplit(" ", 0)[0]


def fullname(o: object):
    module = o.__class__.__module__
    if module == "__builtin__":
        return o.__class__.__name__  # avoid outputs like '__builtin__.str'
    return module + "." + o.__class__.__name__


async def _save_json_get_request(
    link,
    session: _httpx.AsyncClient,
    headers={},
    allow_redirects=True,
    catch_loops=True,
    function: _Literal["GET"] | _Literal["POST"] | _Literal["PUT"] | _Literal["DELETE"] = "GET",
) -> dict:
    """
    100 requests per minute
    """
    if headers is None:
        headers = {}
    if "User-Agent" not in headers:
        headers["User-Agent"] = (
            "Mozilla/5.0 (Linux; U; Android 14; ru; SM-A245F Build/UP1A.231005.007.A245FXXS6CXH1) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/110.0.0.0 Mobile Safari/537.36"
        )
    headers["Content-Type"] = "application/json"
    if function == "GET":
        function = _httpx.AsyncClient.get  # type: ignore
    elif function == "POST":
        function = _httpx.AsyncClient.post  # type: ignore
    elif function == "PUT":
        function = _httpx.AsyncClient.put  # type: ignore
    elif function == "DELETE":
        function = _httpx.AsyncClient.delete  # type: ignore
    else:
        raise Exception(f"_save_json_get_request not support {function=} with type {type(function)}")

    # print(link, headers, sep="\n")

    count = 1
    while count < _RETRIES_PLUS_ONE:
        try:
            r: _httpx.Response = await function(self=session, url=link, headers=headers, follow_redirects=allow_redirects)  # type: ignore
        except _httpx.ConnectError:
            if catch_loops:
                print(
                    ("\x1b[1A" if count != 1 else "")
                    + f"\33[2K\r\033[0;31mWARNING\033[0m: {link} request loop: count={count}"
                )
            count += 1
            continue
        except _httpx.ConnectTimeout:
            count += 1
            continue
        except _httpx.ReadTimeout:
            count += 1
            continue
        #if "retry-after" not in r.headers:  # old
        if "x-ratelimit-remaining" in r.headers:
            resp = r.json()
            if "toast" in resp["data"] and not (link.endswith("like") and resp["data"]["toast"]["message"].isdigit()) and not (resp["data"]["toast"]["message"] == "success"):
                raise _NotFoundError(f"\n{link = },\nheaders keys = {headers.keys()},\nServer response = {resp}")
            return resp
        elif "connection" not in r.headers or r.headers["content-type"] == "text/html; charset=UTF-8":
            print(
                "Too many requests. Retrying after",
                r.headers.get("retry-after", 5),
                "seconds\r",
                end="",
            )
            await _asyncio.sleep(int(r.headers.get("retry-after", 5)) + 1)
        elif r.headers.get("Content-Type", None) == "plain/json":
            return r.json()
        else:
            raise _UnknownApiError(f"{link},\n{headers.keys()},\n{r.headers = },\n{r.text = }", 100)
        count += 1
    raise _MaxRetriesReachedError("Infinity request loop")


async def _save_json_iter_pages_get_request(
    flink,
    session: _httpx.AsyncClient,
    not_has_next_page_func,
    headers={},
    page_min=1,
    page_max=1,
    allow_redirects=True,
    batch_size=10,
):
    results = {}
    stop_after_page = None
    next_page = page_min
    running_tasks = set()
    collected_data = []

    async def fetch_page(page):
        resp = await _save_json_get_request(
            flink.format(page),
            session=session,
            headers=headers,
            allow_redirects=allow_redirects,
        )
        return page, resp

    async def schedule_tasks():
        nonlocal next_page
        while (
            len(running_tasks) < batch_size and
            (page_max == -1 or next_page <= page_max) and
            (stop_after_page is None or next_page <= stop_after_page)
        ):
            task = _asyncio.create_task(fetch_page(next_page))
            running_tasks.add(task)
            task.page = next_page
            next_page += 1

    await schedule_tasks()

    next_to_collect = page_min

    while running_tasks:
        done, pending = await _asyncio.wait(running_tasks, return_when=_asyncio.FIRST_COMPLETED)

        for task in done:
            running_tasks.remove(task)
            try:
                page, resp = task.result()
            except _asyncio.CancelledError:
                continue

            results[page] = resp

            if not_has_next_page_func(resp):
                stop_after_page = page
                for t in list(running_tasks):
                    if getattr(t, 'page', None) is not None and t.page > stop_after_page:
                        t.cancel()
                        running_tasks.remove(t)

        await schedule_tasks()

        while next_to_collect in results:
            resp = results.pop(next_to_collect)
            collected_data.extend(resp.get("data", []))
            next_to_collect += 1

            if stop_after_page is not None and next_to_collect > stop_after_page:
                for t in running_tasks:
                    t.cancel()
                running_tasks.clear()
                break

    while next_to_collect in results:
        resp = results.pop(next_to_collect)
        collected_data.extend(resp.get("data", []))
        next_to_collect += 1

    return collected_data


T = _TypeVar("T")


def get_matched(obj: _Iterable[T], condition: _Callable) -> T | None:
    for e in obj:
        if condition(e):
            return e
    return None


class ChapterContent:
    def __init__(self, rawdata: dict):
        self.rawdata = rawdata
        if "restricted_view" in rawdata.keys() and not rawdata["restricted_view"]["is_open"]:
            raise _RestrictedError(f"Chapter content is restricted {rawdata["restricted_view"]},\n{rawdata = }")
        try:
            self.type_: str = rawdata["content"]["type"]  # type_ = "doc"
        except TypeError:
            self.type_ = "xml"
        except KeyError:
            if "pages" in rawdata:
                self.type_ = "manga"
            else:
                raise _UnknownApiError(f"Unknown type: {rawdata}", 139)
        if self.type_ == "manga":
            self.model = _MangaContentModel(**rawdata)
        else:
            self.model = _ContentModel(**rawdata)

    def writeto(
        self,
        directory="",
        filename="",
        forse_write=False,
        with_extention=True,
        all_data=False,
        dump_json=False,
        name_schema="Том {volume} Глава {number} - {name}",
    ):
        not_forse_write = not forse_write

        if filename == "":
            filename = name_schema.format(
                volume=self.model.volume, number=self.model.number, name=self.model.name
            )
        if directory != "":
            directory = check_slash(directory)

        filename += (
            with_extention or (len(spl := filename.split(".")) != 1 and spl[-1] != 0)
        ) * ("." + type__to_extention[self.type_])

        fileexists = _os.path.isfile(directory + filename)

        if not_forse_write and not (
            not fileexists
            or (
                input(
                    f'Rewrite file "{_os.path.abspath(directory + filename)}"? ("y"|"Y" for yes): '
                ).lower()
                == "y"
            )
        ):
            return False

        with open(directory + safe_filename(filename), "w") as file:
            if not all_data:
                if self.type_ == "xml":
                    data = self.rawdata["content"]
                else:
                    data = self.rawdata["content"]["content"]
            else:
                data = self.rawdata
            if dump_json and self.type_ == "doc":
                data = _json.dumps(data, ensure_ascii=False)
            file.write(str(data))
        return True

    async def __url_in_html_src_tag_of_image(
        self, link: str, normalize: _Callable, session: _httpx.AsyncClient
    ):
        from base64 import b64encode

        link = normalize(link)
        c = b64encode((await session.get(link)).content).decode()
        return f"data:image/{link.split("/")[-1].split(".")[-1]};base64,{c}"

    async def process_images(self, session, bs_parser="lxml"):
        if self.type_ != "xml":
            raise TypeError(f"Type {self.type_} cannot process images")
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(self.rawdata["content"], bs_parser)
        imgs = soup.find_all("img")
        normalize = lambda x: (
            x if x.startswith("http") else ("https://ranobelib.me" + x)
        )
        for cont, img in zip(
            await _asyncio.gather(
                *map(
                    lambda x: self.__url_in_html_src_tag_of_image(
                        x["src"], normalize, session
                    ),
                    imgs,
                )
            ),
            imgs,
        ):
            img["src"] = cont

        self.rawdata["content"] = str(soup)
        return self

    def tohtml(self):
        if self.type_ == "xml":
            return self
        elif self.type_ != "doc":
            raise _UnknownApiError(f"Type {self.type_} cannot be converted to html", 212)
        attach = {e.pop("name"): e for e in self.rawdata["attachments"]}
        self.rawdata["content"] = "".join(
            [
                f'<meta charset="utf-8"><h1>Том {self.model.volume} Глава {self.model.number} - {self.model.name}</h1><main>',
                *self.__json_to_html(self.rawdata["content"]["content"], attach),
                "</main>",
            ]
        )
        self.type_ = "xml"
        return self

    def __json_to_html(self, e0: list, attachments: dict) -> list[str]:
        ret_str: list[str] = []
        for e in e0:
            match e["type"]:
                case "text":
                    if "marks" in e:
                        marks = map(lambda x: f"mark-{x['type']}", e["marks"])
                        marks = ' class="' + " ".join(marks) + '"'
                        ret_str.append(f"<span{marks}>{e['text']}</span>")
                    else:
                        ret_str.append(e["text"])
                case "paragraph":
                    if "attrs" in e:
                        if "textAlign" in e["attrs"]:
                            align = str(e["attrs"]["textAlign"])
                        else:
                            raise _UnknownApiError(
                                f"Unknown html attribute:{self.model.id}: {e['attrs']}",
                                239,
                            )
                    else:
                        align = "p"
                    if "content" in e:
                        ret_str.append(
                            f"<{align}>{''.join(self.__json_to_html(e["content"], attachments))}</{align}>"
                        )
                    else:
                        ret_str.append(
                            '<p class="node-paragraph"><br class="node-hardBreak"></p>'
                        )
                case "hardBreak":
                    ret_str.append("<br>")
                case "heading":
                    level: int = e["attrs"]["level"]
                    for e1 in e["content"]:
                        if e1["type"] == "text":
                            ret_str.append(f"<h{level}>{e1['text']}</h{level}>")
                        else:
                            raise _UnknownApiError(
                                f"Not implemented (2):{self.model.id}: {e1}", 255
                            )
                case "image":
                    attrs = e["attrs"]
                    if "description" in attrs and attrs["description"] != "":
                        ret_str.append(
                            f'<div class="node-image-description">{attrs["description"]}</div>'
                        )
                    if len(attrs["images"]) > 1:
                        ret_str.append(
                            '<div class="node-image node-image_gallery eh_o" data-scroll-content="">'
                        )
                    for index, e in enumerate(attrs["images"]):
                        img = attachments[e["image"]]
                        ret_str.append(
                            f'<img src="{"https://ranobelib.me" + img["url"]}" class="_loaded node-image-item" loading="lazy" data-lightbox-index="{index}" style="aspect-ratio: {img["width"]} / {img["height"]};">'
                        )
                    if len(attrs["images"]) > 1:
                        ret_str.append("</div>")
                case "horizontalRule":
                    ret_str.append('<hr class="node-horizontalRule">')
                case "blockquote":
                    ret_str.append(
                        f'<blockquote class="node-{e["type"]}">'
                        + "".join(self.__json_to_html(e["content"], attachments))
                        + "</blockquote>"
                    )
                case "bulletList":
                    ret_str.append(
                        f'<ul class="node-{e["type"]}">'
                        + "".join(self.__json_to_html(e["content"], attachments))
                        + "</ul>"
                    )
                case "listItem":
                    ret_str.append(
                        '<li class="node-listItem">'
                        + "".join(self.__json_to_html(e["content"], attachments))
                        + "</li>"
                    )
                case _:
                    print(f"WARNING: paragraph type is unknown: {e}")
                    ret_str.extend(
                        [
                            "<",
                            e["type"],
                            ">",
                            *self.__json_to_html(e, attachments),
                            "</",
                            e["type"],
                            ">",
                        ]
                    )
        return ret_str

    def __repr__(self) -> str:
        return f"<{fullname(self)} object type={self.type_}>"

    # def tojson(self):
    #    if self.type_ == "doc":
    #        return self
    #    ret_sp = []
    #    for e in bs:
    #        pass
    #    self.type_ = "doc"
    #    return self


class Chapter:
    def __init__(
        self, rawdata: dict, slug_url, session: _httpx.AsyncClient, auth_token=None
    ):

        self.raw: dict = rawdata
        self.session = session
        self.beriar: dict[str, str] | None = auth_token
        self.slug_url: str = slug_url
        self.model = _ChapterModel(**rawdata)
        self._teams: list[_BranchModel] | None = None
        self.last_content: ChapterContent | None = None

    # FIXME: cache only one translator, and other overwrite him
    async def content(
        self,
        translator_id: int | str | None = None,
        translators_priority: list[_BranchModel] | None = None,
        cache_response=False,
        use_cached=True,
    ):
        if translators_priority is not None:
            for translator in translators_priority:
                if translator.teams in map(lambda x: x.teams, self.model.branches):
                    translator_id = translator.branch_id
                    break
        if (  # elif need?
            self.last_content
            and use_cached
            and self.last_content.model.branch_id == translator_id
            and translator_id is not None
        ):
            return self.last_content
        try:
            cc = ChapterContent(
                (
                    await _save_json_get_request(
                        "{}api/manga/{}/chapter?{}number={}&volume={}".format(
                            _mangalib_api_link,
                            self.slug_url,
                            (
                                ""
                                if translator_id is None
                                else f"branch_id={translator_id}&"
                            ),
                            self.model.number,
                            self.model.volume,
                        ),
                        self.session,
                        headers=self.beriar,
                    )
                )["data"]
            )
        except _NotFoundError as err:
            if (
                bool(self.model.branches[0].moderation)
                and self.model.branches[0].moderation.id == 0
            ):
                raise _ModerationError(self, self.slug_url)
            else:
                raise err
        # !Somehow branch_id always null!  # already fix?
        # if (cc.model.branch_id is None):
        #    # print(cc.model)
        #    raise UnknownApiError("Possibly api issue, report on github", 345)
        # if (translator_id and cc.model.branch_id != translator_id) or (not translator_id and cc.model.branch_id != self.model.branches[0].branch_id):
        #    raise UnknownApiError("Possibly api issue, report on github", 347)
        if cache_response:
            self.last_content = cc
        return cc

    async def switch_like(self):
        if self.beriar:
            c = (await _save_json_get_request(
                f"{_mangalib_api_link}api/chapters/{self.model.id}/like", headers=self.beriar,
                session=self.session,
                function="POST",
            ))["data"]
            self.raw["is_liked"] = c["chapter"]["is_liked"]
            return c
        #{'toast': {'type': 'silent', 'message': '12897'}, 'chapter': {'likes_count': 12897, 'is_liked': False}}
        raise _UnauthorisedError("For like chapter need auth first")

    async def set_like(self, to_state: bool, /,
                       current_state: bool | None = None,
                       get_content = False,
                       do_and_think_later=False
                       ):
        f1 = False
        if current_state:
            self.raw["is_liked"] = current_state
        if self.raw.get("is_liked", None) is None:
            if not self.last_content and get_content:
                await self.content(cache_response=True)

            if self.last_content:
                self.raw["is_liked"] = self.last_content.rawdata["is_liked"]

        if self.raw.get("is_liked", None) is None or do_and_think_later:
            if not do_and_think_later:
                raise _UnauthorisedError("For like chapter need to know current like state")
            f1 = await self.switch_like()

        if self.raw["is_liked"] != to_state:
            c = await self.switch_like()
            if f1:
                return False
            else:
                return c
        return bool(f1)

    def __repr__(self) -> str:
        return f"<{fullname(self)} object: volume={self.model.volume} number={self.model.number}>"


async def _dow_img(
    save_directory: str,
    rus_name,
    k,
    v,
    session: _httpx.AsyncClient,
    check_file_exists=True,
):
    filename = f"{save_directory + safe_filename(rus_name)}/{k}_{v.split('/')[-1]}"
    if len(filename.split("/")[-1].split(".")) == 1:
        filename += ".jpg"
    async def getsize(session: _httpx.AsyncClient, v):
        count = 0
        while count < _RETRIES_PLUS_ONE:
            try:
                h = await session.head(v, headers={"Referer": "https://mangalib.me/"})
                size = int(h.headers["Content-Length"])
            except (_httpx.ConnectTimeout, _httpx.ReadTimeout):
                count += 1
                continue
            except KeyError:
                raise _UnknownApiError(h.headers, h.reason_phrase)
            break
        if count == _RETRIES_PLUS_ONE:
            raise RecursionError("Infinity request loop")
        return size
    if (
        not check_file_exists
        or not _os.path.isfile(filename)
        or (await getsize(session, v) != _os.path.getsize(filename))
    ):
        count = 0
        while count < _RETRIES_PLUS_ONE:
            try:
                async with session.stream("GET", v, headers={"Referer": "https://mangalib.me/"}) as response:
                    async with _aiofiles.open(filename, "wb") as file:
                        async for chunk in response.aiter_bytes(65_536):
                            await file.write(chunk)
            except (_httpx.ReadTimeout, _httpx.ConnectTimeout, _httpx.RemoteProtocolError):
                count += 1
                continue
            break
        if count == _RETRIES_PLUS_ONE:
            raise _MaxRetriesReachedError("Infinity request loop")


async def __dow_chapters(
    chapter: Chapter,
    images_name_prefix,
    img_path,
    session,
    image_server,
    not_silent,
    translators_priority,
    check_file_exists=True,
):
    count = 0
    while count < _RETRIES_PLUS_ONE:
        try:
            chapter_content = await chapter.content(
                translators_priority=translators_priority
            )
        except _ModerationError as err:
            print(f"{fullname(err)}: {err.__str__()}")
            return
        except _httpx.ConnectTimeout:
            count += 1
            continue
        break
    if count == _RETRIES_PLUS_ONE:
        raise _MaxRetriesReachedError("Infinity request loop")

    await _asyncio.gather(
        *map(
            lambda i: get_image(
                i,
                img_path,
                session,
                image_server,
                not_silent,
                check_file_exists=check_file_exists,
            ),
            map(
                lambda y: [
                    images_name_prefix.format(
                        index=chapter_content.model.pages.index(y),
                        index_plus_one=chapter_content.model.pages.index(y) + 1,
                    )
                    + y.image,
                    y.url,
                ],
                chapter_content.model.pages,
            ),
        )
    )

    if not_silent:
        saveprint(
            f'chapter volume={chapter.model.volume}, number={chapter.model.number}, name={chapter.model.name.__repr__().replace("\'", "\"")} downloaded'
        )
        saveprint("", new=True)


type All = _Any


async def download_manga(
    session,
    novel,
    novel_chapters: list[Chapter] | All = All,
    save_directory: str = "",
    *,
    silent=False,
    check_directories: list[str] | None = None,
    download_thumbs=True,
    images_name_prefix="{index_plus_one}_",
    check_file_exists=True,
    translators_priority: list[_BranchModel] | None = None,
    high_resolution=False,
    image_server: str | None = None,
    input_vpn_disable_req: None | _Callable = None,
    do_only_vpn_stuff=False,
    one_by_one=False,
    chapter_name: _Callable[
        [Chapter, str, str], str
    ] = lambda chapter, save_directory, name: f"{save_directory}{safe_filename(name)}/{safe_filename(chapter.model.volume + " " + chapter.model.number + ((" " + chapter.model.name) if chapter.model.name is not None else ""))}/",
):
    not_silent = not silent
    del silent
    site = novel.model.site
    servers: list[dict] = (
        await _ContantsCache().get_constants(session, ["imageServers"])
    )["imageServers"]

    if high_resolution:
        serv_id = "main"
    else:
        serv_id = "compress"

    if site == 4:
        site_ids = [4]
    elif site == 1 or site == 2:
        site_ids = [1, 2, 3]
    else:
        import inspect

        print(inspect.stack())
        raise TypeError(f"{inspect.stack()[0][3]} download only manga-like")

    if novel_chapters is All:
        novel_chapters = await novel.chapters()

    try:
        image_server = get_matched(servers, lambda x: x["id"] == serv_id and x["site_ids"] == site_ids)["url"]
    except TypeError:
        print(serv_id, site_ids)
        raise
    del site_ids
    del serv_id

    rus_name: str = (
        novel.model.rus_name
        if novel.model.rus_name != "" and novel.model.rus_name is not None
        else novel.model.name
    )

    if check_directories:
        for directory in check_directories:
            if rus_name in _os.listdir(directory):
                save_directory = check_slash(directory)

    is_os_error = False
    rus_name_copy = rus_name
    while True:
        try:
            _os.mkdir(save_directory + safe_filename(rus_name_copy))
        except FileExistsError:
            pass
        except OSError as exc:
            is_os_error = True
            if exc.errno == 36:
                if len(rus_name_copy) != 0:
                    rus_name_copy = rus_name_copy[:-1]
                    continue
                raise _FilenameTooBigError(
                    f"OSError (36): filename is too big: {save_directory + safe_filename(rus_name) = }"
                )
            else:
                raise exc
        rus_name = rus_name_copy
        break

    if is_os_error and check_directories:
        if not_silent:
            print(
                f'\033[38;5;3mRuntime: OSError: Filename is too long, checking directories again.. filename = \033[0m"{rus_name}"'
            )
        for directory in check_directories:
            if rus_name in _os.listdir(directory):
                save_directory = check_slash(directory)
    del is_os_error

    if download_thumbs:
        try:
            # FIXME: split part of addition_tools.py to core.py
            back_url = (await novel.addition_info(["background"], auth=str(type(novel)) == "<class 'sociallib.novelTypes.Slash'>"))["background"]["url"]
        except _NotFoundError:
            print("WARNING: background  NotFoundError")
            back_url = (await novel.addition_info(["background"], auth=True))["background"]["url"]

        def check_orig(x):
            try:
                return x.orig
            except AttributeError:
                return x.default

        dic: dict = {f"orig{e.info}": check_orig(e.cover) for e in await novel.covers()}
        if back_url[0] != "/":
            dic.update({"background": back_url})
        else:
            if not_silent:
                print("Background not find")
        if len(dic.items()) == 0:
            dic["thumbnail"] = novel.model.cover.default
    if input_vpn_disable_req:
        input_vpn_disable_req()
    if do_only_vpn_stuff:
        return _asyncio.gather(
            *map(
                lambda i: _dow_img(
                    save_directory,
                    rus_name,
                    i[0],
                    i[1],
                    session,
                    check_file_exists=check_file_exists,
                ),
                dic.items(),
            )
        )
    if download_thumbs:
        await _asyncio.gather(
            *map(
                lambda i: _dow_img(
                    save_directory,
                    rus_name,
                    i[0],
                    i[1],
                    session,
                    check_file_exists=check_file_exists,
                ),
                dic.items(),
            )
        )

    save_chapters_img = list(
        map(lambda x: chapter_name(x, save_directory, rus_name), novel_chapters)
    )

    for save_chapter in save_chapters_img:
        try:
            _os.mkdir(save_chapter)
        except FileExistsError:
            pass

    if not_silent:
        print("Getting image links..")

    chs = map(
        lambda i: __dow_chapters(
            i[1],
            images_name_prefix,
            save_chapters_img[i[0]],
            session,
            image_server,
            not_silent,
            translators_priority=translators_priority,
            check_file_exists=check_file_exists,
        ),
        enumerate(novel_chapters),
    )
    if one_by_one:
        for ch in chs:
            await ch
    else:
        await _asyncio.gather(*chs)


def saveprint(value: str, end: str | None = "\n", _sp=[0], new: bool = False):
    if new:
        _sp[0] = 0
    else:
        stroka = value
        l = _sp[0]
        w = _shutil.get_terminal_size().columns
        print(((l // w + ((l % w) != 0)) * "\x1b[1A\x1b[2K") + "\r" + stroka, end=end)
        _sp[0] = len(stroka)


def pick_site(url: str):
    try:
        manga_like = [
            "https://img33.imgslib.link",
            "https://img2.imglib.info",
            "https://img4.imgslib.link",
        ]
        return manga_like[(manga_like.index(url) + 1) % len(manga_like)]
    except ValueError:
        hentai_like = ["https://img3.imglib.info", "https://img2h.imgslib.link"]
        return hentai_like[(hentai_like.index(url) + 1) % len(hentai_like)]


async def get_image(
    i,
    sch,
    session: _httpx.AsyncClient,
    image_server,
    not_silent,
    check_file_exists=True,
    recursive_depth=0,
):
    name = i[0]
    url = i[1]
    if recursive_depth == _RETRIES_PLUS_ONE:
        raise _MaxRetriesReachedError(
            f'All attempts to download image have failed!\nSome image info:\n\tlink="{url}",\n\tfilepath="{sch + name}"'
        )
    if _os.path.isfile(sch + name):
        count = 0
        while count < _RETRIES_PLUS_ONE:
            try:
                is_file_all_data = int(
                    (await session.head(image_server + url, headers={"Referer": "https://mangalib.me/"})).headers["Content-Length"]
                ) != _os.path.getsize(sch + name)
            except (_httpx.ReadTimeout, _httpx.ConnectTimeout, _httpx.PoolTimeout, _httpx.LocalProtocolError, _httpx.ReadError, _httpx.WriteError):
                count += 1
                continue
            except _httpx.ConnectError as e:
                print(image_server + url)
                raise e
            break
        if count == _RETRIES_PLUS_ONE:
            raise _MaxRetriesReachedError("Infinity request loop")
    else:
        is_file_all_data = True
    if not check_file_exists or is_file_all_data:
        count = 0
        while count < _RETRIES_PLUS_ONE:
            try:
                async with session.stream("GET", image_server + url, headers={"Referer": "https://mangalib.me/"}) as response:
                    async with _aiofiles.open(sch + name, "wb") as file:
                        async for chunk in response.aiter_bytes(65_536):
                            await file.write(chunk)
            except (_httpx.PoolTimeout, _httpx.ReadTimeout, _httpx.ConnectTimeout, _httpx.ConnectError, _httpx.RemoteProtocolError, _httpx.ReadError, _httpx.ProxyError):
                count += 1
                continue
            break
        if count > _RETRIES_PLUS_ONE:
            raise _MaxRetriesReachedError(
                f'Max retry count ({count}) for url "{image_server + url}"'
            )

    try:
        size = _os.path.getsize(sch + name)
    except FileNotFoundError:
        size = 0
    if size == 0:
        await get_image(
            i,
            sch,
            session,
            pick_site(image_server),
            not_silent,
            recursive_depth=recursive_depth + 1,
        )
    elif size < 17:
        with open(sch + name, "r") as file:
            text = file.read()
        if text == "400 Bad Request":
            await get_image(
                i,
                sch,
                session,
                pick_site(image_server),
                not_silent,
                recursive_depth=recursive_depth + 1,
            )
        else:
            raise _UnknownApiError(f"{text = }", 579)
    elif size == 612:
        raise _UnknownApiError(f"Client does not have access rights to the content so server is rejecting to give proper response 403, {image_server + url = }", 797)
    elif not_silent:
        saveprint(image_server + url + " downloaded")
