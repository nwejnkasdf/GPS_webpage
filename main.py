from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auth import AdminRequired, is_admin, require_admin_html
from database import init_db
from routers import auth as auth_router
from routers.admin import attendance as admin_attendance
from routers.admin import members, sessions, weeks
from routers.public import attendance as public_attendance

app = FastAPI(title="BOJ 알고리즘 동아리 출석 체커", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup():
    init_db()


# ── 관리자 인증 실패 핸들러 ────────────────────────────────────────────────────
@app.exception_handler(AdminRequired)
async def admin_required_handler(request: Request, exc: AdminRequired):
    return RedirectResponse(url="/admin/login", status_code=303)


# ── API 라우터 ────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth_router.router)
app.include_router(sessions.router,          prefix=PREFIX, tags=["sessions"])
app.include_router(members.router,           prefix=PREFIX, tags=["members"])
app.include_router(weeks.router,             prefix=PREFIX, tags=["weeks"])
app.include_router(admin_attendance.router,  prefix=PREFIX, tags=["attendance-admin"])
app.include_router(public_attendance.router, prefix=PREFIX, tags=["attendance-public"])


# ── HTML 페이지 라우트 ─────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "public/index.html", {"request": request, "is_admin": is_admin(request)}
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
