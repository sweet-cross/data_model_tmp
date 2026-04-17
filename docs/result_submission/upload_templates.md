## File formats for upload
The platform accepts two file formats: comma-separated values (csv) and Excel (xlsx).

!!! important
    You should submit **one single file**. The submitted file must include all category and value columns.

| File type | Sheet    | Category columns                                                                                                                                     | Value columns                                             | Templates                                                                                                                                                                                                                                                                                         |
| --------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| csv       |          | `scenario_group`, `scenario_name`, `scenario_variant`, `variable`, `use_technology_fuel`, `country`, `model`, `unit`, `time_resolution`, `timestamp` | `value`                                                   | [`cross2025_20260317`](../templates/resultsCross_stacked_2026_03_17.csv)<br>[`cross2025_20251001`](../templates/resultsCross_stacked_2025_10_01.csv)<br>[`nuclear2025_20260317`](../templates/resultsCross_nuclear_stacked_2026_03_17.csv)<br>[`nuclear2025_20251125`](../templates/results_cross_nuclear2025_stacked.csv) |
| excel     | `annual` | `scenario_group`, `scenario_name`, `scenario_variant`, `variable`, `use_technology_fuel`, `country`, `model`, `unit`, `time_resolution`, `timestamp` | One column per year with header `yyyy`                    | [`cross2025_20260317`](../templates/resultsCross_excel_2026_03_17.xlsx)<br>[`cross2025_20251001`](../templates/resultsCross_excel_2025_10_01.xlsx)<br>[`nuclear2025_20260317`](../templates/results_cross_nuclear2025.xlsx)<br>[`nuclear2025_20251125`](../templates/resultsCross_nuclear_excel_2026_03_17.xlsx) |
| excel     | `hourly` | `scenario_group`, `scenario_name`, `scenario_variant`, `variable`, `use_technology_fuel`, `country`, `model`, `unit`, `time_resolution`, `timestamp` | One column per typical day with header `dd.MM.yyyy HH:mm` |                                                                                                                                                                                                                                                                                                   |


## Zero values
Zero values must be explicitly written as `0`.

!!! warning
    Empty cells will return an error during submission.

## Variables not in your model
You can exclude all variables that are not part of your model results.

!!! warning
    Empty cells will return an error during submission.


## Problems uploading data

If you encounter issues when uploading data, please send an email to [sweet-cross](mailto:sweet.cross.ch[at]gmail.com?subject=technicalproblem) including:
- The file you tried to upload
- A description of the error