from PySide6.QtWidgets import QGraphicsTextItem, QGraphicsSceneMouseEvent
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QFocusEvent, QFont, QInputMethodEvent, QKeyEvent

from loguru import logger


class NodeTag(QGraphicsTextItem):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setFlag(
            QGraphicsTextItem.GraphicsItemFlag.ItemAcceptsInputMethod, True
        )
        # self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.text = text
        self.setPlainText(text)
        self.setDefaultTextColor(Qt.GlobalColor.red)
        self.setFont(QFont("Fira Code", 14))
        self.setPos(0, 0)
        self.setZValue(12)

    # def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
    #     if self.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction:
    #         self.setTextInteractionFlags(
    #             Qt.TextInteractionFlag.TextEditable
    #             | Qt.TextInteractionFlag.TextEditorInteraction
    #         )
    #     self.setFocus()
    #     return super().mouseDoubleClickEvent(event)

    # def inputMethodEvent(self, event: QInputMethodEvent) -> None:
    #     event.accept()
        # return super().inputMethodEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        # self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setSelected(False)
        return super().focusOutEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        if self.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction:
            self.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditable
                | Qt.TextInteractionFlag.TextEditorInteraction
            )
        return super().focusInEvent(event)
