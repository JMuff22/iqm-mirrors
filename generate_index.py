import os
import sys
from packaging.version import parse as parse_version


def generate_html(package_data, output_path):
	"""Generates an HTML file from a dictionary of packages and versions."""
	# GitHub repository base URL
	github_repo_url = "https://github.com/JMuff22/iqm-mirrors"

	html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IQM Package Documentation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            line-height: 1.6; color: #333; max-width: 1200px; margin: 40px auto; padding: 0 20px;
        }
        h1, h2 { border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
        .package { margin-bottom: 2em; }
        .versions-grid { display: flex; flex-wrap: wrap; gap: 8px; align-items: flex-start; }
        .version-item {
            display: flex; flex-direction: column; align-items: center; gap: 4px;
            min-width: 80px; text-align: center;
        }
        .version-link {
            text-decoration: none; background-color: #f6f8fa; color: #24292e;
            padding: 6px 12px; border-radius: 6px; border: 1px solid #d1d5da;
            font-weight: 500; display: block; width: 100%; box-sizing: border-box;
        }
        .version-link:hover { background-color: #f0f2f4; border-color: #c9d1d9; }
        .latest .version-link { font-weight: bold; border-color: #0366d6; background-color: #ddf4ff; }
        .source-link {
            text-decoration: none; color: #586069; font-size: 0.8em; padding: 2px 6px;
            border: 1px solid #d1d5da; border-radius: 3px; background-color: #fafbfc;
            white-space: nowrap;
        }
        .source-link:hover { color: #24292e; background-color: #f3f4f6; }
        .source-link::before { content: "📁 "; }
        @media (max-width: 768px) {
            .versions-grid { flex-direction: column; }
            .version-item { min-width: 100%; }
        }
    </style>
</head>
<body>
    <h1>IQM Package Documentation</h1>
"""

	for package, versions in sorted(package_data.items()):
		html += '    <div class="package">\n'
		html += f"        <h2>{package}</h2>\n"
		html += '        <div class="versions-grid">\n'

		has_latest = "latest" in versions
		# Sort versions correctly, putting 'latest' first if it exists
		other_versions = [v for v in versions if v != "latest"]

		# Filter out versions that can't be parsed and sort the rest
		valid_versions = []
		invalid_versions = []
		for v in other_versions:
			try:
				parse_version(v)
				valid_versions.append(v)
			except Exception:
				invalid_versions.append(v)

		sorted_versions = sorted(valid_versions, key=parse_version, reverse=True)
		# Add invalid versions at the end (alphabetically sorted)
		sorted_versions.extend(sorted(invalid_versions))

		if has_latest:
			sorted_versions.insert(0, "latest")

		for version in sorted_versions:
			version_class = "latest" if version == "latest" else ""

			# Generate source code link
			if version == "latest":
				source_url = f"{github_repo_url}/tree/main/{package}"
			else:
				# For versioned builds, link to the git tag
				# Convert version like "v31.0.0" to tag like "iqm-client/v31.0.0"
				clean_version = version if version.startswith("v") else f"v{version}"
				tag_name = f"{package}/{clean_version}"
				source_url = f"{github_repo_url}/tree/{tag_name}/{package}"

			html += f'            <div class="version-item {version_class}">\n'
			html += f'                <a href="{package}/{version}/index.html" class="version-link">{version}</a>\n'
			source_link_html = (
				f'                <a href="{source_url}" class="source-link" target="_blank" '
				f'title="View source code">source</a>\n'
			)
			html += source_link_html
			html += "            </div>\n"

		html += "        </div>\n"
		html += "    </div>\n"

	html += """
</body>
</html>
"""
	with open(output_path, "w") as f:
		f.write(html)
	print(f"Successfully generated index page at {output_path}")


def main():
	if len(sys.argv) != 2:
		print("Usage: python generate_index.py <site_directory>")
		sys.exit(1)

	site_dir = sys.argv[1]
	if not os.path.isdir(site_dir):
		print(f"Creating site directory at '{site_dir}'")
		os.makedirs(site_dir, exist_ok=True)

	packages = {}
	for package_name in os.listdir(site_dir):
		package_path = os.path.join(site_dir, package_name)
		if os.path.isdir(package_path):
			# Skip non-package directories
			if package_name in [".git", "main-branch", ".github", "node_modules", "__pycache__"]:
				continue
			# Skip hidden directories and files
			if package_name.startswith("."):
				continue

			versions = []
			for version_name in os.listdir(package_path):
				if os.path.isdir(os.path.join(package_path, version_name)):
					# Skip non-version directories like jupyter_execute, .doctrees, etc.
					if version_name in ["jupyter_execute", ".doctrees", "_static", "_sources"]:
						continue
					versions.append(version_name)
			if versions:
				packages[package_name] = versions

	if not packages:
		print("No packages found to index.")
		return

	output_file = os.path.join(site_dir, "index.html")
	generate_html(packages, output_file)


if __name__ == "__main__":
	main()
