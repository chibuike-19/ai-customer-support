from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env into the environment, so Pydantic AI also finds ANTHROPIC_API_KEY.
load_dotenv()


class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    database_url: str
    classifier_model: str = "openai:gpt-4o-mini"
    agent_model: str = "openai:gpt-4o-mini"
    poll_interval_seconds: int = 60
    dashboard_username: str = "admin"
    dashboard_password: str = ""
    # Run the Gmail poller inside the web app. Turn off for local dashboard work.
    poller_enabled: bool = False


settings = Settings()