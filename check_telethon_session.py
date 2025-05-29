#!/usr/bin/env python3
"""
Telethon Session Diagnostic Tool | VX Edition

This script checks a Telethon session file and displays its structure
to help diagnose issues with session conversion.
"""

import os
import sys
import sqlite3
import base64
import struct
from pathlib import Path

def check_telethon_session(session_path):
    """Check a Telethon session file and display its structure"""
    print(f"Checking Telethon session: {session_path}")
    
    # Ensure file exists
    if not os.path.exists(session_path):
        print(f"Error: Session file not found: {session_path}")
        return False
        
    try:
        # Connect to the SQLite database
        with sqlite3.connect(session_path) as conn:
            cursor = conn.cursor()
            
            # Check if sessions table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall()]
            
            print(f"Found tables: {tables}")
            
            if 'sessions' not in tables:
                print("Error: No 'sessions' table found in this database")
                return False
                
            # Get column information
            cursor.execute("PRAGMA table_info(sessions)")
            columns = cursor.fetchall()
            
            print("\nTable structure for 'sessions':")
            for col in columns:
                print(f"  {col[0]}: {col[1]} ({col[2]})")
                
            # Get session data
            cursor.execute("SELECT * FROM sessions")
            session_data = cursor.fetchone()
            
            if not session_data:
                print("\nNo session data found in the 'sessions' table")
                return False
                
            print("\nSession data:")
            for i, col in enumerate(columns):
                # Don't print auth_key directly as it's binary data
                if col[1] == 'auth_key':
                    print(f"  {col[1]}: <binary data> (length: {len(session_data[i]) if session_data[i] else 0} bytes)")
                else:
                    print(f"  {col[1]}: {session_data[i]}")
                    
            # Check DC ID specifically
            dc_id_index = None
            for i, col in enumerate(columns):
                if col[1] == 'dc_id':
                    dc_id_index = i
                    break
                    
            if dc_id_index is not None:
                dc_id = session_data[dc_id_index]
                print(f"\nDC ID found: {dc_id} (type: {type(dc_id).__name__})")
                
                if not isinstance(dc_id, int) or dc_id < 1 or dc_id > 5:
                    print(f"Warning: DC ID {dc_id} is invalid. Must be an integer between 1 and 5.")
                else:
                    print("DC ID is valid.")
            else:
                print("\nWarning: No 'dc_id' column found in the 'sessions' table")
                
            # Check server_address specifically
            server_index = None
            for i, col in enumerate(columns):
                if col[1] == 'server_address':
                    server_index = i
                    break
                    
            if server_index is not None:
                server = session_data[server_index]
                print(f"\nServer address found: {server}")
            else:
                print("\nWarning: No 'server_address' column found in the 'sessions' table")
                
            # Check auth_key specifically
            auth_key_index = None
            for i, col in enumerate(columns):
                if col[1] == 'auth_key':
                    auth_key_index = i
                    break
                    
            if auth_key_index is not None:
                auth_key = session_data[auth_key_index]
                print(f"\nAuth key found: {type(auth_key).__name__}, length: {len(auth_key) if auth_key else 0} bytes")
                
                if not auth_key:
                    print("Warning: Auth key is empty or null")
            else:
                print("\nWarning: No 'auth_key' column found in the 'sessions' table")
                
            return True
                
    except Exception as e:
        print(f"Error checking session file: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("\n=========================================")
    print("   Telethon Session Checker | VX Edition")
    print("=========================================\n")
    
    if len(sys.argv) < 2:
        print("Usage: python check_telethon_session.py <path_to_session_file>")
        return 1
        
    session_path = sys.argv[1]
    
    # Add .session extension if not present
    if not session_path.endswith('.session'):
        session_path = f"{session_path}.session"
        
    check_telethon_session(session_path)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 