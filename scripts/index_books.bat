@echo off
REM Library Indexer - Windows Batch Script
REM This script makes it easy to run the library indexer on Windows

echo.
echo ========================================
echo    Library Indexer - Windows Version
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "index_library.py" (
    echo ERROR: index_library.py not found
    echo Please run this script from the library indexer directory
    pause
    exit /b 1
)

REM Check if data directory exists
if not exist "data" (
    echo WARNING: data directory not found
    echo Please create a 'data' directory with your EPUB files
    echo.
)

echo Available commands:
echo.
echo 1. Index books in data directory
echo 2. Show database statistics
echo 3. Search books
echo 4. Export library to JSON
echo 5. Run tests
echo 6. Exit
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto index_books
if "%choice%"=="2" goto show_stats
if "%choice%"=="3" goto search_books
if "%choice%"=="4" goto export_library
if "%choice%"=="5" goto run_tests
if "%choice%"=="6" goto exit_script

echo Invalid choice. Please try again.
pause
goto :eof

:index_books
echo.
echo Indexing books in data directory...
echo.
python index_library.py index data
echo.
pause
goto :eof

:show_stats
echo.
echo Showing database statistics...
echo.
python index_library.py stats
echo.
pause
goto :eof

:search_books
echo.
set /p query="Enter search term: "
echo.
python index_library.py search "%query%"
echo.
pause
goto :eof

:export_library
echo.
set /p filename="Enter export filename (or press Enter for default): "
if "%filename%"=="" (
    python index_library.py export
) else (
    python index_library.py export --output-file "%filename%"
)
echo.
pause
goto :eof

:run_tests
echo.
echo Running tests...
echo.
python test_indexing.py
echo.
pause
goto :eof

:exit_script
echo.
echo Goodbye!
exit /b 0
