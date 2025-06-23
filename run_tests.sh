#!/bin/bash

# Activate virtual environment and run tests with proper PYTHONPATH
source .venv/bin/activate
export PYTHONPATH=.

echo "Running comprehensive test suite for updall..."
echo "=============================================="

# Run tests with coverage
python -m pytest tests/ -v --cov=. --cov-report=term-missing --tb=short

echo ""
echo "Test execution completed."
echo ""
echo "To run specific test files:"
echo "  PYTHONPATH=. python -m pytest tests/test_config.py -v"
echo "  PYTHONPATH=. python -m pytest tests/test_systems.py -v"
echo "  PYTHONPATH=. python -m pytest tests/test_error_handler.py -v"
echo ""
echo "To run tests with coverage:"
echo "  PYTHONPATH=. python -m pytest tests/ --cov=. --cov-report=html"