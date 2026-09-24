from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_password: str = Field(default="change_me", description="Main application password")
    default_home_team: str = Field(default="Home", description="Default name of home team")
    default_away_team: str = Field(default="Away", description="Default name of away team")
    state_file: str = Field(default="scoreboard_state.json", description="File to store state")
    state_max_age_minutes: int = Field(default=90, description="Maximum age of state file in minutes")
    default_mode: int = Field(default=2, description="Default state of scoreboard (Date/Time)")
    default_brightness: int = Field(default=8, description="Default brightness level (0-15, 255=Auto)")
    default_halftime_length: int = Field(default=45, description="Default halftime length in minutes")
    default_overtime_length: int = Field(default=15, description="Default overtime length in minutes")
    active_roster_id: int | None = Field(default=None, description="Active match roster profile")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")