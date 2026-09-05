# Extract Status

No `.hyper` extract is included. The Tableau Hyper API is not installed in the repository's locked local environment, so the implementation kit uses compact UTF-8 CSV sources. If Hyper is later added in an isolated environment, reconcile its row counts, schema, profile identity, and SHA-256 checksum against `tableau_data_manifest.yml` before use.
