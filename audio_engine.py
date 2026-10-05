"""
Audio Engine for AudioJoiner Studio
Powered by FFmpeg with libsoxr resampler (SoX Resampler Library).
Handles complex audio filtergraphs for crossfading, silence insertion, 
fade-in/fade-out, high-fidelity sample rate conversion, and progress monitoring.
"""

import os
import sys
import json
import shutil
import subprocess
import re
from typing import List, Dict, Optional, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

# Global custom paths if configured by user via GUI
CUSTOM_FFMPEG_PATH: Optional[str] = None
CUSTOM_FFPROBE_PATH: Optional[str] = None

SOXR_PRESETS = {
    "none": {
        "name": "No Resample (FFmpeg default)",
        "precision": 0,
        "cutoff": 0,
        "description": "No explicit resampler; FFmpeg only converts the sample rate where tracks differ"
    },
    "soxr_vhq": {
        "name": "Very High Quality (28-bit VHQ)",
        "precision": 28,
        "cutoff": 0.95,
        "description": "Best possible audio quality, 28-bit precision, 95% passband bandwidth"
    },
    "soxr_hq": {
        "name": "High Quality (20-bit HQ)",
        "precision": 20,
        "cutoff": 0.91,
        "description": "Professional 20-bit precision, ideal balance of fidelity and speed"
    },
    "soxr_mq": {
        "name": "Medium Quality (16-bit MQ)",
        "precision": 16,
        "cutoff": 0.85,
        "description": "Standard 16-bit precision, faster rendering"
    }
}

CROSSFADE_CURVES = [
    ("tri", "Triangular (Linear gain)"),
    ("qsin", "Quarter of Sine wave"),
    ("esin", "Exponential Sine"),
    ("hsin", "Half of Sine wave"),
    ("log", "Logarithmic"),
    ("par", "Parabolic"),
    ("nofade", "No Fade (Cut)")
]

FORMAT_CONFIGS = {
    "FLAC": {
        "ext": ".flac",
        "codec": "flac",
        "options": ["-compression_level", "8"],
        "default_depth": "24",
        "lossless": True
    },
    "WAV": {
        "ext": ".wav",
        "codec": "pcm_s24le",
        "options": [],
        "default_depth": "24",
        "lossless": True
    },
    "MP3": {
        "ext": ".mp3",
        "codec": "libmp3lame",
        "options": [],  # bitrate added at run time by build_encoder_options()
        "default_depth": "16",
        "lossless": False
    },
    "AAC": {
        "ext": ".m4a",
        "codec": "aac",
        "options": [],  # bitrate added at run time by build_encoder_options()
        "default_depth": "16",
        "lossless": False
    },
    "OGG": {
        "ext": ".ogg",
        "codec": "libvorbis",
        "options": [],  # bitrate added at run time by build_encoder_options()
        "default_depth": "16",
        "lossless": False
    },
    "OPUS": {
        "ext": ".opus",
        "codec": "libopus",
        "options": [],  # bitrate added at run time by build_encoder_options()
        "default_depth": "16",
        "lossless": False
    },
    "ALAC": {
        "ext": ".m4a",
        "codec": "alac",
        "options": [],
        "default_depth": "24",
        "lossless": True
    }
}


def build_encoder_options(format_key: str, bitrate_kbps: int) -> List[str]:
    """
    Encoder options for the chosen format. For lossy formats the user's
    selected bitrate is applied directly. No -q:a / quality flag is added,
    because it would override -b:a and switch libmp3lame to VBR.
    """
    fmt = FORMAT_CONFIGS.get(format_key, FORMAT_CONFIGS["FLAC"])
    if fmt["lossless"]:
        return list(fmt["options"])
    opts = ["-b:a", f"{int(bitrate_kbps)}k"]
    if format_key == "OPUS":
        opts += ["-vbr", "on"]
    return opts


