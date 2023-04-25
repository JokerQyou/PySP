import sys
from enum import Enum
from functools import partial
from typing import List
from dataclasses import dataclass

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QRect, QRectF, QSize, QObject, Signal, QSizeF, QMargins
from PySide6.QtGui import QPixmap, QPainter, QCursor, QColor, QScreen, QMouseEvent, QKeyEvent, QPen, QAction, QBrush, QFont, QActionGroup, QTransform, QInputMethodEvent
from PySide6.QtWidgets import QLabel, QApplication, QGraphicsScene, QGraphicsView, QToolBar, QFrame, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem, QGraphicsSceneMouseEvent, QGraphicsSceneHoverEvent, QGraphicsSceneContextMenuEvent
from PySide6.QtGui import QGuiApplication
from PIL import ImageQt, Image
from mss import ScreenShotError, mss
from loguru import logger

from theme import ThemeContainer
from op_text import NodeTag


@dataclass
class ImageData:
    image: QPixmap
    position: QPoint


class SelectionBorder(QGraphicsRectItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setBrush(QBrush(Qt.GlobalColor.transparent))
        self.setPen(
            QPen(
                QColor(0, 122, 204, 255),
                2,  # border width
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.FlatCap,
                Qt.PenJoinStyle.MiterJoin,
            )
        )


class Op(Enum):
    None_ = 0
    Text = 1


class ResizeEdge(Enum):
    None_ = 0
    TopLeft = 1
    Top = 2
    TopRight = 3
    Right = 4
    BottomRight = 5
    Bottom = 6
    BottomLeft = 7
    Left = 8


class EditorView(QGraphicsView):
    selectionUpdated = Signal(QRect)
    editorClosed = Signal()

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setMouseTracking(True)
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setFrameStyle(QFrame.Shape.NoFrame)

        self.dragging = False
        self.draggingOrigin = QPoint()
        self.draggingSelection = False
        self.resizeEdge = ResizeEdge.None_
        # 选择区域
        self.selectionArea = QRect()
        # 选择区域的图片内容，也就是明亮的部分
        self.selectionAreaItem = QGraphicsPixmapItem(QPixmap())
        # 选择区域的边框，拖动可以改变选区大小
        self.selectionBorder = SelectionBorder(QRectF())
        # 遮罩层，这是选区外的黑色半透明部分
        self.screenMask = QGraphicsRectItem(self.scene().sceneRect())
        # 原始的完整图片
        self.original_pixmap = QPixmap()
        # 当前的操作
        self.op = Op.None_
        # 所有添加到场景（画布）中的项
        self.history: List[QGraphicsItem] = []

    def reset(self):
        self.scene().clear()

        self.dragging = False
        self.draggingOrigin = QPoint()
        self.draggingSelection = False
        self.resizeEdge = ResizeEdge.None_
        self.selectionArea = QRect()
        self.selectionAreaItem = QGraphicsPixmapItem(QPixmap())
        self.selectionBorder = SelectionBorder(QRectF())
        self.screenMask = QGraphicsRectItem(self.scene().sceneRect())
        self.screenMask.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.screenMask.setPen(QPen(Qt.GlobalColor.transparent))
        self.original_pixmap = QPixmap()

    def start_edit(self, pixmap: QPixmap):
        self.reset()  # TODO Remove this

        self.original_pixmap = pixmap
        self.scene().setSceneRect(pixmap.rect())
        self.setFixedSize(pixmap.deviceIndependentSize().toSize())
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.screenMask.setRect(self.scene().sceneRect())
        self.scene().addPixmap(pixmap)
        self.scene().addItem(self.screenMask)
        self.scene().addItem(self.selectionAreaItem)
        self.scene().addItem(self.selectionBorder)
        self.update_selection_area()

    def update_selection_border(self):
        area = self.selectionArea.normalized()
        self.selectionBorder.setRect(area.adjusted(-1, -1, 1, 1))
        # draw four small circle points on the corners
        # self.selectionBorder.

    def update_cursor_shape(self, pos: QPoint):
        area = self.selectionArea.normalized()
        if area.isEmpty():
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            return

        if self.op == Op.Text:
            # check if there's a text item under the cursor
            item = self.scene().itemAt(pos, QTransform())
            if item is not None and isinstance(item, NodeTag):
                item.update_cursor_shape(item.mapFromScene(pos))
                pass
            else:
                self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
            return

        # if cursor is on the border, change to resize cursor
        if area.adjusted(5, 5, -5, -5).contains(pos):
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        else:
            # check if cursor is outside one of the four borders
            on_top = pos.y() < area.top()
            on_bottom = pos.y() > area.bottom()
            on_left = pos.x() < area.left()
            on_right = pos.x() > area.right()
            # check if cursor is AT one of the four borders
            at_top = area.top() <= pos.y() <= area.top() + 5
            at_bottom = area.bottom() - 5 <= pos.y() <= area.bottom()
            at_left = area.left() <= pos.x() <= area.left() + 5
            at_right = area.right() - 5 <= pos.x() <= area.right()
            # check if cursor is on one of the four corners
            if on_top and on_left:
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            elif on_top and on_right:
                self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
            elif on_bottom and on_left:
                self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
            elif on_bottom and on_right:
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            # check if cursor is outside one of the four corners
            elif at_top and at_left:
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            elif at_top and at_right:
                self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
            elif at_bottom and at_left:
                self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
            elif at_bottom and at_right:
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            # check if cursor is on one of the four borders
            elif at_left or at_right or on_left or on_right:
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            elif at_top or at_bottom or on_top or on_bottom:
                self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
            else:
                self.unsetCursor()

    def selectOp(self, op: Op):
        self.op = op
        self.update_cursor_shape(self.mapFromGlobal(QCursor.pos()))

    def update_selection_area(self):
        area = self.selectionArea.normalized()
        if not area.isEmpty():
            dpr = self.original_pixmap.devicePixelRatioF()
            pixmap_area = QRectF(
                area.topLeft().toPointF() * dpr,
                area.size().toSizeF() * dpr,
            ).toRect()
            self.selectionAreaItem.setPixmap(
                self.original_pixmap.copy(pixmap_area)
            )
            self.selectionAreaItem.setPos(area.topLeft())
            # self.selectionAreaItem.stackBefore(self.screenMask)
            self.selectionUpdated.emit(area)
            self.update_selection_border()

    # def keyPressEvent(self, event: QKeyEvent):
    #     if event.key() == Qt.Key.Key_Escape:
    #         self.editorClosed.emit()
    #     super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()

            # when double clicking, check if an item is under the cursor
            # and if so, let the item handle the event (typically entering edit mode)
            if event.type() == QMouseEvent.Type.MouseButtonDblClick:
                return super().mousePressEvent(event)

            # create a new selection area
            if self.selectionArea.normalized().isEmpty():
                logger.debug(
                    'drag.start @({x}, {y})', x=point.x(), y=point.y(),
                )
                self.dragging = True
                self.selectionArea.setTopLeft(event.position().toPoint())
                # this is intentionally left out because on Hi-DPI screens
                # it would produce tiny selection area (1x1 px) that's hard to see,
                # and it's not very useful anyway.
                # so we only update the selection area when the mouse is moved
                # self.update_selection_area()
                # self.update()
            # resize the selection area if cursor is outside the selection area
            else:
                area = self.selectionArea.normalized()
                if self.selectionArea != area:
                    self.selectionArea = area
                    logger.debug('selection area normalized on the fly')

                if self.op == Op.Text:
                    # check if there's already a text item under the cursor
                    item = self.scene().itemAt(point, QTransform())
                    if item is None or item in [self.screenMask, self.selectionArea, self.selectionBorder]:
                        text_item = NodeTag('text')
                        self.history.append(text_item)
                        self.scene().addItem(text_item)
                        # put text item at cursor position, align the cursor position to center of left edge of text item
                        text_item.setPos(
                            point.x(),
                            point.y() - text_item.boundingRect().height() / 2
                        )
                        # item might have been shrinked, so we need to update
                        # the whole view, in case some drawn content is still at the old position
                        text_item.scaleChanged.connect(self.update)
                        text_item.xChanged.connect(self.update)
                        text_item.yChanged.connect(self.update)
                        text_item.widthChanged.connect(self.update)
                        text_item.heightChanged.connect(self.update)
                        logger.debug(
                            'item.text added @({x}, {y})', x=point.x(), y=point.y()
                        )
                    elif isinstance(item, NodeTag):
                        item.setFocus()
                        logger.debug('item.text edit')
                    return super().mousePressEvent(event)

                # if cursor is inside the selection area, drag the selection area
                if area.adjusted(6, 6, -6, -6).contains(point):
                    self.draggingOrigin = point
                    self.draggingSelection = True
                    return

                # check if cursor is outside one of the four borders
                on_top = point.y() < area.top()
                on_bottom = point.y() > area.bottom()
                on_left = point.x() < area.left()
                on_right = point.x() > area.right()
                # check if cursor is AT one of the four borders
                at_top = area.top() <= point.y() <= area.top() + 5
                at_bottom = area.bottom() - 5 <= point.y() <= area.bottom()
                at_left = area.left() <= point.x() <= area.left() + 5
                at_right = area.right() - 5 <= point.x() <= area.right()
                if on_top and on_left:
                    self.selectionArea.setTopLeft(point)
                    self.resizeEdge = ResizeEdge.TopLeft
                elif on_top and on_right:
                    self.selectionArea.setTopRight(point)
                    self.resizeEdge = ResizeEdge.TopRight
                elif on_bottom and on_left:
                    self.selectionArea.setBottomLeft(point)
                    self.resizeEdge = ResizeEdge.BottomLeft
                elif on_bottom and on_right:
                    self.selectionArea.setBottomRight(point)
                    self.resizeEdge = ResizeEdge.BottomRight
                elif on_top:
                    self.selectionArea.setTop(point.y())
                    self.resizeEdge = ResizeEdge.Top
                elif on_bottom:
                    self.selectionArea.setBottom(point.y())
                    self.resizeEdge = ResizeEdge.Bottom
                elif on_left:
                    self.selectionArea.setLeft(point.x())
                    self.resizeEdge = ResizeEdge.Left
                elif on_right:
                    self.selectionArea.setRight(point.x())
                    self.resizeEdge = ResizeEdge.Right
                elif at_top and at_left:
                    self.resizeEdge = ResizeEdge.TopLeft
                elif at_top and at_right:
                    self.resizeEdge = ResizeEdge.TopRight
                elif at_bottom and at_left:
                    self.resizeEdge = ResizeEdge.BottomLeft
                elif at_bottom and at_right:
                    self.resizeEdge = ResizeEdge.BottomRight
                elif at_top:
                    self.resizeEdge = ResizeEdge.Top
                elif at_bottom:
                    self.resizeEdge = ResizeEdge.Bottom
                elif at_left:
                    self.resizeEdge = ResizeEdge.Left
                elif at_right:
                    self.resizeEdge = ResizeEdge.Right

                self.update_selection_area()
                # self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            self.selectionArea.setBottomRight(event.position().toPoint())
            area = self.selectionArea.normalized()
            logger.debug(
                'drag.drag topLeft=({x}, {y}) size=({w}, {h})',
                x=area.x(), y=area.y(),
                w=area.width(), h=area.height(),
            )
            self.update_selection_area()
            self.update()
            return

        if self.draggingSelection:
            point = event.position().toPoint()
            # prevent from dragging the selection area outside the view
            offset = point - self.draggingOrigin
            preview = self.selectionArea.translated(offset)
            if preview.left() < 0:
                preview.translate(-preview.left(), 0)
            if preview.top() < 0:
                preview.translate(0, -preview.top())
            if preview.right() > self.width():
                preview.translate(self.width() - preview.right(), 0)
            if preview.bottom() > self.height():
                preview.translate(0, self.height() - preview.bottom())

            self.draggingOrigin = point
            self.selectionArea = preview
            self.update_selection_area()
            self.update()
            return

        point = event.position().toPoint()
        self.update_cursor_shape(point)

        if self.op != Op.None_:
            return super().mouseMoveEvent(event)

        if self.resizeEdge == ResizeEdge.TopLeft:
            self.selectionArea.setTopLeft(point)
        elif self.resizeEdge == ResizeEdge.TopRight:
            self.selectionArea.setTopRight(point)
        elif self.resizeEdge == ResizeEdge.BottomLeft:
            self.selectionArea.setBottomLeft(point)
        elif self.resizeEdge == ResizeEdge.BottomRight:
            self.selectionArea.setBottomRight(point)
        elif self.resizeEdge == ResizeEdge.Top:
            self.selectionArea.setTop(point.y())
        elif self.resizeEdge == ResizeEdge.Bottom:
            self.selectionArea.setBottom(point.y())
        elif self.resizeEdge == ResizeEdge.Left:
            self.selectionArea.setLeft(point.x())
        elif self.resizeEdge == ResizeEdge.Right:
            self.selectionArea.setRight(point.x())
        else:
            return
        logger.debug('resizeEdge={e}', e=self.resizeEdge)
        self.update_selection_area()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.op != Op.None_:
            return super().mouseReleaseEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            if self.dragging:
                logger.debug('drag.end @({x}, {y})', x=point.x(), y=point.y())
                self.dragging = False
                self.selectionArea.setBottomRight(point)
                self.update_selection_area()
                self.update()
                self.update_cursor_shape(point)
                return

            if self.draggingSelection:
                logger.debug(
                    'drag.selection.end @({x}, {y})', x=point.x(), y=point.y())
                self.draggingSelection = False
                self.draggingOrigin = QPoint()
                self.update_cursor_shape(point)
                return

            if self.resizeEdge != ResizeEdge.None_:
                self.resizeEdge = ResizeEdge.None_
                self.update_cursor_shape(point)
                return

    def get_result(self) -> QPixmap:
        self.scene().clearFocus()
        self.scene().clearSelection()
        self.scene().update()

        area = self.selectionArea.normalized()
        dpr = self.original_pixmap.devicePixelRatioF()

        pixmap_area = QRectF(
            area.topLeft().toPointF() * dpr,
            area.size().toSizeF() * dpr,
        ).toRect()

        pixmap = self.original_pixmap.copy(pixmap_area)
        painter = QPainter(pixmap)
        self.scene().render(
            painter,
            QRect(QPoint(), pixmap_area.size()),
            pixmap_area,
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        return pixmap


class EditorWindow(QLabel):
    pinned = Signal(ImageData)
    saved = Signal(QPixmap)
    copied = Signal(QPixmap)

    def __init__(self, themer: ThemeContainer):
        super().__init__()

        self.themer = themer

        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled)
        self.setWindowState(
            self.windowState()
            | Qt.WindowState.WindowFullScreen
        )

        self.setWindowIcon(self.themer.get_icon("Capture"))
        self.setWindowTitle("Fullscreen editor")

        self.scene = QGraphicsScene(self)
        self.editorView = EditorView(self.scene, self)

        # Floating toolbar
        toolbar = QToolBar(self)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #F3F3F3;
                border: 2px solid #007ACC;
            }
        """)
        self.toolGroup = QActionGroup(self)
        self.toolGroup.setExclusive(True)
        self.action_op_text: QAction = toolbar.addAction(
            self.themer.get_icon("Text"), "Pin",
        )
        self.action_op_text.setCheckable(True)
        self.toolGroup.addAction(self.action_op_text)
        self.action_op_text.triggered.connect(
            partial(self.select_tool, Op.Text)
        )
        self.action_op_text.toggled.connect(
            partial(self.select_tool, Op.Text)
        )

        toolbar.addSeparator()
        self.action_cancel: QAction = toolbar.addAction(
            self.themer.get_icon("Quit"), "Cancel",
        )
        self.action_cancel.triggered.connect(self.close)
        self.action_cancel.setShortcut("Esc")

        self.action_pin: QAction = toolbar.addAction(
            self.themer.get_icon("Pin"), "Pin",
        )
        self.action_pin.triggered.connect(self.pin_result)

        self.action_save: QAction = toolbar.addAction(
            self.themer.get_icon("Save"), "Save as",
        )
        self.action_save.triggered.connect(self.save_result)

        self.action_copy: QAction = toolbar.addAction(
            self.themer.get_icon("CopyToClipboard"), "Copy",
        )
        self.action_copy.triggered.connect(self.copy_result)

        self.toolbar = toolbar
        self.toolbar.hide()
        self.editorView.selectionUpdated.connect(self.update_widgets)
        self.editorView.editorClosed.connect(self.close)

        self.size_tip = QLabel(self)
        tip_font = QFont("Fira Code", 12)
        if not tip_font.exactMatch():
            for family in QFont.families():
                if 'Mono' in family:
                    tip_font.setFamily(family)
                    break
        self.size_tip.setFont(tip_font)
        self.size_tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 9999×9999 px = 12 chracters
        tip_rect = self.size_tip.fontMetrics().boundingRect("9999×9999 px")
        self.size_tip.setFixedSize(
            tip_rect.size().grownBy(QMargins(3, 4, 3, 4))
        )
        # use a dark color for background and light color for text
        self.size_tip.setStyleSheet('''
            QLabel {
                background-color: #2C2C2C;
                color: #F3F3F3;
            }
        ''')
        self.size_tip.hide()

        self.themer.themeChanged.connect(self.update_icons)

    def select_tool(self, op: Op):
        # click checked action to uncheck it
        if self.editorView.op == op:
            self.toolGroup.setExclusive(False)
            if op == Op.Text:
                self.action_op_text.setChecked(False)
            self.editorView.selectOp(Op.None_)
            self.toolGroup.setExclusive(True)
        else:
            self.toolGroup.checkedAction().setChecked(False)
            if op == Op.Text:
                self.action_op_text.setChecked(True)
            self.editorView.selectOp(op)

    def update_icons(self):
        self.setWindowIcon(self.themer.get_icon("Capture"))
        self.action_cancel.setIcon(self.themer.get_icon("Quit"))
        self.action_pin.setIcon(self.themer.get_icon("Pin"))
        self.action_save.setIcon(self.themer.get_icon("Save"))
        self.action_copy.setIcon(self.themer.get_icon("CopyToClipboard"))

    def edit_new_capture(self, pixmap: QPixmap):
        logger.debug('editor.new_capture')
        self.editorView.start_edit(pixmap)
        self.showFullScreen()

    def closeEvent(self, event):
        self.toolbar.hide()
        self.size_tip.hide()
        self.scene.clear()
        self.editorView.reset()
        self.hide()
        return event.ignore()

    def update_widgets(self, selectionArea: QRect):
        area = selectionArea.normalized()
        if area.isEmpty():
            self.toolbar.hide()
            return

        if not self.toolbar.isVisible():
            self.toolbar.show()

        if not self.size_tip.isVisible():
            self.size_tip.show()

        self.adjust_widget_positions(selectionArea)

    def adjust_widget_positions(self, selectionArea: QRect):
        outsideGap = 5
        # when there's a valid selection area, put the toolbar:
        #  - if there's enough space below the selection area, below the selection area (to the left)
        #  - else: on the bottom line of selection area (also to the left)
        area = selectionArea.normalized()

        toolbarTopLeft = area.bottomLeft() + QPoint(0, outsideGap + 2)
        # toolbarTopLeft.setX(toolbarTopLeft.x() - 2)  # border width is 2px
        if toolbarTopLeft.y() + self.toolbar.height() > self.height():
            toolbarTopLeft.setY(
                area.bottomLeft().y() - self.toolbar.height() + 2
            )
        self.toolbar.move(toolbarTopLeft)

        # put size tip label above the selection area, with a gap
        # if there's not enough space above the selection area,
        # try to put it inside the selection area (to the top)
        sizeTipTopLeft = area.topLeft() - QPoint(0, self.size_tip.height() + outsideGap)
        if sizeTipTopLeft.y() < 0:
            sizeTipTopLeft.setY(area.topLeft().y())
        self.size_tip.setText(f'{area.width()}×{area.height()} px')
        self.size_tip.move(sizeTipTopLeft)

    def pin_result(self):
        area = self.editorView.selectionArea.normalized()  # FIXME
        self.pinned.emit(ImageData(
            image=self.editorView.get_result(),
            position=area.topLeft(),
        ))
        self.close()

    def copy_result(self):
        self.copied.emit(self.editorView.get_result())
        self.close()

    def save_result(self):
        self.saved.emit(self.editorView.get_result())
        # self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    capturer = mss()
    data: ScreenShotError = capturer.grab(capturer.monitors[0])
    image = ImageQt.ImageQt(
        Image.frombytes('RGB', data.size, data.bgra, 'raw', 'BGRX')
    )
    logger.debug(
        'shot.new raw_image_size={}, data_valid={}',
        data.size,
        not image.isNull(),
    )
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(
        QGuiApplication.primaryScreen().devicePixelRatio()
    )

    themer = ThemeContainer()

    class TmpEditorWindow(EditorWindow):
        def closeEvent(self, event):
            logger.debug('editor.close')
            return event.accept()

    editor = TmpEditorWindow(themer)
    editor.edit_new_capture(pixmap)

    text_item = NodeTag('text 1')
    text_item.setPos(300, 400)
    editor.editorView.history.append(text_item)
    editor.editorView.scene().addItem(text_item)

    text_2 = QGraphicsTextItem('text 2')
    text_2.setPos(400, 400)
    text_2.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextEditorInteraction)
    text_2.setFlags(
        QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        | QGraphicsItem.GraphicsItemFlag.ItemStopsClickFocusPropagation
    )
    text_2.setZValue(10)
    text_2.setDefaultTextColor(Qt.GlobalColor.green)
    editor.editorView.history.append(text_2)
    editor.editorView.scene().addItem(text_2)

    def save_test_image(image: QPixmap):
        logger.debug('save_test_image')
        image.save('/tmp/test.png')
        editor.close()

    editor.saved.connect(save_test_image)

    sys.exit(app.exec())
