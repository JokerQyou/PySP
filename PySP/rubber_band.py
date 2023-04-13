from PySide6.QtWidgets import QLabel, QRubberBand, QApplication
from PySide6.QtGui import QPaintEvent, QPainter, QColor, QPen, Qt, QBrush


class BorderedRubberBand(QRubberBand):
    def __init__(self, shape: QRubberBand.Shape, parent=None) -> None:
        super().__init__(shape, parent)
        # self.setAutoFillBackground(False)
        self.setWindowOpacity(0)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter()
        pen = QPen(Qt.GlobalColor.red)
        pen.setWidth(int(self.devicePixelRatioF()))
        pen.setStyle(Qt.PenStyle.SolidLine)

        brush = QBrush(Qt.GlobalColor.transparent)
        painter.begin(self)
        painter.setBrush(brush)
        painter.setPen(pen)
        painter.drawRect(event.rect())
        painter.end()
        return event.accept()
