# sociallib-py

Unofficial API for lib sites (mangalib.me, ranobelib.me, etc.)

## Features

- Read info about all types of objects (People, Manga, Franchise, etc.)
- Use Bearer token for authorization
- Download all objects (Manga, Ranobe, etc.)
- Read, remove, mark as read, and download notifications
- Search all types of objects
- Like chapters

## Installation

```
pip install sociallib-py
```

> Note: This does not install the `examples/` folder.

## Usage

Check the files in the `examples/` folder for usage examples. For instance:

```
import asyncio
from httpx import AsyncClient, Limits, Timeout

from sociallib.libapi import LibAccount
from sociallib.novelTypes import Hentai
from sociallib.addition_tools import extract_slug_url


async def likeall(full_url: str):
    async with AsyncClient(
        limits=Limits(max_connections=30), timeout=Timeout(60), http2=True
    ) as cli:
        la = LibAccount(cli, "user.json")
        url = extract_slug_url(full_url)
        if url:
            manga = await Hentai(
                cli, auth_token=la.beriar, print_warnings=False
            ).recover_model(url, use_auth=True)
            chs = await manga.chapters()
            print(
                sum(
                    await asyncio.gather(
                        *[e.set_like(True, do_and_think_later=True) for e in chs]
                    )
                ),
                "likes switched",
            )

asyncio.run(likeall(input("full_url: ")))

```

## Contributing

Feel free to modify and send suggestions or pull requests. Issues and feedback are welcome!

## Todo

1. Split `sociallib/addition_tools.py` into `addition_tools.py` and `core.py`
2. Use `sociallib/color_codes.py` in all scripts
3. Implement more API features, like comment chapters

## License

This project is licensed under MIT. See the LICENSE file for details.

