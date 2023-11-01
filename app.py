import sys
import os
from PyQt5.QtWidgets import QDialog, QFormLayout, QLabel, QApplication, QWidget ,QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QFileDialog, QProgressBar, QDesktopWidget, QMessageBox
from PyQt5 import QtGui
import json
from scrapper import Scrapper
from PyQt5.QtCore import QCoreApplication 

basedir = os.path.dirname(__file__)
scrapper_obj = Scrapper()

try:
    from ctypes import windll  # Only exists on Windows.
    myappid = 'subreddit.downloader'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Login')
        self.setFixedSize(300, 180)
        self.center()
        font = QtGui.QFont("Segoe UI", 10)
        self.setFont(font)

        layout = QFormLayout()
        self.client_id = QLineEdit(self)
        self.client_secret = QLineEdit(self)
        self.username = QLineEdit(self)
        self.password = QLineEdit(self)
        self.login_button = QPushButton('Login', self)

        layout.addRow(QLabel('Client Id:'), self.client_id)
        layout.addRow(QLabel('Client Secret:'), self.client_secret)
        layout.addRow(QLabel('Username:'), self.username)
        layout.addRow(QLabel('Password:'), self.password)
        layout.addRow(self.login_button)

        self.login_button.clicked.connect(self.login)

        self.setLayout(layout)
        
        try:
            with open(os.path.join(basedir, 'session.json')) as f:
                creds = json.loads(f.read())

            if not creds == {}:
                self.client_id.setText(creds['client_id'])
                self.client_secret.setText(creds['client_secret'])
                self.username.setText(creds['username'])
                self.password.setText(creds['password'])
        except:
            pass
                
    
    def login(self):
        # Implement your login logic here
        scrapper_obj.login(self.client_id.text().strip(), self.client_secret.text().strip(), 
                           self.username.text().strip(), self.password.text().strip())
        if scrapper_obj.reddit:
            with open(os.path.join(basedir, 'session.json'), 'w') as f:
                f.write(
                    json.dumps({
                    'client_id':self.client_id.text().strip(),
                    'client_secret':self.client_secret.text().strip(),
                    'username':self.username.text().strip(),
                    'password':self.password.text().strip()
                    })
                    )
            
            self.accept()  # Close the login dialog if login is successful
        else:
            QMessageBox.warning(self, 'Login Failed', 'Please check your credentials.')

    def center(self):
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

class MyQtApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.folder_path = False

    def initUI(self):
        self.setWindowTitle('Subreddit Downloader')
        self.setFixedSize(450, 230)
        # Center to the screen
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

        # Create a QFont with the desired font and size
        font = QtGui.QFont("Segoe UI", 12)
        self.setFont(font)  # Set the font for the main window

        # Create a central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Create a QVBoxLayout for the central widget
        central_layout = QVBoxLayout(central_widget)

        self.input_box = QLineEdit(central_widget)
        self.input_box.setPlaceholderText("Enter subreddit name. eg- museum")
        central_layout.addWidget(self.input_box)

        self.folder_selector_btn = QPushButton('Select Download Folder', central_widget)
        self.folder_selector_btn.clicked.connect(self.openFolderDialog)
        central_layout.addWidget(self.folder_selector_btn)

        self.progress_bar = QProgressBar(central_widget)
        self.progress_bar.setRange(0, 100)
        central_layout.addWidget(self.progress_bar)
        self.progress_bar.hide()

        # Create an QHBoxLayout for buttons
        button_layout = QHBoxLayout()

        self.start_button = QPushButton('Start Download', central_widget)
        self.start_button.setStyleSheet("font-weight: bold;")
        self.start_button.clicked.connect(self.startProcess)
        button_layout.addWidget(self.start_button)

        central_layout.addLayout(button_layout)

        # Connect the signal to update the progress bar
        scrapper_obj.progress_updated.connect(self.updateProgressBar)
        scrapper_obj.finished_execution.connect(self.show_finished)


    def openFolderDialog(self):
        self.folder_path = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if os.path.exists(self.folder_path):
            self.folder_selector_btn.setText('Download folder selected ✔')
        else:
            self.showDialog(title='Error', msg='Folder path selected for download is invalid.')

    def startProcess(self):
        if scrapper_obj.isRunning():
            scrapper_obj.stop_signal = True
            # Quite app here   
            QCoreApplication.quit() 

        if self.input_box.text().strip() == '':
            self.showDialog(title='Error', msg='Subreddit name not provided.')
            return

        if not self.folder_path:
            self.showDialog(title='Error', msg='Download folder not selected.')
            return

        if self.input_box.text().strip().startswith("https://"):
            self.showDialog(title='Error', msg='Please enter subreddit name, not a link.')
            return
        elif self.input_box.text().strip().startswith("r/"):
            subreddit_name = self.input_box.text().replace('/r','').strip()
        else:
            subreddit_name = self.input_box.text().strip()

        if not scrapper_obj.check_subreddit_existance(subreddit_name):
            self.showDialog(title="Error", msg='No subreddit exists with the provided name.')
            return

        scrapper_obj.folder_path = self.folder_path
        scrapper_obj.start()

        # Make progress bar visible
        self.progress_bar.show()
        self.folder_selector_btn.setEnabled(False)
        self.input_box.setEnabled(False)
        self.start_button.setText('Cancel') 
        
    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)

    def show_finished(self):
        QMessageBox.information(self, 'Result', f'Downloaded {scrapper_obj.total_downloaded} new images.' )
        QCoreApplication.quit()

    def showDialog(self, title, msg):
        # Create a QMessageBox dialog with an "OK" button
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(msg)
        dialog.setIcon(QMessageBox.Information)
        dialog.addButton('OK', QMessageBox.AcceptRole)

        # Close the dialog when the "OK" button is pressed
        dialog.exec_()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(basedir, 'icon.ico')))
    login_dialog = LoginDialog()

    if login_dialog.exec_() == QDialog.Accepted:
        app.setWindowIcon(QtGui.QIcon(os.path.join(basedir, 'icon.ico')))
        main_window = MyQtApp()
        main_window.show()
        sys.exit(app.exec_())
