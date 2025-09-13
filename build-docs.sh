#!/usr/bin/env bash

# This script builds the Sphinx documentation for a single package generically.
# It dynamically appends a central intersphinx mapping configuration.

set -e # Exit immediately if a command exits with a non-zero status.

BASE_PACKAGE_NAME=$1
VERSION=$2
FULL_PACKAGE_SPEC=$3
DOCS_SOURCE_DIR="./${BASE_PACKAGE_NAME}/docs"
BUILD_OUTPUT_DIR="./_site/${BASE_PACKAGE_NAME}/${VERSION}"

if [ -z "$BASE_PACKAGE_NAME" ] || [ -z "$VERSION" ] || [ -z "$FULL_PACKAGE_SPEC" ]; then
  echo "Usage: $0 <base-package-name> <version> <full-package-spec>"
  exit 1
fi

if [ ! -d "$DOCS_SOURCE_DIR" ] || [ ! -f "${DOCS_SOURCE_DIR}/conf.py" ]; then
  echo "Info: Documentation source directory or conf.py not found at ${DOCS_SOURCE_DIR}. Skipping."
  exit 0
fi

echo "Found documentation source at: ${DOCS_SOURCE_DIR}"

# Create a temporary copy of conf.py to avoid modifying the original
TEMP_CONF="${DOCS_SOURCE_DIR}/conf_temp.py"
cp "${DOCS_SOURCE_DIR}/conf.py" "$TEMP_CONF"

# Append this generated config to the temporary conf.py
cat intersphinx_mappings.py >> "$TEMP_CONF"

# Temporarily replace the original conf.py
mv "${DOCS_SOURCE_DIR}/conf.py" "${DOCS_SOURCE_DIR}/conf_original.py"
mv "$TEMP_CONF" "${DOCS_SOURCE_DIR}/conf.py"

echo "✓ Documentation configuration prepared"

echo "--- Building docs for ${BASE_PACKAGE_NAME} version ${VERSION} ---"

# For versioned builds, checkout the specific git tag to get the right source code
if [ "$VERSION" != "latest" ]; then
  CLEAN_VERSION="${VERSION#v}"
  TAG_NAME="${BASE_PACKAGE_NAME}/v${CLEAN_VERSION}"
  
  echo "Checking out git tag: ${TAG_NAME}"
  if git rev-parse --verify "${TAG_NAME}" >/dev/null 2>&1; then
    # Create a temporary directory for the specific version
    TEMP_DIR=$(mktemp -d)
    echo "Creating temporary checkout at: ${TEMP_DIR}"
    
    # Clone the current repo to temp directory and checkout the specific tag
    git clone . "${TEMP_DIR}" --quiet
    (cd "${TEMP_DIR}" && git checkout "${TAG_NAME}" --quiet)
    
    # Update the docs source directory to point to the tagged version
    DOCS_SOURCE_DIR="${TEMP_DIR}/${BASE_PACKAGE_NAME}/docs"
    
    # Add cleanup for temp directory
    cleanup() {
      if [ -f "${DOCS_SOURCE_DIR}/conf_original.py" ]; then
        mv "${DOCS_SOURCE_DIR}/conf_original.py" "${DOCS_SOURCE_DIR}/conf.py"
      fi
      if [ -d "${TEMP_DIR}" ]; then
        rm -rf "${TEMP_DIR}"
      fi
    }
    trap cleanup EXIT
    
    echo "✓ Successfully checked out ${TAG_NAME}"
  else
    echo "WARNING: Git tag ${TAG_NAME} not found. Using current source code (may not match installed version)."
  fi
else
  echo "Building latest version - using current source code"
fi



echo "Installing from spec: '${FULL_PACKAGE_SPEC}' version ${VERSION}"

