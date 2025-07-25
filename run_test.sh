#!/bin/bash
# run_tests.sh - Test runner script for Content Processor Service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if pytest is installed
check_pytest() {
    if ! command -v pytest &> /dev/null; then
        print_error "pytest is not installed. Install test requirements first:"
        echo "pip install -r requirements-test.txt"
        exit 1
    fi
}

# Function to run basic tests
run_basic_tests() {
    print_header "Running Basic Tests"
    pytest tests/ -v
}

# Function to run tests with coverage
run_coverage_tests() {
    print_header "Running Tests with Coverage"
    pytest tests/ \
        --cov=src \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-fail-under=80 \
        -v
    
    if [ $? -eq 0 ]; then
        print_success "Coverage report generated in htmlcov/index.html"
    fi
}

# Function to run specific test categories
run_unit_tests() {
    print_header "Running Unit Tests Only"
    pytest tests/test_services/ tests/test_utils/ tests/test_models/ -v -m "not integration"
}

run_integration_tests() {
    print_header "Running Integration Tests Only"
    pytest tests/test_api/ -v
}

# Function to run tests in parallel
run_parallel_tests() {
    print_header "Running Tests in Parallel"
    pytest tests/ -v -n auto
}

# Function to run tests with detailed output
run_detailed_tests() {
    print_header "Running Tests with Detailed Output"
    pytest tests/ -v -s --tb=long
}

# Function to run specific test file
run_specific_test() {
    local test_file=$1
    if [ -z "$test_file" ]; then
        print_error "Please specify a test file"
        echo "Usage: $0 specific tests/test_services/test_document_processor.py"
        exit 1
    fi
    
    print_header "Running Specific Test: $test_file"
    pytest "$test_file" -v
}

# Function to run linting and formatting checks
run_quality_checks() {
    print_header "Running Code Quality Checks"
    
    # Check if tools are available
    if command -v black &> /dev/null; then
        echo "🔍 Checking code formatting with black..."
        black --check src/ tests/ || print_warning "Code formatting issues found"
    fi
    
    if command -v flake8 &> /dev/null; then
        echo "🔍 Checking code style with flake8..."
        flake8 src/ tests/ || print_warning "Code style issues found"
    fi
    
    if command -v mypy &> /dev/null; then
        echo "🔍 Checking types with mypy..."
        mypy src/ || print_warning "Type checking issues found"
    fi
}

# Function to show test statistics
show_test_stats() {
    print_header "Test Statistics"
    pytest tests/ --collect-only -q | grep -E "test session starts|collected"
}

# Function to run smoke tests (quick essential tests)
run_smoke_tests() {
    print_header "Running Smoke Tests"
    pytest tests/test_api/test_main.py::TestHealthEndpoint::test_health_check_success \
           tests/test_services/test_document_processor.py::TestDocumentProcessor::test_process_document_creates_complete_document \
           tests/test_utils/test_file_validator.py::TestFileValidator::test_validate_file_success \
           -v
}

# Function to clean test artifacts
clean_test_artifacts() {
    print_header "Cleaning Test Artifacts"
    rm -rf .pytest_cache/
    rm -rf htmlcov/
    rm -rf .coverage
    rm -rf __pycache__/
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    print_success "Test artifacts cleaned"
}

# Function to setup test environment
setup_test_env() {
    print_header "Setting up Test Environment"
    
    # Install test requirements
    if [ -f "requirements-test.txt" ]; then
        pip install -r requirements-test.txt
        print_success "Test requirements installed"
    else
        print_warning "requirements-test.txt not found"
    fi
    
    # Set environment variables for testing
    export PYTHONPATH="${PYTHONPATH}:./src"
    export TESTING=true
    print_success "Test environment configured"
}

# Main script logic
case "${1:-help}" in
    "basic"|"")
        check_pytest
        run_basic_tests
        ;;
    "coverage")
        check_pytest
        run_coverage_tests
        ;;
    "unit")
        check_pytest
        run_unit_tests
        ;;
    "integration")
        check_pytest
        run_integration_tests
        ;;
    "parallel")
        check_pytest
        run_parallel_tests
        ;;
    "detailed")
        check_pytest
        run_detailed_tests
        ;;
    "specific")
        check_pytest
        run_specific_test "$2"
        ;;
    "quality")
        run_quality_checks
        ;;
    "stats")
        check_pytest
        show_test_stats
        ;;
    "smoke")
        check_pytest
        run_smoke_tests
        ;;
    "clean")
        clean_test_artifacts
        ;;
    "setup")
        setup_test_env
        ;;
    "all")
        check_pytest
        run_quality_checks
        run_coverage_tests
        ;;
    "help")
        echo "Content Processor Service - Test Runner"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  basic         Run basic tests (default)"
        echo "  coverage      Run tests with coverage report"
        echo "  unit          Run unit tests only"
        echo "  integration   Run integration tests only"
        echo "  parallel      Run tests in parallel"
        echo "  detailed      Run tests with detailed output"
        echo "  specific FILE Run specific test file"
        echo "  quality       Run code quality checks"
        echo "  stats         Show test statistics"
        echo "  smoke         Run quick smoke tests"
        echo "  clean         Clean test artifacts"
        echo "  setup         Setup test environment"
        echo "  all           Run quality checks and coverage tests"
        echo "  help          Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 basic"
        echo "  $0 coverage"
        echo "  $0 specific tests/test_services/test_document_processor.py"
        echo "  $0 unit"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac