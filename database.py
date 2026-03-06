from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings

DATABASE_URL = settings.DATABASE_URL
# Railway는 postgres:// 형식으로 제공하지만 SQLAlchemy는 postgresql:// 필요
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import session, member, week, week_problem, attendance  # noqa: F401
    from models import club_info, club_image, announcement  # noqa: F401
    from models import telepathy, boj_game  # noqa: F401
    Base.metadata.create_all(bind=engine)


def ensure_club_info(db):
    from models.club_info import ClubInfo
    if not db.query(ClubInfo).first():
        db.add(ClubInfo(intro_text=""))
        db.commit()


def ensure_recreation_defaults(db):
    from services.recreation_service import ensure_default_telepathy_teams

    ensure_default_telepathy_teams(db)
