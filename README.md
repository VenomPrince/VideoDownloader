# Video Downloader

A simple and clean web application to download videos from various platforms.

## Features

- Download videos from multiple platforms (YouTube, Vimeo, etc.)
- Support for playlists and multiple video options
- Clean and responsive user interface
- Easy to use - just paste the URL and download
- Hidden settings panel for better UX

## Installation

1. Make sure you have Python 3.7+ installed
2. Clone this repository
3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python app.py
```

2. Open your web browser and go to `http://localhost:5000`
3. Paste a video URL and click "Get Info"
4. Click the download button next to the video you want to download
5. Downloaded videos will be saved in the `downloads` folder

## Known Issues

- HTTP 403 Forbidden error may occur when:
  - Downloading playlists
  - Accessing certain videos
  - After stopping and resuming downloads
- Workaround: Try clearing your browser cache and cookies, or try again later

## Supported Platforms

This application uses yt-dlp which supports a wide range of video platforms including:
- YouTube
- Vimeo
- Facebook
- Twitter
- Instagram
- And many more!

## Note

Make sure you have proper rights to download the videos you're trying to download.
