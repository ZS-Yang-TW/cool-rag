from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str
    openai_base_url: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.7

    # VLLM Configuration
    vllm_api_key: str | None = None
    vllm_base_url: str
    vllm_model: str
    vllm_max_input_tokens: int = 44000
    vllm_max_output_tokens: int = 8000
    vllm_reasoning_effort: str = "medium"

    # Database Configuration
    db_host: str
    db_port: int = 5432
    db_username: str
    db_password: str
    db_database: str

    # Documents Configuration
    documents_dir: str = "/workspace/documents"

    # Application Configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    environment: str = "development"

    # CORS Configuration
    enable_cors: bool
    cors_origins: list[str] = ["http://localhost:3000"]

    # Retrieval Configuration
    top_k_results: int = 7
    similarity_threshold: float = 0.4
    chunk_size: int = 320
    chunk_overlap: int = 64
    embedding_batch_size: int = 20

    # MMR (Maximal Marginal Relevance) Configuration
    use_mmr: bool = True
    mmr_lambda: float = 0.5
    mmr_fetch_k: int = 20

    # Token Budget Configuration (Memory Management)
    token_budget_max_context: int = 16000
    token_budget_memory: int = 4000
    token_budget_retrieval: int = 8000
    token_budget_output: int = 2000
    token_budget_system_prompt: int = 500

    # Logging
    file_log_level: str = "INFO"
    console_log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        """Database URL for SQLAlchemy"""
        return f"postgresql://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_database}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()  # type: ignore[call-arg]
