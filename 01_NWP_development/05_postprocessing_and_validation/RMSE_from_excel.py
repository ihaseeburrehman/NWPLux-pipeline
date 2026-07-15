# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import pandas as pd
import matplotlib.pyplot as plt
import os
from sklearn.metrics import mean_squared_error
import numpy as np


# Path to the updated Excel file
file_path_updated = '/Users/haseeb.rehman/Desktop/parameters_comparison_with_and_without_ZTD_July2021_event.xlsx'

def process_and_calculate_rmse(data, sheet_name):
    print(f"Processing sheet: {sheet_name}")
    print(data)

    # Drop columns with all NaN values
    data.dropna(axis=1, how='all', inplace=True)

    # Convert all columns to numeric, coercing errors to NaN
    data = data.apply(pd.to_numeric, errors='coerce')

    # Drop rows with NaN values in the observed or predicted columns
    data.dropna(subset=[data.columns[1], data.columns[2], data.columns[6]], inplace=True)

    # Print the data to check if the columns are correct
    print(data.head())

    observed_values = data.iloc[:, 1]
    predicted_0000hr_columns = data.columns[2:5]  # Corrected based on your input
    predicted_0600hr_columns = data.columns[5:9]  # Corrected based on your input

    rmse_results_0000hr = {col: np.sqrt(mean_squared_error(observed_values, data[col])) for col in predicted_0000hr_columns}
    rmse_results_0600hr = {col: np.sqrt(mean_squared_error(observed_values, data[col])) for col in predicted_0600hr_columns}

    return rmse_results_0000hr, rmse_results_0600hr



def create_and_save_rmse_plot(rmse_results_0000hr, rmse_results_0600hr, title, graph_name):
    rmse_values_0000hr = list(rmse_results_0000hr.values())
    rmse_values_0600hr = list(rmse_results_0600hr.values())
    models = [x.replace(' (GFS + ZTD+ Radiosonde)', '').replace(' (ds083.2 + ZTD + Radiosonde)', '') for x in rmse_results_0600hr.keys()]

    # Remove trailing "1" from labels
    models = [model.rstrip("1") for model in models]

    plt.figure(figsize=(10, 8))
    model_names = list(rmse_results_0000hr.keys())
    plt.scatter(model_names, rmse_results_0000hr.values(), color='blue', marker="x" , label='0000hr Predictions')
    plt.scatter(model_names, rmse_results_0600hr.values(), color='red', marker="x", label='0600hr Predictions')
    plt.title(f'{title}\nRMSE Values (Root Mean Square Error)')
    plt.title(title)
    plt.xlabel('Prediction Models')
    plt.ylabel('RMSE')
    plt.xticks(rotation=0)

    
    plt.legend()
    plt.grid(True)
    
    # Adjusted position and size of the note
    plt.text(0.01, -0.25, note, transform=plt.gca().transAxes, fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.5))
     
    # Adjust the layout
    plt.tight_layout()

    # Saving the plot
    output_folder = '/Users/haseeb.rehman/Desktop/For_Animation/correlation_plots/'
    output_file = os.path.join(output_folder, f"{graph_name}.png")
    plt.savefig(output_file, dpi=400)
    
    # Show and close the plot
    plt.show()
    plt.close()


# Loading data from the separate sheets
data_precip = pd.read_excel(file_path_updated, sheet_name='precip', header=4)
data_rh = pd.read_excel(file_path_updated, sheet_name='RH', header=4)
data_t2 = pd.read_excel(file_path_updated, sheet_name='T2', header=4)

# Calculate RMSE for each parameter
rmse_precip_0000hr, rmse_precip_0600hr = process_and_calculate_rmse(data_precip, 'precip')
rmse_rh_0000hr, rmse_rh_0600hr = process_and_calculate_rmse(data_rh, 'RH')
rmse_t2_0000hr, rmse_t2_0600hr = process_and_calculate_rmse(data_t2, 'T2')

# Note to be added to the charts
note = "Data Assimilation (DA)\n1=(GFS + SYNOP + TEMP + TAMDAR )\n2=(GFS + SYNOP + TEMP + TAMDAR + ZTD)\nwhere\nSYNOP = Surface Synoptic Observations\nTEMP = Upper Air Data, Radiosondes\nTAMDAR = Tropospheric Airborne Meteorological Data Reporting\nZTD = Zenith Total Delay"

# Creating and saving RMSE plots for each parameter
create_and_save_rmse_plot(rmse_precip_0000hr, rmse_precip_0600hr, 'RMSE of Predictions for Precipitation - 24 hr Accumulation', 'Precipitation_RMSE')
create_and_save_rmse_plot(rmse_rh_0000hr, rmse_rh_0600hr, 'RMSE of Predictions for Relative Humidity', 'Relative_Humidity_RMSE')
create_and_save_rmse_plot(rmse_t2_0000hr, rmse_t2_0600hr, 'RMSE of Predictions for Temperature (T2)', 'Temperature_RMSE')


