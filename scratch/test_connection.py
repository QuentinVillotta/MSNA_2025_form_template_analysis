"""Test database connection with asset table."""

from src.db import DatabaseConnection

db = DatabaseConnection()

# Test query
df = db.execute_query("SELECT * FROM asset LIMIT 5")
print(df.head())
print(df.info())