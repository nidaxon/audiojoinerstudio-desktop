"""
Modern Themes and Stylesheets for PyQt6 AudioJoiner Studio
Fully optimized for 720p screens, high-DPI scaling, and Windows 10/11 Dark & Light modes.
"""

DARK_THEME_QSS = """
/* AudioJoiner Studio - Modern Dark Theme */
QMainWindow, QWidget#centralWidget {
    background-color: #121316;
    color: #f1f5f9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
}

QWidget {
    color: #e2e8f0;
}

/* Splitter - Eliminates unwanted white/light vertical separator line */
QSplitter {
    background-color: #121316;
}

QSplitter::handle {
    background-color: #23242c;
}

QSplitter::handle:horizontal {
    width: 3px;
    background-color: #272832;
}

QSplitter::handle:horizontal:hover {
    background-color: #6366f1;
}

QSplitter::handle:vertical {
    height: 3px;
    background-color: #272832;
}

/* Scroll Area for 720p screen adaptation */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #16171b;
    width: 8px;
    margin: 0px 0px 0px 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #333644;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #4f5263;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* Group Boxes */
QGroupBox {
    background-color: #18191f;
    border: 1px solid #292c36;
    border-radius: 8px;
    margin-top: 18px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
    font-size: 12px;
    color: #f8fafc;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 4px;
    padding: 0 6px;
    background-color: #18191f;
    color: #ffffff;
    font-weight: 700;
}

QGroupBox QLabel {
    color: #cbd5e1;
    font-size: 11px;
    font-weight: 500;
}

/* Tooltips */
QToolTip {
    background-color: #24252e;
    color: #f8fafc;
    border: 1px solid #4f46e5;
    padding: 4px 8px;
    font-size: 12px;
}

/* Dialogs & message boxes (success / error / confirmation popups) */
QDialog, QMessageBox {
    background-color: #16171b;
    color: #f1f5f9;
}

QDialog QLabel, QMessageBox QLabel {
    color: #e2e8f0;
    background: transparent;
    font-size: 12px;
}

QMessageBox QPushButton, QDialog QPushButton {
    min-width: 78px;
}

QMessageBox QTextEdit, QDialog QTextEdit {
    background-color: #0d0e12;
    color: #e2e8f0;
    border: 1px solid #2d303e;
}

/* Push Buttons */
QPushButton {
    background-color: #24252e;
    color: #f8fafc;
    border: 1px solid #383b48;
    border-radius: 6px;
    padding: 5px 12px;
    font-weight: 500;
    font-size: 12px;
    min-height: 26px;
}

QPushButton:hover {
    background-color: #31333f;
    border-color: #4f5266;
}

QPushButton:pressed {
    background-color: #1b1c23;
}

QPushButton:disabled {
    background-color: #18191f;
    color: #64748b;
    border-color: #252630;
}

/* Primary Action Button */
QPushButton#primaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
    color: #ffffff;
    font-weight: 600;
    border: 1px solid #4338ca;
    padding: 8px 16px;
    font-size: 13px;
    min-height: 32px;
}

QPushButton#primaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #4f46e5);
}

QPushButton#primaryButton:pressed {
    background: #3730a3;
}

/* Secondary / Tool buttons */
QPushButton#toolButton {
    padding: 4px 8px;
    font-size: 11px;
    min-height: 24px;
}

/* Track List */
QListWidget {
    background-color: #15161a;
    border: 1px solid #292c36;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    color: #f8fafc;
    alternate-background-color: #191a20;
}

QListWidget::item {
    background-color: #1c1d24;
    border: 1px solid #292c36;
    border-radius: 6px;
    padding: 6px 10px;
    margin-bottom: 3px;
    color: #f8fafc;
}

QListWidget::item:hover {
    background-color: #252630;
    border-color: #3d4050;
}

QListWidget::item:selected {
    background-color: #312e81;
    border-color: #6366f1;
    color: #ffffff;
}

/* Drop-down and Inputs - Guaranteed min-height to prevent vertical text cropping */
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #1c1d23;
    border: 1px solid #343746;
    border-radius: 6px;
    padding: 3px 8px;
    color: #f8fafc;
    font-size: 12px;
    min-height: 26px;
    selection-background-color: #4f46e5;
}

QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #51566c;
}

QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #6366f1;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #343746;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox::down-arrow {
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #94a3b8;
    margin-right: 2px;
}

QComboBox::down-arrow:hover {
    border-top-color: #ffffff;
}

QComboBox QAbstractItemView {
    background-color: #1c1d23;
    border: 1px solid #3b3f4f;
    selection-background-color: #4338ca;
    selection-color: #ffffff;
    color: #f8fafc;
    padding: 4px;
    min-height: 26px;
}

/* SpinBox arrows */
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #343746;
    border-bottom: 1px solid #343746;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid #343746;
}

/* Progress Bar */
QProgressBar {
    background-color: #17181e;
    border: 1px solid #292c36;
    border-radius: 6px;
    height: 16px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    font-size: 10px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #818cf8);
    border-radius: 5px;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 5px;
    background: #252632;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #6366f1;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #f8fafc;
    border: 2px solid #6366f1;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #ffffff;
    border-color: #818cf8;
}

/* Labels and Texts - Crisp high contrast */
QLabel {
    color: #e2e8f0;
}

QLabel#headerTitle {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
}

QLabel#subtitle {
    font-size: 11px;
    color: #a0aec0;
}

QStatusBar {
    background-color: #121316;
    border-top: 1px solid #23242c;
    color: #a0aec0;
    font-size: 11px;
}
"""

