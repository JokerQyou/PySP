from PySide6.QtDBus import QDBusAbstractAdaptor, QDBusConnection
from PySide6.QtCore import QObject, Signal, ClassInfo, Slot

from loguru import logger

SERVICE_ID = 'info.mynook.pysp'


@ClassInfo({
    'D-Bus Interface': SERVICE_ID,
    'D-Bus Introspection': f"""
<interface name="{SERVICE_ID}">
  <method name="takeScreenshot"></method>
</interface>
""",
})
class DBusAdapter(QDBusAbstractAdaptor):
    takeScreenshot = Signal()

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        QDBusConnection.sessionBus().registerObject('/', self.parent())
        QDBusConnection.sessionBus().registerService(SERVICE_ID)
        logger.debug('qdbus.register')

    @Slot(name='takeScreenshot', result=None)
    def takeScreenshot(self):
        self.parent().shotter.take()
