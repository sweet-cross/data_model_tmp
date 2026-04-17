"""The registry defines the data items that should appear in the documentation."""

from dataclasses import dataclass
from pathlib import Path

DIMENSIONS_YAML_DIR = Path(__file__).resolve().parent / "data" / "dimensions"
DIMENSIONS_XLSX = DIMENSIONS_YAML_DIR / "dimensions.xlsx"
ASSUMPTIONS_YAML_DIR = Path(__file__).resolve().parent / "data" / "assumptions"


@dataclass
class DimensionRegistryItem:
    contract_file: str
    sheet_name: str
    # When True the dimension appears in the overview table only: no nav entry
    # and no per-dimension page are generated. The CSV is still written to
    # /downloads/dimensions/ so the overview row can still point at data.
    # Use this for dimensions too large to render as a card tree (e.g. ISO regions).
    index_only: bool = False


dimension_registry: dict[str, DimensionRegistryItem] = {
    "dim_building": DimensionRegistryItem(
        contract_file="dim_building",
        sheet_name="dim_building",
    ),
    "dim_endusesector": DimensionRegistryItem(
        contract_file="dim_endusesector",
        sheet_name="dim_endusesector",
    ),
    "dim_fuel": DimensionRegistryItem(
        contract_file="dim_fuel",
        sheet_name="dim_fuel",
    ),
    "dim_iso_region": DimensionRegistryItem(
        contract_file="dim_iso_region",
        sheet_name="dim_iso_region",
        index_only=True,
    ),
    "dim_resource": DimensionRegistryItem(
        contract_file="dim_resource",
        sheet_name="dim_resource",
    ),
    "dim_tech_generation": DimensionRegistryItem(
        contract_file="dim_tech_generation",
        sheet_name="dim_tech_generation",
    ),
    "dim_tech_heat": DimensionRegistryItem(
        contract_file="dim_tech_heat",
        sheet_name="dim_tech_heat",
    ),
    "dim_tech_hydrogen": DimensionRegistryItem(
        contract_file="dim_tech_hydrogen",
        sheet_name="dim_tech_hydrogen",
    ),
    "dim_tech_liquids": DimensionRegistryItem(
        contract_file="dim_tech_liquids",
        sheet_name="dim_tech_liquids",
    ),
    "dim_tech_methane": DimensionRegistryItem(
        contract_file="dim_tech_methane",
        sheet_name="dim_tech_methane",
    ),
    "dim_tech_storage": DimensionRegistryItem(
        contract_file="dim_tech_storage",
        sheet_name="dim_tech_storage",
    ),
    "dim_trn_mode_freight": DimensionRegistryItem(
        contract_file="dim_trn_mode_freight",
        sheet_name="dim_trn_mode_freight",
    ),
    "dim_trn_mode_private": DimensionRegistryItem(
        contract_file="dim_trn_mode_private",
        sheet_name="dim_trn_mode_private",
    ),
    "dim_use_elec": DimensionRegistryItem(
        contract_file="dim_use_elec",
        sheet_name="dim_use_elec",
    ),
    "dim_use_hydrogen": DimensionRegistryItem(
        contract_file="dim_use_hydrogen",
        sheet_name="dim_use_hydrogen",
    ),
    "dim_use_liquids": DimensionRegistryItem(
        contract_file="dim_use_liquids",
        sheet_name="dim_use_liquids",
    ),
    "dim_use_methane": DimensionRegistryItem(
        contract_file="dim_use_methane",
        sheet_name="dim_use_methane",
    ),
}


@dataclass
class AssumptionRegistryItem:
    """Registry entry for one scenario-assumption contract.

    Assumption contracts are yaml-only: there is no bulk workbook to pull rows
    from, so `sheet_name` (used by dimensions) does not apply. The per-page
    render consumes the yaml directly via `docs/macros/contracts.load_contract`.
    """

    contract_file: str


assumption_registry: dict[str, AssumptionRegistryItem] = {
    "entsoe_tyndp_ntc": AssumptionRegistryItem(contract_file="entsoe_tyndp_ntc"),
    "scenass_aviation_fuel_demand": AssumptionRegistryItem(
        contract_file="scenass_aviation_fuel_demand"
    ),
    "scenass_biomass_potential": AssumptionRegistryItem(
        contract_file="scenass_biomass_potential"
    ),
    "scenass_cost_generation_technologies": AssumptionRegistryItem(
        contract_file="scenass_cost_generation_technologies"
    ),
    "scenass_cost_heating_technologies": AssumptionRegistryItem(
        contract_file="scenass_cost_heating_technologies"
    ),
    "scenass_cost_storage_technologies": AssumptionRegistryItem(
        contract_file="scenass_cost_storage_technologies"
    ),
    "scenass_electric_appliances_useful_energy_demand": AssumptionRegistryItem(
        contract_file="scenass_electric_appliances_useful_energy_demand"
    ),
    "scenass_energy_reference_area": AssumptionRegistryItem(
        contract_file="scenass_energy_reference_area"
    ),
    "scenass_freight_transport_useful_energy_demand": AssumptionRegistryItem(
        contract_file="scenass_freight_transport_useful_energy_demand"
    ),
    "scenass_gdp": AssumptionRegistryItem(contract_file="scenass_gdp"),
    "scenass_hdd": AssumptionRegistryItem(contract_file="scenass_hdd"),
    "scenass_households": AssumptionRegistryItem(contract_file="scenass_households"),
    "scenass_import_prices": AssumptionRegistryItem(
        contract_file="scenass_import_prices"
    ),
    "scenass_passenger_transport_useful_energy_demand": AssumptionRegistryItem(
        contract_file="scenass_passenger_transport_useful_energy_demand"
    ),
    "scenass_population": AssumptionRegistryItem(contract_file="scenass_population"),
    "scenass_process_heat_useful_energy_demand": AssumptionRegistryItem(
        contract_file="scenass_process_heat_useful_energy_demand"
    ),
    "scenass_space_heating_useful_energy_demand": AssumptionRegistryItem(
        contract_file="scenass_space_heating_useful_energy_demand"
    ),
    "scenass_warm_water_useful_energy_demand": AssumptionRegistryItem(
        contract_file="scenass_warm_water_useful_energy_demand"
    ),
    "scenass_working_population": AssumptionRegistryItem(
        contract_file="scenass_working_population"
    ),
}
