from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auth import AdminRequired, is_admin, require_admin_html
from database import SessionLocal, ensure_club_info, ensure_recreation_defaults, get_db, init_db
from routers import auth as auth_router
from routers.admin import attendance as admin_attendance
from routers.admin import recreation as admin_recreation
from routers.admin import members, sessions, weeks
from routers.admin import club_info as club_info_router
from routers.admin import club_images as club_images_router
from routers.admin import announcements as announcements_router
from routers.public import attendance as public_attendance
from routers.public import recreation as public_recreation

app = FastAPI(title="GPS 동아리", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    try:
        ensure_club_info(db)
        ensure_recreation_defaults(db)
    finally:
        db.close()


# ── 관리자 인증 실패 핸들러 ────────────────────────────────────────────────────
@app.exception_handler(AdminRequired)
async def admin_required_handler(request: Request, exc: AdminRequired):
    return RedirectResponse(url="/admin/login", status_code=303)


# ── API 라우터 ────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth_router.router)
app.include_router(sessions.router,              prefix=PREFIX, tags=["sessions"])
app.include_router(members.router,               prefix=PREFIX, tags=["members"])
app.include_router(weeks.router,                 prefix=PREFIX, tags=["weeks"])
app.include_router(admin_attendance.router,      prefix=PREFIX, tags=["attendance-admin"])
app.include_router(admin_recreation.router,      prefix=PREFIX, tags=["recreation-admin"])
app.include_router(public_attendance.router,     prefix=PREFIX, tags=["attendance-public"])
app.include_router(public_recreation.router,     prefix=PREFIX, tags=["recreation-public"])
app.include_router(club_info_router.router,      prefix=PREFIX, tags=["club-info"])
app.include_router(club_images_router.router,    prefix=PREFIX, tags=["club-images"])
app.include_router(announcements_router.router,  prefix=PREFIX, tags=["announcements"])


# ── 이미지 바이너리 서빙 ──────────────────────────────────────────────────────
@app.get("/images/{image_id}")
def serve_image(image_id: int, db=Depends(get_db)):
    from models.club_image import ClubImage
    img = db.query(ClubImage).filter(ClubImage.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    return Response(
        content=img.data,
        media_type=img.content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ── HTML 페이지 라우트 ─────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "public/home.html", {"request": request, "is_admin": is_admin(request)}
    )


@app.get("/attendance", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "public/index.html", {"request": request, "is_admin": is_admin(request)}
    )


@app.get("/recreation", response_class=HTMLResponse)
def recreation_home(request: Request):
    return templates.TemplateResponse(
        "public/recreation.html",
        {"request": request, "is_admin": is_admin(request)},
    )


@app.get("/recreation/telepathy/representative", response_class=HTMLResponse)
def telepathy_representative_page(request: Request):
    return templates.TemplateResponse(
        "public/telepathy_player.html",
        {
            "request": request,
            "is_admin": is_admin(request),
            "role": "representative",
            "role_label": "대표",
            "page_title": "텔레파시 게임 대표 입력",
        },
    )


@app.get("/recreation/telepathy/team", response_class=HTMLResponse)
def telepathy_team_page(request: Request):
    return templates.TemplateResponse(
        "public/telepathy_player.html",
        {
            "request": request,
            "is_admin": is_admin(request),
            "role": "team",
            "role_label": "팀",
            "page_title": "텔레파시 게임 팀 입력",
        },
    )


@app.get("/recreation/telepathy/display", response_class=HTMLResponse)
def telepathy_display_page(request: Request):
    return templates.TemplateResponse(
        "public/telepathy_display.html",
        {"request": request, "is_admin": is_admin(request)},
    )


@app.get("/recreation/boj-tier", response_class=HTMLResponse)
def boj_tier_page(request: Request):
    return templates.TemplateResponse(
        "public/boj_tier.html",
        {"request": request, "is_admin": is_admin(request)},
    )


@app.get("/session/{session_id}", response_class=HTMLResponse)
def public_session(request: Request, session_id: int):
    return templates.TemplateResponse(
        "public/attendance.html",
        {"request": request, "session_id": session_id, "is_admin": is_admin(request)},
    )


@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(require_admin_html)])
def admin_dashboard(request: Request):
    return templates.TemplateResponse(
        "admin/index.html", {"request": request, "is_admin": True}
    )


@app.get("/admin/club-info", response_class=HTMLResponse, dependencies=[Depends(require_admin_html)])
def admin_club_info(request: Request):
    return templates.TemplateResponse(
        "admin/club_info.html", {"request": request, "is_admin": True}
    )


@app.get("/admin/images", response_class=HTMLResponse, dependencies=[Depends(require_admin_html)])
def admin_images(request: Request):
    return templates.TemplateResponse(
        "admin/images.html", {"request": request, "is_admin": True}
    )


@app.get("/admin/announcements", response_class=HTMLResponse, dependencies=[Depends(require_admin_html)])
def admin_announcements(request: Request):
    return templates.TemplateResponse(
        "admin/announcements.html", {"request": request, "is_admin": True}
    )


@app.get("/admin/recreation", response_class=HTMLResponse, dependencies=[Depends(require_admin_html)])
def admin_recreation_page(request: Request):
    return templates.TemplateResponse(
        "admin/recreation.html", {"request": request, "is_admin": True}
    )


@app.get("/admin/sessions/{session_id}", response_class=HTMLResponse, dependencies=[Depends(require_admin_html)])
def admin_session(request: Request, session_id: int):
    return templates.TemplateResponse(
        "admin/session_detail.html",
        {"request": request, "session_id": session_id, "is_admin": True},
    )


@app.get("/admin/weeks/{week_id}", response_class=HTMLResponse, dependencies=[Depends(require_admin_html)])
def admin_week(request: Request, week_id: int):
    return templates.TemplateResponse(
        "admin/week_detail.html",
        {"request": request, "week_id": week_id, "is_admin": True},
    )


@app.get("/admin/sessions/{session_id}/attendance", response_class=HTMLResponse, dependencies=[Depends(require_admin_html)])
def admin_attendance_page(request: Request, session_id: int):
    return templates.TemplateResponse(
        "admin/attendance.html",
        {"request": request, "session_id": session_id, "is_admin": True},
    )
