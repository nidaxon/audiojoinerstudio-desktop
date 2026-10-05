#!/usr/bin/env python3
"""
AudioJoiner Studio - Native Desktop Audio Compilation Workstation
Framework: PyQt6
Resampling Engine: FFmpeg + libsoxr (High-Quality 64-bit polyphase resampler)
Platforms: Windows, macOS, Linux
"""

import os
import re
import sys
import shutil
from typing import List, Optional

from PyQt6.QtCore import (
    Qt, QSize, QMimeData, QUrl, QFileInfo
)
from PyQt6.QtGui import (
    QPixmap, QIcon, QFont, QAction, QDragEnterEvent, QDropEvent, QColor, QPalette
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QSplitter, QStatusBar,
    QFrame, QMenu, QAbstractItemView, QTextEdit, QScrollArea, QDialog
)

from audio_engine import (
    AudioJoinWorker, CompilationConfig, SOXR_PRESETS,
    CROSSFADE_CURVES, FORMAT_CONFIGS,
    probe_track, find_binary, check_soxr_support
)
from playlist_parser import (
    PlaylistParser, AudioTrackInfo, SUPPORTED_AUDIO_EXTENSIONS,
    PLAYLIST_EXTENSIONS
)
from styles import DARK_THEME_QSS, LIGHT_THEME_QSS


APP_NAME = "AudioJoiner Studio"
APP_VERSION = "1.0.0"
LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.html"


