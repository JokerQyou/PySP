from PySide6.QtWidgets import QLabel, QRubberBand, QApplication
from PySide6.QtGui import QPaintEvent, QPainter, QColor, QPen, Qt, QBrush
from PySide6.QtCore import QMarginsF


class BorderedRubberBand(QRubberBand):
    def __init__(self, shape: QRubberBand.Shape, parent=None) -> None:
        super().__init__(shape, parent)
        self.setWindowOpacity(0)

        self.pen = QPen(Qt.GlobalColor.red)
        self.pen.setWidthF(self.devicePixelRatioF())
        self.pen.setStyle(Qt.PenStyle.SolidLine)

        self.margins = None
        if self.devicePixelRatioF() == 1.0:
            self.margins = QMarginsF(
                0,
                0,
                self.pen.widthF(),
                self.pen.widthF(),
            ).toMargins()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)
        painter.setPen(self.pen)

        if self.margins is None:
            area = event.rect()
        else:
            area = event.rect().marginsRemoved(self.margins)
        painter.drawRect(area)
        painter.end()
        return event.accept()