# For versioned builds, install the specific version
if [ "$VERSION" != "latest" ]; then
  # Strip 'v' prefix from version if present (e.g., v2.39 -> 2.39)
  CLEAN_VERSION="${VERSION#v}"
  
  # Special handling for older iqm-client versions
  if [[ "$BASE_PACKAGE_NAME" == "iqm-client" ]]; then
    # Check if version is < 30.0
    if [[ $(echo "$CLEAN_VERSION 30.0" | awk '{print ($1 < $2)}') == 1 ]]; then
      echo "Installing older iqm-client version with numba/llvmlite workaround"
      VERSIONED_SPEC="${FULL_PACKAGE_SPEC}==${CLEAN_VERSION}"
      uv pip install -U "${VERSIONED_SPEC}" numba llvmlite
    else
      echo "Installing newer iqm-client version normally"
      VERSIONED_SPEC="${FULL_PACKAGE_SPEC}==${CLEAN_VERSION}"
      uv pip install "${VERSIONED_SPEC}"
    fi
  else
    # Standard installation for other packages
    VERSIONED_SPEC="${FULL_PACKAGE_SPEC}==${CLEAN_VERSION}"
    echo "Installing versioned package: ${VERSIONED_SPEC}"
    uv pip install "${VERSIONED_SPEC}"
  fi
  
  # Verify the installed version matches what we expected
  echo "Verifying installed version..."
  
  # All IQM packages are under the iqm namespace
  # Convert package name: iqm-client -> iqm_client, iqm-pulse -> pulse, etc.
  if [[ "$BASE_PACKAGE_NAME" == "iqm-client" ]]; then
    MODULE_NAME="iqm_client"
  else
    # For other iqm packages, remove 'iqm-' prefix
    MODULE_NAME="${BASE_PACKAGE_NAME#iqm-}"
    MODULE_NAME="${MODULE_NAME//-/_}"  # Replace any remaining hyphens with underscores
  fi
  
  INSTALLED_VERSION=$(python -c "from iqm import ${MODULE_NAME}; print(${MODULE_NAME}.__version__)" 2>/dev/null || echo "unknown")
  echo "Expected version: ${CLEAN_VERSION}"
  echo "Installed version: ${INSTALLED_VERSION}"
  echo "Module checked: iqm.${MODULE_NAME}"
  
  if [ "$INSTALLED_VERSION" != "$CLEAN_VERSION" ] && [ "$INSTALLED_VERSION" != "unknown" ]; then
    echo "WARNING: Version mismatch! Expected ${CLEAN_VERSION} but got ${INSTALLED_VERSION}"
    echo "This might indicate a problem with the package installation or version specification."
    # Don't exit here - continue with documentation build but log the issue
  elif [ "$INSTALLED_VERSION" == "unknown" ]; then
    echo "WARNING: Could not determine installed version. Package might not be properly installed."
    echo "Attempting to list what was actually installed..."
    uv pip show "${BASE_PACKAGE_NAME}" || echo "Package not found in pip list"
  else
    echo "✓ Version verification successful"
  fi
  
else
  # For latest builds, install the latest version
  echo "Installing latest version: ${FULL_PACKAGE_SPEC}"
  uv pip install "${FULL_PACKAGE_SPEC}"
  
  # Show what version was installed for latest builds
  echo "Verifying installed version for latest build..."
  
  # Use same module naming logic as versioned builds
  if [[ "$BASE_PACKAGE_NAME" == "iqm-client" ]]; then
    MODULE_NAME="iqm_client"
  else
    MODULE_NAME="${BASE_PACKAGE_NAME#iqm-}"
    MODULE_NAME="${MODULE_NAME//-/_}"
  fi
  
  INSTALLED_VERSION=$(python -c "from iqm import ${MODULE_NAME}; print(${MODULE_NAME}.__version__)" 2>/dev/null || echo "unknown")
  echo "Installed latest version: ${INSTALLED_VERSION}"
  echo "Module checked: iqm.${MODULE_NAME}"
fi

if [ -f "${DOCS_SOURCE_DIR}/requirements.txt" ]; then
  echo "Installing documentation-specific requirements..."
  uv pip install -r "requirements-docs.txt"
fi

# Show all installed packages for debugging
echo "=== Installed packages (for debugging) ==="
echo "Target package and related:"
uv pip list | grep -i "iqm\|sphinx\|furo" || echo "No matching packages found"
echo ""
echo "Specific package details:"
uv pip show "$BASE_PACKAGE_NAME" 2>/dev/null || echo "Package $BASE_PACKAGE_NAME not found in pip show"
echo "==========================================="

echo "Running Sphinx..."
python -m sphinx -b html -j auto "${DOCS_SOURCE_DIR}" "${BUILD_OUTPUT_DIR}"

# Clean up unnecessary build artifacts
echo "Cleaning up build artifacts..."
rm -rfv "${BUILD_OUTPUT_DIR}/jupyter_execute"
rm -rfv "./_site/${BASE_PACKAGE_NAME}/jupyter_execute"
find "${BUILD_OUTPUT_DIR}" -type d -name ".doctrees" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_OUTPUT_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

touch "${BUILD_OUTPUT_DIR}/.nojekyll"
touch _site/.nojekyll

echo "--- Successfully built docs for ${BASE_PACKAGE_NAME} version ${VERSION} ---"
