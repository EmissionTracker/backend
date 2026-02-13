from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/emissiontracker"

    # AWS Cognito
    cognito_region: str = "us-east-1"
    cognito_user_pool_id: str

    # AWS S3
    s3_bucket_name: str
    aws_region: str = "us-east-1"

    # App
    app_env: str = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def cognito_jwks_url(self) -> str:
        return (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com"
            f"/{self.cognito_user_pool_id}/.well-known/jwks.json"
        )


settings = Settings()
