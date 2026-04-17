# Upload result files to CROSSHub

## Prepare the data

The first step in submitting data is preparing your data. The platform has to ways of uploading data: using a file or directly using the python client. The data should include all the compulsory [fields](/data-model/docs/fields)  and the standard naming convention for [variable names](/data-model/docs/variables).


## Upload the data using a CSV or Excel file

Once you have prepared the data, follow these steps:

1. Go to the [upload page](https://app.sweetcross.link/dashboard) 
2. Sign in with your model credentials
3. Upload **one single** Excel or CSV file following the [template](/data-model/docs/upload/files)

{: .warning }
The platform validates the file. It checks column names, variable names, units, etc. If any specifications are not met, the submission will fail and an error will be returned

## Automatic submission with the CROSS Client

!!! warning
This is in experimental stage and subject to changes

[`crossclient`](https://sweet-cross.github.io/crossclient) is Python package developed to directly interact with the CROSS platform. 
It allows for the automatic submission of result files using python and without any manual upload. A more detailed 
description of the process and example code is provided in the [documentation](https://sweet-cross.github.io/crossclient/api/#result-submission). 
The current version allows for automatic upload. In future releases we add the possibility to validate files locally, i.e., before the upload of the results.

## File formats
The platform accepts two file formats: comma-separated values (csv) and Excel (xlsx).

!!! important
You should submit **one single file**. The submitted file must include all category and value columns.

| File type | Sheet                                                                                                                                                | Category columns                                                                                                                                     | Value columns                          | Templates                                                                                                                                                                                                                                                                                                                                      |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| csv       |                                                                                                                                                      | `scenario_group`, `scenario_name`, `scenario_variant`, `variable`, `use_technology_fuel`, `country`, `model`, `unit`, `time_resolution`, `timestamp` | `value`                                | [`cross2025_20260317`](/data-model/files/resultsCross_stacked_2026_03_17.csv)<br>[`cross2025_20251001`](/data-model/files/resultsCross_stacked_2025_10_01.csv)<br>[`nuclear2025_20260317`](/data-model/files/resultsCross_nuclear_stacked_2026_03_17.csv)<br>[`nuclear2025_20251125`](/data-model/files/results_cross_nuclear2025_stacked.csv) |
| excel     | `annual`                                                                                                                                             | `scenario_group`, `scenario_name`, `scenario_variant`, `variable`, `use_technology_fuel`, `country`, `model`, `unit`, `time_resolution`, `timestamp` | One column per year with header `yyyy` | [`cross2025_20260317`](/data-model/files/resultsCross_excel_2026_03_17.xlsx)<br>[`cross2025_20251001`](/data-model/files/resultsCross_excel_2025_10_01.xlsx) <br>[`nuclear2025_20260317`](/data-model/files/results_cross_nuclear2025.xlsx)<br>[`nuclear2025_20251125`](/data-model/files/resultsCross_nuclear_excel_2026_03_17.xlsx)          |
| `hourly`  | `scenario_group`, `scenario_name`, `scenario_variant`, `variable`, `use_technology_fuel`, `country`, `model`, `unit`, `time_resolution`, `timestamp` | One column per typical day with header `dd.MM.yyyy HH:mm`                                                                                            |


## Zero values
Zero values must be explicitly written as `0`.

{: .warning }
Empty cells will return an error during submission

## Variables not in your model
You can exclude all variables that are not part of your model results.

{: .warning }
Empty cells will return an error during submission


## Problems uploading data

If you encounter issues when uploading data, please send an email to [sweet-cross](mailto:sweet.cross.ch[at]gmail.com?subject=technicalproblem) including:
- The file you tried to upload
- A description of the error