def find_binary(binary_name: str) -> str:
    """
    Search comprehensively for executable in PATH, adjacent directories,
    PyInstaller frozen bundle folders, and standard platform paths.
    """
    global CUSTOM_FFMPEG_PATH, CUSTOM_FFPROBE_PATH
    if binary_name.lower() == "ffmpeg" and CUSTOM_FFMPEG_PATH and os.path.isfile(CUSTOM_FFMPEG_PATH):
        return CUSTOM_FFMPEG_PATH
    if binary_name.lower() == "ffprobe" and CUSTOM_FFPROBE_PATH and os.path.isfile(CUSTOM_FFPROBE_PATH):
        return CUSTOM_FFPROBE_PATH

    env_var = "FFMPEG_PATH" if binary_name.lower() == "ffmpeg" else "FFPROBE_PATH"
    if os.environ.get(env_var) and os.path.isfile(os.environ[env_var]):
        return os.environ[env_var]

    candidate_dirs = []

    # 1. Directory of sys.executable (crucial for standalone Windows .exe)
    if sys.executable:
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidate_dirs.extend([exe_dir, os.path.join(exe_dir, "bin")])

    # 2. PyInstaller MEIPASS temporary directory if frozen
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidate_dirs.extend([meipass, os.path.join(meipass, "bin")])

    # 3. Directory of this script
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_dirs.extend([script_dir, os.path.join(script_dir, "bin")])
    except Exception:
        pass

    # 4. Current working directory
    try:
        cwd = os.getcwd()
        candidate_dirs.extend([cwd, os.path.join(cwd, "bin")])
    except Exception:
        pass

    # 5. Standard Windows installation paths
    if sys.platform == 'win32':
        candidate_dirs.extend([
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
            r"C:\Program Files (x86)\ffmpeg\bin",
            r"C:\tools\ffmpeg\bin",
            os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Links")
        ])

    # Check candidate folders
    extensions = [".exe", ""] if sys.platform == 'win32' else ["", ".exe"]
    for d in candidate_dirs:
        if not d or not os.path.isdir(d):
            continue
        for ext in extensions:
            target = os.path.join(d, f"{binary_name}{ext}")
            if os.path.isfile(target):
                return target

    # System PATH lookup
    found = shutil.which(binary_name)
    if found:
        return found
    if sys.platform == 'win32':
        found_win = shutil.which(f"{binary_name}.exe")
        if found_win:
            return found_win

    return binary_name


def check_soxr_support(ffmpeg_bin: str) -> bool:
    """Verify if the local FFmpeg build has libsoxr enabled."""
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        null_target = "NUL" if os.name == 'nt' else "/dev/null"
        cmd = [
            ffmpeg_bin, "-v", "error", 
            "-f", "lavfi", "-i", "sine=d=0.05", 
            "-af", "aresample=resampler=soxr", 
            "-f", "null", null_target
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=5, startupinfo=startupinfo)
        return proc.returncode == 0
    except Exception:
        return False


def probe_track(filepath: str, ffprobe_bin: Optional[str] = None) -> Dict:
    """Extract precise duration, sample rate, channels, and bitrate using ffprobe or ffmpeg."""
    bin_path = ffprobe_bin or find_binary("ffprobe")
    info = {
        "duration": 0.0,
        "sample_rate": 44100,
        "channels": 2,
        "bitrate": 0
    }
    
    # Try ffprobe first
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        cmd = [
            bin_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            filepath
        ]
        proc = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=10, 
            startupinfo=startupinfo
        )
        if proc.returncode == 0 and proc.stdout:
            data = json.loads(proc.stdout)
            audio_stream = None
            for s in data.get("streams", []):
                if s.get("codec_type") == "audio":
                    audio_stream = s
                    break

            fmt = data.get("format", {})
            if "duration" in fmt:
                try:
                    info["duration"] = float(fmt["duration"])
                except (ValueError, TypeError):
                    pass
            elif audio_stream and "duration" in audio_stream:
                try:
                    info["duration"] = float(audio_stream["duration"])
                except (ValueError, TypeError):
                    pass

            if audio_stream:
                if "sample_rate" in audio_stream:
                    info["sample_rate"] = int(audio_stream["sample_rate"])
                if "channels" in audio_stream:
                    info["channels"] = int(audio_stream["channels"])
                if "bit_rate" in audio_stream:
                    info["bitrate"] = int(audio_stream["bit_rate"])
    except Exception:
        pass

    # Reliable fallback using ffmpeg if duration is still 0
    if info["duration"] <= 0.0:
        try:
            ffmpeg_bin = find_binary("ffmpeg")
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cmd_f = [ffmpeg_bin, "-i", filepath]
            proc_f = subprocess.run(cmd_f, capture_output=True, text=True, timeout=10, startupinfo=startupinfo)
            combined = (proc_f.stderr or "") + (proc_f.stdout or "")
            dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", combined)
            if dur_match:
                hours = int(dur_match.group(1))
                mins = int(dur_match.group(2))
                secs = float(dur_match.group(3))
                info["duration"] = hours * 3600 + mins * 60 + secs

            sr_match = re.search(r"Audio:.*?, (\d+)\s*Hz", combined)
            if sr_match:
                info["sample_rate"] = int(sr_match.group(1))
            if "stereo" in combined.lower():
                info["channels"] = 2
            elif "mono" in combined.lower():
                info["channels"] = 1
        except Exception:
            pass

    return info


