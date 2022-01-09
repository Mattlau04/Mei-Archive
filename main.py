# Mei Archiver | Mattlau04, 08/01/2022

import os
import sys
import time
from datetime import datetime as dt
from typing import List

import pixivpy3
from colorama import init
from dateutil.parser import parse
from termcolor import cprint

########## Config ##########
LOG_TO_CONSOLE: bool = True # Set to False if you're running headless like a fag
LOG_FILE: str = "log.txt" # Set to False to disable logging to a file
SAVE_TO: str = "./Mei" # The folder to which save the pics (relative to the script's dir)
DATA_FILE: str = "fat.tits" # Filename for saving important data

PIXIV_REFRESH_TOKEN: str = "Put_token_here" # Holy shit pixiv just make an API already
CHECK_INTERVAL: int = 30 # How often to check for new pics (in seconds)
USER_ID: int = 15904233 # The artist's user id

# Only one of the two below need to be true for a post for it to be downloaded
TITLE_MATCH: List[str] = ["助眠合集", "寐老妈"] # Match the post if one of these string is in the title
TAG_MATCH: str = "寐" # Match the post if it has this tag

DEBUG_MODE = False # just prints extra shit
############################

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

def read_last_pid():
    """Gets the last checekd PID from the data file"""
    try:
        with open(DATA_FILE, 'r') as f:
            return int(f.readline())
    except FileNotFoundError:
        return 0

def write_last_pid(pid):
    """Writes the last checekd PID to the data file"""
    with open(DATA_FILE, 'w+') as f:
        f.write(str(pid))

def check_posts(pixivapi: pixivpy3.AppPixivAPI, check_after: int) -> int:
    """Checks for new downloadable post and return the id of the latest post checked"""
    higest_checked_pid = 0
    post_page = 0
    while True: #god i wish we had do...while in python
    # Break if there's no more post to check or we reach already checked posts
        log(f"Getting page {post_page+1} of posts", 'blue')
        pics: List[dict] = pixivapi.user_illusts(USER_ID, type='illust', offset=post_page*30) # We get 30 posts at a time
        # if max(pics['illusts'], key=lambda x:x['id'])['id'] <= check_after: # Aka the most recent post was already checked
        #     break
        for p in pics['illusts']:
            debug_print(f"checking post {p['id']}")
            higest_checked_pid = max(higest_checked_pid, p['id'])
            if p['id'] > check_after: # Aka we didn't check that post yet
                if any(s in p['title'] for s in TITLE_MATCH) or any(TAG_MATCH == t['name'] for t in p['tags']):
                    log(f"Post {p['id']} ({p['title']}) matched, downloading {p['page_count']} pic(s)", 'green')
                    post_dt = parse(p['create_date'])
                    # For some reason the URLs can be either in meta_pages or meta_single_page so we have to check both
                    if p["meta_single_page"]:
                        download_pic(p["meta_single_page"]["original_image_url"], post_dt)
                    for page in p["meta_pages"]: 
                        download_pic(page['image_urls']['original'], post_dt)
        post_page += 1
        if not pics['illusts']: # If there are no more posts to check
            break
        if p['id'] <= check_after: # Aka we had already checked that last post, no need to get more pages
            break

    log(f"Done checking posts, checked up to post {higest_checked_pid}", 'yellow')
    return higest_checked_pid

def download_pic(url: str, creation_date: dt) -> None:
    """Downloads the pic and gives it a creation time of the publishing of the pixiv post"""
    filename = os.path.basename(url)
    epoch = creation_date.timestamp()
    
    pixivapi.download(url, name=filename, path=SAVE_TO)
    os.utime(os.path.join(SAVE_TO, filename), (epoch, epoch))

def countdown(duration: int) -> None:
    """Waits a certain ammount of seconds with a nice countdown"""
    if LOG_TO_CONSOLE:
        for i in range(duration, 0, -1):
            cprint(f"Waiting {i} seconds...       ", 'grey', end='\r')
            time.sleep(1)
    else:
        time.sleep(duration)

if __name__ == "__main__":
    os.chdir(sys.path[0]) # Set working dir to script's dir
    if not os.path.isdir(SAVE_TO):
        os.mkdir(SAVE_TO)

    # That's probably the part that causes to crash when headless so putting that in a if
    if LOG_TO_CONSOLE:
        init()
    
    pixivapi = auth_to_pixiv()
    pid = read_last_pid()

    while True:
        pid = check_posts(pixivapi, pid)
        write_last_pid(pid)
        countdown(CHECK_INTERVAL)
