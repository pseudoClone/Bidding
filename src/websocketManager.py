from uuid import UUID
from fastapi import WebSocket
import logging

"""
Since, HTTP is stateless, we have no way to manage connections to our API by 
clients.
We could use DB for this but frequent read and writes to PostgreSQL by throwaway
connections does not make sense. So, instead we save it in memory, this will 
take up some memory but make our work fast. Maybe in future, we use Redis or 
something like that.
"""

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.activeConnections: dict[str, list[WebSocket]] = {}

    async def connect(self, webSocket: WebSocket, auctionID: UUID):
        await webSocket.accept()
        auctionKey = str(auctionID)
        if auctionKey not in self.activeConnections:
            self.activeConnections[auctionKey] = []
            """
            Ig this is similar to struct{}{} in go. Because we could have saved
            this is a set data structure but that would consume extra bytes.
            """
        self.activeConnections[auctionKey].append(webSocket)

    def disconnect(self, webSocket: WebSocket, auctionID: UUID):
        auctionKey = str(auctionID)
        if auctionKey in self.activeConnections:
            self.activeConnections[auctionKey].remove(webSocket)
            if not self.activeConnections[auctionKey]:
                del self.activeConnections[auctionKey]

    async def broadcastToAuction(self, auctionID: UUID, message: dict):
        auctionKey = str(auctionID)
        if auctionKey not in self.activeConnections:
            return
        disconnected = []
        for connection in self.activeConnections[auctionKey]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    f"Failed to send message in auction {auctionKey}: {e}"
                )
                disconnected.append(connection)
        for connection in disconnected:
            self.disconnect(connection, auctionID)


manager = ConnectionManager()
