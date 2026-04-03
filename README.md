# biovector

## Data location

Biovector now keeps runtime CSV data outside the source tree.

- Default runtime data directory: `~/.local/share/biovector`
- Override with: `BIOVECTOR_DATA_DIR=/path/to/dir`

On first run, Biovector bootstraps missing runtime files from packaged seed CSVs.
