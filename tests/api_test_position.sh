#!/bin/bash
# API test for /position endpoint
# tests/api_test_position.sh

set -e  # Exit on any error

# Configuration
BASE_URL="${BASE_URL:-http://localhost:5000}"
POSITION_ENDPOINT="$BASE_URL/position"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

# Function to print test results
print_result() {
    local test_name="$1"
    local result="$2"
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name - $result"
    fi
}

# Function to check if server is running
check_server() {
    echo "Checking if server is running at $BASE_URL..."
    if curl -s -f "$BASE_URL/" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Server is running"
        return 0
    else
        echo -e "${RED}✗${NC} Server is not running at $BASE_URL"
        echo "Please start the Flask server first: python app.py"
        exit 1
    fi
}

# Function to validate JSON response structure
validate_json_structure() {
    local json="$1"
    local expected_fields="$2"
    
    for field in $expected_fields; do
        if ! echo "$json" | jq -e "has(\"$field\")" > /dev/null 2>&1; then
            echo "Missing field: $field"
            return 1
        fi
    done
    return 0
}

# Function to test /position endpoint
test_position_endpoint() {
    local room="$1"
    local test_name="$2"
    local expected_status="$3"
    
    echo -e "\n${YELLOW}Testing${NC}: $test_name"
    echo "Request: GET $POSITION_ENDPOINT?room=$room"
    
    # Make request and capture response
    local response
    local http_status
    
    response=$(curl -s -w "\n%{http_code}" "$POSITION_ENDPOINT?room=$room")
    http_status=$(echo "$response" | tail -n1)
    local json_response=$(echo "$response" | head -n -1)
    
    echo "HTTP Status: $http_status"
    echo "Response: $json_response"
    
    # Check HTTP status code
    if [ "$http_status" != "$expected_status" ]; then
        print_result "$test_name" "Expected HTTP $expected_status, got $http_status"
        return
    fi
    
    # For successful responses, validate JSON structure
    if [ "$http_status" = "200" ]; then
        # Check if response is valid JSON
        if ! echo "$json_response" | jq empty > /dev/null 2>&1; then
            print_result "$test_name" "Invalid JSON response"
            return
        fi
        
        # Validate required fields
        local required_fields="position timestamp sources"
        local validation_error
        validation_error=$(validate_json_structure "$json_response" "$required_fields")
        
        if [ $? -ne 0 ]; then
            print_result "$test_name" "JSON structure validation failed: $validation_error"
            return
        fi
        
        # Validate position array structure
        local position_length
        position_length=$(echo "$json_response" | jq '.position | length')
        
        if [ "$position_length" != "3" ]; then
            print_result "$test_name" "Position array should have 3 elements, got $position_length"
            return
        fi
        
        # Validate position contains numbers
        local position_valid
        position_valid=$(echo "$json_response" | jq '.position | map(type) | map(. == "number") | all')
        
        if [ "$position_valid" != "true" ]; then
            print_result "$test_name" "Position array should contain only numbers"
            return
        fi
        
        # Validate sources structure
        local sources_fields="pdr fingerprint qr_reset"
        local sources_json
        sources_json=$(echo "$json_response" | jq '.sources')
        
        local sources_validation_error
        sources_validation_error=$(validate_json_structure "$sources_json" "$sources_fields")
        
        if [ $? -ne 0 ]; then
            print_result "$test_name" "Sources structure validation failed: $sources_validation_error"
            return
        fi
        
        # Check timestamp format (should be ISO 8601)
        local timestamp
        timestamp=$(echo "$json_response" | jq -r '.timestamp')
        
        if [[ ! "$timestamp" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
            print_result "$test_name" "Invalid timestamp format: $timestamp"
            return
        fi
        
        print_result "$test_name" "PASS"
        
    elif [ "$http_status" = "400" ]; then
        # For error responses, check if error message is present
        if echo "$json_response" | jq -e 'has("error")' > /dev/null 2>&1; then
            print_result "$test_name" "PASS"
        else
            print_result "$test_name" "Error response missing 'error' field"
        fi
        
    elif [ "$http_status" = "500" ]; then
        # For server errors, accept any response (may contain debug info)
        print_result "$test_name" "PASS"
    else
        print_result "$test_name" "Unexpected HTTP status: $http_status"
    fi
}

# Function to setup test data (if needed)
setup_test_data() {
    echo -e "\n${YELLOW}Setting up test data...${NC}"
    
    # Create minimal test QR event if file doesn't exist
    local qr_events_file="../data/qr_events.json"
    if [ ! -f "$qr_events_file" ]; then
        echo "Creating test QR events file..."
        mkdir -p "$(dirname "$qr_events_file")"
        cat > "$qr_events_file" << 'EOF'
[
  {
    "type": "qr",
    "room": "2-01",
    "timestamp": "2024-01-01T10:00:00Z",
    "position": [2.194291, 41.406351]
  }
]
EOF
        echo "Created $qr_events_file"
    fi
}

# Main test execution
main() {
    echo "=== API Test: /position endpoint ==="
    echo "Base URL: $BASE_URL"
    echo "Date: $(date)"
    
    # Check if server is running
    check_server
    
    # Setup test data if needed
    setup_test_data
    
    echo -e "\n${YELLOW}Running position endpoint tests...${NC}"
    
    # Test valid room formats
    test_position_endpoint "201" "Valid room format (3 digits)" "200"
    test_position_endpoint "2-01" "Valid room format (normalized)" "200"
    test_position_endpoint "15" "Valid room format (2 digits)" "200"
    
    # Test invalid requests
    test_position_endpoint "" "Missing room parameter" "400"
    
    # Test with no room parameter at all
    echo -e "\n${YELLOW}Testing${NC}: No room parameter"
    echo "Request: GET $POSITION_ENDPOINT"
    
    local no_room_response
    local no_room_status
    no_room_response=$(curl -s -w "\n%{http_code}" "$POSITION_ENDPOINT")
    no_room_status=$(echo "$no_room_response" | tail -n1)
    
    echo "HTTP Status: $no_room_status"
    echo "Response: $(echo "$no_room_response" | head -n -1)"
    
    if [ "$no_room_status" = "400" ]; then
        print_result "No room parameter" "PASS"
    else
        print_result "No room parameter" "Expected HTTP 400, got $no_room_status"
    fi
    
    # Summary
    echo -e "\n=== Test Summary ==="
    echo "Tests run: $TESTS_RUN"
    echo "Tests passed: $TESTS_PASSED"
    echo "Tests failed: $((TESTS_RUN - TESTS_PASSED))"
    
    if [ $TESTS_PASSED -eq $TESTS_RUN ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed.${NC}"
        exit 1
    fi
}

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error${NC}: jq is required for JSON parsing but not installed"
    echo "Please install jq: sudo apt-get install jq (Ubuntu) or brew install jq (macOS)"
    exit 1
fi

# Run main function
main "$@"