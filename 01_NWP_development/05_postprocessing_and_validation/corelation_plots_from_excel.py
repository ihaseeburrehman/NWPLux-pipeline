import pandas as pd
import matplotlib.pyplot as plt
import os

# Path to the updated Excel file
file_path_updated = '/Users/haseeb.rehman/Desktop/parameters_comparison_with_and_without_ZTD_July2021_event.xlsx'

# Function to process data and calculate correlations
def process_and_correlate(data, sheet_name):
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

    # Calculate correlations
    observed_values = data.iloc[:, 1]
    predicted_0000hr_columns = data.columns[2:5]  # Corrected based on your input
    predicted_0600hr_columns = data.columns[5:9]  # Corrected based on your input

    correlation_results_0000hr = {col: observed_values.corr(data[col]) for col in predicted_0000hr_columns}
    correlation_results_0600hr = {col: observed_values.corr(data[col]) for col in predicted_0600hr_columns}

    return correlation_results_0000hr, correlation_results_0600hr


# Function to create and save scatter plots with note
def create_and_save_scatter_plot(correlation_results_0000hr, correlation_results_0600hr, title, graph_name, note):
    correlation_values_0000hr = list(correlation_results_0000hr.values())
    correlation_values_0600hr = list(correlation_results_0600hr.values())
    models = [x.replace(' (GFS + ZTD+ Radiosonde)', '').replace(' (ds083.2 + ZTD + Radiosonde)', '') for x in correlation_results_0600hr.keys()]

    # Remove trailing "1" from labels
    models = [model.rstrip("1") for model in models]

    plt.figure(figsize=(10, 8))
    plt.scatter(models, correlation_values_0000hr, color='blue', marker="x" , label='0000hr Predictions')
    plt.scatter(models, correlation_values_0600hr, color='red', marker="x", label='0600hr Predictions')
    plt.axhline(y=1, color='green', linestyle='-', label='Observed (Correlation = 1)')
    plt.title(title)
    plt.xlabel('Prediction Models')
    plt.ylabel('Correlation Coefficient')
    plt.xticks(rotation=0)
    plt.ylim(-1, 1.1)
    
    # Adjusted position and size of the note
    plt.text(0.01, -0.25, note, transform=plt.gca().transAxes, fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.5))
    
    plt.legend()
    plt.grid(True)

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

# Calculating correlations for each parameter
# Calculate correlations for each parameter, passing the DataFrame and the sheet name as arguments
corr_precip_0000hr, corr_precip_0600hr = process_and_correlate(data_precip, 'precip')
corr_rh_0000hr, corr_rh_0600hr = process_and_correlate(data_rh, 'RH')
corr_t2_0000hr, corr_t2_0600hr = process_and_correlate(data_t2, 'T2')


# Note to be added to the charts
note = "Data Assimilation (DA)\n1=(GFS + SYNOP + TEMP + TAMDAR )\n2=(GFS + SYNOP + TEMP + TAMDAR + ZTD)\nwhere\nSYNOP = Surface Synoptic Observations\nTEMP = Upper Air Data, Radiosondes\nTAMDAR = Tropospheric Airborne Meteorological Data Reporting\nZTD = Zenith Total Delay"

# Creating and saving scatter plots for each parameter with the note
create_and_save_scatter_plot(corr_precip_0000hr, corr_precip_0600hr, 'Correlation of Predictions with Observed Precipitation - 24 hr Accumulation', 'Precipitation_Correlation', note)
create_and_save_scatter_plot(corr_rh_0000hr, corr_rh_0600hr, 'Correlation of Predictions with Observed Relative Humidity', 'Relative_Humidity_Correlation', note)
create_and_save_scatter_plot(corr_t2_0000hr, corr_t2_0600hr, 'Correlation of Predictions with Observed Temperature (T2)', 'Temperature_Correlation', note)


