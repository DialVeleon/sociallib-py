import os
import httpx
import asyncio
import aiofiles
from asyncstdlib import enumerate as aenumerate, iter as aiter
from sociallib.libapi import LibAccount
from sociallib.models import AniChapterModel
from sociallib.novelTypes import Anime, Collection, Hentai, User
from sociallib.addition_tools import download_manga, Chapter


save_directory = os.popen("echo $HOME").read().strip() + "/storage/.Books/Jap/"
check_directories = [
        save_directory + "Hentai/",
        save_directory + "Manga/",
        save_directory + "Ranobe/",
        ]
save_directory += "Source/"


def for_filename(x: str):
    sp = [("?", "¿"), (":", ";"), ('"', ""), ("/", " в "), ("&amp;", "&"), ("*", "")]
    for e in sp:
        x = x.replace(e[0], e[1])
    return x


async def download_collections(collections: list[Collection], user: User, auth):
    async for index, collection in aenumerate(collections):
        content = await collection.collectioncontent(collection.model.id)
        async for index1, block in aenumerate(content.blocks):
            async for index2, item in aenumerate(block.items):
                manga = item.related
                if isinstance(manga, Hentai):
                    manga.beriar = auth
                print("\n", manga.model.rus_name if manga.model.rus_name != "" and manga.model.rus_name is not None else manga.model.name, sep="")
                ch = await manga.chapters()
                await download_manga(manga.session, manga, ch, save_directory)
                # chapters: list[Chapter] = await manga.chapters()
                # async for index, chapter in aenumerate(chapters):
                #    chapter.beriar = auth
                #    chapter.model.


async def download_anime(novel: Anime, chapters: list[AniChapterModel], subtitles=False):
    rus_name = (
        novel.model.rus_name
        if (novel.model.rus_name != "" and novel.model.rus_name is not None)
        else novel.model.name
    )

    try:
        os.mkdir(save_directory + for_filename(rus_name))
    except FileExistsError:
        pass
    save_chapters_path = list(
        map(
            lambda chapter: (
                save_directory
                + for_filename(rus_name)
                + "/"
                + for_filename(
                    chapter.season
                    + " "
                    + chapter.number
                    + " "
                    + (chapter.name if chapter.name != None else "")
                )
                + "/"
            ),
            chapters,
        )
    )

    for save_chapter in save_chapters_path:
        try:
            os.mkdir(save_chapter)
        except FileExistsError:
            pass

    nov_dat = map(lambda x: [x.id, x.number, x.season], chapters)
    print("Getting episodes..")
    eps = await asyncio.gather(*[novel.episode(e[0]) for e in nov_dat])
    picked_teams = []
    for e in eps:
        ep_teams = []
        for e1 in e.players:
            if e1.player == "Animelib" and e1.translation_type.id == (2 - subtitles):
                if e1.team.name not in ep_teams:
                    ep_teams.append(e1.team.name)
        is_pick = False
        for e1 in ep_teams:
            if e1 in picked_teams:
                picked_teams.append(e1)
                is_pick = True
                break
        if not is_pick:
            print("index team_name")
            for index, e1 in enumerate(ep_teams):
                print(index, e1)
            picked_teams.append(ep_teams[int(input())])
    picked_hrefs = []
    for i, t in enumerate(eps):
        e = picked_teams[i]
        for e1 in t.players:
            if (
                e1.player == "Animelib"
                and e1.translation_type.id == (2 - subtitles)
                and e1.team.name == e
            ):
                picked_hrefs.append(e1.video.quality[0].href)
                break
    print(list(map(lambda x: dow_link + x, picked_hrefs)))
    print(f"Download {len(picked_hrefs)} series..")

    import subprocess

    command_palette = 'curl "{}{}" > {}{}'

    async for index, link in aenumerate(picked_hrefs):
        subprocess.run(
            command_palette.format(
                dow_link,
                link,
                save_chapters_path[index].replace(" ", "\\ "),
                link.split("/")[-1],
            ),
            shell=True,
        )


