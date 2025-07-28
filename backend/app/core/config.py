from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import  (
    computed_field,
    AnyUrl
)
from urllib.parse import quote_plus

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True
    )
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Gitlytix"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = "clickhouse123" 
    CLICKHOUSE_HOST: str = "clickhouse"  # Use Docker service name
    CLICKHOUSE_PORT: int = 9000  # Native protocol port
    CLICKHOUSE_DB: str = "default"
    CLICKHOUSE_SECURE: bool = False  # Set to False for Docker development setup
    
    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # ClickHouse SQLAlchemy doesn't support https scheme directly
        # Instead, we use the native scheme with secure=True parameter
        secure_param = "?secure=true" if self.CLICKHOUSE_SECURE else ""
        
        # Format: clickhouse+native://username:password@host:port/database?secure=true
        password_part = f":{quote_plus(self.CLICKHOUSE_PASSWORD)}" if self.CLICKHOUSE_PASSWORD else ""
        return f"clickhouse+native://{self.CLICKHOUSE_USER}{password_part}@{self.CLICKHOUSE_HOST}:{self.CLICKHOUSE_PORT}/{self.CLICKHOUSE_DB}{secure_param}"

settings = Settings()
