QSS = """
* { font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #e6ecf7; }
QWidget#root { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #0b0f19, stop:0.5 #16213a, stop:1 #2a3b60); }
QDialog { background: #151c2d; }
QWidget#toolbar { border-bottom: 1px solid rgba(255,255,255,0.07); }
QWidget#bottombar { background: rgba(8,11,18,0.55); border-top: 1px solid rgba(255,255,255,0.08); }
QFrame#info { background: rgba(8,11,18,0.45); border-top: 1px solid rgba(255,255,255,0.08); }
QFrame#fadebar { border-bottom: 1px solid rgba(255,255,255,0.07); }
QToolButton { background: transparent; border: 0; border-radius: 8px; padding: 4px; color: #9fb0cf; }
QToolButton:hover { background: rgba(255,255,255,0.10); }
QToolButton:checked { background: rgba(53,195,232,0.22); }
QToolButton#catBtn { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-radius: 9px; }
QToolButton#catBtn:hover { background: rgba(255,255,255,0.12); }
QToolButton#catBtn:checked { background: rgba(53,195,232,0.22); border: 1px solid #35c3e8; }
QPushButton { background: rgba(255,255,255,0.09); border: 0; border-radius: 7px; padding: 5px 10px; }
QPushButton:hover { background: rgba(255,255,255,0.17); }
QPushButton:disabled { color: #5d6b84; }
QPushButton#addCat { background: transparent; border: 1px dashed rgba(159,176,207,0.6); color: #9fb0cf; border-radius: 9px; padding: 0; font-size: 16px; }
QPushButton#addCat:hover { border-color: #35c3e8; color: #35c3e8; }
QPushButton#primary { background: #5fd0ee; color: #06222c; font-weight: 600; padding: 7px 16px; font-size: 13px; border-radius: 9px; }
QPushButton#primary:hover { background: #7ddcf4; }
QPushButton#gold { background: #e0a84a; color: #2a1d05; font-weight: 600; }
QPushButton#gold:hover { background: #ecb95e; }
QPushButton[page="true"] { background: transparent; padding: 2px 6px; min-width: 12px; border-radius: 7px; color: #aab8d6; }
QPushButton[page="true"]:hover { background: rgba(255,255,255,0.12); }
QPushButton[current="true"] { background: rgba(53,195,232,0.25); color: #ffffff; font-weight: 600; }
QLineEdit { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 3px 8px; }
QLineEdit:focus { border: 1px solid #35c3e8; }
QListWidget { background: transparent; border: 0; outline: 0; }
QListWidget::item { border-radius: 10px; padding: 4px; color: #e6ecf7; }
QListWidget::item:hover { background: rgba(255,255,255,0.08); }
QListWidget::item:selected { background: rgba(53,195,232,0.28); color: #ffffff; }
QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.18); border-radius: 2px; }
QSlider::sub-page:horizontal { background: #35c3e8; border-radius: 2px; }
QSlider::handle:horizontal { background: #e6ecf7; width: 12px; margin: -5px 0; border-radius: 6px; }
QScrollBar:vertical { width: 8px; background: transparent; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.22); border-radius: 4px; min-height: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QMenu { background: #1a2338; border: 1px solid #2a3350; padding: 4px; }
QMenu::item { padding: 6px 20px; border-radius: 6px; }
QMenu::item:selected { background: rgba(53,195,232,0.30); }
QMenu::item:disabled { color: #5d6b84; }
QMenu::separator { height: 1px; background: #2a3350; margin: 4px 8px; }
QCheckBox { spacing: 8px; }
QLabel#muted { color: #8fa0bf; font-size: 12px; }
QLabel#heroTitle { font-size: 15px; font-weight: 600; }
QLabel#heroDesc { color: #aab8d6; }
QLabel#toast { background: #e6ecf7; color: #10192b; padding: 7px 14px; border-radius: 14px; font-size: 12px; }
QFrame#previewPanel { background: #111a2e; border-top: 2px solid #35c3e8; border-top-left-radius: 14px; border-top-right-radius: 14px; }
QLabel#dragChip { background: rgba(224,168,74,0.18); border: 1px dashed #e0a84a; color: #e0a84a; border-radius: 8px; padding: 5px 10px; }
QLabel#dragChip:hover { background: rgba(224,168,74,0.32); }
QSplitter::handle { background: rgba(255,255,255,0.10); }
QSplitter::handle:hover { background: #35c3e8; }
QSplitter::handle:horizontal { width: 6px; }
QSplitter::handle:vertical { height: 6px; }
QPlainTextEdit, QTextEdit { background: #0f1729; border: 1px solid rgba(255,255,255,0.10); border-radius: 10px; padding: 10px; selection-background-color: #2f8f84; }
QSpinBox, QDoubleSpinBox, QComboBox { background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.14); border-radius: 7px; padding: 4px 8px; }
QComboBox QAbstractItemView { background: #1a2338; border: 1px solid #2a3350; selection-background-color: rgba(53,195,232,0.30); }
QTabWidget::pane { border: 1px solid rgba(255,255,255,0.10); border-radius: 8px; }
QTabBar::tab { background: rgba(255,255,255,0.06); padding: 7px 14px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; }
QTabBar::tab:selected { background: rgba(53,195,232,0.28); }
QTreeWidget { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.10); border-radius: 8px; outline: 0; }
QTreeWidget::item:selected { background: rgba(53,195,232,0.28); }
QScrollBar:horizontal { height: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; }
QScrollBar::handle:horizontal { background: rgba(255,255,255,0.28); border-radius: 5px; min-width: 24px; }
QCheckBox::indicator { width: 16px; height: 16px; }
"""
