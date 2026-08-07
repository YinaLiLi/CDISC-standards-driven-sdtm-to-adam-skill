# Configuration

Runtime configuration is currently explicit Python input rather than a required config-file loader. The implemented public entry point is `standards_driven_sdtm_adam.pipeline.V1Pipeline`.

The committed configuration files document expected structure:

- `config/standards/*.yaml`: standards and reference manifests
- `config/pipeline.example.yaml`: illustrative v1 pipeline input shape

Local CDISC source files referenced by manifests should remain outside Git unless redistribution is explicitly allowed.
