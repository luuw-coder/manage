import sys

from PySide6.QtWidgets import QApplication

from app.db import Database
from app.main_window import MainWindow
from app.paths import db_path


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Manage Moho")
    win = MainWindow(Database(db_path()))
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
