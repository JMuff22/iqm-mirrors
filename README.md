# IQM-Mirrors

This repository is intended to mirror all of IQM's client-side python packages that are available on `pypi.org` according to `packages.txt`. For each released version, this repository should contain a commit and tag associated with that particular package version. This should enable:

1. Viewing of the latest available source code in the web and to compare changes between particular versions easier
2. Documentation for a particular package version. 

## Configuration

Configuration in `packages.txt` should be of the form 

```txt
package-name, min_version
```