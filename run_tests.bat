@echo off
REM Batch script to run the full performance test suite
REM Usage: run_tests.bat

echo.
echo ============================================================
echo API Performance Optimization Test Suite
echo ============================================================
echo.

setlocal enabledelayedexpansion

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not available in PATH
    exit /b 1
)

REM Install dependencies if needed
echo [1] Checking dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)
echo [OK] Dependencies installed

REM Seed database
echo.
echo [2] Seeding database...
python seed_db.py
if errorlevel 1 (
    echo [ERROR] Database seeding failed
    exit /b 1
)

REM Run performance tests
echo.
echo [3] Running performance tests...
python runner.py
if errorlevel 1 (
    echo [ERROR] Performance tests failed
    exit /b 1
)

echo.
echo ============================================================
echo All tests completed successfully!
echo Results saved to: results.json
echo Review: REVIEW_SUMMARY.md
echo Documentation: README.md
echo ============================================================
