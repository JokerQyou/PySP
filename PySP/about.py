import PySide6.QtWidgets as QtWidgets
import PySide6.QtGui as QtGui

from theme import ThemeContainer


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, themer: ThemeContainer):
        super().__init__()
        self.themer = themer

        self.setWindowTitle("About")

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        icon = self.themer.get_icon("Capture")
        label = QtWidgets.QLabel()
        label.setPixmap(icon.pixmap(256, 256))
        layout.addWidget(label)

        text = "<center><h1>PySP</h1></center>"
        text += "<p>Version 1.0.0</p>"
        text += 'Icons by <a href="https://icons8.com/">Icons8</a>'
        label = QtWidgets.QLabel(text)
        label.setOpenExternalLinks(True)
        layout.addWidget(label)

        button = QtWidgets.QPushButton("OK")
        button.clicked.connect(self.close)
        layout.addWidget(button)
