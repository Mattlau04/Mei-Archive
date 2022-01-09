# Mei Archiver | Mattlau04, 08/01/2022

import os
import sys
import time
from datetime import datetime as dt
from typing import List, Tuple

import pixivpy3
from colorama import init
from dateutil.parser import parse
from termcolor import cprint
from pprint import pprint
import requests
import requests.cookies

# Important: he doesn't have a naming convention on fanbox, so some posts Mei be missing (haha funny pun)

############### Config ###############
LOG_TO_CONSOLE: bool = True # Set to False if you're running headless like a fag
LOG_FILE: str = "log.txt" # Set to False to disable logging to a file
SAVE_TO: str = "./Mei" # The folder to which save the pics (relative to the script's dir)
DATA_FILE: str = "huge.tits" # Filename for saving important data (relative to the script's dir)

PIXIV_REFRESH_TOKEN: str = "put_refresh_token_here" # Holy shit pixiv just make an API already
CHECK_INTERVAL: int = 600 # How often to check for new pics (in seconds) | Recommended: 600
USER_ID: int = 15904233 # The artist's user id (this is also his fanbox PID and will therefore also be used for kemono)

# Only one of the two below need to be true for a post for it to be downloaded
TITLE_MATCH: List[str] = ["助眠合集", "寐老妈", "寐"] # Match the post if one of these string is in the title (and/or the description on kemono only)
TAG_MATCH: str = "寐" # Match the post if it has this tag

ENABLE_KEMONO = True # Scraping fanbox using kemono
DOWNLOAD_KEMONO_FILES = True # Files are often thumbnails so you might want to not download them, it will stilld download attachements tho
FILE_EXTENSION_BLACKLIST = ['zip'] # Only applies to kemono, mostly to not download huge zips

DEBUG_MODE = False # just prints extra shit
######################################

def log(text: str, color: str) -> None:
    """Logs a message to console (with color) and a to a file"""
    # First we format the message
    formated_text = dt.now().strftime("[%d/%m/%Y | %H:%M:%S] ") + text

    if LOG_TO_CONSOLE:
        cprint(formated_text, color=color)

    if LOG_FILE:
        with open(LOG_FILE, "a+", encoding='utf8') as f:
            f.write(formated_text + '\n')

def debug_print(*args, **kwargs) -> None:
    """Prints something only if debug mode is on"""
    if DEBUG_MODE:
        print(*args, **kwargs)

def auth_to_pixiv() -> pixivpy3.AppPixivAPI:
    """This might get stuck for a while because pixiv is gay"""
    tries = 1
    while True: #Pain, just pain
        try:
            pixivapi = pixivpy3.AppPixivAPI() #init pixiv session
            pixivapi.auth(refresh_token=PIXIV_REFRESH_TOKEN)
            break
        except pixivpy3.PixivError:
            wait = min(60, 2**tries) # Waits 2s then 4 then 8, 16, 32, then caps at 60
            log(f"Failed to auth into pixiv, trying again after {wait}s (try {tries})", 'red')
            countdown(wait)
            tries += 1
    return pixivapi

def read_last_pid() -> Tuple[int, int]:
    """Gets the last checekd PIDs from the data file (first is Pixiv's and second is Kemono's"""
    try:
        with open(DATA_FILE, 'r') as f:
            return map(int, f.readline().split(',')) # We read, then split, then convert to int
    except FileNotFoundError: # In case the file doesn't exist yet
        return (0, 0)

def write_last_pid(pixiv_pid: int, kemono_pid: int):
    """Writes the last checekd PIDs to the data file"""
    with open(DATA_FILE, 'w+') as f:
        f.write(f"{pixiv_pid},{kemono_pid}")

def check_pixiv_posts(pixivapi: pixivpy3.AppPixivAPI, check_after: int) -> int:
    """Checks for new downloadable post on pixiv and return the id of the latest post checked"""
    higest_checked_pid = 0
    post_page = 0
    while True: #god i wish we had do...while in python
    # Break if there's no more post to check or we reach already checked posts
        log(f"Getting page {post_page+1} of pixiv posts", 'blue')
        pics: List[dict] = pixivapi.user_illusts(USER_ID, type='illust', offset=post_page*30) # We get 30 posts at a time
        # if max(pics['illusts'], key=lambda x:x['id'])['id'] <= check_after: # Aka the most recent post was already checked
        #     break
        for p in pics['illusts']:
            debug_print(f"checking pixiv post {p['id']}")
            higest_checked_pid = max(higest_checked_pid, p['id'])
            if p['id'] > check_after: # Aka we didn't check that post yet
                if any(s in p['title'] for s in TITLE_MATCH) or any(TAG_MATCH == t['name'] for t in p['tags']):
                    log(f"Pixiv post {p['id']} ({p['title']}) matched, downloading {p['page_count']} pic(s)", 'green')
                    post_dt = parse(p['create_date'])
                    # For some reason the URLs can be either in meta_pages or meta_single_page so we have to check both
                    if p["meta_single_page"]:
                        download_pixiv_pic(p["meta_single_page"]["original_image_url"], post_dt)
                    for page in p["meta_pages"]: 
                        download_pixiv_pic(page['image_urls']['original'], post_dt)
        post_page += 1
        if not pics['illusts']: # If there are no more posts to check
            break
        if p['id'] <= check_after: # Aka we had already checked that last post, no need to get more pages
            break
    log(f"Done checking pixiv posts, checked up to post {higest_checked_pid}", 'yellow')
    return higest_checked_pid

