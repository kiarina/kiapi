# Security Policy

## Supported Versions

Security fixes are handled for the current `main` branch and the latest released
version on a best-effort basis.

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.

Report security issues by emailing the maintainer:

```text
kiarinadawa@gmail.com
```

Include:

- affected version or commit
- affected capability or endpoint
- reproduction steps
- impact and any known mitigations
- relevant logs or request examples, with secrets removed

## Operational Security Notes

kiapi is designed primarily as a local API server for trusted users on Apple
Silicon machines.

- By default, `kiapi run` binds to `127.0.0.1:8000`.
- Use `--host 0.0.0.0` only on trusted networks.
- Configure an auth token before exposing kiapi beyond localhost.
- Treat generated files, uploaded files, fetched URLs, and model outputs as
  untrusted data.
- Review the licenses and safety terms for each model and package you activate.
- The Web capability starts Docker subprocesses for search and fetch backends;
  use it only in environments where Docker execution is acceptable.

kiapi includes URL safety checks for user-provided network inputs, but they are
not a substitute for network isolation when operating in untrusted environments.
