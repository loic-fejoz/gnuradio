from PyQt5.QtCore import *
import grc.api.mcp

class MCPWorker(QRunnable):
    def __init__(self, main_window):
        super().__init__()
        self.mcp_server = grc.api.mcp.attach(main_window)
    
    @pyqtSlot()
    def run(self):
        self.mcp_server.run(transport="streamable-http")