def download_pixiv_pic(url: str, creation_date: dt) -> None:
    """Downloads the pic and gives it a creation time of the publishing of the pixiv post"""
    filename = os.path.basename(url)
    epoch = creation_date.timestamp()
    
    pixivapi.download(url, name=filename, path=SAVE_TO)
    os.utime(os.path.join(SAVE_TO, filename), (epoch, epoch))

def download_kemono_pic(url: str, creation_date: dt, filename: str, session: requests.Session) -> None:
    """Downloads the pic and gives it a creation time of the publishing of the fanbox post"""
    epoch = creation_date.timestamp()
    
    with open(os.path.join(SAVE_TO, filename), 'wb+') as f:
        r = session.get(url)
        f.write(r.content)

    os.utime(os.path.join(SAVE_TO, filename), (epoch, epoch))

def countdown(duration: int) -> None:
    """Waits a certain ammount of seconds with a nice countdown"""
    if LOG_TO_CONSOLE:
        for i in range(duration, 0, -1):
            cprint(f"Waiting {i} seconds...       ", 'cyan', end='\r')
            time.sleep(1)
    else:
        time.sleep(duration)

# Thanks https://github.com/NanDesuKa-FR/ddos-guard-bypass
def bypass_ddosguards(s: requests.Session) -> None:
    """Bypasses cringe DDOS-guard, why are image ddosguard protected in the first place smh"""
    r = s.post("https://check.ddos-guard.net/check.js")
    r.raise_for_status()
    for key, value in s.cookies.items():
        s.cookies.set_cookie(requests.cookies.create_cookie(key, value))

def check_kemono_posts(s: requests.Session, check_after: int) -> int:
    higest_checked_pid = 0
    # First we bypass DDoS-Guard
    bypass_ddosguards(s)

    # Then we download stuff
    offset = 0
    while True:
        log(f"Getting kemono posts with an offset of {offset}", 'blue')
        r = requests.get(f'https://kemono.party/api/fanbox/user/{USER_ID}', params={'o': offset}).json()
        for p in r: # For every posts
            debug_print(f"checking kemono post {p['id']}")
            higest_checked_pid = max(higest_checked_pid, int(p['id']))
            if int(p['id']) > check_after: # Aka we didn't check that post yet
                #pprint(p)
                if any(s in p['title'] for s in TITLE_MATCH) or any(s in p['content'] for s in TITLE_MATCH): # If title match
                    log(f"Kemono post {p['id']} ({p['title']}) matched with {len(p['attachments'])} attachement(s) and {'a' if p['file'] else 'no'} file", 'green')
                    post_dt = parse(p['published'])
                    if DOWNLOAD_KEMONO_FILES and p['file']: # If we want to download file and there is a file
                        if not p['file']['name'].split('.')[-1] in FILE_EXTENSION_BLACKLIST: # Aka we can download
                            debug_print(f"Downloading https://kemono.party/data{p['file']['path']}?f={p['file']['name']}")
                            download_kemono_pic(f"https://kemono.party/data{p['file']['path']}?f={p['file']['name']}", post_dt, session=s, filename=p['file']['name']) # Yeah there's no prettier way to get the URL
                        else:
                            log(f"Skipping download of post {p['id']}'s file, as it's extension is in the blacklist", 'magenta') 
                    for a in p['attachments']: # We get attachements and not files bc files are just thumbnails or not pics
                        if not a['name'].split('.')[-1] in FILE_EXTENSION_BLACKLIST: # Aka we can download
                            debug_print(f"Downloading https://kemono.party/data{a['path']}?f={a['name']}")
                            download_kemono_pic(f"https://kemono.party/data{a['path']}?f={a['name']}", post_dt, session=s, filename=a['name']) # Yeah there's no prettier way to get the URL
                        else:
                            log(f"Skipping download of one of post {p['id']}'s attachements, as it's extension is in the blacklist", 'magenta')
        if int(p['id']) <= check_after: # Aka we had already checked that last post, no need to get more pages
            break
        offset += len(r) # This is usually 25, but since it's not a public API we can't be too careful
        if not r: # Aka we reached the end of the posts
            break
    log(f"Done checking kemono posts, checked up to post {higest_checked_pid}", 'yellow')
    return higest_checked_pid

if __name__ == "__main__":
    os.chdir(sys.path[0]) # Set working dir to script's dir
    if not os.path.isdir(SAVE_TO):
        os.mkdir(SAVE_TO)

    # That's probably the part that causes to crash when headless so putting that in a if
    if LOG_TO_CONSOLE:
        init()

    if ENABLE_KEMONO:
        kemonosession = requests.Session()
    
    pixiv_pid, kemono_pid = read_last_pid()
    pixivapi = auth_to_pixiv()

    while True: # We get the posts, write down that we checked them, then wait
        pixiv_pid = check_pixiv_posts(pixivapi, pixiv_pid)
        if ENABLE_KEMONO:
            kemono_pid = check_kemono_posts(kemonosession, kemono_pid)
        write_last_pid(pixiv_pid, kemono_pid)
        countdown(CHECK_INTERVAL)