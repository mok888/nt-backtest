#!/bin/bash

################################################################################
# NautilusTrader RSI Strategy - VPS Deployment Script
#
# This script sets up the environment on a Linux VPS for running the RSI
# backtesting strategy.
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# Requirements:
#   - Linux VPS (Ubuntu 20.04+ or similar)
#   - Python 3.12+ or the script will install pyenv
#   - Sudo access (for system packages)
#
################################################################################

set -e  # Exit on any error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Print banner
print_banner() {
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   NautilusTrader RSI Strategy - VPS Deployment Script      ║"
    echo "║   Production-Ready Backtesting & Optimization              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check Python version
check_python_version() {
    print_info "Checking Python version..."

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        print_info "Found Python $PYTHON_VERSION"

        if [ "$PYTHON_MAJOR" -eq "3" ] && [ "$PYTHON_MINOR" -ge "12" ]; then
            print_success "Python 3.12+ detected: $PYTHON_VERSION"
            return 0
        else
            print_warning "Python version $PYTHON_VERSION detected. Recommended: Python 3.12+"
            return 1
        fi
    else
        print_error "Python 3 not found"
        return 1
    fi
}

# Install system dependencies
install_system_dependencies() {
    print_info "Installing system dependencies..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Debian/Ubuntu
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y \
                python3 \
                python3-pip \
                python3-venv \
                git \
                curl \
                wget \
                build-essential \
                libssl-dev \
                libffi-dev \
                python3-dev \
                cmake \
                pkg-config
        # Fedora/RHEL
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y \
                python3 \
                python3-pip \
                git \
                curl \
                wget \
                gcc \
                gcc-c++ \
                make \
                openssl-devel \
                libffi-devel \
                python3-devel \
                cmake \
                pkg-config
        fi
    fi

    print_success "System dependencies installed"
}

# Install uv (fast Python package installer)
install_uv() {
    print_info "Installing uv (fast Python package manager)..."

    if ! command -v uv &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
        print_success "uv installed successfully"
    else
        print_info "uv already installed"
    fi
}

# Create Python virtual environment
create_virtualenv() {
    print_info "Creating Python virtual environment..."

    VENV_DIR="./venv"

    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment already exists at $VENV_DIR"
        read -p "Do you want to remove and recreate it? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing existing virtual environment..."
            rm -rf "$VENV_DIR"
        else
            print_info "Using existing virtual environment"
            return 0
        fi
    fi

    python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created at $VENV_DIR"
}

# Activate virtual environment
activate_virtualenv() {
    print_info "Activating virtual environment..."

    VENV_DIR="./venv"
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found at $VENV_DIR"
        exit 1
    fi

    source "$VENV_DIR/bin/activate"
    print_success "Virtual environment activated"
}

# Upgrade pip
upgrade_pip() {
    print_info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel
    print_success "pip upgraded"
}

# Install NautilusTrader
install_nautilustrader() {
    print_info "Installing NautilusTrader (this may take a few minutes)..."

    uv pip install nautilus_trader

    print_success "NautilusTrader installed"
}

# Install requirements
install_requirements() {
    print_info "Installing project requirements..."

    pip install -r requirements.txt

    print_success "All requirements installed"
}

# Create directory structure
create_directories() {
    print_info "Creating directory structure..."

    mkdir -p data/catalog
    mkdir -p logs
    mkdir -p results
    mkdir -p output

    print_success "Directory structure created"
}

# Download initial data
download_data() {
    print_info "Downloading initial data..."

    python3 data_loader.py

    print_success "Data download complete"
}

# Run quick test
run_quick_test() {
    print_info "Running quick backtest to verify installation..."

    python3 backtest.py

    print_success "Quick test completed"
}

# Print final instructions
print_instructions() {
    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  DEPLOYMENT COMPLETE!${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Your NautilusTrader RSI strategy is now ready to use!"
    echo ""
    echo -e "${YELLOW}Quick Start:${NC}"
    echo ""
    echo "  1. Activate the virtual environment:"
    echo "     source venv/bin/activate"
    echo ""
    echo "  2. Run a single backtest:"
    echo "     python3 backtest.py"
    echo ""
    echo "  3. Run parameter optimization:"
    echo "     python3 optimizer.py"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo ""
    echo "  - Activate environment:  source venv/bin/activate"
    echo "  - Deactivate:         deactivate"
    echo "  - Run backtest:       python3 backtest.py"
    echo "  - Run optimizer:      python3 optimizer.py"
    echo "  - Download data:      python3 data_loader.py"
    echo ""
    echo -e "${YELLOW}Output Files:${NC}"
    echo ""
    echo "  - Results:            results/*.csv"
    echo "  - Equity curve:       results/equity_curve.png"
    echo "  - Summary report:     results/summary_report.txt"
    echo "  - Logs:               logs/*.log"
    echo ""
    echo -e "${YELLOW}Important Notes:${NC}"
    echo ""
    echo "  - Always activate the virtual environment before running scripts"
    echo "  - Data is cached in data/catalog - re-run data_loader.py to refresh"
    echo "  - Optimization can take several hours depending on parameters"
    echo "  - Monitor logs/ directory for detailed output"
    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Main deployment function
main() {
    print_banner

    print_info "Starting deployment..."
    echo ""

    # Check Python version
    check_python_version || install_system_dependencies

    # Install uv
    install_uv

    # Create virtual environment
    create_virtualenv

    # Activate virtual environment
    activate_virtualenv

    # Upgrade pip
    upgrade_pip

    # Install NautilusTrader
    install_nautilustrader

    # Install requirements
    install_requirements

    # Create directories
    create_directories

    # Download initial data
    download_data

    # Run quick test
    run_quick_test

    # Print instructions
    print_instructions
}

# Run main function
main "$@"
