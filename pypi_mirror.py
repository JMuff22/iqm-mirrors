import os
import sys
import requests
import subprocess
import shutil
import tarfile
import tempfile
import re
from packaging.version import parse as parse_version


def clean_directory(path):
	"""Removes all files and subdirectories in a given path."""
	if not os.path.exists(path):
		return
	for item in os.listdir(path):
		item_path = os.path.join(path, item)
		try:
			if os.path.isfile(item_path) or os.path.islink(item_path):
				os.unlink(item_path)
			elif os.path.isdir(item_path):
				shutil.rmtree(item_path)
		except Exception as e:
			print(f"Failed to delete {item_path}. Reason: {e}")


def get_pypi_data(package_name):
	"""Fetches package metadata from the PyPI JSON API."""
	print(f"Fetching metadata for '{package_name}' from PyPI...")
	url = f"https://pypi.org/pypi/{package_name}/json"
	response = requests.get(url)
	if response.status_code != 200:
		print(f"Error: Could not find package '{package_name}' on PyPI. Status code: {response.status_code}")
		return None
	print("Successfully fetched metadata.")
	return response.json()


def download_and_extract(url, target_dir):
	"""Downloads and extracts a source tarball into the target directory."""
	with tempfile.TemporaryDirectory() as temp_dir:
		print(f"Downloading from {url}...")
		response = requests.get(url, stream=True)
		response.raise_for_status()

		tar_path = os.path.join(temp_dir, "source.tar.gz")
		with open(tar_path, "wb") as f:
			shutil.copyfileobj(response.raw, f)
		print("Download complete.")

		print(f"Extracting {tar_path}...")
		with tarfile.open(tar_path, "r:gz") as tar:
			tar.extractall(path=temp_dir)
		print("Extraction complete.")

		extracted_items = os.listdir(temp_dir)
		source_subdirs = [item for item in extracted_items if os.path.isdir(os.path.join(temp_dir, item))]
		if not source_subdirs:
			print("Error: Could not find the extracted source directory in the tarball.")
			return False

		source_root = os.path.join(temp_dir, source_subdirs[0])

		print(f"Moving contents from '{source_root}' to '{target_dir}'...")
		for item in os.listdir(source_root):
			shutil.move(os.path.join(source_root, item), target_dir)
		print("Move complete.")
	return True


def git_commit_and_tag(repo_dir, package_dir, package_name, version_str):
	"""Commits changes in a specific package directory and creates a tag."""
	print(f"Creating Git commit and tag for {package_name} version {version_str}...")

	# Use standard GitHub Actions bot user
	# subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], cwd=repo_dir, check=True)
	# subprocess.run(['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'], cwd=repo_dir, check=True)

	# Stage changes ONLY from the specific package directory
	subprocess.run(["git", "add", package_dir], cwd=repo_dir, check=True)

	commit_message = f"feat({package_name}): Release version {version_str}"
	# Check if there are any staged changes to commit
	status_result = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=repo_dir)
	if status_result.returncode != 0:
		subprocess.run(["git", "commit", "--no-verify", "-m", commit_message], cwd=repo_dir, check=True)
	else:
		print("No file changes to commit.")

	tag_name = f"{package_name}/v{version_str}"
	subprocess.run(["git", "tag", tag_name], cwd=repo_dir, check=True)

	print(f"Successfully committed and tagged version {tag_name}.")
	print("-" * 30)


def parse_config(file_path):
	"""Parses a config file for package names and minimum versions."""
	packages = []
	try:
		with open(file_path, "r") as f:
			for line in f:
				line = line.strip()
				if not line or line.startswith("#"):
					continue

				# Handle packages with extras like: iqm-benchmarks[docs,mgst],2.39
				# Find the last comma to split package spec from version
				last_comma_idx = line.rfind(",")
				if last_comma_idx == -1:
					# No version specified
					package_name = line
					min_version = None
				else:
					package_name = line[:last_comma_idx].strip()
					min_version = line[last_comma_idx + 1 :].strip()
					if not min_version:
						min_version = None

				if package_name:
					packages.append({"name": package_name, "min_version": min_version})
	except FileNotFoundError:
		print(f"Error: Config file not found at '{file_path}'")
		sys.exit(1)
	return packages


