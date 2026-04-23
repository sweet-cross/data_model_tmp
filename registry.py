"""The registry defines the data items that should appear in the documentation."""

from dataclasses import dataclass
from pathlib import Path

DIMENSIONS_YAML_DIR = Path(__file__).resolve().parent / "data" / "dimensions"
DIMENSIONS_XLSX = DIMENSIONS_YAML_DIR / "dimensions.xlsx"
ASSUMPTIONS_YAML_DIR = Path(__file__).resolve().parent / "data" / "assumptions"
RESULTS_YAML_DIR = Path(__file__).resolve().parent / "data" / "results"


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
class FlexibleDimensionRegistryItem:
    """Registry entry for a flat-schema dimension whose data lives in the
    shared dimensions workbook.

    Unlike `DimensionRegistryItem`, flexible dimensions do not carry a
    hierarchy (no parent_id / level columns). The page composition mirrors
    assumption/result pages — yaml metadata + Frictionless fields table —
    and optionally renders the underlying data inline when `show_data` is
    True.
    """

    contract_file: str
    show_data: bool = False
    # None falls back to `contract_file`. Set explicitly when the sheet name
    # in the dimensions workbook diverges from the contract name.
    data_sheet: str | None = None

    @property
    def sheet_name(self) -> str:
        return self.data_sheet or self.contract_file


flexible_dimension_registry: dict[str, FlexibleDimensionRegistryItem] = {
    "dim_model": FlexibleDimensionRegistryItem(
        contract_file="dim_model",
        show_data=True,
    ),
}


@dataclass
class ContractRegistryItem:
    """Registry entry for a yaml-only contract (assumptions, results).

    These contracts have no bulk workbook to pull rows from, so `sheet_name`
    (used by dimensions) does not apply. The per-page render consumes the yaml
    directly via `docs/macros/contracts.load_contract`.
    """

    contract_file: str


assumption_registry: dict[str, ContractRegistryItem] = {
    "entsoe_tyndp_ntc": ContractRegistryItem(contract_file="entsoe_tyndp_ntc"),
    "scenass_aviation_fuel_demand": ContractRegistryItem(
        contract_file="scenass_aviation_fuel_demand"
    ),
    "scenass_biomass_potential": ContractRegistryItem(
        contract_file="scenass_biomass_potential"
    ),
    "scenass_cost_generation_technologies": ContractRegistryItem(
        contract_file="scenass_cost_generation_technologies"
    ),
    "scenass_cost_heating_technologies": ContractRegistryItem(
        contract_file="scenass_cost_heating_technologies"
    ),
    "scenass_cost_storage_technologies": ContractRegistryItem(
        contract_file="scenass_cost_storage_technologies"
    ),
    "scenass_electric_appliances_useful_energy_demand": ContractRegistryItem(
        contract_file="scenass_electric_appliances_useful_energy_demand"
    ),
    "scenass_energy_reference_area": ContractRegistryItem(
        contract_file="scenass_energy_reference_area"
    ),
    "scenass_freight_transport_useful_energy_demand": ContractRegistryItem(
        contract_file="scenass_freight_transport_useful_energy_demand"
    ),
    "scenass_gdp": ContractRegistryItem(contract_file="scenass_gdp"),
    "scenass_hdd": ContractRegistryItem(contract_file="scenass_hdd"),
    "scenass_households": ContractRegistryItem(contract_file="scenass_households"),
    "scenass_import_prices": ContractRegistryItem(
        contract_file="scenass_import_prices"
    ),
    "scenass_passenger_transport_useful_energy_demand": ContractRegistryItem(
        contract_file="scenass_passenger_transport_useful_energy_demand"
    ),
    "scenass_population": ContractRegistryItem(contract_file="scenass_population"),
    "scenass_process_heat_useful_energy_demand": ContractRegistryItem(
        contract_file="scenass_process_heat_useful_energy_demand"
    ),
    "scenass_space_heating_useful_energy_demand": ContractRegistryItem(
        contract_file="scenass_space_heating_useful_energy_demand"
    ),
    "scenass_warm_water_useful_energy_demand": ContractRegistryItem(
        contract_file="scenass_warm_water_useful_energy_demand"
    ),
    "scenass_working_population": ContractRegistryItem(
        contract_file="scenass_working_population"
    ),
}


result_registry: dict[str, ContractRegistryItem] = {
    "result_carbon_emissions": ContractRegistryItem(
        contract_file="result_carbon_emissions"
    ),
    "result_carbon_price": ContractRegistryItem(contract_file="result_carbon_price"),
    "result_district_heat_useful_energy_production": ContractRegistryItem(
        contract_file="result_district_heat_useful_energy_production"
    ),
    "result_electricity_consumption": ContractRegistryItem(
        contract_file="result_electricity_consumption"
    ),
    "result_electricity_consumption_monthly": ContractRegistryItem(
        contract_file="result_electricity_consumption_monthly"
    ),
    "result_electricity_consumption_typical_day": ContractRegistryItem(
        contract_file="result_electricity_consumption_typical_day"
    ),
    "result_electricity_supply": ContractRegistryItem(
        contract_file="result_electricity_supply"
    ),
    "result_electricity_supply_monthly": ContractRegistryItem(
        contract_file="result_electricity_supply_monthly"
    ),
    "result_electricity_supply_typical_day": ContractRegistryItem(
        contract_file="result_electricity_supply_typical_day"
    ),
    "result_freight_road_fec": ContractRegistryItem(
        contract_file="result_freight_road_fec"
    ),
    "result_h2_fec": ContractRegistryItem(contract_file="result_h2_fec"),
    "result_h2_supply": ContractRegistryItem(contract_file="result_h2_supply"),
    "result_installed_capacity": ContractRegistryItem(
        contract_file="result_installed_capacity"
    ),
    "result_liquids_fec": ContractRegistryItem(contract_file="result_liquids_fec"),
    "result_liquids_supply": ContractRegistryItem(
        contract_file="result_liquids_supply"
    ),
    "result_methane_fec": ContractRegistryItem(contract_file="result_methane_fec"),
    "result_methane_supply": ContractRegistryItem(
        contract_file="result_methane_supply"
    ),
    "result_passenger_road_private_fec": ContractRegistryItem(
        contract_file="result_passenger_road_private_fec"
    ),
    "result_passenger_road_public_fec": ContractRegistryItem(
        contract_file="result_passenger_road_public_fec"
    ),
    "result_process_heat_useful_energy_production": ContractRegistryItem(
        contract_file="result_process_heat_useful_energy_production"
    ),
    "result_space_heat_useful_energy_supply": ContractRegistryItem(
        contract_file="result_space_heat_useful_energy_supply"
    ),
    "result_storage_installed_volume": ContractRegistryItem(
        contract_file="result_storage_installed_volume"
    ),
    "result_storage_output": ContractRegistryItem(
        contract_file="result_storage_output"
    ),
    "result_total_system_costs": ContractRegistryItem(
        contract_file="result_total_system_costs"
    ),
}
