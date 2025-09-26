import glob
import os
import re  # For regex-based date extraction

import pandas as pd

# --- DEFINITIVE DATA DICTIONARY (Updated for Long Format and Simplification) ---
DATA_DICTIONARY = {
    'Report_Date': {
        'Description': 'The month and year the Hiring_Rate applies to, converted from the column headers.',
        'Data Type': 'datetime64[ns]',
        'Units/Format': 'YYYY-MM-DD (Standardized to the 1st of the month)',
        'Notes': 'Primary time dimension created by melting the wide-format CSVs.'
    },
    'Industry': {
        'Description': 'The broad industry classification.',
        'Data Type': 'category',
        'Units/Format': 'E.g., "Financial", "Technology"',
        'Notes': 'Matches the primary grouping column in the original CSV.'
    },
    'Hiring_Rate': {
        'Description': 'The raw LinkedIn Hiring Rate index value for the given month and industry.',
        'Data Type': 'float64',
        'Units/Format': 'Index Value (e.g., 0.95)',
        'Notes': 'Used to calculate MoM and YoY changes.'
    },
    'MoM_Change_Percent': {
        'Description': 'Percentage change in the Hiring Rate compared to the previous month.',
        'Data Type': 'float64',
        'Units/Format': 'Percentage (e.g., -10.2 for -10.2% change)',
        'Notes': 'Extracted from the "MoM % Ch" column.'
    },
    'YoY_Change_Percent': {
        'Description': 'Percentage change in the Hiring Rate compared to the same month in the previous year.',
        'Data Type': 'float64',
        'Units/Format': 'Percentage (e.g., -7.8 for -7.8% change)',
        'Notes': 'Extracted from the "YoY % Ch" column.'
    },
    'Report_Country': {
        'Description': 'The country the workforce data refers to (Hardcoded to United States).',
        'Data Type': 'category',
        'Units/Format': 'United States',
        'Notes': 'Hardcoded value based on user instruction.'
    },
    'Original_File_Name': {
        'Description': 'The name of the original CSV file this row of data came from.',
        'Data Type': 'string',
        'Units/Format': 'E.g., "April 2025.csv"',
        'Notes': 'Highly recommended for audit trail.'
    }
    # Report_Region is removed as requested
}

def compile_and_normalize_workforce_reports(folder_path):
    """
    Reads, compiles, and normalizes (melts) wide-format LinkedIn Workforce CSVs.
    """
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    compiled_data_list = []

    if not all_files:
        print(f"ERROR: No CSV files found in the path: {folder_path}")
        return pd.DataFrame()

    # 1. Compilation Loop
    for filename in all_files:
        base_name = os.path.basename(filename)
        print(f"Processing {base_name}...")

        # --- SIMPLIFIED METADATA EXTRACTION ---
        country = 'United States' # Hardcoded as requested
        # Region inference removed as requested
        # --------------------------------------

        df_raw = pd.read_csv(filename)
        
        # 2. STANDARDIZED COLUMN CLEANUP AND RENAMING (Fixed)
        
        # a) Clean column names: remove spaces, slashes, percent signs, and hyphens from all headers.
        df_raw.columns = (
            df_raw.columns.str.strip()
            .str.replace(r'[\s/%\-]', '', regex=True) 
        )
        
        print(f"--- DEBUG: Columns after Cleaning: {df_raw.columns.tolist()} ---")

        # b) Explicitly rename the fixed metric columns to the desired clean names. (Fixed)
        df_raw = df_raw.rename(columns={
            # Using the exact observed names from the last successful debug run
            'MoMChange': 'MoM_Change_Percent', 
            'YoYChange': 'YoY_Change_Percent'
        }, errors='raise') 
        
        # Identify the date columns using a regex pattern (e.g., 'Mar24') (Fixed)
        date_cols = [
            col for col in df_raw.columns 
            if re.match(r'^[A-Za-z]{3}\d{2}$', col) and col != '···'
        ]
        
        print(f"--- DEBUG: Date Columns Found: {date_cols} ---")
        
        # 3. Add file metadata columns
        df_raw['Report_Country'] = country
        # df_raw['Report_Region'] removed
        df_raw['Original_File_Name'] = base_name

        # 4. Normalize (Melt) the Data to Long Format
        # CRITICAL: id_vars updated to exclude 'Report_Region'
        id_vars = ['Industry', 'MoM_Change_Percent', 'YoY_Change_Percent', 
                   'Report_Country', 'Original_File_Name']
        
        df_long = pd.melt(
            df_raw,
            id_vars=id_vars,
            value_vars=date_cols,
            var_name='Report_Date_Raw',
            value_name='Hiring_Rate'
        )

        # 5. Convert the date format ('Mar24') to a proper datetime object (Fixed)
        def parse_workforce_date(date_str):
            # Use format='%b%y' to parse 'Mar24' directly as Month-Year (2024-03-01)
            return pd.to_datetime(date_str, format='%b%y', errors='coerce')
        
        df_long['Report_Date'] = df_long['Report_Date_Raw'].apply(parse_workforce_date)
        df_long = df_long.drop(columns=['Report_Date_Raw'])

        compiled_data_list.append(df_long)

    # 6. Concatenate all DataFrames
    final_df = pd.concat(compiled_data_list, ignore_index=True)
    
    # 7. Enforce Final Data Types for efficiency
    type_map = {k: v['Data Type'] for k, v in DATA_DICTIONARY.items() if k in final_df.columns}
    final_df = final_df.astype(type_map)

    # 8. Attach the Data Dictionary (Metadata)
    final_df.attrs['data_dictionary'] = DATA_DICTIONARY
    
    return final_df

# --- EXECUTION BLOCK ---

def main():
    """
    Main execution function. This is where you define the path 
    and call the primary compilation function.
    """
    
    # This path is based on your previous trace output:
    data_folder_path = r'C:\Users\ibwan\SwYtch-Team-Monkey\Workforce Report'
    
    print(f"--- STARTING COMPILATION FROM: {data_folder_path} ---")
    
    # Call the main function
    final_compiled_df = compile_and_normalize_workforce_reports(data_folder_path)
    
    # Print final verification/debugging output
    if final_compiled_df is None or final_compiled_df.empty:
        print("\n!!! FINAL RESULT: The resulting DataFrame is empty. Check path and file contents. !!!")
    else:
        print("\n--- SUCCESS: Data compilation complete! ---")
        print(f"Final DataFrame Shape: {final_compiled_df.shape}")
        print("\nFirst 50 Rows of Compiled Data (Long Format):")
        print(final_compiled_df.head(100))
        
        # Save the result to a new file in the script's directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, 'compiled_workforce_report.csv')
        final_compiled_df.to_csv(output_path, index=False)
        print(f"\nData successfully saved to: {output_path}")


# This standard Python entry point ensures the main() function runs only 
# when you execute this file directly
if __name__ == "__main__":
    main()
    