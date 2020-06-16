#!/usr/bin/env python3

from bs4 import BeautifulSoup
import os
import sys
import datetime
import time
import hashlib
import requests
from threading import Thread
import json
from http import cookiejar
import fnmatch
import argparse
import shutil
import psutil
import pathlib
import asyncio
import subprocess
from dateutil import parser
import uvloop
from random import shuffle
from asyncio.subprocess import PIPE
from concurrent.futures import ProcessPoolExecutor, as_completed

# Cookies generator
from cookies_generator import cookies_init

# Other configs
from Configs import LYNDA_COOKIES, DOWNLOAD_DIR, MAX_WORKERS, BASE_URL


def parse_arguments():
    parser = argparse.ArgumentParser(description='Lynda Downloader')
    parser.add_argument('-u', '--url')
    parser.add_argument('-f', '--file')
    parser.add_argument('--concurrent', action="store_true")
    return parser, parser.parse_args()


def dl_tutorial(url, concurrent=False):
    start_time = time.perf_counter()
    if not os.path.exists(DOWNLOAD_DIR):
        os.mkdir(DOWNLOAD_DIR)
    tutorial = get_tutorial_data(url)
    create_local_folders(tutorial)
    create_info_txt(tutorial)
    dl_thumb(tutorial)
    if concurrent:
        dl_videos_async(tutorial)
    else:
        dl_videos_sync(tutorial)
    dl_exercise(tutorial)
    end_time = time.perf_counter()
    used_time = (end_time - start_time) / 60
    print(f"used {used_time:0.2f} minutes")
    return tutorial


def get_tutorial_data(url):
    """Get all the necessary info of a tutorial, including video urls and exercise"""
    # Get tutorial info
    tutorial = {}
    cj = cookiejar.MozillaCookieJar(LYNDA_COOKIES)
    cj.load()
    s = requests.Session()
    s.cookies = cj
    res = s.get(url, verify=False)
    soup = BeautifulSoup(res.text, "html.parser")
    thumnailUrl = soup.find('img', attrs={'itemprop': 'thumbnailUrl'}) or ''
    tutorial["thumbnailUrl"] = thumnailUrl['data-lazy-src'] if thumnailUrl else ''
    tutorial["url"] = url
    title_node = soup.find(
        'h1', attrs={'class': 'default-title'}) or ''
    if not title_node:
        return
    tutorial["title"] = title_node.text.replace(
        '/', ' ').strip() if title_node else ''
    for char in '?.!/;:öä':
        tutorial["title"] = tutorial["title"].replace(char, '')
    print(f"\n\"{tutorial['title']}\" is found.\n")
    tutorial["id"] = hashlib.md5(
        tutorial['title'].encode(encoding='UTF-8')).hexdigest()
    tutorial["author"] = soup.find(
        'cite', attrs={'data-ga-label': 'author-name'}).text.strip()
    released_at = soup.find(
        'span', attrs={'id': 'release-date'}).text.strip() or ''
    tutorial["released_at"] = released_at or ''
    tutorial["converted_released_at"] = parser.parse(
        released_at) if released_at else ''
    tutorial["time_required"] = soup.find(
        'span', attrs={'itemprop': 'timeRequired'}).text.strip()
    views_node = soup.find(
        'span', attrs={'id': 'course-viewers'}) or ''
    views = views_node.text.strip() if views_node else '0'
    tutorial["views"] = views
    tutorial["converted_views"] = views.replace(',', '') if views else '0'
    tutorial["description"] = soup.find(
        'div', attrs={'itemprop': 'description'}).text.strip()
    tutorial["level"] = soup.find(
        'div', attrs={'class': 'course-info-stat-cont'}).find('strong').text.strip()
    tutorial["subject_tags"] = [tag.text.strip()
                                for tag in soup.findAll('a', attrs={'data-ga-label': 'topic-tag'})]
    categories = [
        "Business",
        "Design",
        "Developer",
        "IT",
        "Marketing",
        "Web",
        "Photography",
        "Video",
        "Audio + Music",
        "CAD",
        "3D + Animation",
        "Education + Elearning"]
    tutorial["category"] = 'general'
    for tag in tutorial["subject_tags"]:
        if tag in categories:
            tutorial['category'] = tag
    tutorial["software_tags"] = [tag.text.strip() for tag in soup.findAll(
        'a', attrs={'data-ga-label': 'software-tag'})]
    tutorial["downloaded_at"] = datetime.datetime.now().strftime("%b %d, %Y")
    exercise_file_name = soup.find(
        'span', attrs={'class': 'exercise-name'}) or ''
    tutorial["exercise_file_name"] = exercise_file_name.text.strip(
    ) if exercise_file_name else ''
    exercise_file_size = soup.find('span', attrs={'class': 'file-size'}) or ''
    tutorial["exercise_file_size"] = exercise_file_size.text.strip(
    ) if exercise_file_size else ''
    exercise_file_url = soup.find('a', attrs={'class': 'course-file'}) or ''
    tutorial["exercise_file_url"] = BASE_URL + \
        exercise_file_url['href'] if exercise_file_url else ''

    # Get chapters info
    chapters = {}
    toc = soup.find('ul', attrs={'class': 'course-toc'})
    for _, chapter in enumerate(toc.find_all('li', attrs={'role': 'presentation'})):
        ch = chapter.find('h4', attrs={'data-ga-label': 'toc-chapter'})
        if ch:
            lectures = []
            for lecture in chapter.find_all('a', attrs={'class': 'video-name'}):
                lectures.append((lecture.text.strip(), lecture["href"]))
            chapters[ch.text.strip().replace(":", " -").replace('/',
                                                                "-").replace('.', '-')] = lectures

    tutorial["chapters"] = chapters
    return tutorial


