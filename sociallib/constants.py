from typing import Final


RETRIES_PLUS_ONE = 21  # how much will sociallib try to download something

SITE_MANGALIB: Final = "1"
SITE_SLASHLIB: Final = "2"
SITE_RANOBELIB: Final = "3"
SITE_HENTAILIB: Final = "4"
SITE_ANIMELIB: Final = "5"
SITE_USER: Final = "user"
SITE_PEOPLE: Final = "people"
SITE_FRANCHISE: Final = "franchise"
SITE_TEAM: Final = "teams"

READ_TYPE_UNREAD: Final = "unread"
READ_TYPE_ALL: Final = "all"
READ_TYPE_READ: Final = "read"

NOTIF_TYPE_ALL: Final = "all"
NOTIF_TYPE_CHAPTER: Final = "chapter"
NOTIF_TYPE_EPISODE: Final = "episode"
NOTIF_TYPE_COMMENTS: Final = "comments"
NOTIF_TYPE_MESSAGE: Final = "message"
NOTIF_TYPE_OTHER: Final = "other"

__prot = "https://"
__csocial_link = "lib.social/"
api_link: Final = __prot + "api." + __csocial_link
auth_link: Final = __prot + "auth." + __csocial_link
social_link: Final = __prot + __csocial_link
#mangalib_api_link: Final = __prot + "api.cdnlibs.org/" #"api2.mangalib.me/"
mangalib_api_link: Final = __prot + "hapi.hentaicdn.org/"
del __prot
del __csocial_link
