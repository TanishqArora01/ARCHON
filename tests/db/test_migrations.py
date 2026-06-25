from pathlib import Path


def test_initial_migration_exists():
    migration = Path("migrations/versions/0001_initial_schema.py")
    assert migration.exists()
    text = migration.read_text(encoding="utf-8")
    assert "create_table" in text
    assert "symbol_nodes" in text
    assert "repository_documents" in text
