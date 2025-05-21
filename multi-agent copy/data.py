import sqlite3
import csv
import os

def export_db_to_csv(db_path, output_dir="db_exports"):
    """
    Export all tables from a SQLite database to CSV files.
    
    Args:
        db_path: Path to the SQLite database file
        output_dir: Directory to store the CSV files
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get a list of all tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"Found {len(tables)} tables in the database.")
    
    # Export each table to a CSV file
    for table in tables:
        table_name = table[0]
        print(f"Exporting table: {table_name}")
        
        # Get all data from the table
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Write to CSV
        output_file = os.path.join(output_dir, f"{table_name}.csv")
        with open(output_file, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            
            # Write header
            csv_writer.writerow(columns)
            
            # Write data
            csv_writer.writerows(rows)
        
        print(f"Exported {len(rows)} rows to {output_file}")
    
    # Close the connection
    conn.close()
    print("Export completed successfully!")

# Path to your database file
db_path = "/Users/dmondal/Documents/new-adk/my-project/multi-agent copy/code_pipeline.db"

# Export the database to CSV
export_db_to_csv(db_path)