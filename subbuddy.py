#!/usr/bin/python

import os
import sys
import glob
import time
import json
import codecs
import pprint
import urllib
import argparse
import sbconfig
import httplib2
import threading
import subprocess
import gdata.youtube
import gdata.youtube.service

user_email = sbconfig.user_email
user_password = sbconfig.user_password
dev_key = sbconfig.dev_key
refresh_rate = sbconfig.refresh_rate
download_async = sbconfig.download_async
max_simultaneous_dls = sbconfig.max_simultaneous_dls
queue_size = sbconfig.queue_size
download_dash = sbconfig.download_dash
include_nsfw = sbconfig.include_nsfw
use_custom_ffmpeg = sbconfig.use_custom_ffmpeg
username_folders = sbconfig.username_folders
debug_mode = sbconfig.debug_mode
automatic_overwrite = sbconfig.automatic_overwrite

yt_service = gdata.youtube.service.YouTubeService()
yt_service.ssl = True
yt_service.developer_key = dev_key
new_subscription_videos_uri = 'https://gdata.youtube.com/feeds/api/users/default/newsubscriptionvideos'
dldb = 'downloaded'
subdb = 'localsubs'

download_queue = []
retry_queue = []
in_progress = dict()

def main():
  parser = argparse.ArgumentParser(description='YouTube subscription auto downloader command line options.')
  parser.add_argument('-s', '--skip-current-queue', action='store_true')
  parser.add_argument('-g', '--pull-subscriptions', action='store_true')
  parser.add_argument('-p', '--push-subscriptions', action='store_true')
  parser.add_argument('-I', '--run-once', action='store_true')
  parser.add_argument('-c', '--dont-check-subscriptions', action='store_true')
  parser.add_argument('-d', '--download-this')
  parser.add_argument('-z', '--dont-login', action='store_true')
  args = parser.parse_args()

  if not args.dont_login:
    print "Logging in to YouTube"
    login()

  check_files()

  if queue_size != 25:
    if queue_size <= 50 or queue_size >= 1:
      global new_subscription_videos_uri
      new_subscription_videos_uri += '?max-results=' + str(queue_size)

      if include_nsfw == 1:
        new_subscription_videos_uri += "&racy=include"
  else:
    if include_nsfw == 1:
      new_subscription_videos_uri += "?racy=include"

  if args.download_this:
    print "Single video mode."
    video_id = parse_id(args.download_this);

    chosen_v, chosen_a, filename, ext, username = get_video_info(video_id,
      args.dont_login)

    print u"Downloading '{}.{}'".format(filename, ext)
    download_video(video_id, chosen_v, chosen_a, filename, ext, username)

  if args.pull_subscriptions:
    print 'Grabbing remote subscriptions.'
    pull_subscribed_to()

  if args.push_subscriptions:
    print 'Adding local subscriptions.'
    push_subscribed_to()

  if args.skip_current_queue:
    print 'Skipping current subscription queue.'
    skip_current_queue()

  if args.dont_check_subscriptions:
    print 'Goodbye.'
    sys.exit(0)

  if download_async == 1:
    tw = threading.Thread(target=progress_monitor, args=([False]))
    tw.daemon = True
    tw.start()

  while True:
    check_files()
    check_and_download_subscriptions(download_queue)

    if args.run_once:
      print 'Goodbye.'
      sys.exit(0)

    if not download_queue:
      print 'Waiting', refresh_rate, 'seconds...'
      time.sleep(refresh_rate)

def progress_monitor(run_once = True):
  while(True):
    finished = []
    for k, v in in_progress.iteritems():
      if not v.is_alive() and k not in retry_queue:
        finished.append(k)
        log_download(k)

    for key in finished:
      del in_progress[key]
      if key in download_queue:
        download_queue.remove(key)

    if run_once:
      break

    time.sleep(5)

def check_files():
  if not os.path.exists(dldb):
    file(dldb, 'w').close()

  if not os.path.exists(subdb):
    file(subdb, 'w').close()

def log_download(video_id):
  f = open(dldb, 'a')
  f.write(video_id + '\n')
  f.close()

