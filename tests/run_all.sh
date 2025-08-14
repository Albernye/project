#!/bin/bash
# Enhanced test runner script

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test tracking
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Function to print test suite results
print_suite_result() {
    local suite_name="$1"
    local result="$2"
    local details="$3"

    TOTAL_SUITES=$((TOTAL_SUITES + 1))

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $suite_name"
        PASSED_SUITES=$((PASSED_SUITES + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: $suite_name"
        if [ -n "$details" ]; then
            echo -e "${RED}  Details: $details${NC}"
        fi
        FAILED_SUITES=$((FAILED_SUITES + 1))
    fi
}

# Function to check if Flask server is running
check_server() {
    local base_url="${BASE_URL:-http://localhost:5000}"
    if curl -s -f "$base_url/" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Flask server is running at $base_url"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Flask server not running - API tests will be skipped"
        return 1
    fi
}

# Function to run Python unit tests
run_python_tests() {
    print_section "Python Unit Tests"

    cd "$PROJECT_ROOT"

    # Ensure we have the test dependencies
    echo -e "${YELLOW}Ensuring test dependencies are installed...${NC}"
    uv sync

    # Run tests using pytest, capturing the exit status
    echo -e "${YELLOW}Running Python unit tests...${NC}"
    PYTHONPATH=. pytest "$TESTS_DIR"
    local status=$?

    # Check the exit status to determine if tests passed or failed
    if [ $status -eq 0 ]; then
        print_suite_result "Python Unit Tests" "PASS" ""
    else
        print_suite_result "Python Unit Tests" "FAIL" "Some tests failed."
    fi

    return $status
}

# Main test runner
main() {
    # Run Python unit tests
    run_python_tests

    # Check server status
    check_server

    # Run all API route tests
    print_section "API Route Tests"
    for f in "$TESTS_DIR"/api_test_*.sh; do
        echo -e "${YELLOW}Running $f ...${NC}"
        bash "$f"
    done

    # Print summary
    print_section "Test Summary"
    echo -e "${BLUE}Total test suites: $TOTAL_SUITES${NC}"
    echo -e "${GREEN}Passed: $PASSED_SUITES${NC}"
    echo -e "${RED}Failed: $FAILED_SUITES${NC}"

    # Exit with non-zero status if any test suite failed
    if [ $FAILED_SUITES -gt 0 ]; then
        exit 1
    fi
}

# Execute main function
main
