from fastapi import FastAPI, Depends

from sqlmodel import Session

from .engine import engine
from .model import Auction, AuctionCreate

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
