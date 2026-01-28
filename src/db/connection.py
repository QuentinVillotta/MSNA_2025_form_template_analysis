"""PostgreSQL database connection module."""

import os
from contextlib import contextmanager
from typing import Generator

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine, text


class DatabaseConnection:
    """Handles PostgreSQL database connections."""

    def __init__(self):
        """Initialize connection parameters from environment variables."""
        load_dotenv()
        
        self.host = os.getenv("POSTGRES_HOST")
        self.port = os.getenv("POSTGRES_PORT", "5432")
        self.database = os.getenv("POSTGRES_DATABASE")
        self.schema = os.getenv("POSTGRES_SCHEMA")
        self.username = os.getenv("POSTGRES_USERNAME")
        self.password = os.getenv("POSTGRES_PASSWORD")
        self._engine = None

    def get_connection_url(self) -> str:
        """Build SQLAlchemy connection URL."""
        return (
            f"postgresql+psycopg://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
            f"?options=-csearch_path%3D{self.schema}"
        )

    @property
    def engine(self) -> Engine:
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            self._engine = create_engine(self.get_connection_url())
        return self._engine

    @contextmanager
    def get_connection(self) -> Generator:
        """
        Context manager for database connections.
        
        Yields:
            SQLAlchemy Connection
            
        Example:
            with db.get_connection() as conn:
                result = conn.execute(text("SELECT * FROM table"))
        """
        conn = self.engine.connect()
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: dict = None) -> pd.DataFrame:
        """
        Execute a SELECT query and return results as DataFrame.
        
        Args:
            query: SQL query to execute
            params: Query parameters for safe parameterization
            
        Returns:
            pandas DataFrame with query results
        """
        if params:
            return pd.read_sql_query(text(query), self.engine, params=params)
        return pd.read_sql_query(query, self.engine)
