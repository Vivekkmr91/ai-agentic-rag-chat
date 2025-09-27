"""
Configuration settings for the Agentic RAG system
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # Database Configuration
    default_database_url: str = "sqlite:///./example.db"
    database_timeout: int = 30
    
    # Embedding Model Configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # Vector Database Configuration
    chroma_persist_directory: str = "./chroma_db"
    vector_search_top_k: int = 10
    
    # Search Configuration
    hybrid_search_alpha: float = 0.5  # Balance between vector and keyword search
    max_search_results: int = 20
    
    # Agent Configuration
    max_query_length: int = 10000
    query_timeout: int = 60
    agent_retry_attempts: int = 3
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "rag_system.log"
    
    # Performance Configuration
    max_concurrent_queries: int = 10
    cache_size: int = 1000
    
    # Schema Extraction Configuration
    schema_sample_size: int = 5
    max_tables_to_process: int = 100
    
    # SQL Execution Configuration
    sql_execution_timeout: int = 30
    max_result_rows: int = 1000
    allowed_sql_operations: list = ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN"]
    
    # Security Configuration
    enable_sql_validation: bool = True
    restrict_dangerous_operations: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()

# Derived configurations
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = PROJECT_ROOT / "cache"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Database configurations for different environments
DATABASE_CONFIGS = {
    "sqlite": {
        "driver": "sqlite",
        "example_url": "sqlite:///./example.db",
        "features": ["schema_extraction", "basic_queries"],
        "limitations": ["no_concurrent_writes", "basic_types"]
    },
    "postgresql": {
        "driver": "postgresql+asyncpg",
        "example_url": "postgresql://user:password@localhost:5432/database",
        "features": ["full_sql", "advanced_types", "concurrent_access"],
        "limitations": []
    },
    "mysql": {
        "driver": "mysql+aiomysql",
        "example_url": "mysql://user:password@localhost:3306/database",
        "features": ["full_sql", "concurrent_access"],
        "limitations": ["limited_types"]
    }
}

# Agent type configurations
AGENT_CONFIGS = {
    "query_analyzer": {
        "max_complexity": 10,
        "timeout": 5,
        "retry_attempts": 2
    },
    "schema_agent": {
        "cache_ttl": 300,  # 5 minutes
        "max_tables": 50,
        "timeout": 15
    },
    "sql_agent": {
        "execution_timeout": 30,
        "max_result_size": "10MB",
        "validation_level": "strict"
    },
    "text_agent": {
        "max_context_length": 4000,
        "confidence_threshold": 0.6,
        "timeout": 10
    },
    "synthesis_agent": {
        "max_sources": 5,
        "response_format": "markdown",
        "timeout": 8
    }
}

# Search engine configurations
SEARCH_CONFIGS = {
    "vector_search": {
        "similarity_threshold": 0.6,
        "rerank": True,
        "rerank_top_k": 20
    },
    "keyword_search": {
        "min_score": 0.1,
        "boost_exact_match": 2.0,
        "boost_phrase_match": 1.5
    },
    "hybrid_search": {
        "alpha": 0.5,
        "normalization": "min_max",
        "combine_method": "weighted_sum"
    }
}

def get_database_config(db_type: str) -> dict:
    """Get database configuration by type"""
    return DATABASE_CONFIGS.get(db_type, DATABASE_CONFIGS["sqlite"])

def get_agent_config(agent_type: str) -> dict:
    """Get agent configuration by type"""
    return AGENT_CONFIGS.get(agent_type, {})

def get_search_config(search_type: str) -> dict:
    """Get search configuration by type"""
    return SEARCH_CONFIGS.get(search_type, {})