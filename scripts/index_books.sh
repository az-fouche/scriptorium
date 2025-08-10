#!/bin/bash

# Library Indexer - Unix/Linux Shell Script
# This script makes it easy to run the library indexer on Unix/Linux systems

echo
echo "========================================"
echo "   Library Indexer - Unix/Linux Version"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.7+ and try again"
    exit 1
fi

# Check if required files exist
if [ ! -f "index_library.py" ]; then
    echo "ERROR: index_library.py not found"
    echo "Please run this script from the library indexer directory"
    exit 1
fi

# Check if data directory exists
if [ ! -d "data" ]; then
    echo "WARNING: data directory not found"
    echo "Please create a 'data' directory with your EPUB files"
    echo
fi

# Function to show menu
show_menu() {
    echo "Available commands:"
    echo
    echo "1. Index books in data directory"
    echo "2. Show database statistics"
    echo "3. Search books"
    echo "4. Export library to JSON"
    echo "5. Run tests"
    echo "6. Exit"
    echo
}

# Function to index books
index_books() {
    echo
    echo "Indexing books in data directory..."
    echo
    python3 index_library.py index data
    echo
    read -p "Press Enter to continue..."
}

# Function to show stats
show_stats() {
    echo
    echo "Showing database statistics..."
    echo
    python3 index_library.py stats
    echo
    read -p "Press Enter to continue..."
}

# Function to search books
search_books() {
    echo
    read -p "Enter search term: " query
    echo
    python3 index_library.py search "$query"
    echo
    read -p "Press Enter to continue..."
}

# Function to export library
export_library() {
    echo
    read -p "Enter export filename (or press Enter for default): " filename
    if [ -z "$filename" ]; then
        python3 index_library.py export
    else
        python3 index_library.py export --output-file "$filename"
    fi
    echo
    read -p "Press Enter to continue..."
}

# Function to run tests
run_tests() {
    echo
    echo "Running tests..."
    echo
    python3 test_indexing.py
    echo
    read -p "Press Enter to continue..."
}

# Main menu loop
while true; do
    show_menu
    read -p "Enter your choice (1-6): " choice
    
    case $choice in
        1)
            index_books
            ;;
        2)
            show_stats
            ;;
        3)
            search_books
            ;;
        4)
            export_library
            ;;
        5)
            run_tests
            ;;
        6)
            echo
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid choice. Please try again."
            read -p "Press Enter to continue..."
            ;;
    esac
done
