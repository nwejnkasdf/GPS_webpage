from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./boj_attendance.db"
    BOJ_REQUEST_DELAY: float = 2.5
    SOLVED_AC_REQUEST_DELAY: float = 0.4
    BOJ_MAX_RETRIES: int = 3
    DEBUG: bool = False

    # 관리자 인증
    ADMIN_PASSWORD: str = "changeme"
    SECRET_KEY: str = "please-change-this-secret-key"
    SESSION_MAX_AGE: int = 86400 * 7  # 7일

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