def resource_path(*parts: str) -> str:
    """Resolve a bundled resource path (works from source and inside a PyInstaller build)."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def make_logo_label(size: int, parent=None) -> QLabel:
    """QLabel showing assets/logo.png scaled smoothly (HiDPI-aware) to fit size x size."""
    lbl = QLabel(parent)
    lbl.setFixedSize(size, size)
    lbl.setStyleSheet("background: transparent;")
    pm = QPixmap(resource_path("assets", "logo.png"))
    if not pm.isNull():
        screen = QApplication.primaryScreen()
        dpr = screen.devicePixelRatio() if screen else 1.0
        scaled = pm.scaled(
            int(size * dpr), int(size * dpr),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        scaled.setDevicePixelRatio(dpr)
        lbl.setPixmap(scaled)
    return lbl


class DragDropTrackList(QListWidget):
    """QListWidget supporting internal drag-and-drop reordering and external file dropping."""
    
    def __init__(self, parent=None, on_files_dropped=None):
        super().__init__(parent)
        self.on_files_dropped = on_files_dropped
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                local_path = url.toLocalFile()
                if local_path and os.path.exists(local_path):
                    file_paths.append(local_path)

            if file_paths and self.on_files_dropped:
                self.on_files_dropped(file_paths)
                event.acceptProposedAction()
        else:
            # Internal re-ordering
            super().dropEvent(event)


class AudioJoinerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioJoiner Studio — Soxr Hi-Fi Compilation")
        self.resize(980, 580)
        self.setMinimumSize(740, 440)
        
        self.is_dark_mode = True
        self.tracks: List[AudioTrackInfo] = []
        self.worker: Optional[AudioJoinWorker] = None
        
        self.init_ui()
        self.apply_theme()
        self.check_ffmpeg_environment()

    def check_ffmpeg_environment(self):
        """Verify FFmpeg and Soxr availability and inform the user."""
        ffmpeg_path = find_binary("ffmpeg")
        if not ffmpeg_path or ffmpeg_path == "ffmpeg" or (not os.path.isfile(ffmpeg_path) and not shutil.which(ffmpeg_path)):
            if hasattr(self, 'engine_btn'):
                self.engine_btn.setText("⚠ Locate FFmpeg")
            self.statusBar().showMessage(
                "Notice: FFmpeg not detected in PATH. Click 'Locate FFmpeg' or place ffmpeg.exe next to app.", 
                10000
            )
        else:
            has_soxr = check_soxr_support(ffmpeg_path)
            tag = "libsoxr 64-bit" if has_soxr else "SWR Hi-Fi"
            if hasattr(self, 'engine_btn'):
                self.engine_btn.setText(f"⚙ Engine: {tag}")
            self.statusBar().showMessage(f"Engine Ready: {ffmpeg_path} ({tag})", 4000)

    def show_engine_dialog(self):
        import audio_engine
        dlg = QDialog(self)
        dlg.setWindowTitle("FFmpeg & Soxr Engine Settings")
        dlg.resize(520, 300)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        
        ffmpeg_path = audio_engine.find_binary("ffmpeg")
        ffprobe_path = audio_engine.find_binary("ffprobe")
        has_soxr = audio_engine.check_soxr_support(ffmpeg_path) if (ffmpeg_path and (os.path.isfile(ffmpeg_path) or shutil.which(ffmpeg_path))) else False
        
        info_label = QLabel(
            f"<b>FFmpeg Binary:</b><br>{ffmpeg_path or 'Not Found'}<br><br>"
            f"<b>FFprobe Binary:</b><br>{ffprobe_path or 'Not Found'}<br><br>"
            f"<b>libsoxr Resampler Status:</b><br>"
            f"{'✓ Enabled (libsoxr 64-bit polyphase active)' if has_soxr else '⚠ Not compiled into this build (Falling back to high-quality SWR resampler)'}"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"font-size: 12px; color: {'#f8fafc' if self.is_dark_mode else '#0f172a'};")
        layout.addWidget(info_label)
        
        btn_browse = QPushButton("📁 Select Custom ffmpeg.exe...")
        def browse_ffmpeg():
            filt = "Executable (*.exe);;All Files (*)" if sys.platform == 'win32' else "All Files (*)"
            fp, _ = QFileDialog.getOpenFileName(dlg, "Select ffmpeg binary", "", filt)
            if fp and os.path.isfile(fp):
                audio_engine.CUSTOM_FFMPEG_PATH = fp
                probe_cand = os.path.join(os.path.dirname(fp), "ffprobe.exe" if sys.platform == 'win32' else "ffprobe")
                if os.path.isfile(probe_cand):
                    audio_engine.CUSTOM_FFPROBE_PATH = probe_cand
                self.check_ffmpeg_environment()
                dlg.accept()
                QMessageBox.information(self, "FFmpeg Updated", f"Active FFmpeg set to:\n{fp}")
        btn_browse.clicked.connect(browse_ffmpeg)
        layout.addWidget(btn_browse)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)
        dlg.exec()

    def show_about_dialog(self):
        link = "#818cf8" if self.is_dark_mode else "#4f46e5"
        muted = "#94a3b8" if self.is_dark_mode else "#64748b"
        dlg = QDialog(self)
        dlg.setWindowTitle(f"About {APP_NAME}")
        dlg.setMinimumWidth(500)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(10)

        # Logo + name (inline)
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_row.addStretch()
        title_row.addWidget(make_logo_label(36, dlg), 0, Qt.AlignmentFlag.AlignVCenter)
        name_lbl = QLabel(f"<span style='font-size:22px; font-weight:700;'>{APP_NAME}</span>")
        name_lbl.setTextFormat(Qt.TextFormat.RichText)
        title_row.addWidget(name_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch()
        layout.addLayout(title_row)

        html = f"""
        <style>a {{ color: {link}; text-decoration: none; }}</style>
        <div style="text-align:center;">
          <p style="color:{muted}; margin:0;">v{APP_VERSION}</p>
          <p style="margin:8px 0 0 0;">by <a href="https://github.com/nidaxon">Ixnando Ondang</a></p>
        </div>
        <hr>
        <p style="margin:0 0 4px 0;"><b>Acknowledgements</b></p>
        <p style="margin:0 0 4px 0;">
          <a href="https://ffmpeg.org">FFmpeg</a> &mdash; audio decoding, filtering and encoding.
        </p>
        <p style="margin:0;">
          <a href="https://sourceforge.net/projects/soxr/">libsoxr</a> &mdash; the SoX Resampler library
          for high-quality sample rate conversion.
        </p>
        <hr>
        <p style="text-align:center; margin:0;">
          Licensed under the <a href="{LICENSE_URL}">GNU General Public License v3.0</a>
        </p>
        <hr>
        <p style="text-align:center; margin:0;">
          Powered by <a href="https://www.python.org">Python</a> +
          <a href="https://www.riverbankcomputing.com/software/pyqt/">PyQt6</a>
          | Created Using <a href="https://aistudio.google.com">Google AI Studio</a>
          and <a href="https://claude.ai">Claude</a>
        </p>
        """
        lbl = QLabel(html)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        lbl.setOpenExternalLinks(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(lbl)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)
        dlg.exec()

    def init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # ----------------- Top Header Bar -----------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        header_title = QLabel("AudioJoiner Studio", self)
        header_title.setObjectName("headerTitle")
        
        subtitle = QLabel("Native Multi-Track Crossfade & Soxr Polyphase Resampling Suite", self)
        subtitle.setObjectName("subtitle")
        title_box.addWidget(header_title)
        title_box.addWidget(subtitle)
        header_layout.addWidget(make_logo_label(32, self), 0, Qt.AlignmentFlag.AlignVCenter)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Engine settings button
        self.engine_btn = QPushButton("⚙ FFmpeg Engine", self)
        self.engine_btn.setObjectName("toolButton")
        self.engine_btn.setToolTip("Check or configure FFmpeg binary and libsoxr engine")
        self.engine_btn.clicked.connect(self.show_engine_dialog)
        header_layout.addWidget(self.engine_btn)

        # About button
        self.about_btn = QPushButton("ℹ About", self)
        self.about_btn.setObjectName("toolButton")
        self.about_btn.setToolTip("About AudioJoiner Studio")
        self.about_btn.clicked.connect(self.show_about_dialog)
        header_layout.addWidget(self.about_btn)

        # Theme toggle button
        self.theme_btn = QPushButton("🌙 Dark Mode", self)
        self.theme_btn.setObjectName("toolButton")
        self.theme_btn.setToolTip("Toggle Dark / Light Theme")
        self.theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_btn)

        main_layout.addLayout(header_layout)

        # ----------------- Main Splitter -----------------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)

        # === Left Panel: Track Management & File Queue ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        # Action Buttons Toolbar
        btn_toolbar = QHBoxLayout()
        btn_toolbar.setSpacing(6)

        self.btn_add_files = QPushButton("➕ Add Files", self)
        self.btn_add_files.setToolTip("Add individual audio files (.mp3, .flac, .wav, .aac, .ogg, etc.)")
        self.btn_add_files.clicked.connect(self.add_individual_files)

        self.btn_add_dir = QPushButton("📁 Add Folder", self)
        self.btn_add_dir.setToolTip("Add all audio files from a directory")
        self.btn_add_dir.clicked.connect(self.add_directory)

        self.btn_add_pls = QPushButton("📑 Add Playlist", self)
        self.btn_add_pls.setToolTip("Import playlist (.m3u, .m3u8, .pls)")
        self.btn_add_pls.clicked.connect(self.add_playlist)

        self.btn_clear = QPushButton("🗑 Clear", self)
        self.btn_clear.setObjectName("toolButton")
        self.btn_clear.setToolTip("Clear all tracks from the queue")
        self.btn_clear.clicked.connect(self.clear_all_tracks)

        btn_toolbar.addWidget(self.btn_add_files)
        btn_toolbar.addWidget(self.btn_add_dir)
        btn_toolbar.addWidget(self.btn_add_pls)
        btn_toolbar.addStretch()
        btn_toolbar.addWidget(self.btn_clear)
        left_layout.addLayout(btn_toolbar)

        # Track List Box with Drag & Drop Reordering
        self.track_list = DragDropTrackList(self, on_files_dropped=self.handle_dropped_files)
        self.track_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.track_list.customContextMenuRequested.connect(self.show_track_context_menu)
        left_layout.addWidget(self.track_list)

        # List Re-ordering and Navigation controls
        reorder_bar = QHBoxLayout()
        reorder_bar.setSpacing(6)

        self.btn_move_up = QPushButton("▲ Move Up", self)
        self.btn_move_up.setObjectName("toolButton")
        self.btn_move_up.clicked.connect(self.move_track_up)

        self.btn_move_down = QPushButton("▼ Move Down", self)
        self.btn_move_down.setObjectName("toolButton")
        self.btn_move_down.clicked.connect(self.move_track_down)

        self.btn_remove = QPushButton("✖ Remove", self)
        self.btn_remove.setObjectName("toolButton")
        self.btn_remove.clicked.connect(self.remove_selected_tracks)

        self.lbl_track_count = QLabel("0 tracks (00:00 total)", self)
        self.lbl_track_count.setObjectName("subtitle")

        reorder_bar.addWidget(self.btn_move_up)
        reorder_bar.addWidget(self.btn_move_down)
        reorder_bar.addWidget(self.btn_remove)
        reorder_bar.addStretch()
        reorder_bar.addWidget(self.lbl_track_count)
        left_layout.addLayout(reorder_bar)

        splitter.addWidget(left_widget)

        # === Right Panel: Wrapped in QScrollArea for 720p Screen Support ===
        right_scroll = QScrollArea(self)
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(2, 0, 6, 0)
        right_layout.setSpacing(8)

        # --- Group 1: Output Codec Setting ---
        output_group = QGroupBox("1. Output Codec Setting", self)
        output_layout = QGridLayout(output_group)
        output_layout.setSpacing(6)

        # Default start location for the Save As dialog
        music_dir = os.path.expanduser("~/Music")
        self.selected_output_dir = music_dir if os.path.isdir(music_dir) else os.path.expanduser("~")

        # Format & Bitrate
        output_layout.addWidget(QLabel("Format:"), 0, 0)
        self.combo_format = QComboBox(self)
        self.combo_format.setMinimumHeight(28)
        for fmt in FORMAT_CONFIGS.keys():
            self.combo_format.addItem(fmt)
        self.combo_format.setCurrentText("FLAC")
        self.combo_format.currentTextChanged.connect(self.on_format_changed)
        output_layout.addWidget(self.combo_format, 0, 1)

        self.combo_quality = QComboBox(self)
        self.combo_quality.setMinimumHeight(28)
        output_layout.addWidget(self.combo_quality, 0, 2)

        # Sample rate (applies whether or not libsoxr is used)
        output_layout.addWidget(QLabel("Sample Rate:"), 1, 0)
        self.combo_sample_rate = QComboBox(self)
        self.combo_sample_rate.setMinimumHeight(28)
        self.combo_sample_rate.addItems(["48000 Hz (Standard Hi-Fi)", "44100 Hz (CD Audio)", "96000 Hz (Studio Hi-Res)", "192000 Hz (Master)"])
        self.combo_sample_rate.setCurrentIndex(0)
        output_layout.addWidget(self.combo_sample_rate, 1, 1, 1, 2)
        self.on_format_changed(self.combo_format.currentText())

        right_layout.addWidget(output_group)

        # --- Group 2: Resampler Preset ---
        soxr_group = QGroupBox("2. Resampler", self)
        soxr_layout = QGridLayout(soxr_group)
        soxr_layout.setSpacing(6)

        soxr_layout.addWidget(QLabel("Soxr Preset:"), 0, 0)
        self.combo_soxr_preset = QComboBox(self)
        self.combo_soxr_preset.setMinimumHeight(28)
        for key, val in SOXR_PRESETS.items():
            self.combo_soxr_preset.addItem(val["name"], key)
        self.combo_soxr_preset.setCurrentIndex(0)  # No Resample
        soxr_layout.addWidget(self.combo_soxr_preset, 0, 1, 1, 2)

        right_layout.addWidget(soxr_group)

        # --- Group 3: Transitions & Track Fades ---
        trans_group = QGroupBox("3. Track Transitions, Silence && Fades", self)
        trans_layout = QGridLayout(trans_group)
        trans_layout.setSpacing(6)

        trans_layout.addWidget(QLabel("Transition:"), 0, 0)
        self.combo_trans_mode = QComboBox(self)
        self.combo_trans_mode.setMinimumHeight(28)
        self.combo_trans_mode.addItems([
            "Crossfade Between Tracks",
            "Custom Silence Gap Between Tracks",
            "Seamless Gapless Cut (Direct)"
        ])
        self.combo_trans_mode.currentIndexChanged.connect(self.on_trans_mode_changed)
        trans_layout.addWidget(self.combo_trans_mode, 0, 1, 1, 2)

        # Crossfade duration
        self.lbl_xfade_dur = QLabel("Crossfade Duration:")
        self.spin_xfade_dur = QDoubleSpinBox(self)
        self.spin_xfade_dur.setMinimumHeight(28)
        self.spin_xfade_dur.setRange(0.2, 30.0)
        self.spin_xfade_dur.setSingleStep(0.5)
        self.spin_xfade_dur.setValue(3.0)
        self.spin_xfade_dur.setSuffix(" s")
        trans_layout.addWidget(self.lbl_xfade_dur, 1, 0)
        trans_layout.addWidget(self.spin_xfade_dur, 1, 1)

        # Crossfade curve
        self.combo_xfade_curve = QComboBox(self)
        self.combo_xfade_curve.setMinimumHeight(28)
        for code, label in CROSSFADE_CURVES:
            self.combo_xfade_curve.addItem(label, code)
        trans_layout.addWidget(self.combo_xfade_curve, 1, 2)

        # Silence gap
        self.lbl_silence = QLabel("Silence Gap:")
        self.spin_silence = QDoubleSpinBox(self)
        self.spin_silence.setMinimumHeight(28)
        self.spin_silence.setRange(0.1, 60.0)
        self.spin_silence.setSingleStep(0.5)
        self.spin_silence.setValue(2.0)
        self.spin_silence.setSuffix(" s")
        trans_layout.addWidget(self.lbl_silence, 2, 0)
        trans_layout.addWidget(self.spin_silence, 2, 1, 1, 2)

        # Fade in & Fade out
        trans_layout.addWidget(QLabel("Start Fade-In:"), 3, 0)
        self.spin_fade_in = QDoubleSpinBox(self)
        self.spin_fade_in.setMinimumHeight(28)
        self.spin_fade_in.setRange(0.0, 15.0)
        self.spin_fade_in.setValue(1.0)
        self.spin_fade_in.setSuffix(" s")
        trans_layout.addWidget(self.spin_fade_in, 3, 1)

        trans_layout.addWidget(QLabel("End Fade-Out:"), 4, 0)
        self.spin_fade_out = QDoubleSpinBox(self)
        self.spin_fade_out.setMinimumHeight(28)
        self.spin_fade_out.setRange(0.0, 20.0)
        self.spin_fade_out.setValue(2.5)
        self.spin_fade_out.setSuffix(" s")
        trans_layout.addWidget(self.spin_fade_out, 4, 1)

        self.combo_trans_mode.setCurrentIndex(2)  # Seamless Gapless Cut (Direct) by default
        self.on_trans_mode_changed(self.combo_trans_mode.currentIndex())
        right_layout.addWidget(trans_group)

        right_layout.addStretch()

        right_scroll.setWidget(right_widget)

        # Right column = scrollable settings + fixed action buttons below
        right_container = QWidget(self)
        right_container_layout = QVBoxLayout(right_container)
        right_container_layout.setContentsMargins(8, 0, 0, 0)
        right_container_layout.setSpacing(8)
        right_container_layout.addWidget(right_scroll, 1)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        action_layout.setContentsMargins(2, 0, 6, 0)

        self.btn_start = QPushButton("⚡ Join Tracks", self)
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.setMinimumHeight(34)
        self.btn_start.clicked.connect(self.start_compilation)

        self.btn_cancel = QPushButton("⛔ Cancel", self)
        self.btn_cancel.setMinimumHeight(34)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_compilation)

        action_layout.addWidget(self.btn_start, 2)
        action_layout.addWidget(self.btn_cancel, 1)
        right_container_layout.addLayout(action_layout)

        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        main_layout.addWidget(splitter, 1)

        # ----------------- Bottom Progress & Status Bar -----------------
        bottom_frame = QFrame(self)
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.setSpacing(4)

        prog_layout = QHBoxLayout()
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.lbl_status = QLabel("Ready. Drag audio files or playlists to begin.", self)
        self.lbl_status.setObjectName("subtitle")

        prog_layout.addWidget(self.progress_bar, 1)
        bottom_layout.addLayout(prog_layout)
        bottom_layout.addWidget(self.lbl_status)

        main_layout.addWidget(bottom_frame)

        self.setStatusBar(QStatusBar(self))

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def apply_theme(self):
        app = QApplication.instance()
        if self.is_dark_mode:
            self.setStyleSheet(DARK_THEME_QSS)
            self.theme_btn.setText("☀ Light Mode")
            if app:
                pal = QPalette()
                pal.setColor(QPalette.ColorRole.Window, QColor("#121316"))
                pal.setColor(QPalette.ColorRole.WindowText, QColor("#f1f5f9"))
                pal.setColor(QPalette.ColorRole.Base, QColor("#16171b"))
                pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#1c1d23"))
                pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1c1d23"))
                pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#f8fafc"))
                pal.setColor(QPalette.ColorRole.Text, QColor("#f8fafc"))
                pal.setColor(QPalette.ColorRole.Button, QColor("#24252e"))
                pal.setColor(QPalette.ColorRole.ButtonText, QColor("#f8fafc"))
                pal.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
                pal.setColor(QPalette.ColorRole.Highlight, QColor("#4f46e5"))
                pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
                app.setPalette(pal)
        else:
            self.setStyleSheet(LIGHT_THEME_QSS)
            self.theme_btn.setText("🌙 Dark Mode")
            if app:
                pal = QPalette()
                pal.setColor(QPalette.ColorRole.Window, QColor("#f8fafc"))
                pal.setColor(QPalette.ColorRole.WindowText, QColor("#0f172a"))
                pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
                pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f1f5f9"))
                pal.setColor(QPalette.ColorRole.Text, QColor("#0f172a"))
                pal.setColor(QPalette.ColorRole.Button, QColor("#f1f5f9"))
                pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1e293b"))
                pal.setColor(QPalette.ColorRole.Highlight, QColor("#4f46e5"))
                pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
                app.setPalette(pal)

    def on_format_changed(self, text: str):
        self.combo_quality.clear()
        if FORMAT_CONFIGS[text]["lossless"]:
            if text == "ALAC":
                self.combo_quality.addItems(["24-bit Lossless", "16-bit Lossless"])
            else:
                self.combo_quality.addItems(["24-bit Lossless", "16-bit Lossless", "32-bit Float"])
        else:
            self.combo_quality.addItems(["320 kbps", "256 kbps", "192 kbps", "160 kbps", "128 kbps", "96 kbps"])

    def on_trans_mode_changed(self, index: int):
        # 0 = Crossfade, 1 = Silence, 2 = Seamless
        is_xfade = (index == 0)
        is_silence = (index == 1)

        self.lbl_xfade_dur.setVisible(is_xfade)
        self.spin_xfade_dur.setVisible(is_xfade)
        self.combo_xfade_curve.setVisible(is_xfade)

        self.lbl_silence.setVisible(is_silence)
        self.spin_silence.setVisible(is_silence)

    # ----------------- File Queue Management -----------------
    def add_individual_files(self):
        ext_filter = "Audio Files (*.mp3 *.flac *.wav *.aac *.m4a *.ogg *.opus *.aiff *.alac);;All Files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Add Audio Files", "", ext_filter)
        if files:
            self.append_tracks_from_paths(files)

    def add_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Add Audio Directory", "")
        if dir_path:
            tracks = PlaylistParser.scan_directory(dir_path, recursive=True)
            self.append_track_objects(tracks)

    def add_playlist(self):
        ext_filter = "Playlist Files (*.m3u *.m3u8 *.pls);;All Files (*)"
        pls_path, _ = QFileDialog.getOpenFileName(self, "Open Playlist", "", ext_filter)
        if pls_path:
            tracks = PlaylistParser.parse_path(pls_path)
            if tracks:
                self.append_track_objects(tracks)
            else:
                QMessageBox.warning(
                    self, "Empty or Unsupported Playlist", 
                    "Could not extract valid audio tracks from the playlist file."
                )

    def handle_dropped_files(self, paths: List[str]):
        self.append_tracks_from_paths(paths)

    def append_tracks_from_paths(self, paths: List[str]):
        new_tracks = []
        for p in paths:
            new_tracks.extend(PlaylistParser.parse_path(p))
        self.append_track_objects(new_tracks)

    def append_track_objects(self, tracks: List[AudioTrackInfo]):
        for t in tracks:
            # Probe metadata if duration is unknown
            if t.duration <= 0:
                meta = probe_track(t.filepath)
                t.duration = meta.get("duration", 0.0)
                t.sample_rate = meta.get("sample_rate")
                t.channels = meta.get("channels")
            
            self.tracks.append(t)
            item = QListWidgetItem(self.format_track_label(t, len(self.tracks)))
            item.setData(Qt.ItemDataRole.UserRole, t.filepath)
            self.track_list.addItem(item)

        self.update_track_summary()

    def format_track_label(self, track: AudioTrackInfo, index: int) -> str:
        dur = track.formatted_duration()
        fmt = track.format
        return f"{index:02d}. {track.title}   [{fmt} · {dur} · {track.formatted_size()}]"

    def refresh_track_indices(self):
        for i in range(self.track_list.count()):
            item = self.track_list.item(i)
            fp = item.data(Qt.ItemDataRole.UserRole)
            # Find matching track info
            track = next((t for t in self.tracks if t.filepath == fp), None)
            if track:
                item.setText(self.format_track_label(track, i + 1))
        self.update_track_summary()

    def update_track_summary(self):
        count = self.track_list.count()
        total_sec = 0.0
        # Re-sync self.tracks order with QListWidget order
        reordered_tracks = []
        for i in range(count):
            item = self.track_list.item(i)
            fp = item.data(Qt.ItemDataRole.UserRole)
            match = next((t for t in self.tracks if t.filepath == fp), None)
            if match:
                reordered_tracks.append(match)
                total_sec += match.duration

        self.tracks = reordered_tracks
        mins = int(total_sec // 60)
        secs = int(total_sec % 60)
        self.lbl_track_count.setText(f"{count} tracks ({mins:02d}:{secs:02d} total)")
        self.btn_start.setEnabled(count > 0)

    def move_track_up(self):
        row = self.track_list.currentRow()
        if row > 0:
            item = self.track_list.takeItem(row)
            self.track_list.insertItem(row - 1, item)
            self.track_list.setCurrentRow(row - 1)
            self.refresh_track_indices()

    def move_track_down(self):
        row = self.track_list.currentRow()
        if 0 <= row < self.track_list.count() - 1:
            item = self.track_list.takeItem(row)
            self.track_list.insertItem(row + 1, item)
            self.track_list.setCurrentRow(row + 1)
            self.refresh_track_indices()

    def remove_selected_tracks(self):
        selected_items = self.track_list.selectedItems()
        if not selected_items:
            return
        for it in selected_items:
            row = self.track_list.row(it)
            self.track_list.takeItem(row)
        self.refresh_track_indices()

    def clear_all_tracks(self):
        self.track_list.clear()
        self.tracks.clear()
        self.update_track_summary()

    def show_track_context_menu(self, pos):
        item = self.track_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        act_up = menu.addAction("Move Up")
        act_down = menu.addAction("Move Down")
        menu.addSeparator()
        act_del = menu.addAction("Remove Track")
        act_folder = menu.addAction("Open Containing Folder")

        chosen = menu.exec(self.track_list.mapToGlobal(pos))
        if chosen == act_up:
            self.move_track_up()
        elif chosen == act_down:
            self.move_track_down()
        elif chosen == act_del:
            self.remove_selected_tracks()
        elif chosen == act_folder:
            fp = item.data(Qt.ItemDataRole.UserRole)
            if fp and os.path.exists(fp):
                folder = os.path.dirname(fp)
                if sys.platform == 'win32':
                    os.startfile(folder)
                elif sys.platform == 'darwin':
                    import subprocess
                    subprocess.Popen(['open', folder])
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', folder])

    # ----------------- Compilation Process -----------------
    def start_compilation(self):
        if self.track_list.count() == 0:
            QMessageBox.warning(self, "No Tracks", "Please add at least one audio track to join.")
            return

        fmt_key = self.combo_format.currentText()
        ext = FORMAT_CONFIGS[fmt_key]["ext"]

        # Collect track filepaths in order
        track_paths = []
        for i in range(self.track_list.count()):
            item = self.track_list.item(i)
            track_paths.append(item.data(Qt.ItemDataRole.UserRole))

        # Native "Save As" dialog (Windows / macOS / Linux) to pick folder + filename
        default_path = os.path.join(self.selected_output_dir, "Compilation_Track" + ext)
        output_full_path, _ = QFileDialog.getSaveFileName(
            self, "Save Joined Audio As", default_path,
            f"{fmt_key} Audio (*{ext})"
        )
        if not output_full_path:
            return  # user cancelled

        # Native dialogs may not append the extension automatically
        if not output_full_path.lower().endswith(ext):
            output_full_path += ext
            if os.path.exists(output_full_path):
                resp = QMessageBox.question(
                    self, "File Exists",
                    f"'{os.path.basename(output_full_path)}' already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if resp != QMessageBox.StandardButton.Yes:
                    return

        # Never overwrite one of the source tracks
        out_norm = os.path.normcase(os.path.abspath(output_full_path))
        if any(os.path.normcase(os.path.abspath(tp)) == out_norm for tp in track_paths):
            QMessageBox.warning(
                self, "Invalid Output File",
                "The output file is one of the tracks being joined. Please choose a different name."
            )
            return

        # Remember the folder for next time
        self.selected_output_dir = os.path.dirname(output_full_path) or self.selected_output_dir

        # Prepare configuration
        config = CompilationConfig()
        config.output_path = output_full_path
        config.format_key = fmt_key
        config.soxr_preset = self.combo_soxr_preset.currentData()
        config.use_soxr = config.soxr_preset != "none"

        # Sample rate
        sr_text = self.combo_sample_rate.currentText()
        if "48000" in sr_text:
            config.sample_rate = 48000
        elif "44100" in sr_text:
            config.sample_rate = 44100
        elif "96000" in sr_text:
            config.sample_rate = 96000
        elif "192000" in sr_text:
            config.sample_rate = 192000

        # Quality / bit depth / bitrate
        qual_text = self.combo_quality.currentText()
        if FORMAT_CONFIGS[fmt_key]["lossless"]:
            if "24-bit" in qual_text:
                config.bit_depth = "24"
            elif "16-bit" in qual_text:
                config.bit_depth = "16"
            elif "32-bit" in qual_text:
                config.bit_depth = "32"
        else:
            m = re.search(r"(\d+)\s*kbps", qual_text)
            if m:
                config.bitrate_kbps = int(m.group(1))

        # Transitions
        trans_idx = self.combo_trans_mode.currentIndex()
        if trans_idx == 0:
            config.transition_mode = "crossfade"
            config.crossfade_duration = self.spin_xfade_dur.value()
            config.crossfade_curve1 = self.combo_xfade_curve.currentData()
            config.crossfade_curve2 = self.combo_xfade_curve.currentData()
        elif trans_idx == 1:
            config.transition_mode = "silence"
            config.silence_gap = self.spin_silence.value()
        else:
            config.transition_mode = "direct"

        config.start_fade_in = self.spin_fade_in.value()
        config.end_fade_out = self.spin_fade_out.value()

        # UI state updates
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Initializing FFmpeg worker...")

        # Start background worker
        self.worker = AudioJoinWorker(track_paths, config)
        self.worker.progress_changed.connect(self.on_worker_progress)
        self.worker.compilation_finished.connect(self.on_worker_finished)
        self.worker.start()

    def cancel_compilation(self):
        if self.worker:
            self.lbl_status.setText("Cancelling compilation...")
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)

    def on_worker_progress(self, percent: float, status_msg: str):
        self.progress_bar.setValue(int(percent))
        self.lbl_status.setText(status_msg)

    def on_worker_finished(self, success: bool, msg: str):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        
        if success:
            self.progress_bar.setValue(100)
            self.lbl_status.setText("Compilation finished successfully.")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Compilation Succeeded")
            msg_box.setText("<b>Track joined successfully.</b>")
            msg_box.setInformativeText(str(msg).replace("Successfully created: ", ""))
            btn_open = msg_box.addButton("Open Destination Folder", QMessageBox.ButtonRole.ActionRole)
            btn_open.setMinimumWidth(190)
            msg_box.addButton(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            if msg_box.clickedButton() == btn_open and self.worker:
                out_path = self.worker.config.output_path
                folder = os.path.dirname(out_path)
                if sys.platform == 'win32':
                    os.startfile(folder)
                elif sys.platform == 'darwin':
                    import subprocess
                    subprocess.Popen(['open', folder])
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', folder])
        else:
            self.lbl_status.setText("Status: " + str(msg)[:60] + "...")
            self.show_error_dialog("Compilation Failed", msg)

    def show_error_dialog(self, title: str, error_msg: str):
        dlg = QDialog(self)
        dlg.setWindowTitle("Audio Join Error")
        dlg.resize(660, 440)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)

        title_lbl = QLabel(f"<b>{title}</b>")
        title_lbl.setStyleSheet("font-size: 15px; color: #ef4444;")
        dark = self.is_dark_mode
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            "<b>Troubleshooting & Tips:</b><br>"
            "• <b>Crossfade Duration:</b> If audio tracks are shorter than crossfade duration, reduce crossfade (e.g. 1.0s) or choose 'Seamless Gapless Cut (Direct)'.<br>"
            "• <b>File In Use / Permission:</b> Check if the output destination folder exists and the target file isn't currently open in a music player.<br>"
            "• <b>FFmpeg Binary:</b> Click 'Locate FFmpeg' below to ensure your local FFmpeg build is valid and supports libsoxr."
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {'#cbd5e1' if dark else '#334155'}; font-size: 11px;")
        layout.addWidget(desc_lbl)

        layout.addWidget(QLabel("<b>FFmpeg Diagnostic Output:</b>"))
        log_edit = QTextEdit()
        log_edit.setReadOnly(True)
        full_text = error_msg
        if self.worker and getattr(self.worker, 'full_log', None):
            full_text += "\n\n--- Full FFmpeg Engine Log ---\n" + "\n".join(self.worker.full_log)
        log_edit.setPlainText(full_text)
        if dark:
            log_edit.setStyleSheet(
                "background-color: #0d0e12; color: #fca5a5; font-family: Consolas, monospace; font-size: 11px; border: 1px solid #2d303e;"
            )
        else:
            log_edit.setStyleSheet(
                "background-color: #fef2f2; color: #991b1b; font-family: Consolas, monospace; font-size: 11px; border: 1px solid #fecaca;"
            )
        layout.addWidget(log_edit)

        btn_row = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy Error Log")
        def copy_log():
            cb = QApplication.clipboard()
            if cb:
                cb.setText(full_text)
            btn_copy.setText("✓ Log Copied!")
        btn_copy.clicked.connect(copy_log)
        btn_row.addWidget(btn_copy)

        btn_engine = QPushButton("⚙ Configure FFmpeg...")
        btn_engine.clicked.connect(lambda: (dlg.reject(), self.show_engine_dialog()))
        btn_row.addWidget(btn_engine)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)
        dlg.exec()


def main():
    # Enable high-DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    # Windows: own taskbar identity so the app icon shows instead of python.exe's
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Ixnando.AudioJoinerStudio.1")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("AudioJoiner Studio")
    app.setOrganizationName("AudioJoiner")

    # Application icon: window title bar, taskbar, dock, Alt-Tab (all dialogs inherit it)
    icon = QIcon(resource_path("assets", "icon.ico"))
    if icon.isNull():
        icon = QIcon(resource_path("assets", "icon.png"))
    app.setWindowIcon(icon)

    window = AudioJoinerMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
