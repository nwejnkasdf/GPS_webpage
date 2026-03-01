from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import COOKIE_NAME, create_session_cookie
from config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse(
        "admin/login.html", {"request": request, "error": error}
    )


@router.post("/admin/login")
async def login(request: Request, password: str = Form(...)):
    if password != settings.ADMIN_PASSWORD:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "비밀번호가 올바르지 않습니다."},
            status_code=401,
        )

    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_session_cookie(),
        httponly=True,
        samesite="lax",
        max_age=settings.SESSION_MAX_AGE,
    )
    return response


@router.get("/admin/logout")
def logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key=COOKIE_NAME)
    return response