def create_local_folders(tutorial):
    """Create local folders"""
    # Create local folders
    tutorial_root = DOWNLOAD_DIR + '/' + tutorial["title"]
    if not os.path.exists(tutorial_root):
        os.mkdir(tutorial_root)
        print(f"\"{tutorial['title']}\" folder is created.\n")
    else:
        print(f"\"{tutorial['title']}\" folder already exists.\n")
    for chapter, _ in tutorial["chapters"].items():
        chapter_dir = tutorial_root + '/' + chapter
        if not os.path.exists(chapter_dir):
            os.mkdir(chapter_dir)
            print(f"\"{chapter}\" folder is created.\n")
        else:
            print(f"\"{chapter}\" folder already exists.\n")


def create_info_txt(tutorial):
    text = ''
    text += f"Title: {tutorial['title']}\n\n"
    text += f"Course Url: {tutorial['url']}\n\n"
    text += f"Author: {tutorial['author']}\n\n"
    text += f"Released Date: {tutorial['released_at']}\n\n"
    text += f"Duration: {tutorial['time_required']}\n\n"
    text += f"Views: {tutorial['views']}\n\n"
    text += f"Skill Level: {tutorial['level']}\n\n"
    text += f"Category: {tutorial['category']}\n\n"
    text += f"Subject Tags: {', '.join(tutorial['subject_tags'])}\n\n"
    text += f"Software Tags: {', '.join(tutorial['software_tags'])}\n\n"
    text += f"Description: \n{tutorial['description']}\n\n"

    course_content = ''
    for chapter, lectures in tutorial["chapters"].items():
        course_content += (chapter + '\n')
        for _, lecture in enumerate(lectures):
            course_content += ('  ' + lecture[0] + '\n')
    text += f"Course Content: \n{course_content}\n\n"
    tutorial_root = DOWNLOAD_DIR + '/' + tutorial["title"]
    filename = tutorial['title'] + '.txt'
    filepath = tutorial_root + '/' + filename
    with open(filepath, "w") as txtfile:
        txtfile.write(text)


def dl_videos_sync(tutorial):
    results = dl_videos_s(tutorial)
    print("Videos and Srts DOWNLOADING IS DONE")
    return results


def dl_videos_s(tutorial):
    tasks = []
    tutorial_root = DOWNLOAD_DIR + '/' + tutorial["title"]
    for chapter, lectures in tutorial["chapters"].items():
        for _, lecture in enumerate(lectures):
            chapter_dir = tutorial_root + '/' + chapter
            tasks.append(dl_video_s(lecture, chapter_dir))
    return tasks


