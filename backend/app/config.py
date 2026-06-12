from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    AICORE_CLIENT_ID: str
    AICORE_CLIENT_SECRET: str
    AICORE_AUTH_URL: str
    AICORE_BASE_URL: str
    AICORE_RESOURCE_GROUP: str = "default"
    LLM_DEPLOYMENT_ID: str

    HANA_HOST: str
    HANA_PORT: int = 443
    HANA_USER: str
    HANA_PASSWORD: str
    HANA_SCHEMA: str

    CPI_API_URL: str = "https://api-eih-qa.next-decade.com/external/integrationhub/correlation/logs/v1"
    CPI_SOURCE: str = "workday"
    CPI_DESTINATION: str = "sap"


settings = Settings()
