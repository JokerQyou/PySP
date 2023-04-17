from PySide6.QtCore import QRect, QPoint, QPropertyAnimation, QEasingCurve, Qt
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction, QGuiApplication

from loguru import logger
from typing import List
from qdbus import DBusAdapter

from shotter import Shotter
from image import ImageLabel
from editor import Editor, ImageData


class TrayIcon(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        self.setIcon(QIcon("icon.png"))
        self.setToolTip('PySP')

        self.images: List[ImageLabel] = []
        self.animations = []
        self.shotter = Shotter(self)
        self.editor = Editor()
        self.editor.edited.connect(self.handle_new_image)
        self.shotter.captured.connect(self.editor.edit_new_capture)

        self.menu = QMenu()
        self.capture_action = QAction("Capture", self)
        self.capture_action.triggered.connect(self.take_screenshot)
        self.menu.addAction(self.capture_action)

        self.locate_action = QAction("Locate images", self)
        self.locate_action.triggered.connect(self.move_windows_on_screen)
        self.menu.addAction(self.locate_action)

        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(self.quit)
        self.menu.addAction(self.quit_action)

        self.setContextMenu(self.menu)

        self.activated.connect(self.take_screenshot)

        self.dbus_adapter = DBusAdapter(self)

        logger.debug('PySP started')

    def take_screenshot(self):
        self.shotter.take()

    def handle_new_image(self, img: ImageData):
        image = ImageLabel(
            img.image,
            img.position,
        )
        self.images.append(image)
        logger.debug(
            'manager.image.pin size=({w}*{h}), pos=({x}, {y}), indep_size=({iw}*{ih}), dpr={pr}, total_images={n}',
            w=img.image.size().width(),
            h=img.image.size().height(),
            x=img.position.x(),
            y=img.position.y(),
            iw=img.image.deviceIndependentSize().width(),
            ih=img.image.deviceIndependentSize().height(),
            pr=img.image.devicePixelRatio(),
            n=len(self.images),
        )

        def cleanup():
            self.images.remove(image)
            logger.debug(
                'manager.image.destroy, total_images={n}', n=len(self.images),
            )
        image.destroyed.connect(cleanup)
        image.show()

    def quit(self):
        logger.debug('PySP quit')
        QApplication.instance().quit()

    def move_windows_on_screen(self):
        screen = QGuiApplication.primaryScreen()
        screen_rect = screen.availableGeometry()

        for window in self.images:
            window_rect = window.geometry()
            overlap = QRect(screen_rect).intersected(window_rect)
            if overlap.width() < window_rect.width() * 0.5 or overlap.height() < window_rect.height() * 0.5:
                x, y = window_rect.x(), window_rect.y()

                # 如果窗口在屏幕左侧
                if x + window_rect.width() * 0.5 < screen_rect.left():
                    x = screen_rect.left()
                # 如果窗口在屏幕右侧
                elif x > screen_rect.right() - window_rect.width() * 0.5:
                    x = screen_rect.right() - window_rect.width()

                # 如果窗口在屏幕顶部
                if y + window_rect.height() * 0.5 < screen_rect.top():
                    y = screen_rect.top()
                # 如果窗口在屏幕底部
                elif y > screen_rect.bottom() - window_rect.height() * 0.5:
                    y = screen_rect.bottom() - window_rect.height()

                # 创建动画
                animation = QPropertyAnimation(window, b"geometry")
                animation.setDuration(170)  # 动画持续时间，单位毫秒
                animation.setStartValue(window_rect)
                animation.setEndValue(
                    QRect(QPoint(x, y), window_rect.size())
                )
                animation.setEasingCurve(
                    QEasingCurve.Type.OutCirc
                )  # 设置缓动曲线
                animation.start(
                    QPropertyAnimation.DeletionPolicy.DeleteWhenStopped
                )
                self.animations.append(animation)
                animation.destroyed.connect(
                    lambda _: self.animations.remove(animation)
                )
