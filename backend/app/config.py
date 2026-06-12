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

    ALLOWED_ORIGINS: str = "*"  # comma-separated list, e.g. "https://frontend.cfapps.us10.hana.ondemand.com"

    LLM_USAGE_MONITOR_APP_ID: str = "28"
    LLM_USAGE_MONITOR_MODEL_NAME: str = "claude-sonnet-4-6"
    LLM_USAGE_MONITOR_CALL_TYPE_L_INVOKE: str = "l_invoke"
    LLM_USAGE_MONITOR_CALL_TYPE_A_INVOKE: str = "a_invoke"
    LLM_USAGE_MONITOR_BASE_URL: str = ""
    LLM_USAGE_MONITOR_API_KEY: str = ""


settings = Settings()
