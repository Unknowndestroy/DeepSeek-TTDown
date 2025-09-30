#!/usr/bin/env python3

import os
import sys
import re
import requests
import subprocess
from urllib.parse import urlparse

class TikTokDownloader:
    def __init__(self):
        self.download_dir = os.path.expanduser("~/storage/downloads/TikTok")
        self.audio_dir = os.path.join(self.download_dir, "Audio")
        self.video_dir = os.path.join(self.download_dir, "Video")
        
        # Create directories
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)
        
        # Colors
        self.RED = '\033[0;31m'
        self.GREEN = '\033[0;32m'
        self.YELLOW = '\033[1;33m'
        self.BLUE = '\033[0;34m'
        self.NC = '\033[0m'
    
    def print_banner(self):
        banner = f"""
{self.GREEN}
╔══════════════════════════════════════╗
║      TikTok Downloader for Termux    ║
║         Like ssstiktok Tool          ║
╚══════════════════════════════════════╝
{self.NC}
"""
        print(banner)
    
    def check_dependencies(self):
        """Check if required tools are installed"""
        try:
            subprocess.run(["which", "yt-dlp"], check=True, capture_output=True)
            subprocess.run(["which", "ffmpeg"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print(f"{self.RED}Error: yt-dlp or ffmpeg not found!{self.NC}")
            print("Install with: pip install yt-dlp && pkg install ffmpeg")
            sys.exit(1)
    
    def is_valid_tiktok_url(self, url):
        """Validate TikTok URL"""
        patterns = [
            r'^https://(vm|www)\.tiktok\.com/',
            r'^https://vt\.tiktok\.com/'
        ]
        return any(re.match(pattern, url) for pattern in patterns)
    
    def get_video_title(self, url):
        """Extract video title from TikTok page"""
        try:
            response = requests.get(url, timeout=10)
            title_match = re.search(r'<title>(.*?)</title>', response.text)
            if title_match:
                title = title_match.group(1)
                # Clean title for filename
                title = re.sub(r'[^\w\s-]', '', title)
                title = re.sub(r'[-\s]+', '_', title)
                return title[:100]
        except:
            pass
        return "tiktok_video"
    
    def download_video(self, url, mode="both"):
        """Download video using yt-dlp"""
        try:
            title = self.get_video_title(url)
            print(f"{self.BLUE}Downloading: {title}{self.NC}")
            
            if mode in ["audio", "both"]:
                # Download audio
                cmd = [
                    "yt-dlp", "-x", "--audio-format", "mp3",
                    "-o", os.path.join(self.audio_dir, "%(title)s.%(ext)s"),
                    url
                ]
                subprocess.run(cmd, check=True)
            
            if mode in ["video", "both"]:
                # Download video
                cmd = [
                    "yt-dlp", "-f", "best[height<=720]",
                    "-o", os.path.join(self.video_dir, "%(title)s.%(ext)s"),
                    url
                ]
                subprocess.run(cmd, check=True)
            
            print(f"{self.GREEN}✓ Download completed: {title}{self.NC}")
            return True
            
        except subprocess.CalledProcessError:
            print(f"{self.RED}✗ Download failed: {url}{self.NC}")
            return False
    
    def run(self):
        """Main function"""
        self.print_banner()
        self.check_dependencies()
        
        # Get number of videos
        try:
            video_count = int(input(f"{self.YELLOW}Enter the number of videos you want to download: {self.NC}"))
        except ValueError:
            print(f"{self.RED}Error: Please enter a valid number{self.NC}")
            sys.exit(1)
        
        # Collect URLs
        urls = []
        for i in range(video_count):
            while True:
                url = input(f"{self.BLUE}Enter link {i+1}: {self.NC}").strip()
                if self.is_valid_tiktok_url(url):
                    urls.append(url)
                    print(f"{self.GREEN}✓ URL added{self.NC}")
                    break
                else:
                    print(f"{self.RED}✗ Invalid TikTok URL. Please enter a valid TikTok link{self.NC}")
        
        # Choose download mode
        print(f"\n{self.YELLOW}Choose download mode:{self.NC}")
        print("1. Video + Audio (default)")
        print("2. Video only")
        print("3. Audio only")
        
        choice = input(f"{self.BLUE}Enter choice [1-3]: {self.NC}").strip()
        mode_map = {"1": "both", "2": "video", "3": "audio"}
        mode = mode_map.get(choice, "both")
        
        # Download summary
        print(f"\n{self.YELLOW}Download Summary:{self.NC}")
        print(f"Mode: {mode}")
        print(f"Videos to download: {len(urls)}")
        print(f"Download directory: {self.download_dir}")
        
        # Start downloading
        print(f"\n{self.YELLOW}Starting download...{self.NC}")
        success_count = 0
        
        for url in urls:
            if self.download_video(url, mode):
                success_count += 1
            print("-" * 40)
        
        # Final summary
        print(f"\n{self.GREEN}Download Complete!{self.NC}")
        print(f"Successfully downloaded: {success_count}/{len(urls)} videos")
        print(f"Files saved in: {self.download_dir}")

if __name__ == "__main__":
    downloader = TikTokDownloader()
    downloader.run()