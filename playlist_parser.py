"""
Playlist and Audio File Parser for AudioJoiner Studio
Supports M3U, M3U8, PLS playlists, folders/directories, and standalone audio files.
"""

import os
import sys
import configparser
from typing import List, Dict, Optional, Tuple

SUPPORTED_AUDIO_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.aac', '.m4a', '.ogg', 
    '.opus', '.aiff', '.aif', '.wma', '.alac', '.ape'
}

PLAYLIST_EXTENSIONS = {'.m3u', '.m3u8', '.pls'}


class AudioTrackInfo:
    def __init__(self, filepath: str, title: Optional[str] = None, duration: float = 0.0):
        self.filepath = os.path.abspath(filepath)
        self.filename = os.path.basename(filepath)
        self.title = title if title else os.path.splitext(self.filename)[0]
        self.duration = duration  # In seconds
        self.filesize = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        self.format = os.path.splitext(filepath)[1].lower().replace('.', '').upper()
        self.sample_rate: Optional[int] = None
        self.channels: Optional[int] = None
        self.bitrate: Optional[int] = None

    def to_dict(self) -> Dict:
        return {
            "filepath": self.filepath,
            "filename": self.filename,
            "title": self.title,
            "duration": self.duration,
            "filesize": self.filesize,
            "format": self.format,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bitrate": self.bitrate,
        }

    def formatted_duration(self) -> str:
        if self.duration <= 0:
            return "--:--"
        mins = int(self.duration // 60)
        secs = int(self.duration % 60)
        return f"{mins}:{secs:02d}"

    def formatted_size(self) -> str:
        size = self.filesize
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} GB"


class PlaylistParser:
    @staticmethod
    def parse_m3u(filepath: str) -> List[AudioTrackInfo]:
        """Parse M3U / M3U8 files with relative or absolute paths."""
        tracks = []
        base_dir = os.path.dirname(os.path.abspath(filepath))
        current_title = None
        current_duration = 0.0

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#EXTINF:"):
                    # Format: #EXTINF:123,Artist - Title
                    meta = line[8:].split(',', 1)
                    try:
                        dur_str = meta[0].strip()
                        current_duration = max(0.0, float(dur_str))
                    except ValueError:
                        current_duration = 0.0
                    if len(meta) > 1:
                        current_title = meta[1].strip()
                elif not line.startswith("#"):
                    # File path
                    if os.path.isabs(line):
                        audio_path = line
                    else:
                        audio_path = os.path.normpath(os.path.join(base_dir, line))

                    if os.path.isfile(audio_path):
                        tracks.append(AudioTrackInfo(audio_path, title=current_title, duration=current_duration))
                    current_title = None
                    current_duration = 0.0
        return tracks

    @staticmethod
    def parse_pls(filepath: str) -> List[AudioTrackInfo]:
        """Parse PLS playlist format."""
        tracks = []
        base_dir = os.path.dirname(os.path.abspath(filepath))
        config = configparser.ConfigParser(interpolation=None)
        
        try:
            config.read(filepath, encoding='utf-8')
            if 'playlist' in config:
                section = config['playlist']
                num_entries = section.getint('NumberOfEntries', 0)
                
                # Try indexed 1..N or iterate keys
                for i in range(1, num_entries + 1):
                    file_key = f"File{i}"
                    title_key = f"Title{i}"
                    len_key = f"Length{i}"

                    if file_key in section:
                        raw_path = section[file_key]
                        if os.path.isabs(raw_path):
                            audio_path = raw_path
                        else:
                            audio_path = os.path.normpath(os.path.join(base_dir, raw_path))

                        if os.path.isfile(audio_path):
                            title = section.get(title_key, None)
                            length = section.getfloat(len_key, 0.0)
                            tracks.append(AudioTrackInfo(audio_path, title=title, duration=max(0.0, length)))
        except Exception as e:
            print(f"Error parsing PLS playlist {filepath}: {e}", file=sys.stderr)
            
        return tracks

    @classmethod
    def scan_directory(cls, dir_path: str, recursive: bool = True) -> List[AudioTrackInfo]:
        """Scan a directory for all recognized audio files."""
        tracks = []
        if recursive:
            for root, _, files in os.walk(dir_path):
                for f in sorted(files):
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_AUDIO_EXTENSIONS:
                        full_path = os.path.join(root, f)
                        tracks.append(AudioTrackInfo(full_path))
        else:
            for f in sorted(os.listdir(dir_path)):
                full_path = os.path.join(dir_path, f)
                if os.path.isfile(full_path):
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_AUDIO_EXTENSIONS:
                        tracks.append(AudioTrackInfo(full_path))
        return tracks

    @classmethod
    def parse_path(cls, path: str) -> List[AudioTrackInfo]:
        """Automatically detect if path is a directory, playlist, or single audio file."""
        if not os.path.exists(path):
            return []

        if os.path.isdir(path):
            return cls.scan_directory(path)

        ext = os.path.splitext(path)[1].lower()
        if ext in {'.m3u', '.m3u8'}:
            return cls.parse_m3u(path)
        elif ext == '.pls':
            return cls.parse_pls(path)
        elif ext in SUPPORTED_AUDIO_EXTENSIONS:
            return [AudioTrackInfo(path)]
        return []
