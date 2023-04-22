from PySide6.QtCore import QRect, QPoint, QPropertyAnimation, QEasingCurve, Qt
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QFileDialog
from PySide6.QtGui import QIcon, QAction, QGuiApplication, QActionGroup, QPixmap
from functools import partial

from loguru import logger
from typing import List
from about import AboutDialog
from qdbus import DBusAdapter

from shotter import Shotter
from image import ImageLabel
from editor import Editor, ImageData
from theme import ThemeContainer


class TrayIcon(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        self.setToolTip('PySP')

        self.themer = ThemeContainer()
        self.themer.themeChanged.connect(self.update_icons)

        self.images: List[ImageLabel] = []
        self.animations = []
        self.shotter = Shotter(self)

        self.editor = Editor(self.themer)
        self.editor.pinned.connect(self.pin_image)
        self.editor.copied.connect(self.copy_image)
        self.editor.saved.connect(self.save_image)
        self.shotter.captured.connect(self.editor.edit_new_capture)

        self.about_open = False

        self.setIcon(self.themer.get_icon('Capture'))

        self.menu = QMenu()
        self.capture_action = QAction(
            self.themer.get_icon('Capture'), "Capture", self,
        )
        self.capture_action.triggered.connect(self.take_screenshot)
        self.menu.addAction(self.capture_action)

        self.locate_action = QAction(
            self.themer.get_icon('Locate'), "Locate images", self,
        )
        self.locate_action.triggered.connect(self.move_windows_on_screen)
        self.menu.addAction(self.locate_action)

        self.menu.addSeparator()

        self.themes_menu = self.menu.addMenu(
            self.themer.get_icon("ChangeTheme"), "Theme",
        )
        self.theme_group = QActionGroup(self.themes_menu)
        self.theme_group.setExclusive(True)

        # self.theme_group.triggered.connect(update_selected_radio)
        for theme_name in self.themer.theme_names():
            action = QAction(theme_name, self)
            action.triggered.connect(
                partial(self.themer.change_theme, theme_name)
            )
            action.setCheckable(True)
            self.theme_group.addAction(action)
            self.themes_menu.addAction(action)
            if theme_name == self.themer.theme:
                action.setChecked(True)

        self.about_action = QAction(
            self.themer.get_icon('About'), "About", self,
        )
        self.about_action.triggered.connect(self.show_about_dialog)
        self.menu.addAction(self.about_action)

        self.menu.addSeparator()
        self.quit_action = QAction(
            self.themer.get_icon('Quit'), "Quit", self,
        )
        self.quit_action.triggered.connect(self.quit)
        self.menu.addAction(self.quit_action)

        self.setContextMenu(self.menu)

        self.activated.connect(self.take_screenshot)

        self.dbus_adapter = DBusAdapter(self)

        logger.debug('app.started')

    def update_icons(self):
        self.setIcon(self.themer.get_icon('Capture'))
        self.capture_action.setIcon(self.themer.get_icon('Capture'))
        self.locate_action.setIcon(self.themer.get_icon('Locate'))
        self.themes_menu.setIcon(self.themer.get_icon('ChangeTheme'))
        self.about_action.setIcon(self.themer.get_icon('About'))
        self.quit_action.setIcon(self.themer.get_icon('Quit'))

    def take_screenshot(self):
        self.shotter.take()

    def pin_image(self, img: ImageData):
        image = ImageLabel(
            img.image,
            img.position,
            self.themer,
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

    def copy_image(self, pixmap: QPixmap):
        QApplication.clipboard().setPixmap(pixmap)

    def save_image(self, pixmap: QPixmap):
        selected = QFileDialog.getSaveFileName(
            None,
            "Save image as",
            filter="PNG image (*.png)",
            selectedFilter="PNG image (*.png)",
        )
        if len(selected) > 0 and selected[0] != '':
            pixmap.save(selected[0], "png")

    def quit(self):
        logger.debug('app.quit')
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

    def show_about_dialog(self):
        if self.about_open:
            return

        self.about_open = True
        about_dialog = AboutDialog(self.themer)
        about_dialog.setModal(True)
        logger.debug('about.show')
        about_dialog.exec_()
        self.about_open = False
