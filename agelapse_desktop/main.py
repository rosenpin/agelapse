import sys
from PyQt5.QtWidgets import QApplication
from src.ui import MainWindow  # Import the MainWindow from the ui module

def main():
    app = showUI()
    sys.exit(app.exec_())


def showUI():
    try:    
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        return app
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
