---
name: pandas-data
description: Data analysis and cleaning basics with pandas
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - python
    - pandas
    - data
    category: data
    requires_toolsets:
    - terminal
    provenance: official
---

# Data with pandas
- **Read:** `df = pd.read_csv("data.csv")` ; peek `df.head()`, `df.info()`
- **Select:** `df["col"]`, `df.loc[df.age>30]`
- **Clean:** `df.dropna()`, `df.fillna(0)`, `df.drop_duplicates()`
- **Group:** `df.groupby("category")["value"].mean()`
- **New column:** `df["ratio"] = df.a / df.b`
- **Write:** `df.to_csv("out.csv", index=False)`
