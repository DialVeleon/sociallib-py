#sites:
MANGALIB = "1"
SLASHLIB = "2"
RANOBELIB = "3"
HENTAILIB = "4"
ANIMELIB = "5"
#? USER = "user"


# server_constants -> imageServers
id        label      url                        site_ids
main      Первый     https://img2.imglib.info   [1, 2, 3]
secondary Второй     https://img4.imgslib.link  [1, 2, 3]
compress  Сжатия     https://img33.imgslib.link [1, 2, 3]
download  Скачивание https://img33.imgslib.link [1, 2, 3]
crop      Crop pages https://crops.mangalib.me  [1, 2, 3]
main      Первый     https://img2h.imgslib.link [4]
secondary Второй     https://img2h.imgslib.link [4]
compress  Сжатия     https://img3.imglib.info   [4]
crop      Crop pages https://crops.hentailib.me [4]


#READ_TYPES:
"unread"
"all"
"read"

#NOTIF_TYPES:
"all"
"chapter"
"episode"
"comments"
"message"
"other"

#ENDPOINTS:
"https://api.lib.social/"
"https://auth.lib.social/"
"https://api.mangalib.me/"
"https://api.cdnlibs.org/"
"https://hapi.hentaicdn.org/"  # work at August 2025
#? "https://lib.social/"

beriar: str = {"Authorization": "Beriar {bigtoken}"}
slug_url = 154219--manmaru-meido-no-shihaisha-sama-goshujin-sama
                    or
                    manmaru-meido-no-shihaisha-sama-goshujin-sama

episode_id = 94126


+ user-agent #?
# me
https://api.mangalib.me/api/auth/me + beriar
https://api.mangalib.me/api/notifications/count" + beriar
https://api.mangalib.me/api/notifications?notification_type={NOTIF_TYPES}&page={int}&read_type={READ_TYPES}&sort_type=desc + beriar

# search
https://api.lib.social/api/manga?q={anystring}&site_id[]={pick(1,2,3,4)}&page={int >= 1}&fields[]=rate_avg&fields[]=rate&fields[]=releaseDate
https://api.lib.social/api/anime?q={anystring}&site_id[]=5&page={int}&fields[]=rate_avg&fields[]=rate&fields[]=releaseDate
https://api.mangalib.me/api/user?q={anystring.len > 1}&page={int}&sort_type=asc&sort_by=id

# manga
https://api.mangalib.me/api/manga/{slug_url}/chapters
https://api.mangalib.me/api/manga/{slug_url}/chapter?number=1&volume=1

# anime
https://api.mangalib.me/api/episodes?anime_id={slug_url}
https://api.mangalib.me/api/episodes/{episode_id}
https://api.mangalib.me/api/anime/{slug_url}/stats?bookmarks=true&rating=true
https://api.mangalib.me/api/anime/{slug_url}/similar
https://api.mangalib.me/api/anime/{slug_url}/relations
https://api.mangalib.me/api/comments?page={int}&post_id={anime_id}&post_type=anime&sort_by=id&sort_type=desc
https://api.mangalib.me/api/comments/sticky?post_id={anime_id}&post_type=anime
https://api.mangalib.me/api/reviews?page={int}&reviewable_id={anime_id}&reviewable_type=anime&sort_by=newest
https://api.mangalib.me/api/anime/{slug_url}?fields[]=background&fields[]=eng_name&fields[]=otherNames&fields[]=summary&fields[]=releaseDate&fields[]=type_id&fields[]=caution&fields[]=views&fields[]=close_view&fields[]=rate_avg&fields[]=rate&fields[]=genres&fields[]=tags&fields[]=teams&fields[]=user&fields[]=franchise&fields[]=authors&fields[]=publisher&fields[]=userRating&fields[]=moderated&fields[]=metadata&fields[]=metadata.count&fields[]=metadata.close_comments&fields[]=anime_status_id&fields[]=time&fields[]=episodes&fields[]=episodes_count&fields[]=episodesSchedule
https://api.mangalib.me/api/collections/{collection_id}
https://api.mangalib.me/api/user/{user_id}/stats
https://api.mangalib.me/api/user/{user_id}/chapters?moderated=1&page=1
https://api.mangalib.me/api/ignore/{user_id} + beriar
https://api.mangalib.me/api/friendship/{user_id}
https://api.mangalib.me/api/friendship?page=1&status=1&user_id={user_id}
https://api.mangalib.me/api/friendship/{user_id}/mutual?page={int}
https://api.mangalib.me/api/user/{user_id}?fields[]=background&fields[]=rolespoints&fields[]=ban_info&fields[]=gender&fields[]=created_at&fields[]=about&fields[]=teams
https://api.mangalib.me/api/anime/{slug_url}/similar
https://api.mangalib.me/api/anime/{slug_url}/relations
https://api.mangalib.me/api/bookmarks/folder/{user_id}
https://api.mangalib.me/api/bookmarks?page={int}&sort_by=name&sort_type=desc&status={bookmark_index}&user_id={user_id}
https://api.mangalib.me/api/user/{user_id}/comments?page=1&sort_by=id&sort_type=desc
https://api.mangalib.me/api/collections?limit={12}&page={int}&sort_by=newest&sort_type=desc&subscriptions={0}&user_id={user_id}
https://api.mangalib.me/api/reviews?limit={12}&page={int}&sort_by=newest&sort_type=desc&subscriptions={0}&user_id={user_id}&status=published
https://api.mangalib.me/api/reviews?limit={12}&page={int}&sort_by=newest&sort_type=desc&subscriptions={0}&user_id={user_id}&status=published&evaluation=positive
https://api.mangalib.me/api/reviews?limit={12}&page={int}&sort_by=newest&sort_type=desc&subscriptions={0}&user_id={user_id}&status=published&evaluation=negative
https://api.mangalib.me/api/reviews?limit={12}&page={int}&sort_by=newest&sort_type=desc&subscriptions={0}&user_id={user_id}&status=published&evaluation=neutral

