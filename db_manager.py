import sqlite3
from tabulate import tabulate
from werkzeug.security import generate_password_hash

# Database connection
def get_db():
    conn = sqlite3.connect('data/inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==================== CRUD OPERATIONS ====================

def get_all_tables():
    """Get list of all tables in the database"""
    conn = get_db()
    tables = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """).fetchall()
    conn.close()
    return [table['name'] for table in tables]

def get_table_columns(table_name):
    """Get column names for a table"""
    conn = get_db()
    cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 1")
    columns = [description[0] for description in cursor.description]
    conn.close()
    return columns

def get_all_records(table_name):
    """Read all records from a table"""
    conn = get_db()
    records = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    conn.close()
    return records

def create_record(table_name, data):
    """Create a new record in the specified table"""
    conn = get_db()
    cursor = conn.cursor()
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?'] * len(data))
    
    # Handle password hashing for users table
    if table_name == 'users' and 'password' in data:
        data['password'] = generate_password_hash(data['password'])
    
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    cursor.execute(query, tuple(data.values()))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id

def update_record(table_name, record_id, data):
    """Update an existing record"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Handle password hashing for users table
    if table_name == 'users' and 'password' in data:
        data['password'] = generate_password_hash(data['password'])
    
    set_clause = ', '.join([f"{key} = ?" for key in data])
    query = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
    values = list(data.values()) + [record_id]
    
    cursor.execute(query, tuple(values))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected

def delete_record(table_name, record_id):
    """Delete a record from the table"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (record_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected

# ==================== USER INTERFACE ====================

def display_table(table_name):
    """Display all records from a table"""
    columns = get_table_columns(table_name)
    records = get_all_records(table_name)
    
    if not records:
        print(f"\nNo records found in {table_name}")
        return
    
    # Convert Row objects to dictionaries
    records = [dict(record) for record in records]
    
    print(f"\n=== {table_name.upper()} ===")
    print(tabulate(records, headers="keys", tablefmt="grid"))

def get_user_input(columns):
    """Get user input for creating/updating records"""
    data = {}
    for column in columns:
        if column == 'id':
            continue  # Skip ID as it's auto-incremented
            
        value = input(f"Enter {column}: ")
        
        # Convert empty strings to None for database NULL
        if value.strip() == '':
            value = None
        elif column in ['price', 'weight', 'length', 'width', 'height']:
            try:
                value = float(value)
            except ValueError:
                value = None
        elif column in ['stock_quantity', 'quantity']:
            try:
                value = int(value)
            except ValueError:
                value = None
        elif column in ['featured', 'customizable', 'is_admin']:
            value = value.lower() in ['true', 'yes', '1', 'y']
            
        data[column] = value
    return data

def main_menu():
    """Main menu interface"""
    while True:
        print("\n=== IGL CLONE DATABASE MANAGER ===")
        tables = get_all_tables()
        
        # Display tables
        for i, table in enumerate(tables, 1):
            print(f"{i}. {table}")
        print("0. Exit")
        
        try:
            choice = int(input("\nSelect a table to manage (0 to exit): "))
            if choice == 0:
                break
            selected_table = tables[choice-1]
            table_menu(selected_table)
        except (ValueError, IndexError):
            print("Invalid selection. Please try again.")

def table_menu(table_name):
    """CRUD operations for a specific table"""
    while True:
        print(f"\n=== {table_name.upper()} MANAGEMENT ===")
        print("1. List all records")
        print("2. Add new record")
        print("3. Update record")
        print("4. Delete record")
        print("5. Back to main menu")
        
        try:
            choice = int(input("\nSelect operation: "))
            
            if choice == 1:
                display_table(table_name)
            elif choice == 2:
                columns = get_table_columns(table_name)
                print(f"\nCreating new {table_name} record:")
                data = get_user_input(columns)
                record_id = create_record(table_name, data)
                print(f"Record created with ID: {record_id}")
            elif choice == 3:
                display_table(table_name)
                record_id = input("\nEnter ID of record to update: ")
                columns = get_table_columns(table_name)
                print(f"\nUpdating {table_name} record (leave blank to keep current value):")
                data = get_user_input(columns)
                affected = update_record(table_name, record_id, data)
                print(f"{affected} record(s) updated")
            elif choice == 4:
                display_table(table_name)
                record_id = input("\nEnter ID of record to delete: ")
                confirm = input(f"Are you sure you want to delete record {record_id}? (y/n): ")
                if confirm.lower() == 'y':
                    affected = delete_record(table_name, record_id)
                    print(f"{affected} record(s) deleted")
            elif choice == 5:
                break
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

if __name__ == "__main__":
    # Install tabulate if not already installed
    try:
        from tabulate import tabulate
    except ImportError:
        import subprocess
        subprocess.run(['pip', 'install', 'tabulate'])
        from tabulate import tabulate
    
    print("Welcome to IGL Clone Database Manager")
    main_menu()