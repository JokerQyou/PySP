from PySide6.QtWidgets import QLabel, QRubberBand, QApplication
from PySide6.QtGui import QPaintEvent, QPainter, QColor, QPen, Qt, QBrush
from PySide6.QtCore import QMarginsF


class BorderedRubberBand(QRubberBand):
    def __init__(self, shape: QRubberBand.Shape, parent=None) -> None:
        super().__init__(shape, parent)
        # self.setAutoFillBackground(False)
        self.setWindowOpacity(0)
        self.pen = QPen(Qt.GlobalColor.red)
        self.pen.setWidthF(self.devicePixelRatioF())
        print(self.pen.width(), self.pen.widthF())
        self.pen.setStyle(Qt.PenStyle.SolidLine)

        self.brush = QBrush(Qt.GlobalColor.transparent)

        self.margins = QMarginsF(
            self.pen.widthF(),
            self.pen.widthF(),
            self.pen.widthF(),
            self.pen.widthF(),
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        painter.drawRect(event.rect().marginsRemoved(self.margins.toMargins()))
        painter.end()
        return event.accept()
