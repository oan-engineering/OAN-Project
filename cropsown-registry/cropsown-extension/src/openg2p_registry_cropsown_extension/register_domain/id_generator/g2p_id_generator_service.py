from datetime import date

from openg2p_fastapi_common.service import BaseService
from openg2p_registry_core.interfaces import G2PIdGeneratorInterface, IdAffix
from openg2p_registry_core.models.g2p_register import G2PRegister


class G2PIdGeneratorService(BaseService, G2PIdGeneratorInterface):
    """Functional-id affixes for the crop sown registers.

    A crop sown id carries the season it belongs to:

        REG/S1/2026/00012

    The season segment is S1-S4, one per cropping season, taken from the
    record's own `season`. A record with no season yet falls back to the
    seasonless form (REG/2026/00012) rather than guessing a number.

    The year is resolved when the id is minted, so a record created in 2027
    carries /2027/. The padding is the id-generator pool's idLength (5), set in
    the Helm values.
    """

    # register mnemonic -> sequence prefix, minus the season and year segments
    PREFIXES = {
        "cropsown": "REG",
        "production": "CROP/PROD",
        "cluster": "CLTR",
        "infestation": "PI",
    }

    # Ethiopian cropping calendar order: the main rains first, then the short
    # rains, then irrigated and perennial cropping.
    SEASON_NUMBERS = {
        "CROP_SEASON_MEHER": 1,
        "MEHER": 1,
        "CROP_SEASON_BELG": 2,
        "BELG": 2,
        "CROP_SEASON_BEGA": 3,
        "BEGA": 3,
    }

    @classmethod
    def season_segment(cls, season: str | None) -> str:
        """`CROP_SEASON_MEHER` / `MEHER` -> `S1/`, unknown or missing -> `` (no segment)."""
        number = cls.SEASON_NUMBERS.get(str(season or "").strip().upper())
        return f"S{number}/" if number else ""

    def generate_prefix_suffix(
        self, g2p_register: G2PRegister, register_mnemonic: str
    ) -> IdAffix:
        mnemonic = (register_mnemonic or "").lower()
        if isinstance(g2p_register, dict):
            season_val = g2p_register.get("production_season") or g2p_register.get("season")
        else:
            season_val = (
                getattr(g2p_register, "production_season", None)
                or getattr(g2p_register, "season", None)
            )
        season = self.season_segment(season_val)
        year = date.today().year

        prefix = self.PREFIXES.get(mnemonic)
        if prefix:
            return IdAffix(prefix=f"{prefix}/{season}{year}/", suffix="")

        return IdAffix(prefix=f"CROP/{mnemonic.upper() or 'REC'}/{season}{year}/", suffix="")
