import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgresql://u:p@host/db", "postgresql+asyncpg://u:p@host/db"),
        ("postgres://u:p@host/db", "postgresql+asyncpg://u:p@host/db"),
        ("postgresql+asyncpg://u:p@host/db", "postgresql+asyncpg://u:p@host/db"),
        ("  postgresql://u:p@host/db  ", "postgresql+asyncpg://u:p@host/db"),
    ],
)
def test_async_database_url_uses_the_asyncpg_driver(database_url, expected):
    assert Settings(database_url=database_url).async_database_url == expected


def test_async_database_url_rejects_an_empty_url():
    with pytest.raises(ValueError, match="DATABASE_URL must not be empty"):
        _ = Settings(database_url="   ").async_database_url
