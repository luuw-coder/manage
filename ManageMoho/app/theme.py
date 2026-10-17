BG = "#1b1c20"
BAR = "#15161a"
PANEL = "#23252b"
BTN = "#2b2e35"
BTN_HOVER = "#363a43"
TEXT = "#e8e9ec"
MUTED = "#9a9da6"
ACCENT = "#3fb6a8"
GOLD = "#e0a84a"

QSS = f"""
* {{ font-family: 'Segoe UI', sans-serif; font-size: 13px; color: {TEXT}; }}
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget#toolbar, QWidget#bottom {{ background: {BAR}; }}
QWidget#toolbar {{ border-bottom: 1px solid #33353b; }}
QWidget#bottom {{ border-top: 1px solid #33353b; }}
QWidget#tabs {{ background: {BG}; }}
QScrollArea {{ border: 0; background: transparent; }}
QToolButton {{ background: {BTN}; border: 0; border-radius: 7px; padding: 5px; }}
QToolButton:hover {{ background: {BTN_HOVER}; }}
QToolButton:checked {{ background: #2f8f84; }}
QPushButton {{ background: {BTN}; border: 0; border-radius: 7px; padding: 7px 12px; }}
QPushButton:hover {{ background: {BTN_HOVER}; }}
QPushButton[tab="true"]:checked {{ background: {ACCENT}; color: #10201e; font-weight: 600; }}
QPushButton[ghost="true"] {{ background: transparent; border: 1px dashed {ACCENT}; color: {ACCENT}; }}
QPushButton[ghost="true"]:hover {{ background: #20312f; }}
QPushButton[gold="true"] {{ background: {GOLD}; color: #2a1d05; font-weight: 600; }}
QPushButton[gold="true"]:hover {{ background: #ecb95e; }}
QPushButton#uploadBox {{ background: {PANEL}; border: 2px dashed #4a4d55; border-radius: 14px;
    font-size: 15px; padding: 20px; }}
QPushButton#uploadBox:hover {{ border-color: {ACCENT}; background: #262a30; }}
QLineEdit {{ background: {BTN}; border: 1px solid #3a3c43; border-radius: 7px; padding: 5px 8px; }}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QListWidget {{ background: transparent; border: 0; outline: 0; }}
QListWidget::item {{ border-radius: 9px; padding: 4px; }}
QListWidget::item:hover {{ background: #2a2d34; }}
QListWidget::item:selected {{ background: #2f8f84; color: white; }}
QSlider::groove:horizontal {{ height: 4px; background: #3a3c43; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {TEXT}; width: 12px; margin: -5px 0; border-radius: 6px; }}
QScrollBar:horizontal {{ height: 6px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: #3a3c43; border-radius: 3px; min-width: 24px; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar::handle:vertical {{ background: #3a3c43; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QMenu {{ background: #23252b; border: 1px solid #3a3c43; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 5px; }}
QMenu::item:selected {{ background: #2f8f84; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#heading {{ font-weight: 600; font-size: 14px; }}
"""
