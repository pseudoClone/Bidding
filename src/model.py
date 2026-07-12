from sqlmodel import Field, SQLModel, Relationship
from pydantic import model_validator, BaseModel
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime, timezone

class User(SQLModel, table=True):
        id: UUID | None = Field(primary_key=True, 
                                default_factory=uuid4, unique=True, index=True)
        username: str = Field(unique=True, index=True, nullable=False)
        email: str = Field(unique=True, index=True, nullable=False)
        hashed_password: str = Field(nullable=False)
        is_active: bool = Field(default=True)

        created_auctions: list["Auction"] = Relationship(
                back_populates="creator")
        bids: list["Bid"] = Relationship(back_populates="bidder")
        """
                Same as line 37, if I had kept it just `Bid` instead of "Bid", 
                it would me to have reference to Bid before it is created.
                require
        """

class Auction(SQLModel, table=True):
        id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
        title: str = Field(index=True, nullable=False)
        description: str | None = Field(default=None)

        starting_bid: Decimal = Field(default=0.0, 
                                      max_digits=10, decimal_places=2)
        current_highest_bid: Decimal = Field(default=0.0, 
                                             max_digits=10, decimal_places=2)
        created_at: datetime = Field(
                default_factory=lambda: datetime.now(timezone.utc)
                )
        start_time: datetime = Field(nullable=False)
        end_time: datetime = Field(nullable=False)

        creator_id: UUID = Field(foreign_key="user.id", nullable=False)
        
        """
                Don't use User.id instead of "User.id" because we have to ensure
                that the User class has to be initialized before Auction and we
                have to deal with futures and shit.
        """

        creator: User = Relationship(back_populates="created_auctions")
        bids: list["Bid"] = Relationship(back_populates="auction")
        """
        This matches the bidder: User = Relationship(back_populates="bids") part
        """

        @model_validator(mode="after")
        def validatetimes(self) -> Auction:
                if self.end_time <= self.start_time:
                        raise ValueError(
                                "End time must be greater than start time "
                                )
                return self

class Bid(SQLModel, table=True):
        id: UUID = Field(primary_key=True, default_factory=uuid4, index=True)
        amount: Decimal = Field(max_digits=10, decimal_places=2, nullable=False)
        timestamp: datetime = Field(
                default_factory=lambda: datetime.now(timezone.utc)
                )
        auction_id: UUID = Field(foreign_key="auction.id", nullable=False)
        bidder_id: UUID = Field(foreign_key="user.id", nullable=False)
        auction: Auction = Relationship(back_populates="bids")
        bidder: User = Relationship(back_populates="bids")


class AuctionCreate(BaseModel):
        title: str
        description: str | None = None
        starting_bid: Decimal
        start_time: datetime
        end_time: datetime
        creator_id: UUID #until we have oauth2