import pandas as pd
import numpy as np

# === Step 1: Load the raw data without headers ===
input_file = '/home/ahmed/Downloads/Smart_Air_Quality_Monitor_data.csv'  # Change to your raw data file
df = pd.read_csv(input_file, header=None)

# === Step 2: Manually assign column names ===
df.columns = ['Timestamp(ms)', 'MQ2_Raw', 'MQ7_Raw', 'Temperature(°C)', 'Humidity(%)']

# === Step 3: Convert Timestamp to seconds (Time in seconds) ===
df['Time(s)'] = df['Timestamp(ms)'] / 1000.0

# === Step 4: Convert raw sensor values to approximate ppm ===
# These conversions are estimated and depend on your hardware's calibration
# Replace these formulas with real calibration data if available

# Basic conversion logic using a linear approximation (example only)
df['MQ2(ppm)'] = df['MQ2_Raw'].apply(lambda x: (x - 100) * 0.5 if x > 100 else 0)
df['MQ7(ppm)'] = df['MQ7_Raw'].apply(lambda x: (x - 100) * 0.6 if x > 100 else 0)

# === Step 5: Optional classification (e.g., Fire Alert) ===
df['Fire_Alert'] = ((df['MQ2(ppm)'] > 300) | (df['MQ7(ppm)'] > 250)).astype(int)

# === Step 6: Select and order final columns ===
df_final = df[[
    'Timestamp(ms)', 'Time(s)',
    'MQ2(ppm)', 'MQ7(ppm)',
    'Temperature(°C)', 'Humidity(%)',
    'Fire_Alert'
]]

# === Step 7: Save to new CSV ===
output_file = 'converted_sensor_data.csv'
df_final.to_csv(output_file, index=False)

print(f"✅ Data converted and saved to '{output_file}'")
