from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from sqlmodel import Session, select
from uuid import UUID
from .engine import get_session
from .model import Auction, AuctionCreate, BidCreate, Bid, User
from datetime import datetime, timezone
from .security import verifyPassword, createAccessToken
from .security import getCurrentUser
import jwt
from jwt import PyJWTError
from .security import SECRET_KEY, ALGORITHM
from fastapi import WebSocket, Query, WebSocketDisconnect
from .websocketManager import manager
import json
from decimal import Decimal, InvalidOperation

app = FastAPI()


@app.post("/auctions", response_model=Auction)
def create_auction(
    auction_data: AuctionCreate,
    session: Session = Depends(get_session),
    currentUseri: User = Depends(getCurrentUser),
):
    db_auction = Auction(
        **auction_data.model_dump(),
        current_highest_bid=auction_data.starting_bid,
        creator_id=currentUseri.id,
    )
    session.add(db_auction)
    session.commit()
    session.refresh(db_auction)
    return db_auction


@app.post("/auctions/{auction_id}/bid", response_model=Bid)
async def place_bid(
    auction_id: UUID,
    bid_data: BidCreate,
    session: Session = Depends(get_session),
    currentUseri: User = Depends(getCurrentUser),
):
    auction = session.get(Auction, auction_id)
    if not auction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"This auction with auction id: {auction_id} does not exist",
        )
    now = datetime.now(timezone.utc)
    if now < auction.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auction has not started yet",
        )
    if now > auction.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auction has already ended",
        )
    if bid_data.amount <= auction.current_highest_bid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bid must be higher than the current highest bid"
            + f"{auction.current_highest_bid}",
        )
    if currentUseri.id == auction.creator_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot place a bid in own auction",
        )
    new_bid = Bid(
        amount=bid_data.amount,
        auction_id=auction_id,
        bidder_id=currentUseri.id,
        timestamp=now,
    )
    session.add(new_bid)
    auction.current_highest_bid = bid_data.amount
    session.add(auction)

    session.commit()
    session.refresh(new_bid)

    broadcastPayload = {
        "event": "new_bid",
        "auction_id": str(auction_id),
        "highest_bid": str(auction.current_highest_bid),
        "timestamp": new_bid.timestamp.isoformat(),
    }
    await manager.broadcastToAuction(auction_id, broadcastPayload)
    return new_bid


@app.post("/token")
def loginForAccessToken(
    formData: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    statement = select(User).where(User.username == formData.username)
    user = session.exec(statement=statement).first()

    if not user or not verifyPassword(formData.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to do this action",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )
    accessToken = createAccessToken(data={"sub": str(user.id)})
    return {"access_token": accessToken, "token_type": "bearer"}


async def getWebSocketUser(token: str, session: Session) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        userID = payload.get("sub")
        if userID:
            return session.get(User, userID)
    except PyJWTError:
        return None
    return None


@app.websocket("/auctions/{auction_id}/ws")
async def auctionWebSocket(
    webSocket: WebSocket,
    auctionID: UUID,
    token: str = Query(...),
    # This of this like spread operator in JS, but here it works with the URL
    session: Session = Depends(get_session),
):
    user = await getWebSocketUser(token=token, session=session)
    if not user:
        await webSocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.connect(webSocket=webSocket, auctionID=auctionID)

    try:
        while True:
            rawData = await webSocket.receive_text()
            try:
                data = json.loads(rawData)
                bidAmount = Decimal(str(data.get("amount")))
            except (
                json.JSONDecodeError, 
                KeyError, ValueError, InvalidOperation):  # fmt: skip
                await webSocket.send_json(
                    {"error": "Invalid payload operation"}
                )
                continue
            auction = session.get(Auction, auctionID)

            if not auction:
                await webSocket.send_json({"error": "Auction not found"})
                continue

            now = datetime.now(timezone.utc)
            if now < auction.start_time:
                await webSocket.send_json(
                    {"error": "Auction has not started yet"}
                )
            if now > auction.end_time:
                await webSocket.send_json(
                    {"error": "Auction has already ended"}
                )
            newBid = Bid(
                amount=bidAmount,
                auction_id=auctionID,
                bidder_id=user.id,
                timestamp=now,
            )
            session.add(newBid)
            auction.current_highest_bid = bidAmount
            session.add(auction)
            session.commit()
            session.refresh(newBid)

            broadcastPayload = {
                "event": "new_bid",
                "auction_id": str(auctionID),
                "highest_bid": str(auction.current_highest_bid),
                "timestamp": newBid.timestamp.isoformat(),
            }
            await manager.broadcastToAuction(auctionID, broadcastPayload)

    except WebSocketDisconnect:
        manager.disconnect(webSocket=webSocket, auctionID=auctionID)