LIGHT_THEME_QSS = """
/* AudioJoiner Studio - Modern Light Theme */
QMainWindow, QWidget#centralWidget {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
}

QWidget {
    color: #1e293b;
}

QSplitter {
    background-color: #f8fafc;
}

QSplitter::handle {
    background-color: #e2e8f0;
}

QSplitter::handle:horizontal {
    width: 3px;
    background-color: #cbd5e1;
}

QSplitter::handle:horizontal:hover {
    background-color: #4f46e5;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 8px;
    margin: 0px 0px 0px 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 18px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
    font-size: 12px;
    color: #0f172a;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 4px;
    padding: 0 6px;
    background-color: #ffffff;
    color: #0f172a;
    font-weight: 700;
}

QGroupBox QLabel {
    color: #334155;
    font-size: 11px;
    font-weight: 500;
}

/* Tooltips */
QToolTip {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #94a3b8;
    padding: 4px 8px;
    font-size: 12px;
}

/* Dialogs & message boxes (success / error / confirmation popups) */
QDialog, QMessageBox {
    background-color: #f8fafc;
    color: #0f172a;
}

QDialog QLabel, QMessageBox QLabel {
    color: #0f172a;
    background: transparent;
    font-size: 12px;
}

QMessageBox QPushButton, QDialog QPushButton {
    min-width: 78px;
}

QPushButton {
    background-color: #f1f5f9;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px 12px;
    font-weight: 500;
    font-size: 12px;
    min-height: 26px;
}

QPushButton:hover {
    background-color: #e2e8f0;
    border-color: #94a3b8;
}

QPushButton:pressed {
    background-color: #cbd5e1;
}

QPushButton:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}

QPushButton#primaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
    color: #ffffff;
    font-weight: 600;
    border: 1px solid #4338ca;
    padding: 8px 16px;
    font-size: 13px;
    min-height: 32px;
}

QPushButton#primaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #4f46e5);
}

QPushButton#toolButton {
    padding: 4px 8px;
    font-size: 11px;
    min-height: 24px;
}

QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    color: #0f172a;
    alternate-background-color: #f8fafc;
}

QListWidget::item {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px 10px;
    margin-bottom: 3px;
    color: #0f172a;
}

QListWidget::item:hover {
    background-color: #f1f5f9;
    border-color: #cbd5e1;
}

QListWidget::item:selected {
    background-color: #e0e7ff;
    border-color: #6366f1;
    color: #312e81;
}

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 3px 8px;
    color: #0f172a;
    font-size: 12px;
    min-height: 26px;
}

QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #94a3b8;
}

QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #4f46e5;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #e2e8f0;
}

QComboBox::down-arrow {
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #64748b;
    margin-right: 2px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    selection-background-color: #e0e7ff;
    selection-color: #1e1b4b;
    color: #0f172a;
    padding: 4px;
    min-height: 26px;
}

QProgressBar {
    background-color: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    height: 16px;
    text-align: center;
    color: #0f172a;
    font-weight: 600;
    font-size: 10px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
    border-radius: 5px;
}

QSlider::groove:horizontal {
    height: 5px;
    background: #e2e8f0;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #4f46e5;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #4f46e5;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QLabel {
    color: #334155;
}

QLabel#headerTitle {
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
}

QLabel#subtitle {
    font-size: 11px;
    color: #64748b;
}

QStatusBar {
    background-color: #f8fafc;
    border-top: 1px solid #e2e8f0;
    color: #64748b;
    font-size: 11px;
}
"""