async def download_ranobe(
    session,
    novel,
    novel_chapters: list[Chapter],
    save_directory: str,
    download_thumbs=True,
    not_silent=True,
    check_directories: list[str] | None = None,
):

    check_slash = lambda x: x if x[-1] == "/" else (x + "/")

    rus_name: str = (
        novel.model.rus_name
        if (novel.model.rus_name != "" and novel.model.rus_name is not None)
        else novel.model.name
    )

    if check_directories:
        for directory in check_directories:
            if rus_name in os.listdir(directory):
                save_directory = check_slash(directory)

    try:
        os.mkdir(save_directory + for_filename(rus_name))
    except FileExistsError:
        pass

    if download_thumbs:
        back_url = (await novel.addition_info(["background"], auth=True))["background"]["url"]
        def check_orig(x):
            try:
                return x.orig
            except AttributeError:
                return x.default
        dic: dict = {f"orig{e.info}": check_orig(e.cover) for e in await novel.covers()}
        if back_url[0] == "/":
            print("Background url dont finded")
        else:
            dic.update({"background": back_url})

        async for k, v in aiter(dic.items()):
            filename = f"{save_directory + for_filename(rus_name)}/{k}_{v.split('/')[-1]}"
            if len(filename.split("/")[-1].split(".")) == 1:
                filename += ".jpg"
            if not os.path.isfile(filename):
                async with session.stream("GET", v) as response:
                    async with aiofiles.open(
                        filename,
                        "wb",
                    ) as file:
                        async for chunk in response.aiter_bytes(65_536):
                            await file.write(chunk)
    async def dow_ran(e: Chapter):
        cont = await e.content()
        (await cont.tohtml().process_images(session)).writeto(save_directory + for_filename(rus_name))
        if not_silent:
            print(f'\x1b[2K\rchapter volume={cont.model.volume}, number={cont.model.number}, name="{cont.model.name}" downloaded')

    await asyncio.gather(*map(dow_ran, novel_chapters))





dow_link = None
if __name__ == "__main__":
    site = input(
        "1: MANGALIB\n2: SLASHLIB\n3: RANOBELIB\n4: HENTAILIB\n5: ANIMELIB\nC: Collection\n"
    )
    is_ranobe = False
    is_anime = False
    is_collection = False
    match site:
        case "4":
            dow_link = "https://img3.imglib.info"
        case "3":
            is_ranobe = True
        case "5":
            is_anime = True
            dow_link = "https://video1.anilib.me/.%D0%B0s"
        case "1" | "2":
            dow_link = "https://img33.imgslib.link"
        case "C" | "c":
            site = "user"
            is_collection = True
        case _:
            raise Exception("Unmatched site")

    def input_indexes(chapters):
        minusid = lambda id, le: id if id >= 0 else (le+id)%le
        indexes = list(map(lambda x: minusid(int(x), len(chapters)), input("{start} {end}: ").split()))
        if len(indexes) == 0:
            indexes = [0, len(chapters)]
        elif len(indexes) == 1:
            indexes.append(indexes[0])
        indexes[1] += 1
        return indexes

    async def main(q=input("user title: " if is_collection else "manga title: "), forse_auth: bool = False, proxy: httpx.Proxy | None = None):
        async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(20),proxy=proxy) as session:
            novels = await LibAccount(session, "user.json").search(q, site, throw_beriar_to_all=is_collection or forse_auth, auth = is_anime or forse_auth)
            try:
                auth = novels[0].beriar
            except IndexError:
                raise Exception("Zero novels found")
            ua = {
                "User-Agent": "Mozilla/5.0 (Linux; U; Android 14; ru; SM-A245F Build/UP1A.231005.007.A245FXXS6CXH1) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/110.0.0.0 Mobile Safari/537.36"
            }
            if auth:
                auth.update(ua)
            else:
                auth = ua

            if is_collection:
                for index, user in enumerate(novels):
                    print(index, user.model.username)
            else:
                for index, novel in enumerate(novels):
                    print(
                        index,
                        (
                            novel.model.rus_name
                            if (
                                novel.model.rus_name != ""
                                and novel.model.rus_name is not None
                            )
                            else str(novel.model.name)
                        ),
                        novel.model.releaseDateString,
                    )

            novel = novels[int(input("index: "))]
            if forse_auth:
                novel.beriar = auth
            if is_collection:
                collections = await novel.collections_preview()
                for index, coll in enumerate(collections):
                    print(index, coll.model.name)
                indexes = input_indexes(collections)
                await download_collections(
                    collections[indexes[0] : indexes[1]], novel, auth
                )
            else:
                chapters = await novel.chapters()

                print("index volume number name")
                for index, chapter in enumerate(chapters):
                    print(
                        index,
                        *(
                            [chapter.season, chapter.number, chapter.name]
                            if is_anime
                            else [
                                chapter.model.volume,
                                chapter.model.number,
                                chapter.model.name,
                            ]
                        ),
                    )
                print()

                indexes = input_indexes(chapters)
                chapters = chapters[indexes[0] : indexes[1]]
                print(len(chapters), "on download")

                if is_ranobe:
                    await download_ranobe(session, novel, chapters, save_directory)
                elif is_anime:
                    await download_anime(novel, chapters)
                else:
                    await download_manga(session, novel, chapters, save_directory, check_directories=check_directories, one_by_one=len(chapters)>100, silent=False)

    proxy = None
    proxy = httpx.Proxy("socks5://127.0.0.1:1080")
    #proxy = httpx.Proxy("socks5h://127.0.0.1:9050")
    asyncio.run(main(forse_auth=True, proxy=proxy))

