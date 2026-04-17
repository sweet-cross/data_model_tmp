"""The registry defines the data items that should appear in the documentation."""

from dataclasses import dataclass
from pathlib import Path

DIMENSIONS_YAML_DIR = Path(__file__).resolve().parent.parent / "data" / "dimensions"
DIMENSIONS_XLSX = DIMENSIONS_YAML_DIR / "dimensions.xlsx"


@dataclass
class DimensionRegistryItem:
    contract_file: str
    sheet_name: str


dimension_registry: dict[str, DimensionRegistryItem] = {
    "dim_building": DimensionRegistryItem(
        contract_file="dim_building",
        sheet_name="dim_building",
    ),
    "dim_tech_generation": DimensionRegistryItem(
        contract_file="dim_tech_generation",
        sheet_name="dim_tech_generation",
    ),
}
