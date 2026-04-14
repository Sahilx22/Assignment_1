"""
Alembic migration environment.

Configured for:
  - Offline mode (generate SQL scripts without a live DB connection)
  - Online mode  (apply migrations against a live PostgreSQL instance)
  - Auto-detection of model changes via SQLAlchemy metadata
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make sure the app package is importable from this script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load metadata
from app.core.config import settings          # noqa: E402
from app.db.session import Base              # noqa: E402
import app.models.user                       # noqa: E402, F401 — registers models on Base

# Alembic Config object (gives access to alembic.ini values)
config = context.config

# Override sqlalchemy.url with the value from our app settings
# Escape % characters for ConfigParser (URL-encoded passwords like %40 need to be %% escaped)
escaped_url = settings.DATABASE_URL.replace("%", "%%")
config.set_main_option("sqlalchemy.url", escaped_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


# Offline mode
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,        # Detect column type changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# Online mode
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Use a fresh connection per migration run
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
