from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_history_has_one_merged_head():
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["006_convert_to_admin_sales_roles"]
