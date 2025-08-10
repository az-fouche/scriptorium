#!/usr/bin/env python3
"""
Test script for autocomplete functionality
"""

import os
import sys
import requests
import json

# Add the webapp directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webapp'))

def test_database():
    """Test if the database has books"""
    try:
        response = requests.get('http://localhost:5000/api/test-database')
        if response.status_code == 200:
            data = response.json()
            print(f"Database test: {data}")
            return data.get('database_working', False)
        else:
            print(f"Database test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error testing database: {e}")
        return False

def test_autocomplete(query):
    """Test autocomplete with a specific query"""
    try:
        response = requests.get(f'http://localhost:5000/api/autocomplete?q={query}')
        if response.status_code == 200:
            suggestions = response.json()
            print(f"Autocomplete for '{query}': {suggestions}")
            return suggestions
        else:
            print(f"Autocomplete failed: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error testing autocomplete: {e}")
        return []

def main():
    """Main test function"""
    print("Testing autocomplete functionality...")
    
    # Test database
    print("\n1. Testing database...")
    db_working = test_database()
    
    if not db_working:
        print("Database is not working. Please check if the server is running and the database exists.")
        return
    
    # Test autocomplete with various queries
    print("\n2. Testing autocomplete...")
    test_queries = ['a', 'ab', 'test', 'book', 'author']
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        suggestions = test_autocomplete(query)
        print(f"Found {len(suggestions)} suggestions")

if __name__ == '__main__':
    main()