def get_existing_tags(repo_dir):
	"""Gets a set of all existing git tags in the repository."""
	if not os.path.exists(os.path.join(repo_dir, ".git")):
		return set()
	try:
		result = subprocess.run(["git", "tag"], cwd=repo_dir, check=True, capture_output=True, text=True)
		if not result.stdout.strip():
			return set()
		return set(result.stdout.strip().split("\n"))
	except (subprocess.CalledProcessError, FileNotFoundError):
		return set()


def process_package(monorepo_root, raw_package_name, min_version_str, existing_tags):
	"""Handles the full mirroring process for a single package."""
	print(f"\n{'=' * 10} Processing Package: {raw_package_name} {'=' * 10}")

	package_name = re.split(r"[\[]", raw_package_name)[0]
	package_dir = os.path.join(monorepo_root, package_name)

	if not os.path.exists(package_dir):
		os.makedirs(package_dir)
		print(f"Created directory for package '{package_name}' at: {package_dir}")

	data = get_pypi_data(package_name)
	if not data:
		print(f"Could not fetch data for {package_name}. Skipping.")
		return

	releases = data.get("releases", {})

	try:
		sorted_versions = sorted(releases.keys(), key=parse_version)
	except Exception:
		sorted_versions = sorted(releases.keys())

	if min_version_str:
		print(f"Filtering versions to include only those >= {min_version_str}")
		try:
			min_version = parse_version(min_version_str)
			filtered_versions = [v for v in sorted_versions if parse_version(v) >= min_version]
			print(f"Found {len(filtered_versions)} versions matching criteria (out of {len(sorted_versions)} total).")
			sorted_versions = filtered_versions
		except Exception as e:
			print(f"Error parsing min_version '{min_version_str}': {e}")
			return

	versions_to_process = [v for v in sorted_versions if f"{package_name}/v{v}" not in existing_tags]

	if not versions_to_process:
		print(f"All versions for '{package_name}' are already mirrored.")
		return

	print(f"Found {len(versions_to_process)} new versions to process for '{package_name}'.")

	for version in versions_to_process:
		print(f"\nProcessing {package_name} version: {version}...")
		release_files = releases[version]

		sdist_file = next((f for f in release_files if f["packagetype"] == "sdist"), None)
		if not sdist_file:
			print(f"Warning: No source distribution found for version {version}. Skipping.")
			continue

		clean_directory(package_dir)

		if not download_and_extract(sdist_file["url"], package_dir):
			print(f"Failed to process version {version}. Halting processing for this package.")
			break

		git_commit_and_tag(monorepo_root, package_dir, package_name, version)

	print(f"\nFinished processing for '{package_name}'.")


def main():
	if len(sys.argv) != 3:
		print("Usage: python pypi_monorepo_mirror.py <config_file.txt> <monorepo_root_dir>")
		sys.exit(1)

	config_file = sys.argv[1]
	monorepo_root = sys.argv[2]

	packages_to_mirror = parse_config(config_file)
	if not packages_to_mirror:
		print("No packages found in the config file. Exiting.")
		sys.exit(0)

	if not os.path.exists(monorepo_root):
		os.makedirs(monorepo_root)

	if not os.path.exists(os.path.join(monorepo_root, ".git")):
		print(f"Initializing Git repository in {monorepo_root}...")
		subprocess.run(["git", "init"], cwd=monorepo_root, check=True)
	else:
		print(f"Using existing Git repository in {monorepo_root}.")

	# Get the state of the repo ONCE at the beginning.
	print("Checking for existing Git tags...")
	existing_tags = get_existing_tags(monorepo_root)
	print(f"Found {len(existing_tags)} existing tags.")

	for package_info in packages_to_mirror:
		process_package(monorepo_root, package_info["name"], package_info["min_version"], existing_tags)

	print("\n\nMirroring process complete for all packages in config file!")


if __name__ == "__main__":
	main()