class CompilationConfig:
    def __init__(self):
        self.output_path: str = ""
        self.format_key: str = "FLAC"
        self.bitrate_kbps: int = 320
        self.bit_depth: str = "24"
        self.sample_rate: int = 48000
        self.use_soxr: bool = False
        self.soxr_preset: str = "none"
        
        # Transitions
        self.transition_mode: str = "crossfade"
        self.crossfade_duration: float = 3.0
        self.crossfade_curve1: str = "tri"
        self.crossfade_curve2: str = "tri"
        self.silence_gap: float = 2.0
        
        # Track fades
        self.start_fade_in: float = 1.0
        self.end_fade_out: float = 2.0


def build_ffmpeg_filtergraph(
    track_durations: List[float], 
    config: CompilationConfig,
    use_soxr: bool = True
) -> Tuple[str, List[str]]:
    """
    Build the complex FFmpeg filtergraph using the libsoxr resampler filter.
    Returns: (filter_complex_string, final_output_map)
    """
    n = len(track_durations)
    if n == 0:
        return "", []

    soxr_meta = SOXR_PRESETS.get(config.soxr_preset, SOXR_PRESETS["none"])

    if use_soxr:
        resample_filter = (
            f"aresample=resampler=soxr:precision={soxr_meta['precision']}:"
            f"osr={config.sample_rate}:cutoff={soxr_meta['cutoff']}"
        )
    else:
        # No explicit resampler: aformat below still conforms the sample rate
        # using FFmpeg's default resampler where a track's rate differs.
        resample_filter = None

    filters = []

    # Step 1: Pre-process each input to conform sample rates, channel layout (stereo),
    # and apply initial fade-in to track 0 or final fade-out to track n-1 safely
    for i in range(n):
        chain = [
            f"aformat=sample_fmts=fltp:sample_rates={config.sample_rate}:channel_layouts=stereo"
        ]
        if resample_filter:
            chain.append(resample_filter)
        
        if i == 0 and config.start_fade_in > 0:
            chain.append(f"afade=t=in:ss=0:d={config.start_fade_in:.2f}")

        # Only apply final fade out if duration is known and long enough to prevent truncation
        if i == n - 1 and config.end_fade_out > 0:
            dur = track_durations[i] if i < len(track_durations) else 0.0
            if dur > config.end_fade_out + 0.5:
                fade_start = max(0.0, dur - config.end_fade_out)
                chain.append(f"afade=t=out:st={fade_start:.2f}:d={config.end_fade_out:.2f}")

        filters.append(f"[{i}:a]{','.join(chain)}[proc_{i}]")

    # Step 2: Combine inputs according to transition mode
    if n == 1:
        return ";".join(filters), ["[proc_0]"]

    if config.transition_mode == "crossfade":
        current_in = "[proc_0]"
        for i in range(1, n):
            out_label = f"[xf_{i}]" if i < n - 1 else "[out_audio]"
            
            # Safe crossfade duration clamping to avoid "Input is too short" filter failures
            dur_a = track_durations[i-1] if (i - 1) < len(track_durations) else 0.0
            dur_b = track_durations[i] if i < len(track_durations) else 0.0
            xfade_dur = config.crossfade_duration

            if dur_a > 0.0 and dur_b > 0.0:
                max_xfade = min(dur_a * 0.45, dur_b * 0.45)
                if xfade_dur > max_xfade:
                    xfade_dur = max(0.2, max_xfade)

            cf_filter = (
                f"{current_in}[proc_{i}]acrossfade="
                f"d={xfade_dur:.2f}:"
                f"c1={config.crossfade_curve1}:"
                f"c2={config.crossfade_curve2}{out_label}"
            )
            filters.append(cf_filter)
            current_in = out_label
        return ";".join(filters), ["[out_audio]"]

    elif config.transition_mode == "silence":
        concat_inputs = []
        for i in range(n):
            concat_inputs.append(f"[proc_{i}]")
            if i < n - 1:
                silence_label = f"[sil_{i}]"
                filters.append(
                    f"aevalsrc=0:d={config.silence_gap:.2f}:s={config.sample_rate}:c=stereo,"
                    f"aformat=sample_fmts=fltp:sample_rates={config.sample_rate}:channel_layouts=stereo{silence_label}"
                )
                concat_inputs.append(silence_label)
        
        total_segments = len(concat_inputs)
        filters.append(
            f"{''.join(concat_inputs)}concat=n={total_segments}:v=0:a=1[out_audio]"
        )
        return ";".join(filters), ["[out_audio]"]

    else:
        concat_inputs = "".join([f"[proc_{i}]" for i in range(n)])
        filters.append(f"{concat_inputs}concat=n={n}:v=0:a=1[out_audio]")
        return ";".join(filters), ["[out_audio]"]