def pull_subscribed_to():
  subscription_feed = yt_service.GetYouTubeSubscriptionFeed(
    'https://gdata.youtube.com/feeds/api/users/default/subscriptions?max-results=50')
  subscribed_to = [line.strip() for line in open(subdb)]
  total_subscriptions = int(subscription_feed.total_results.text)
  total_pages = total_subscriptions / 50

  for x in range(0, total_pages):
    if x > 0:
      try:
        subscription_feed = yt_service.GetYouTubeSubscriptionFeed(
          'https://gdata.youtube.com/feeds/api/users/default/subscriptions?max-results=50&start-index=' +
          str(x * 50))
      except gdata.service.RequestError:
        return

    for entry in subscription_feed.entry:
      if entry.username.text not in subscribed_to:
        f = open(subdb,'a')
        f.write(entry.username.text + '\n')
        f.close()

def push_subscribed_to():
  subscription_feed = yt_service.GetYouTubeVideoFeed(
    'https://gdata.youtube.com/feeds/api/users/default/subscriptions?max-results=50')
  subscribed_to_local = [line.strip() for line in open(subdb)]
  subscribed_to_remote = []
  total_subscriptions = int(subscription_feed.total_results.text)
  total_pages = total_subscriptions / 50

  for x in range(0, total_pages):
    if x > 0:
      try:
        subscription_feed = yt_service.GetYouTubeSubscriptionFeed(
          'https://gdata.youtube.com/feeds/api/users/default/subscriptions?max-results=50&start-index=' +
          str(x * 50))
      except gdata.service.RequestError:
        break

    for entry in subscription_feed.entry:
      subscribed_to_remote.append(entry.username.text)

  for local_sub in subscribed_to_local:
    if local_sub not in subscribed_to_remote:
      new_subscription = yt_service.AddSubscriptionToChannel(
        username_to_subscribe_to=local_sub)

def skip_current_queue():
  ids = get_video_feed()
  downloaded = [line.strip() for line in open(dldb)]

  for video_id in ids:
    if video_id not in downloaded:
      log_download(video_id)

def check_and_download_subscriptions(ids = []):
  if debug_mode == 1 and download_async == 1:
    print("in_progress:")
    pprint.pprint(in_progress.keys())
    print("download_queue:")
    pprint.pprint(download_queue)
    print("retry_queue:")
    pprint.pprint(retry_queue)

  if not ids:
    print "Retrieving subscription feed"
    ids = get_video_feed()

  downloaded = [line.strip() for line in open(dldb)]

  for video_id in ids:
    if (video_id not in in_progress.keys() and len(in_progress) != max_simultaneous_dls) or download_async == 0:
      if video_id not in downloaded:
        print "Retrieving video info..."
        chosen_v, chosen_a, filename, ext, username = get_video_info(video_id)

        if chosen_v == 1006:
          continue
        else:
          print u"Downloading '{}.{}'".format(filename, ext)

        if download_async == 0:
          download_video(video_id, chosen_v, chosen_a, filename, ext, username)
          log_download(video_id)
        else:
          in_progress[video_id] = threading.Thread(target=download_video,
            args=(video_id, chosen_v, chosen_a, filename, ext, username))

          in_progress[video_id].daemon = True
          in_progress[video_id].start()

          if video_id in download_queue:
            download_queue.remove(video_id)
    elif video_id not in download_queue and video_id not in downloaded:
      download_queue.append(video_id)

  if download_async == 1:
    if download_queue:
      time.sleep(5)

    return download_queue
  else:
    return []

def parse_id(url):
  return url[url.rfind('=') + 1:]

