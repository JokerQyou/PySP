import os
from typing import List
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from loguru import logger

default_theme = 'Office S'


@dataclass
class IconSet:
    name: str

    IconCapture: QIcon
    IconSave: QIcon
    IconCopyToClipboard: QIcon
    IconQuit: QIcon
    IconLocate: QIcon
    IconZoomReset: QIcon
    IconDelete: QIcon
    IconChangeTheme: QIcon
    IconAbout: QIcon
    IconPin: QIcon
    IconText: QIcon


class ThemeContainer(QObject):
    themeChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_sets = self.load_icon_sets()
        self.theme = default_theme

    def get_icon(self, name: str):
        for icon_set in self.icon_sets:
            if icon_set.name == self.theme:
                return getattr(icon_set, f'Icon{name}')
        return None

    def load_icon_sets(self) -> List[IconSet]:
        sets = []
        # list directories under resources/ and load icons from there, using directory name as set name
        for directory in sorted(os.listdir("resources")):
            # strip off number suffix from directory name, then trim and replace all - with spaces
            name = ' '.join([
                s.capitalize()
                for s in directory.rsplit("-", 1)[0].strip().split("-")
            ])
            icon_dir = os.path.join("resources", directory)
            sets.append(IconSet(
                name=name,
                IconCapture=QIcon(os.path.join(icon_dir, "screenshot.png")),
                IconSave=QIcon(os.path.join(icon_dir, "save.png")),
                IconCopyToClipboard=QIcon(
                    os.path.join(icon_dir, "copy-to-clipboard.png")
                ),
                IconQuit=QIcon(os.path.join(icon_dir, "close.png")),
                IconLocate=QIcon(os.path.join(icon_dir, "target.png")),
                IconZoomReset=QIcon(os.path.join(icon_dir, "zoom-reset.png")),
                IconDelete=QIcon(os.path.join(icon_dir, "delete.png")),
                IconChangeTheme=QIcon(
                    os.path.join(icon_dir, "change-theme.png"),
                ),
                IconAbout=QIcon(os.path.join(icon_dir, "info.png")),
                IconPin=QIcon(os.path.join(icon_dir, "pin.png")),
                IconText=QIcon(os.path.join(icon_dir, "text.png")),
            ))
        return sets

    def change_theme(self, theme: str):
        from_theme = self.theme
        if theme == from_theme:
            return

        self.theme = theme
        self.themeChanged.emit(self.theme)
        logger.debug('theme.change {} => {}', from_theme, self.theme)

    def theme_names(self):
        return [icon_set.name for icon_set in self.icon_sets]
