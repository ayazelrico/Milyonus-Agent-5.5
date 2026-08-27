---
name: pdf-extract
description: Extract tables from PDFs and convert to CSV
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - pdf
    - data
    category: data-processing
    requires_toolsets:
    - terminal
    provenance: user
---

# PDF Table Extraction
To extract tables from PDFs:
1. Get raw text with `pdftotext -layout input.pdf -`.
2. Split table regions by column alignment.
3. Write the result as CSV.
For complex tables, suggest the `camelot-py` or `tabula-py` libraries.
