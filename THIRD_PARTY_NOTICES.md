# Third-Party Notices

FinAgentBench's own source code is licensed under the repository's MIT
`LICENSE`. That license does not relicense external producer repositories,
Python build tools, CI actions, or data supplied by users.

## Runtime

`pyproject.toml` declares no third-party runtime dependencies. FinAgentBench
uses only the Python standard library at runtime.

## Build, CI, and integration

- Python and its standard library remain under the Python Software Foundation
  License.
- setuptools and wheel retain their upstream licenses.
- GitHub Actions used by CI retain their respective upstream licenses and
  terms.
- LumenFin is a separate MIT-licensed producer repository with its own
  dependency and data notices. FinAgentBench does not import LumenFin's
  application runtime.

## Fixtures and generated reports

Bundled benchmark fixtures are synthetic unless a file explicitly states
otherwise. FinRun artifacts supplied by external producers and reports
generated from them remain subject to the rights and data terms of their
source material; the FinAgentBench MIT license does not grant rights to
third-party input data.
