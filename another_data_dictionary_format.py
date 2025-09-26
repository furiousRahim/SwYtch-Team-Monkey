import glob
import os
import re
import numpy as np # Needed for some aggregation functions like std

import pandas as pd

# --- DEFINITIVE DATA DICTIONARY (FOR AGGREGATED OUTPUT) ---
AGGREGATED_DICTIONARY = {
    'Industry': {
        'Description': 'The broad industry classification.',
        'Data Type': 'category',
        'Units/Format': 'E.g., "Financial", "Technology"',
        'Notes': 'The primary grouping column.'
    },
    'Hiring_Rate_Mean': {
        'Description': 'The average LinkedIn Hiring Rate Index across all months/files for this industry.',
        'Data Type': 'float64',
        'Units/Format': 'Index Value (Mean)',
        'Notes': 'Aggregated from the Hiring_Rate column.'
    },
    'Hiring_Rate_StdDev': {
        'Description': 'The standard deviation of the LinkedIn Hiring Rate Index across all months/files for this industry.',
        'Data Type': 'float64',
        'Units/Format': 'Index Value (Standard Deviation)',
        'Notes': 'Measures the variability of the rate.'
    },
    'MoM_Change_Percent_Mean': {
        'Description': 'The average Month-over-Month Percentage Change across all months/files for this industry.',
        'Data Type': 'float64',
        'Units/Format': 'Percentage (Mean)',
        'Notes': 'Aggregated from the MoM_Change_Percent column.'
    },
    'YoY_Change_Percent_Mean': {
        'Description': 'The average Year-over-Year Percentage Change across all months/files for this industry.',
        'Data Type': 'float64',
        'Units/Format': 'Percentage (Mean)',
        'Notes': 'Aggregated from the YoY_Change_Percent column.'
    },
    'Total_Observations': {
        'Description': 'The total number of monthly data points compiled for this industry.',
        'Data Type': 'int64',
        'Units/Format': 'Count',
        'Notes': 'Used to assess the reliability of the mean.'
    }
}

# The original dictionary is still used for the intermediate step, but we only use
# the aggregation one for the final output formatting.

def compile_and_normalize_workforce_reports(folder_path):
    """
    Reads, compiles, normalizes (melts), and then summarizes by Industry.
    """
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    compiled_data_list = []

    if not all_files:
        print(f"ERROR: No CSV files found in the path: {folder_path}")
        return pd.DataFrame()

    # 1. Compilation Loop (No changes here from previous successful run)
    for filename in all_files:
        base_name = os.path.basename(filename)
        print(f"Processing {base_name}...")

        # --- SIMPLIFIED METADATA EXTRACTION ---
        country = 'United States'
        df_raw = pd.read_csv(filename)
        
        # 2. STANDARDIZED COLUMN CLEANUP AND RENAMING
        df_raw.columns = (
            df_raw.columns.str.strip()
            .str.replace(r'[\s/%\-]', '', regex=True) 
        )
        print(f"--- DEBUG: Columns after Cleaning: {df_raw.columns.tolist()} ---")

        df_raw = df_raw.rename(columns={
            'MoMChange': 'MoM_Change_Percent', 
            'YoYChange': 'YoY_Change_Percent'
        }, errors='raise') 
        
        # Identify the date columns
        date_cols = [
            col for col in df_raw.columns 
            if re.match(r'^[A-Za-z]{3}\d{2}$', col) and col != '···'
        ]
        
        print(f"--- DEBUG: Date Columns Found: {date_cols} ---")
        
        # 3. Add file metadata columns
        df_raw['Report_Country'] = country
        df_raw['Original_File_Name'] = base_name

        # 4. Normalize (Melt) the Data to Long Format
        id_vars = ['Industry', 'MoM_Change_Percent', 'YoY_Change_Percent', 
                   'Report_Country', 'Original_File_Name']
        
        df_long = pd.melt(
            df_raw,
            id_vars=id_vars,
            value_vars=date_cols,
            var_name='Report_Date_Raw',
            value_name='Hiring_Rate'
        )

        # 5. Convert the date format
        def parse_workforce_date(date_str):
            # Using format='%b%y' to parse 'Mar24' directly
            return pd.to_datetime(date_str, format='%b%y', errors='coerce')
        
        df_long['Report_Date'] = df_long['Report_Date_Raw'].apply(parse_workforce_date)
        df_long = df_long.drop(columns=['Report_Date_Raw'])

        compiled_data_list.append(df_long)

    # 6. Concatenate all DataFrames
    final_df = pd.concat(compiled_data_list, ignore_index=True)

    # 6.5. *** CRITICAL STEP: AGGREGATE BY INDUSTRY ***
    print("\n--- Aggregating data by Industry... ---")
    
    # Define the aggregation operations
    aggregation_rules = {
        'Hiring_Rate': ['mean', 'std', 'count'],
        'MoM_Change_Percent': ['mean'],
        'YoY_Change_Percent': ['mean']
    }
    
    # Group by Industry and apply the aggregations
    df_grouped = final_df.groupby('Industry', as_index=False).agg(
        aggregation_rules
    )

    # Clean up the resulting column names (MultiIndex)
    df_grouped.columns = [
        '_'.join(col).strip('_') if col[1] else col[0]
        for col in df_grouped.columns.values
    ]
    
    # Rename columns to match the AGGREGATED_DICTIONARY
    df_grouped = df_grouped.rename(columns={
        'Hiring_Rate_mean': 'Hiring_Rate_Mean',
        'Hiring_Rate_std': 'Hiring_Rate_StdDev',
        'Hiring_Rate_count': 'Total_Observations',
        'MoM_Change_Percent_mean': 'MoM_Change_Percent_Mean',
        'YoY_Change_Percent_mean': 'YoY_Change_Percent_Mean'
    })

    # 7. Enforce Final Data Types for efficiency
    type_map = {k: v['Data Type'] for k, v in AGGREGATED_DICTIONARY.items() if k in df_grouped.columns}
    final_aggregated_df = df_grouped.astype(type_map)

    # 8. Attach the Data Dictionary (Metadata)
    final_aggregated_df.attrs['data_dictionary'] = AGGREGATED_DICTIONARY
    
    return final_aggregated_df

# --- EXECUTION BLOCK ---

def main():
    """
    Main execution function.
    """
    
    # This path is based on your previous trace output:
    data_folder_path = r'C:\Users\ibwan\SwYtch-Team-Monkey\Workforce Report'
    
    print(f"--- STARTING COMPILATION AND AGGREGATION FROM: {data_folder_path} ---")
    
    # Call the main function
    final_compiled_df = compile_and_normalize_workforce_reports(data_folder_path)
    
    # Print final verification/debugging output
    if final_compiled_df is None or final_compiled_df.empty:
        print("\n!!! FINAL RESULT: The resulting DataFrame is empty. Check path and file contents. !!!")
    else:
        print("\n--- SUCCESS: Data compilation and aggregation complete! ---")
        print(f"Final Aggregated DataFrame Shape: {final_compiled_df.shape}")
        
        # Print the first 10 rows of the final, aggregated data
        print("\nFirst 10 Rows of Final Aggregated Data (Summarized by Industry):")
        # Ensure we print the columns nicely since they are now the aggregate metrics
        pd.set_option('display.max_columns', None)
        print(final_compiled_df.head(10))
        
        # Save the result to a new file, reflecting it is summarized
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, 'compiled_workforce_report_SUMMARY.csv')
        final_compiled_df.to_csv(output_path, index=False)
        print(f"\nData successfully saved to: {output_path}")


if __name__ == "__main__":
    main()