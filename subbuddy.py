#!/usr/bin/python

import os
import sys
import glob
import time
import signal
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
max_simultaneous_dls = sbconfig.max_simultaneous_dls
queue_size = sbconfig.queue_size

yt_service = gdata.youtube.service.YouTubeService()
yt_service.ssl = True
yt_service.developer_key = dev_key
new_subscription_videos_uri = 'https://gdata.youtube.com/feeds/api/users/default/newsubscriptionvideos'
dldb = 'downloaded'
subdb = 'localsubs'

in_progress = []

def main():
	parser = argparse.ArgumentParser(description='YouTube subscription auto downloader command line options.')
	parser.add_argument('-s', '--skip-current-queue', action='store_true')
	parser.add_argument('-g', '--pull-subscriptions', action='store_true')
	parser.add_argument('-p', '--push-subscriptions', action='store_true')
	parser.add_argument('-I', '--run-once', action='store_true')
	parser.add_argument('-d', '--dont-download', action='store_true')
	args = parser.parse_args()
	login()
	check_files()
	
	if queue_size != 25:
		if queue_size <= 50 or queue_size >= 1:
			global new_subscription_videos_uri
			new_subscription_videos_uri += '?max-results=' + str(queue_size)
	
	if args.pull_subscriptions:
		print 'Grabbing remote subscriptions.'
		pull_subscribed_to()
	
	if args.push_subscriptions:
		print 'Adding local subscriptions.'
		push_subscribed_to()
	
	if args.skip_current_queue:
		print 'Skipping current subscription queue.'
		skip_current_queue()
		
	if args.dont_download:
		print 'Goodbye.'
		sys.exit(0)
	
	while True:
		check_files()
		check_and_download_subscriptions()
		
		if args.run_once
			print 'Goodbye.'
			sys.exit(0)
		
		print 'Waiting', refresh_rate, 'seconds...';
		time.sleep(refresh_rate)
		
def check_files():
	if not os.path.exists(dldb):
		file(dldb, 'w').close()
	
	if not os.path.exists(subdb):
		file(subdb, 'w').close()

def pull_subscribed_to():
	subscription_feed = yt_service.GetYouTubeSubscriptionFeed('https://gdata.youtube.com/feeds/api/users/default/subscriptions?max-results=50')
	subscribed_to = [line.strip() for line in open(subdb)]
	total_subscriptions = int(subscription_feed.total_results.text)
	total_pages = total_subscriptions / 50
	
	for x in range(0, total_pages):
		if x > 0:
			try:
				subscription_feed = yt_service.GetYouTubeSubscriptionFeed('https://gdata.youtube.com/feeds/api/users/default/subscriptions?max-results=50&start-index=' + str(x * 50))
			except gdata.service.RequestError:
				return
				
		for entry in subscription_feed.entry:
			if entry.username.text not in subscribed_to:
				f = open(subdb,'a')
				f.write(entry.username.text + '\n')
				f.close()

def push_subscribed_to():
	subscription_feed = yt_service.GetYouTubeVideoFeed('https://gdata.youtube.com/feeds/api/users/default/subscriptions?max-results=50')
	subscribed_to_local = [line.strip() for line in open(subdb)]
	subscribed_to_remote = []
	total_subscriptions = int(subscription_feed.total_results.text)
	total_pages = total_subscriptions / 50
		
	for x in range(0, total_pages):
		if x > 0:
			try:
				subscription_feed = yt_service.GetYouTubeSubscriptionFeed('https://gdata.youtube.com/feeds/api/users/default/subscriptions?max-results=50&start-index=' + str(x * 50))
			except gdata.service.RequestError:
				break
				
		for entry in subscription_feed.entry:
			subscribed_to_remote.append(entry.username.text)
		
	for local_sub in subscribed_to_local:
		if local_sub not in subscribed_to_remote:
			new_subscription = yt_service.AddSubscriptionToChannel(
				username_to_subscribe_to=local_sub)
		
def skip_current_queue():
	ids = get_feed(new_subscription_videos_uri)
	downloaded = [line.strip() for line in open(dldb)]
	
	for video_id in ids:
		if video_id not in downloaded:
			f = open(dldb,'a')
			f.write(video_id + '\n')
			f.close()

def check_and_download_subscriptions():
	ids = get_feed(new_subscription_videos_uri)
	downloaded = [line.strip() for line in open(dldb)]
	
	for video_id in ids:
		if video_id not in in_progress and len(in_progress) < max_simultaneous_dls:
			# youtube-dl will scrape the page before deciding whether or not to download the file
			if video_id not in downloaded:
				in_progress.append(video_id)
				subprocess.call(['youtube-dl', '-o %(uploader)s - %(title)s - %(id)s.%(ext)s', '--restrict-filenames', video_id])
				f = open(dldb,'a')
				f.write(video_id + '\n')
				f.close()
				in_progress.remove(video_id)
	
def login():
	yt_service.email = user_email
	yt_service.password = user_password
	yt_service.ProgrammaticLogin()
	
def get_feed(uri):
	ids = []
	feed = yt_service.GetYouTubeVideoFeed(uri)
	for entry in feed.entry:
		gdata_vido_url = entry.id.text
		video_id = entry.id.text[gdata_vido_url.rfind('/') + 1:]
		ids.append(video_id)
		
	return ids
	
if __name__ == '__main__':
	main()
