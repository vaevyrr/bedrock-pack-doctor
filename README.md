# Bedrock Pack Doctor

A read-only command-line checker for Minecraft Bedrock add-on and resource-pack archives. It checks ZIP integrity, manifests, UUIDs, JSON syntax, and common missing asset references.

## Requirements

- Python 3.10+
- No third-party dependencies

## Usage

```bash
python packdoctor.py path/to/pack.mcpack
python packdoctor.py path/to/pack.mcpack --json report.json
python packdoctor.py path/to/extracted-pack
```

The original pack is never extracted or modified. A clean report means the checks in this tool passed; it is not a complete validation against every Bedrock game-version schema.

## Checks

- ZIP readability and CRC errors
- Root `manifest.json`, required fields, version arrays and UUID format
- Duplicate header/module UUIDs
- JSON syntax in all JSON files
- Common texture/model/particle references where paths can be resolved

## Exit codes

- `0`: no errors (warnings are allowed)
- `1`: errors found
- `2`: input or report could not be read/written

## Tests

```bash
python -m unittest discover -s tests -v
```

MIT License.