def dl_video_s(lecture, chapter_dir):
    """Download video and srt of single lecture"""
    if not LYNDA_COOKIES:
        print("Please set cookies")
        sys.exit(1)
    if os.path.exists(chapter_dir + '/' + lecture[0] + '.mp4'):
        print(f"\"{lecture[0]}\" already exists.")
        return
    process = subprocess.Popen(["youtube-dl", "--output", f"{chapter_dir}/{lecture[0]}.%(ext)s",
                                "--write-sub", "--cookies", LYNDA_COOKIES, lecture[1]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result, err = process.communicate()
    if err:
        print(err)
        sys.exit(1)
    elif result:
        print(f"\"{lecture[0]}\" was downloaded.")
    else:
        print(f"Error downloading {lecture[0]}.")
        sys.exit(1)


def dl_videos_async(tutorial):
    uvloop.install()
    results = asyncio.run(dl_videos(tutorial))
    print("Videos and Srts DOWNLOADING IS DONE")
    return results


async def dl_videos(tutorial):
    """Download videos and srts to local folders"""
    tasks = []
    tutorial_root = DOWNLOAD_DIR + '/' + tutorial["title"]
    for chapter, lectures in tutorial["chapters"].items():
        for _, lecture in enumerate(lectures):
            chapter_dir = tutorial_root + '/' + chapter
            tasks.append(dl_video(lecture, chapter_dir))
    results = await asyncio.gather(*tasks)
    return results


async def dl_video(lecture, chapter_dir):
    """Download video and srt of single lecture"""
    if LYNDA_COOKIES:
        auth = "--cookies " + LYNDA_COOKIES
    else:
        print("Please set cookies")
        sys.exit(1)
    if os.path.exists(chapter_dir + '/' + lecture[0] + '.mp4'):
        print(f"\"{lecture[0]}\" already exists.")
        return
    process = await asyncio.create_subprocess_shell(f"youtube-dl --output \"{chapter_dir}/{lecture[0]}.%(ext)s\" --write-sub {auth} {lecture[1]}", stdout=PIPE, stderr=PIPE)
    result, err = await process.communicate()
    if err:
        print(err)
        sys.exit(1)
    elif result:
        print(f"\"{lecture[0]}\" was downloaded.")
    else:
        print(f"Error downloading {lecture[0]}.")
        sys.exit(1)


def dl_thumb(tutorial):
    """Download thumb images"""
    tutorial_root = DOWNLOAD_DIR + '/' + tutorial["title"]
    image_url = tutorial['thumbnailUrl']
    r = requests.get(image_url, stream=True)
    if r.status_code == 200:
        image_name = tutorial['title'] + '.jpg'
        image_path = tutorial_root + '/' + image_name
        with open(image_path, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
        print(f"Thumb of {tutorial['title']} is downloaded.")


def extract_real_url(original_url):
    cj = cookiejar.MozillaCookieJar(LYNDA_COOKIES)
    cj.load()
    s = requests.Session()
    s.cookies = cj
    r = s.get(original_url)
    if r.status_code == 200:
        return r.url
    else:
        print('Error extracting real exercise file url')
        sys.exit(1)


def dl_exercise(tutorial):
    """Upload exercise file to servers"""
    tutorial_root = DOWNLOAD_DIR + '/' + tutorial["title"]
    if tutorial['exercise_file_url']:
        exercise_file_url = tutorial['exercise_file_url']
        exercise_file_real_url = extract_real_url(exercise_file_url)
        r = requests.get(exercise_file_real_url, stream=True)
        if r.status_code == 200:
            exercise_file_name = tutorial['title'] + '-' + 'exercise' + '.zip'
            exercise_file_path = tutorial_root + '/' + exercise_file_name
            with open(exercise_file_path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
            print(
                f"Exercise file of {tutorial['title']} is downloaded")
    else:
        print("No exercise file to download.")
        return


def download_executor(urls, concurrent=False, max_workers=MAX_WORKERS):
    print(f"{len(urls)} urls to download.")
    shuffle(urls)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(dl_tutorial, url, concurrent)
                   for url in urls]
        results = []
        for result in as_completed(futures):
            results.append(result)
        return results


def main():
    parser, arguments = parse_arguments()
    if arguments.file:
        cookies_init()
        try:
            with open(arguments.file) as urls:
                download_executor(
                    list(urls), arguments.concurrent)
        except Exception as e:
            print(e)
    elif arguments.url:
        cookies_init()
        try:
            urls = [arguments.url]
            download_executor(urls, arguments.concurrent)
        except Exception as e:
            print(e)
    else:
        parser.print_usage()
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Shutdown requested...exiting")
    except Exception:
        sys.exit(0)
