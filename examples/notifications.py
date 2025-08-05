import asyncio

import httpx

from sociallib import libapi
from sociallib.addition_tools import Chapter, download_manga
from sociallib.constants import NOTIF_TYPE_CHAPTER
from sociallib.novelTypes import Manga, Notification, site_models_by_number

from download import check_directories, download_ranobe, save_directory


def get_chapter_obj(notif: Notification, cli: httpx.AsyncClient, la: libapi.LibAccount):
    d = notif.model.data.chapter.model_dump()  # type: ignore
    d.update(
        {
            "index": 0,
            "item_number": 0,
            "number_secondary": "",
            "branches_count": 0,
            "branches": [],
        }
    )
    return Chapter(d, notif.model.data.media.slug_url, cli, la.beriar)


async def get_one_manga_chapter(
        notif: Notification,
        cli: httpx.AsyncClient,
        la: libapi.LibAccount,
        count: int | None = None,
    ):
    novel: Manga = site_models_by_number[notif.model.data.media.site](
        cli, auth_token=la.beriar, model=notif.model.data.media
    )
    if count is None:
        chs = [get_chapter_obj(notif, cli, la)]
    else:
        chs = (await novel.chapters())[-count:]
    if notif.model.data.media.site in {1, 2, 4}:
        await download_manga(
            cli, novel, chs, save_directory, check_directories=check_directories
        )
    elif notif.model.data.media.site == 3:
        await download_ranobe(cli, novel, chs, save_directory, check_directories=check_directories)
    else:
        raise Exception(
            f"{novel} type unsupported to download", notif.model.model_dump_json()
        )
    await notif.mark_read()


async def main(proxy=None):
    async with httpx.AsyncClient(proxy=proxy) as cli:
        la = libapi.LibAccount(cli, "user.json")
        count = (await la.notifications_count())["data"]["unread"]["chapter"]  # type: ignore
        print(f"{count} notifications")
        if count > 0:
            for notif in await la.notifications(NOTIF_TYPE_CHAPTER):
                for e in notif.model.content["content"]:
                    if e["type"] == "hardBreak":
                        print()
                    elif e["type"] == "text":
                        print(str(e["text"]) + " ", end="")
                print()
                sw = (notif.model.category, notif.model.type)
                if sw == ("chapter", "chapter"):
                    if hasattr(notif.model.data, "count"):
                        await get_one_manga_chapter(
                            notif, cli, la, notif.model.data.count  # type: ignore
                        )
                    elif notif.model.data.chapter.expired_at is not None:  # type: ignore
                        print(
                            f"Chapter restricted before {
                            notif.model.data.chapter.expired_at:%d.%m.%Y %H:%M}"  # type: ignore
                        )
                        await notif.mark_delete()
                    else:
                        await get_one_manga_chapter(notif, cli, la)
                elif sw == ("chapter", "chapter.early_access_published"):
                    await get_one_manga_chapter(notif, cli, la)
                elif sw == ("other", "subscription"):
                    print("pass")
                else:
                    raise Exception(
                        f"notif category {sw}", notif.model.model_dump_json()
                    )
                count -= 1
                if count != 0:
                    print("\n")

proxy = None
proxy = httpx.Proxy("socks5h://127.0.0.1:1080")
asyncio.run(main(proxy=proxy))

"""--- Справка ---
category    type
('chapter', 'chapter.early_access_published')  # стала общедоступной  # NotificationDataModel1
('chapter', 'chapter')   # добавлена одна или несколько глав  # NotificationDataModel1 or NotificationDataModel2
('other', 'subscription') # добавлен тейтл/персона в тайтл
  # NotificationDataModel3

"""
