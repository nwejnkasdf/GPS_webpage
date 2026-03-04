from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class ClubInfo(Base):
    __tablename__ = "club_info"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    intro_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
