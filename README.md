SubBuddy-py
===========

## Intro ##
SubBuddy-py is a tiny YouTube subscription auto-downloader written in Python utilizing youtube-dl. It is designed to replace the original .NET based SubBuddy.

## Abridged Setup/Usage Guide ##
1. Install Python (>=2.7.3 or >=3.3)
2. Install youtube-dl (http://rg3.github.io/youtube-dl/)
3. Get a developer key from https://code.google.com/apis/youtube/dashboard
4. Configure the settings in sbconfig.py
5. Run ```pip install httplib2``` in your terminal
6. Run ```python subbuddy.py``` in your terminal

## Downloading Single Videos ##
SubBuddy-py is capable of downloading single videos to make up for youtube-dl on its own won't grab the highest quality video by default if it is availabe in anything higher than 720p. What takes two or three commands and some understanding of YouTube's available formats takes a one liner ( ```python subbuddy.py -czd <VIDEO_ID_OR_URL>``` without the z if you provided login credentials) and a tiny bit of patience in SubBuddy-py.

## Downloading DASH Streams ##
SubBuddy-py ignores DASH streams by default (like youtube-dl), but if you'd like to download >720p videos you can set both ```download_dash``` and ```use_custom_ffmpeg``` to ```1``` in the config file. Most "stable" Linux distros ship with an outdated ffmpeg in their repos or a compatibility geared build from the Libav fork. The only way to guarantee success when SubBuddy-py is set to download DASH streams is to use a static build of ffmpeg from http://www.ffmpeg.org/download.html or by compiling ffmpeg yourself.

## Attributions ##
The GData Python client library is licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
