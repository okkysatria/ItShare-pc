"""
main.py - Entry point for ItShare application.
"""
import sys
import multiprocessing

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--itshare-smb-service":
        from core.smb_server import run_detached_service
        return run_detached_service(sys.argv[2])

    multiprocessing.freeze_support()

    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("ItShare")
    app.setOrganizationName("itshare")

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
