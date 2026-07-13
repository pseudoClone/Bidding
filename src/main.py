from fastapi import FastAPI, Depends, HTTPException, status

from sqlmodel import Session
from uuid import UUID
from .engine import engine
from .model import Auction, AuctionCreate, BidCreate, Bid
from datetime import datetime, timezone

app = FastAPI()


def get_session():
    with Session(engine) as session:
        yield session


@app.post("/auctions", response_model=Auction)
def create_auction(
    auction_data: AuctionCreate, session: Session = Depends(get_session)
):
    db_auction = Auction(
        title=auction_data.title,
        description=auction_data.description,
        starting_bid=auction_data.starting_bid,
        current_highest_bid=auction_data.starting_bid,
        start_time=auction_data.start_time,
        end_time=auction_data.end_time,
        creator_id=auction_data.creator_id,
    )
    session.add(db_auction)
    session.commit()
    session.refresh(db_auction)
    return db_auction


@app.post("/auctions/{auction_id}/bid", response_model=Bid)
def place_bid(
    auction_id: UUID,
    bid_data: BidCreate,
    session: Session = Depends(get_session),
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
    if bid_data.bidder_id == auction.creator_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot place a bid in own auction",
        )
    new_bid = Bid(
        amount=bid_data.amount,
        auction_id=auction_id,
        bidder_id=bid_data.bidder_id,
        timestamp=now,
    )
    session.add(new_bid)
    auction.current_highest_bid = bid_data.amount
    session.add(auction)

    session.commit()
    session.refresh(new_bid)
    return new_bid
