import os
import tempfile
from pathlib import Path
import yt_dlp
from flask import Flask, request, jsonify, send_from_directory
import tkinter as tk
from tkinter import filedialog
import browser_cookie3

# Determine the base directory
BASE_DIR = Path(__file__).parent

# Create a Flask app with a static folder
app = Flask(__name__, 
            static_folder=BASE_DIR / 'static', 
            static_url_path='/static')

# Default download directory
DEFAULT_DOWNLOAD_DIR = Path.home() / 'Downloads' / 'VideoDownloader'
DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

class VideoDownloader:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,  # Changed to get full info
            'no_color': True,
            'format': 'best',
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 3,
            'file_access_retries': 3,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
            }
        }

    def _get_cookies(self, url):
        try:
            if 'youtube.com' in url or 'youtu.be' in url:
                return browser_cookie3.chrome(domain_name='.youtube.com')
            return None
        except:
            return None

    def _retry_with_cleared_cache(self, func, *args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Clear cache on each retry
                with yt_dlp.YoutubeDL() as ydl:
                    ydl.cache.remove()
                
                # Try the operation
                return func(*args, **kwargs)
            except Exception as e:
                if "HTTP Error 403" in str(e) and attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed, retrying...")
                    continue
                raise

    def get_video_info(self, url):
        def _get_info():
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                try:
                    # Extract basic info first
                    basic_info = ydl.extract_info(url, download=False, process=False)
                    if not basic_info:
                        raise Exception("Could not retrieve video information")

                    # Get detailed info
                    info = ydl.extract_info(url, download=False)
                    
                    # Handle playlists
                    if info.get('_type') == 'playlist':
                        if not info.get('entries'):
                            raise Exception("No videos found in playlist")
                        info = info['entries'][0]

                    # Ensure we have the required fields
                    if not info.get('title'):
                        raise Exception("Could not retrieve video title")

                    formats = []
                    for f in info.get('formats', []):
                        # Only include formats with both video and audio
                        if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                            format_id = f.get('format_id', '')
                            ext = f.get('ext', '')
                            resolution = f.get('resolution', 'unknown')
                            filesize = f.get('filesize', 0)
                            
                            # Get more detailed format info
                            vcodec = f.get('vcodec', 'unknown')
                            acodec = f.get('acodec', 'unknown')
                            
                            description = f"{resolution} ({ext})"
                            if filesize:
                                description += f" - {self._format_size(filesize)}"
                            
                            formats.append({
                                'format_id': format_id,
                                'description': description,
                                'ext': ext,
                                'filesize': filesize,
                                'vcodec': vcodec,
                                'acodec': acodec
                            })

                    # Sort formats by quality (assuming higher filesize = better quality)
                    formats.sort(key=lambda x: x.get('filesize', 0), reverse=True)

                    return {
                        'title': info.get('title', 'Unknown Title'),
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail', ''),
                        'webpage_url': info.get('webpage_url', url),
                        'description': info.get('description', ''),
                        'formats': formats,
                        'extractor': info.get('extractor', 'generic'),
                        'extractor_key': info.get('extractor_key', 'Generic')
                    }

                except Exception as e:
                    print(f"Error in video info extraction: {str(e)}")
                    raise

        try:
            return self._retry_with_cleared_cache(_get_info)
        except Exception as e:
            error_msg = str(e)
            if "ERROR:" not in error_msg:
                error_msg = f"ERROR: {error_msg}"
            print(f"Final error in get_video_info: {error_msg}")
            return {'error': error_msg}

    def download(self, url, format_id=None, download_dir=None):
        if not download_dir:
            download_dir = DEFAULT_DOWNLOAD_DIR
        else:
            download_dir = Path(download_dir)
            download_dir.mkdir(parents=True, exist_ok=True)

        def _download():
            with tempfile.TemporaryDirectory() as temp_dir:
                download_opts = self.ydl_opts.copy()
                download_opts.update({
                    'format': format_id if format_id else 'best',
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'merge_output_format': 'mp4',
                    'writethumbnail': False,
                    'writesubtitles': False,
                    'writeautomaticsub': False,
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }],
                    'prefer_ffmpeg': True,
                    'keepvideo': True,
                })

                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    # First, verify we can get the video info
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        raise Exception("Could not retrieve video information")

                    # Handle playlists
                    if info.get('_type') == 'playlist':
                        if not info.get('entries'):
                            raise Exception("No videos found in playlist")
                        info = info['entries'][0]

                    # Download the video
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        raise Exception("Download failed - no information returned")

                    # Find the downloaded file
                    temp_path = Path(temp_dir)
                    downloaded_files = list(temp_path.glob('*.*'))
                    
                    if not downloaded_files:
                        # Check if the file might be in a subdirectory
                        for subdir in temp_path.glob('**/*'):
                            if subdir.is_dir():
                                downloaded_files.extend(subdir.glob('*.*'))
                    
                    if not downloaded_files:
                        raise FileNotFoundError(f"No files found in {temp_dir} or its subdirectories")
                    
                    downloaded_file = downloaded_files[0]
                    
                    # Move to final destination
                    final_filename = self._sanitize_filename(downloaded_file.name)
                    final_path = download_dir / final_filename

                    # Ensure unique filename
                    counter = 1
                    while final_path.exists():
                        name, ext = os.path.splitext(final_filename)
                        final_path = download_dir / f"{name}_{counter}{ext}"
                        counter += 1

                    os.replace(str(downloaded_file), str(final_path))

                    return {
                        'success': True,
                        'filename': final_path.name,
                        'path': str(final_path)
                    }

        try:
            return self._retry_with_cleared_cache(_download)
        except Exception as e:
            error_msg = str(e)
            if "ERROR:" not in error_msg:
                error_msg = f"ERROR: {error_msg}"
            print(f"Final error in download: {error_msg}")
            return {'error': error_msg}

    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def _sanitize_filename(self, filename):
        return "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()

downloader = VideoDownloader()

@app.route('/')
def index():
    return send_from_directory(BASE_DIR / 'templates', 'index.html')

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'})
    return jsonify(downloader.get_video_info(url))

@app.route('/api/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')
    format_id = data.get('format_id')
    download_dir = data.get('download_dir')
    
    if not url:
        return jsonify({'error': 'URL is required'})
        
    return jsonify(downloader.download(url, format_id, download_dir))

@app.route('/api/select_directory', methods=['POST'])
def select_directory():
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Bring the dialog to front
        directory = filedialog.askdirectory()
        root.destroy()
        
        if directory:
            return jsonify({'path': directory})
        return jsonify({'error': 'No directory selected'})
    except Exception as e:
        return jsonify({'error': f'Failed to select directory: {str(e)}'})

@app.route('/api/get_download_dir', methods=['GET'])
def get_download_dir():
    return jsonify({'path': str(DEFAULT_DOWNLOAD_DIR)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
