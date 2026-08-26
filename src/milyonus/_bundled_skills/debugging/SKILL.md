---
name: debugging
description: Sistematik hata ayıklama metodolojisi
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - debug
    - troubleshooting
    - method
    category: gelistirme
    requires_toolsets: []
    provenance: official
---

# Sistematik Hata Ayıklama

Tahminle değil, **yöntemle** ilerle. Sıra:

## 1. Güvenilir şekilde tekrarla
- En küçük tekrarlanabilir örneği (MRE) bul. Tekrar edemiyorsan önce onu çöz.
- Ortamı sabitле: sürüm, girdi, config, saat/zaman dilimi.

## 2. Gözlemle (varsaymadan)
- Gerçek hata mesajını/stack trace'i **sonuna kadar** oku — kök genелde en içteki.
- Log seviyesini yükselt; girdi/çıktı değerlerini yazdır (`print`/logger).
- "Beklenen vs gerçek"i net yaz.

## 3. Daralt (bisect)
- İkili arama: sorunun nerede olmadığını eleyerek yerini yarıya indir.
- `git bisect` ile hangi commit'in bozduğunu bul.
- Bileşenleri izole et (bağımlılığı mock'la, tek modülü çalıştır).

## 4. Hipotez → test
- Tek bir değişken değiştir, tekrar ölç. Bir seferde bir şey.
- "Neden" zincirini kur: 5 kez "neden" sor (5 whys), kök nedene in.

## 5. Düzelt & doğrula
- Kök nedeni düzelt (semptomu değil).
- Hatayı yakalayan bir **regresyon testi** yaz — geri gelmesin.
- Yan etkileri kontrol et; tüm testleri koştur.

## Sık kök nedenler
Off-by-one · null/None · yarış durumu (race) · önbellek eskimesi · sınır değerleri ·
kodlama/encoding · zaman dilimi · float karşılaştırma · env farkı (prod≠dev).
