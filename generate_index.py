import os
import sys
from packaging.version import parse as parse_version

def generate_html(package_data, output_path):
    """Generates an HTML file from a dictionary of packages and versions."""
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Package Documentation</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 40px auto; padding: 0 20px; }
        h1, h2 { border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
        .package { margin-bottom: 2em; }
        .versions-list { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 10px; }
        .versions-list li a { text-decoration: none; background-color: #f6f8fa; color: #24292e; padding: 5px 10px; border-radius: 6px; border: 1px solid #d1d5da; display: inline-block; }
        .versions-list li a:hover { background-color: #f0f2f4; border-color: #c9d1d9; }
        .latest a { font-weight: bold; border-color: #0366d6; background-color: #ddf4ff; }
    </style>
</head>
<body>
    <h1>Package Documentation</h1>
"""

    for package, versions in sorted(package_data.items()):
        html += f'    <div class="package">\n'
        html += f'        <h2>{package}</h2>\n'
        html += '        <ul class="versions-list">\n'
        
        has_latest = 'latest' in versions
        # Sort versions correctly, putting 'latest' first if it exists
        sorted_versions = sorted(
            [v for v in versions if v != 'latest'],
            key=parse_version,
            reverse=True
        )
        if has_latest:
            sorted_versions.insert(0, 'latest')

        for version in sorted_versions:
            version_class = 'latest' if version == 'latest' else ''
            html += f'            <li class="{version_class}"><a href="{package}/{version}/index.html">{version}</a></li>\n'
        
        html += '        </ul>\n'
        html += '    </div>\n'

    html += """
</body>
</html>
"""
    with open(output_path, 'w') as f:
        f.write(html)
    print(f"Successfully generated index page at {output_path}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_index.py <site_directory>")
        sys.exit(1)
    
    site_dir = sys.argv[1]
    if not os.path.isdir(site_dir):
        print(f"Error: Directory not found at '{site_dir}'")
        sys.exit(1)

    packages = {}
    for package_name in os.listdir(site_dir):
        package_path = os.path.join(site_dir, package_name)
        if os.path.isdir(package_path):
            versions = [
                version_name for version_name in os.listdir(package_path)
                if os.path.isdir(os.path.join(package_path, version_name))
            ]
            if versions:
                packages[package_name] = versions

    if not packages:
        print("No packages found to index.")
        return

    output_file = os.path.join(site_dir, 'index.html')
    generate_html(packages, output_file)

if __name__ == "__main__":
    main()
