import asyncio
from sys import argv

from httpx import AsyncClient, Limits, Timeout
from sociallib import libapi
from sociallib.novelTypes import Hentai
from sociallib.addition_tools import extract_slug_url



async def likeall(full_url: str):
    async with AsyncClient(limits=Limits(max_connections=30), timeout=Timeout(60), http2=True) as cli:
        la = libapi.LibAccount(cli, "user.json")
        url = extract_slug_url(full_url)
        if url:
            manga = await Hentai(cli, auth_token=la.beriar, print_warnings=False).recover_model(url, use_auth=True)
            chs = await manga.chapters()
            print(sum(await asyncio.gather(*[e.set_like(True, do_and_think_later=True) for e in chs])), "likes switched")

async def main():
    if len(argv[1:]) == 0:
        await likeall(input("full_url: "))
    else:
        await asyncio.gather(*[likeall(full_url) for full_url in argv[1:]])

asyncio.run(main())

