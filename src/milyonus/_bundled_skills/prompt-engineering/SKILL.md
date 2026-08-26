---
name: prompt-engineering
description: LLM promptlarını ve uygulamalarını tasarlama
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - prompt
    - llm
    - ai
    category: yapay-zeka
    requires_toolsets: []
    provenance: official
---

# Prompt Mühendisliği

## Temel yapı
- **System:** rol, kurallar, çıktı biçimi, kısıtlar (kalıcı davranış).
- **User:** somut görev + gerekli bağlam.
- **Örnekler (few-shot):** 1–5 iyi örnek, formatı gösterir; sıfır-shot yetmezse ekle.

## Etkili teknikler
- **Açık çıktı sözleşmesi:** "Yalnızca JSON döndür: {...}". Şema ver, doğrula.
- **Adım adım düşünme:** karmaşık akıl yürütmede "önce planla, sonra çöz" iste
  (ama kısa/kesin cevaplarda gereksiz uzatmayı önle).
- **Sınırları belirt:** "Bilmiyorsan 'bilmiyorum' de", "uydurma".
- **Rol + kitle:** "Kıdemli güvenlik mühendisi gibi, junior'a açıkla".
- **Böl ve yönet:** tek dev prompt yerine zincir (extract → transform → format).

## Sık hatalar
- Belirsiz talimat → belirsiz çıktı. Somut ol, örnek ver.
- Çelişen kurallar; öncelik sırası belirt.
- Bağlamı gömerken "talimat" ile "veri"yi karıştırmak — veriyi açıkça fence'le
  (Milyonus bunu `<milyonus:memory>` ile yapar).

## Değerlendirme
- Bir test seti (girdi → beklenen) tut; prompt değişince regresyonu ölç.
- LLM-as-judge ile sübjektif kaliteyi puanla; sıcaklığı 0'a çek (tekrarlanabilirlik).
