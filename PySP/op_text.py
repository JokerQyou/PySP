from enum import Enum
from typing import Optional

from PySide6.QtWidgets import QGraphicsTextItem, QGraphicsSceneMouseEvent, QStyleOptionGraphicsItem, QWidget, QStyleOption, QGraphicsScale, QGraphicsItem
from PySide6.QtCore import Qt, QEvent, QPoint, QRect, QRectF, QPointF
from PySide6.QtGui import QFocusEvent, QFont, QInputMethodEvent, QKeyEvent, QPainter, QPen, QColor, QCursor

from loguru import logger


class ResizeDir(Enum):
    TopLeft = 1
    TopRight = 2
    BottomLeft = 3
    BottomRight = 4


class NodeTag(QGraphicsTextItem):
    handle_size = 4

    def __init__(self, text, parent: Optional[QGraphicsItem] = None):
        super().__init__(text, parent)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setFlag(
            QGraphicsTextItem.GraphicsItemFlag.ItemAcceptsInputMethod, True
        )
        self.setFlag(
            QGraphicsTextItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setPlainText(text)
        self.setDefaultTextColor(Qt.GlobalColor.red)
        self.setFont(QFont("Fira Code", 14))
        self.setPos(0, 0)
        self.setZValue(12)

        self.resizing = False
        self.resizing_dir = ResizeDir.TopLeft
        self.current_scale = 1.0

    def focusOutEvent(self, event: QFocusEvent) -> None:
        # self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setSelected(False)
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        return super().focusOutEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        if self.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction:
            self.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditable
                | Qt.TextInteractionFlag.TextEditorInteraction
            )
        return super().focusInEvent(event)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget) -> None:
        if self.isSelected() or self.hasFocus():
            painter.save()

            border_pen = QPen(
                QColor(0, 122, 204, 255),
                1,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.FlatCap,
                Qt.PenJoinStyle.MiterJoin,
            )
            painter.setPen(border_pen)
            painter.drawRect(self.boundingRect().adjusted(1, 1, -1, -1))
            # draw four small filled rectangles inside the corners, as resizing handles
            painter.setBrush(QColor(0, 122, 204, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            handle_size = self.handle_size
            # top left
            painter.drawRect(QRectF(1, 1, handle_size, handle_size))
            # top right
            painter.drawRect(QRectF(
                self.boundingRect().width() - handle_size - 1,
                1,
                handle_size,
                handle_size,
            ))
            # bottom left
            painter.drawRect(QRectF(
                1,
                self.boundingRect().height() - handle_size - 1,
                handle_size,
                handle_size,
            ))
            # bottom right
            painter.drawRect(QRectF(
                self.boundingRect().width() - handle_size - 1,
                self.boundingRect().height() - handle_size - 1,
                handle_size,
                handle_size,
            ))
            painter.restore()
            super().paint(painter, option, widget)
            return
        return super().paint(painter, option, widget)

    def get_cursor_shape(self, point: QPoint) -> Qt.CursorShape:
        handle_size = self.handle_size
        # check if mouse is inside one of the four handles
        rect = self.boundingRect()
        if point.x() < handle_size and point.y() < handle_size:
            # top left
            logger.debug('text.top.left, cursor-> \\')
            return Qt.CursorShape.SizeFDiagCursor
        elif point.x() > rect.width() - handle_size and point.y() < handle_size:
            # top right
            logger.debug('text.top.right, cursor-> /')
            return Qt.CursorShape.SizeBDiagCursor
        elif point.x() < handle_size and point.y() > rect.height() - handle_size:
            # bottom left
            logger.debug('text.bottom.left, cursor-> /')
            return Qt.CursorShape.SizeBDiagCursor
        elif point.x() > rect.width() - handle_size and point.y() > rect.height() - handle_size:
            # bottom right
            logger.debug('text.bottom.right, cursor-> \\')
            return Qt.CursorShape.SizeFDiagCursor
        # check if mouse is on one of the borders, and if so, change to move cursor
        elif point.x() < handle_size or point.x() > rect.width() - handle_size:
            logger.debug('text.left_or_right, cursor-> move')
            return Qt.CursorShape.DragMoveCursor
        elif point.y() < handle_size or point.y() > rect.height() - handle_size:
            logger.debug('text.top_or_bottom, cursor-> move')
            return Qt.CursorShape.DragMoveCursor
        else:
            logger.debug('text.content, cursor-> I')
            return Qt.CursorShape.IBeamCursor
            # self.unsetCursor()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        point = event.pos()
        scene_point = event.scenePos()
        handle_size = self.handle_size
        # check if mouse is inside one of the four handles
        rect = self.boundingRect()
        if point.x() < handle_size and point.y() < handle_size:
            # top left
            self.resizing = True
            self.resizing_dir = ResizeDir.TopLeft
        elif point.x() > rect.width() - handle_size and point.y() < handle_size:
            # top right
            self.resizing = True
            self.resizing_dir = ResizeDir.TopRight
        elif point.x() < handle_size and point.y() > rect.height() - handle_size:
            # bottom left
            self.resizing = True
            self.resizing_dir = ResizeDir.BottomLeft
        elif point.x() > rect.width() - handle_size and point.y() > rect.height() - handle_size:
            # bottom right
            self.resizing = True
            self.resizing_dir = ResizeDir.BottomRight
        else:
            self.resizing = False
            return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.resizing = False
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        # point = event.pos()
        # scene_point = self.mapToScene(point)
        scene_point = event.scenePos()
        # check if mouse is inside one of the four handles
        # and if so, resize (scale) self
        if self.resizing:
            scale = self.current_scale
            preview = self.sceneBoundingRect()
            base = self.sceneBoundingRect()
            rect = self.boundingRect()
            if self.resizing_dir == ResizeDir.TopLeft:
                preview.setTopLeft(scene_point)
            elif self.resizing_dir == ResizeDir.TopRight:
                preview.setTopRight(scene_point)
            elif self.resizing_dir == ResizeDir.BottomLeft:
                preview.setBottomLeft(scene_point)
            elif self.resizing_dir == ResizeDir.BottomRight:
                preview.setBottomRight(scene_point)
            logger.debug(f"preview: {preview}, base: {base}")
            # transform = self.scale_transform
            # self.scale_transform.setOrigin(base.center())
            # self.scale_transform.setXScale(preview.width() / base.width())
            # self.scale_transform.setYScale(preview.height() / base.height())
            # self.setTransform(self.scale_transform, False)
            # self.scale_transform = transform
            scale = max(
                preview.width() / base.width(),
                preview.height() / base.height(),
            ) * self.current_scale
            logger.debug(f"scale: {scale}")
            self.prepareGeometryChange()
            # calculate new position
            self.setTransformOriginPoint(rect.center())
            # if self.resizing_dir == ResizeDir.TopLeft:
            #     # scale based on right bottom, so keep right bottom in place
            #     self.setTransformOriginPoint(base.bottomRight())
            # elif self.resizing_dir == ResizeDir.TopRight:
            #     # scale based on left bottom, so keep left bottom in place
            #     self.setTransformOriginPoint(base.bottomLeft())
            # elif self.resizing_dir == ResizeDir.BottomLeft:
            #     # scale based on right top, so keep right top in place
            #     self.setTransformOriginPoint(base.topRight())
            # elif self.resizing_dir == ResizeDir.BottomRight:
            #     # scale based on left top, so keep left top in place
            #     self.setTransformOriginPoint(base.topLeft())
            self.setScale(scale)
            self.update()
            self.current_scale = scale
            return

        return super().mouseMoveEvent(event)