def get_video_info(video_id, login = True):
  ytdl_args = ['youtube-dl', '-j']
  d_v = ['264','137','136','135','133']
  d_a = ['141','140','139']
  v = ['22','18','5']
  ordered_v = ['264','137','22','136','135','18','133','5']
  chosen_v = ''
  chosen_a = ''
  ext = ''
  needs_a = False

  if login:
    ytdl_args.extend(['--username', user_email, '--password', user_password])

  ytdl_args.append("https://www.youtube.com/watch?v={}".format(video_id))
  ytdl = subprocess.Popen(ytdl_args, stdout=subprocess.PIPE)
  out, err = ytdl.communicate()
  video_info = json.loads(out)

  for preferred in ordered_v:
    if len(chosen_v) > 0:
      break
    for available in video_info['formats']:
      if available['format_id'] == preferred:
        if preferred in d_v:
          if download_dash == 1:
            needs_a = True
            chosen_v = available['url']
            ext = available['ext']
          else:
            break
        else:
          chosen_v = available['url']
          ext = available['ext']
        break

  if needs_a:
    for preferred in d_a:
      if len(chosen_a) > 0:
        break
      for available in video_info['formats']:
        if available['format_id'] == preferred:
          chosen_a = available['url']
          break

  filename = u"{} - {} - {}".format(video_info['uploader'], video_info['title'],
    video_info['id'])

  for c in r'[]/\;,><&*:%=+@!#^()|?^':
    filename = filename.replace(c,'')

  return chosen_v, chosen_a, filename, ext, video_info['uploader']

def download_video(video_id, v_url, a_url, filename, ext, username = ""):
  ffmpeg_args = []

  if username_folders == 1:
    if not os.path.exists(username):
      os.makedirs(username)

    path = u"./{}/{}".format(username, filename)
  else:
    path = u"./{}".format(filename)

  if len(a_url) > 0:
    if not os.path.exists(path + '.m4v'):
      file(path + '.m4v', 'w').close()

    i = 0
    while(True):
      try:
        urllib.urlretrieve(v_url, path + '.m4v')
      except:
        i += 1

        if i < 5:
          continue
        else:
          retry_queue.append(video_id)
          return

      break

    if not os.path.exists(path + '.m4a'):
      file(path + '.m4a', 'w').close()

    i = 0
    while(True):
      try:
        urllib.urlretrieve(a_url, path + '.m4a')
      except:
        i += 1

        if i < 5:
          continue
        else:
          retry_queue.append(video_id)
          return

      break

    if use_custom_ffmpeg == 1:
      ffmpeg_args.append(os.path.abspath('ffmpeg'))
    else:
      ffmpeg_args.append('ffmpeg')

    if automatic_overwrite == 1:
      ffmpeg_args.append('-y')
    else:
      ffmpeg_args.append('-n')

    ffmpeg_args.extend(['-loglevel', 'quiet', '-i', path + '.m4v' , '-i', path
      + '.m4a', '-vcodec', 'copy', '-acodec', 'copy', path + '.mp4'])

    ffmpeg = subprocess.Popen(ffmpeg_args, stdout=subprocess.PIPE)
    out, err = ffmpeg.communicate()

    os.remove(path + '.m4v')
    os.remove(path + '.m4a')
  else:
    if not os.path.exists(path + '.' + ext):
      file(path + '.' + ext, 'w').close()

    i = 0
    while(True):
      try:
        urllib.urlretrieve(v_url, path + '.' + ext)
      except:
        i += 1

        if i < 5:
          continue
        else:
          retry_queue.append(video_id)
          return

      break

  if not os.path.exists(path + '.mp4'):
    retry_queue.append(video_id)
  elif video_id in retry_queue:
    retry_queue.remove(video_id)

def login():
  yt_service.email = user_email
  yt_service.password = user_password
  yt_service.ProgrammaticLogin()

def get_video_feed():
  ids = []

  while(True):
    try:
      feed = yt_service.GetYouTubeVideoFeed(new_subscription_videos_uri)
    except:
      if debug_mode == 1:
        print sys.exc_info()[0]

      time.sleep(5)
      continue
      # tbd: check if 403 and bother user

    break

  if debug_mode == 1:
    print("feed.entry:")

  for entry in feed.entry:
    if debug_mode:
      pprint.pprint(entry.id.text)

    gdata_video_url = entry.id.text
    video_id = entry.id.text[gdata_video_url.rfind('/') + 1:]
    ids.append(video_id)

  return ids

if __name__ == '__main__':
  main()
