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

echo "--- Building docs for ${BASE_PACKAGE_NAME} version ${VERSION} ---"

# Create a temporary copy of conf.py to avoid modifying the original
TEMP_CONF="${DOCS_SOURCE_DIR}/conf_temp.py"
cp "${DOCS_SOURCE_DIR}/conf.py" "$TEMP_CONF"

# Append this generated config to the temporary conf.py
cat intersphinx_mappings.py >> "$TEMP_CONF"

# Temporarily replace the original conf.py
mv "${DOCS_SOURCE_DIR}/conf.py" "${DOCS_SOURCE_DIR}/conf_original.py"
mv "$TEMP_CONF" "${DOCS_SOURCE_DIR}/conf.py"

# Cleanup function to restore original conf.py even if script fails
cleanup() {
  if [ -f "${DOCS_SOURCE_DIR}/conf_original.py" ]; then
    mv "${DOCS_SOURCE_DIR}/conf_original.py" "${DOCS_SOURCE_DIR}/conf.py"
  fi
}
trap cleanup EXIT

echo "Installing from spec: '${FULL_PACKAGE_SPEC}' version ${VERSION}"

# For versioned builds, install the specific version
if [ "$VERSION" != "latest" ]; then
  # Extract base package name and extras separately
  if [[ "$FULL_PACKAGE_SPEC" == *"["* ]]; then
    # Package has extras like iqm-client[qiskit,cirq,cli]
    BASE_NAME="${FULL_PACKAGE_SPEC%%\[*}"
    EXTRAS="${FULL_PACKAGE_SPEC#*\[}"
    VERSIONED_SPEC="${BASE_NAME}==${VERSION}[${EXTRAS}"
  else
    # Simple package name without extras
    VERSIONED_SPEC="${FULL_PACKAGE_SPEC}==${VERSION}"
  fi
  echo "Installing versioned package: ${VERSIONED_SPEC}"
  uv pip install "${VERSIONED_SPEC}"
else
  # For latest builds, install the latest version
  echo "Installing latest version: ${FULL_PACKAGE_SPEC}"
  uv pip install "${FULL_PACKAGE_SPEC}"
fi

if [ -f "${DOCS_SOURCE_DIR}/requirements.txt" ]; then
  echo "Installing documentation-specific requirements..."
  uv pip install -r "requirements-docs.txt"
fi

echo "Running Sphinx..."
python -m sphinx -b html -j auto "${DOCS_SOURCE_DIR}" "${BUILD_OUTPUT_DIR}"

# Clean up unnecessary build artifacts
echo "Cleaning up build artifacts..."
rm -rfv "${BUILD_OUTPUT_DIR}/jupyter_execute"
rm -rfv ""./_site/${BASE_PACKAGE_NAME}/jupyter_execute"
find "${BUILD_OUTPUT_DIR}" -type d -name ".doctrees" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_OUTPUT_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

touch "${BUILD_OUTPUT_DIR}/.nojekyll"

echo "--- Successfully built docs for ${BASE_PACKAGE_NAME} version ${VERSION} ---"
