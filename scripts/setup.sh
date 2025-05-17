#!/bin/bash
# Velocitytree Setup Script
# Automatically creates virtual environment and installs dependencies

set -e  # Exit on error

echo "🌳 Velocitytree Setup Script"
echo "=========================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
    echo "❌ Error: Python 3.8 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Velocitytree in development mode
echo "🌳 Installing Velocitytree..."
pip install -e .

# Install development dependencies if requested
if [ "$1" == "--dev" ]; then
    echo "🛠️  Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To get started with Velocitytree, run:"
echo "  vtree --help"
echo ""