class AudioJoinWorker(QThread):
    """Worker thread that executes FFmpeg compilation without blocking the Qt GUI."""
    progress_changed = pyqtSignal(float, str)
    compilation_finished = pyqtSignal(bool, str)
    log_line_emitted = pyqtSignal(str)

    def __init__(self, track_paths: List[str], config: CompilationConfig):
        super().__init__()
        self.track_paths = track_paths
        self.config = config
        self._is_cancelled = False
        self.process: Optional[subprocess.Popen] = None
        self.full_log: List[str] = []

    def cancel(self):
        self._is_cancelled = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass

    def run(self):
        try:
            ffmpeg_bin = find_binary("ffmpeg")
            ffprobe_bin = find_binary("ffprobe")

            # Validate that ffmpeg actually exists and is executable
            if not ffmpeg_bin or (not os.path.isfile(ffmpeg_bin) and not shutil.which(ffmpeg_bin)):
                self.compilation_finished.emit(
                    False, 
                    "FFmpeg executable not found!\n\n"
                    "Please ensure FFmpeg is installed or place 'ffmpeg.exe' in the same folder as this application."
                )
                return
            
            # Ensure target directory exists
            out_dir = os.path.dirname(os.path.abspath(self.config.output_path))
            os.makedirs(out_dir, exist_ok=True)

            self.progress_changed.emit(2.0, "Analyzing audio metadata and durations...")
            
            # Step 1: Probe durations
            durations = []
            total_duration_estimate = 0.0
            for i, p in enumerate(self.track_paths):
                if self._is_cancelled:
                    self.compilation_finished.emit(False, "Compilation was cancelled.")
                    return
                meta = probe_track(p, ffprobe_bin)
                dur = meta.get("duration", 0.0)
                durations.append(dur)
                total_duration_estimate += dur
                pct = 2.0 + (i / max(1, len(self.track_paths))) * 8.0
                self.progress_changed.emit(pct, f"Probing track {i+1}/{len(self.track_paths)}...")

            # Adjust expected duration for crossfades/silence
            n = len(durations)
            if self.config.transition_mode == "crossfade" and n > 1:
                total_duration_estimate -= (n - 1) * self.config.crossfade_duration
            elif self.config.transition_mode == "silence" and n > 1:
                total_duration_estimate += (n - 1) * self.config.silence_gap
            
            total_duration_estimate = max(1.0, total_duration_estimate)

            # Check if soxr is supported
            has_soxr = False
            if self.config.use_soxr:
                has_soxr = check_soxr_support(ffmpeg_bin)
                if not has_soxr:
                    self.log_line_emitted.emit(
                        "libsoxr is not available in this FFmpeg build; using the standard resampler instead."
                    )
            engine_name = "libsoxr" if has_soxr else "standard resampler"

            # Step 2: Build FFmpeg command
            self.progress_changed.emit(12.0, f"Building {engine_name} filtergraph...")
            filter_str, out_maps = build_ffmpeg_filtergraph(durations, self.config, use_soxr=has_soxr)

            cmd = [ffmpeg_bin, "-y"]
            for p in self.track_paths:
                cmd.extend(["-i", p])

            cmd.extend(["-filter_complex", filter_str])
            for m in out_maps:
                cmd.extend(["-map", m])

            # Strip conflicting video album art and cuesheet/metadata blocks
            cmd.extend(["-vn", "-map_metadata", "-1"])

            # Output format settings
            fmt_info = FORMAT_CONFIGS.get(self.config.format_key, FORMAT_CONFIGS["FLAC"])
            cmd.extend(["-c:a", fmt_info["codec"]])
            cmd.extend(build_encoder_options(self.config.format_key, self.config.bitrate_kbps))

            # Bit depth and sample format options
            if self.config.format_key == "WAV":
                if self.config.bit_depth == "16":
                    cmd.extend(["-c:a", "pcm_s16le"])
                elif self.config.bit_depth == "24":
                    cmd.extend(["-c:a", "pcm_s24le"])
                elif self.config.bit_depth == "32":
                    cmd.extend(["-c:a", "pcm_f32le"])
            elif self.config.format_key == "FLAC":
                if self.config.bit_depth == "16":
                    cmd.extend(["-sample_fmt", "s16"])
                else:
                    cmd.extend(["-sample_fmt", "s32"])

            # Pipe progress output
            cmd.extend(["-progress", "pipe:1", "-nostats"])
            cmd.append(self.config.output_path)

            self.log_line_emitted.emit(f"Running command: {' '.join(cmd)}")
            self.progress_changed.emit(15.0, f"Compiling audio track with {engine_name}...")

            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
                startupinfo=startupinfo
            )

            time_regex = re.compile(r"out_time_us=(\d+)")
            progress_regex = re.compile(r"progress=(\w+)")
            recent_logs = []
            error_diagnostic_lines = []

            while True:
                if self._is_cancelled:
                    if self.process.poll() is None:
                        self.process.terminate()
                    self.compilation_finished.emit(False, "Compilation was cancelled.")
                    return

                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        break
                    continue

                line_str = line.strip()
                if line_str:
                    self.full_log.append(line_str)
                    recent_logs.append(line_str)
                    if len(recent_logs) > 60:
                        recent_logs.pop(0)

                    # Collect lines that appear to indicate actual errors
                    if re.search(r"(error|invalid|failed|cannot|no such|unable|unknown)", line_str, re.IGNORECASE):
                        if not line_str.startswith("out_time") and not line_str.startswith("progress="):
                            error_diagnostic_lines.append(line_str)

                self.log_line_emitted.emit(line_str)

                time_match = time_regex.search(line_str)
                if time_match:
                    current_us = int(time_match.group(1))
                    current_secs = current_us / 1000000.0
                    progress_pct = min(99.0, 15.0 + (current_secs / total_duration_estimate) * 84.0)
                    mins = int(current_secs // 60)
                    secs = int(current_secs % 60)
                    self.progress_changed.emit(
                        progress_pct, 
                        f"Encoding with {engine_name}... {mins:02d}:{secs:02d} rendered ({progress_pct:.1f}%)"
                    )

                prog_match = progress_regex.search(line_str)
                if prog_match and prog_match.group(1) == "end":
                    break

            returncode = self.process.wait()
            if self._is_cancelled:
                self.compilation_finished.emit(False, "Cancelled.")
            elif returncode == 0:
                # Verify that output file actually exists and has nonzero size
                if os.path.isfile(self.config.output_path) and os.path.getsize(self.config.output_path) > 0:
                    self.progress_changed.emit(100.0, "Complete!")
                    self.compilation_finished.emit(True, f"Successfully created: {self.config.output_path}")
                else:
                    self.compilation_finished.emit(
                        False, 
                        f"Output file was created but is empty (0 bytes).\n\n"
                        f"Target path: {self.config.output_path}\n"
                        f"Check if crossfade duration is longer than the audio tracks."
                    )
            else:
                # Gather most informative error lines
                if error_diagnostic_lines:
                    err_detail = "\n".join(error_diagnostic_lines[-8:])
                else:
                    filtered = [l for l in recent_logs if not l.startswith("progress=") and not l.startswith("out_time")]
                    err_detail = "\n".join(filtered[-8:]) if filtered else f"Exit code {returncode}"

                self.compilation_finished.emit(
                    False, 
                    f"FFmpeg error (code {returncode}):\n{err_detail}\n\n"
                    f"Binary: {ffmpeg_bin}\n"
                    f"Engine: {engine_name}"
                )

        except Exception as e:
            self.compilation_finished.emit(False, f"Audio engine error: {str(e)}")
