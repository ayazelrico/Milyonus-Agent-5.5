---
name: pandas-data
description: pandas ile veri analizi ve temizleme temelleri
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
    category: veri
    requires_toolsets:
    - terminal
    provenance: official
---

# pandas ile Veri
- **Oku:** `df = pd.read_csv("veri.csv")` ; ilk bakış `df.head()`, `df.info()`
- **Seç:** `df["sutun"]`, `df.loc[df.yas>30]`
- **Temizle:** `df.dropna()`, `df.fillna(0)`, `df.drop_duplicates()`
- **Grupla:** `df.groupby("kategori")["deger"].mean()`
- **Yeni sütun:** `df["oran"] = df.a / df.b`
- **Yaz:** `df.to_csv("cikti.csv", index=False)`
