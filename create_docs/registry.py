"""The registry defines the data items that should appear in the documentation."""

from dataclasses import dataclass

@dataclass
class DimensionRegistryItem:
    contract_file: str
    sheet_name: str
    
dimension_registry: dict[str, DimensionRegistryItem] = {
    "dim_building": DimensionRegistryItem(
        contract_file="dim_building",
        sheet_name="dim_building"
    )
}