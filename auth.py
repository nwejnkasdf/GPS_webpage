from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import settings

COOKIE_NAME = "admin_session"


class AdminRequired(Exception):
    """관리자 인증 실패 시 raise — main.py의 exception_handler가 /admin/login으로 리다이렉트"""
    pass


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY)


def create_session_cookie() -> str:
    return _serializer().dumps("admin")


def verify_session_cookie(token: str) -> bool:
    if not token:
        return False
    try:
        _serializer().loads(token, max_age=settings.SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def require_admin_html(request: Request) -> None:
    """HTML 페이지용 의존성 — 인증 실패 시 /admin/login 리다이렉트"""
    if not verify_session_cookie(request.cookies.get(COOKIE_NAME, "")):
        raise AdminRequired()


def require_admin_api(request: Request) -> None:
    """API 엔드포인트용 의존성 — 인증 실패 시 401 JSON"""
    if not verify_session_cookie(request.cookies.get(COOKIE_NAME, "")):
        raise HTTPException(status_code=401, detail="관리자 로그인이 필요합니다.")


def is_admin(request: Request) -> bool:
    """템플릿 컨텍스트용 — 현재 요청이 관리자 세션인지 반환"""
    return verify_session_cookie(request.cookies.get(COOKIE_NAME, ""))
