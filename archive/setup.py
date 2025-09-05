#!/usr/bin/env python3
"""
Setup script to install dependencies and initialize the bailiffs matching system.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description=""):
    """Run a shell command and handle errors."""
    print(f"Running: {description or command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Success: {description or command}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {description or command}")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def install_dependencies():
    """Install Python dependencies."""
    print("\n📦 Installing Python dependencies...")
    
    # First, ensure we have pip
    if not run_command(f"{sys.executable} -m pip --version", "Checking pip"):
        return False
    
    # Install requirements
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing dependencies"):
        return False
    
    return True

def copy_env_file():
    """Copy .env.example to .env if it doesn't exist."""
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_example.exists() and not env_file.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from .env.example")
        print("⚠️  Please edit .env file with your database credentials")
    else:
        print("ℹ️  .env file already exists")

def test_imports():
    """Test if critical dependencies can be imported."""
    print("\n🧪 Testing critical imports...")
    
    critical_imports = [
        ("pandas", "pandas"),
        ("requests", "requests"),
        ("sqlalchemy", "sqlalchemy"),
        ("rapidfuzz", "rapidfuzz"),
        ("streamlit", "streamlit")
    ]
    
    success = True
    for module_name, import_name in critical_imports:
        try:
            __import__(import_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
            success = False
    
    return success

def show_next_steps():
    """Show next steps after setup."""
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your PostgreSQL credentials")
    print("2. Create PostgreSQL database:")
    print("   psql -U postgres -f sql/01_setup.sql")
    print("3. Test the API connection:")
    print("   python -m src.api.dane_gov_client")
    print("4. Initialize database tables:")
    print("   python scripts/init_database.py")
    print("5. Run the Streamlit app:")
    print("   streamlit run src/ui/main.py")

def main():
    """Main setup function."""
    print("🚀 Setting up Bailiffs Matching System")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Copy environment file
    copy_env_file()
    
    # Test imports
    if not test_imports():
        print("❌ Some imports failed - please check the installation")
        sys.exit(1)
    
    # Show next steps
    show_next_steps()

if __name__ == "__main__":
    main()
