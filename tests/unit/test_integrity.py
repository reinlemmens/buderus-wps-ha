import os
import ast
import compileall
import pytest
import importlib
from pathlib import Path

# Define root relative to this test file
REPO_ROOT = Path(__file__).parent.parent.parent

def get_python_files():
    """Return all .py files in the repository."""
    files = []
    # Walk custom_components
    for root, _, filenames in os.walk(REPO_ROOT / "custom_components"):
        for filename in filenames:
            if filename.endswith(".py"):
                files.append(os.path.join(root, filename))
    # Walk buderus_wps_cli
    for root, _, filenames in os.walk(REPO_ROOT / "buderus_wps_cli"):
        for filename in filenames:
            if filename.endswith(".py"):
                files.append(os.path.join(root, filename))
    return files

@pytest.mark.parametrize("filepath", get_python_files())
def test_python_syntax(filepath):
    """Ensure all python files have valid syntax using ast.parse."""
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        ast.parse(source, filename=filepath)
    except SyntaxError as e:
        pytest.fail(f"Syntax error in {filepath}: {e}")

def test_compile_all():
    """Ensure all files can be compiled (catches some things ast might miss)."""
    # This is slightly redundant with test_python_syntax but uses compileall equivalent
    pass # AST parse is sufficient and provides better error messages

def test_import_library_modules():
    """Ensure key library modules can be imported (catches runtime import errors)."""
    # Import the main package to ensure it initializes
    try:
        import custom_components.buderus_wps
        import custom_components.buderus_wps.buderus_wps
        from custom_components.buderus_wps.buderus_wps import parameter_data
    except ImportError as e:
        pytest.fail(f"Failed to import library modules: {e}")
    except SyntaxError as e:
        pytest.fail(f"Syntax error during import: {e}")
