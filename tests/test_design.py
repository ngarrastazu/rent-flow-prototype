"""Reglas de docs/DESIGN.md que se pueden comprobar automáticamente."""
import re
from pathlib import Path

from rentflow.ui import theme

UI_DIR = Path(theme.__file__).parent
ALLOWED = re.compile("[✓★☆]")  # símbolos tipográficos que la guía sí usa (verificado y estrellas)
# Rangos de emojis más habituales (pictogramas, símbolos, transporte, banderas, dingbats con variante)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U0001F1E6-\U0001F1FF☀-⛿✀-➿️]")


def test_no_emojis_in_ui():
    """DESIGN.md §9: nada de emojis en la aplicación (se usan iconos Material)."""
    for path in [*UI_DIR.glob("*.py"), UI_DIR.parents[2] / "app.py"]:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not EMOJI.search(ALLOWED.sub("", line)), f"{path.name}:{n}: {line.strip()}"


def test_brand_assets_exist():
    for asset in [theme.LOGO_HORIZONTAL, theme.LOGO_ON_VIOLET, theme.ISOTYPE, theme.ISOTYPE_MONO, theme.APP_ICON]:
        assert asset.is_file(), asset


def test_score_ranges():
    assert theme.score_style(94) == (theme.VIOLET, "Match excelente")
    assert theme.score_style(85) == (theme.VIOLET, "Match excelente")
    assert theme.score_style(84) == (theme.BLUE, "Buen match")
    assert theme.score_style(70) == (theme.BLUE, "Buen match")
    assert theme.score_style(69) == (theme.INK_MUTED, "Match posible")
