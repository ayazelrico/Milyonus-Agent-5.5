---
name: rag-retrieval
description: Retrieval-Augmented Generation sistemi kurma (chunk, embed, ara)
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - rag
    - embeddings
    - vector
    - llm
    - retrieval
    category: yapay-zeka
    requires_toolsets: []
    provenance: official
---

# RAG (Retrieval-Augmented Generation)

Amaç: LLM'e cevap üretirken ilgili kaynak metni bağlama enjekte etmek —
halüsinasyonu azaltır, güncel/özel bilgi sağlar.

## Boru hattı
1. **Yükle & parçala (chunk):** belgeleri ~300–800 token'lık, %10–20 örtüşen
   parçalara böl. Anlamsal sınırları koru (paragraf/başlık).
2. **Gömme (embed):** her parçayı bir embedding modeliyle vektöre çevir
   (ör. OpenAI `text-embedding-3-small`, yerel `bge`/`e5`).
3. **Sakla:** vektörleri bir vektör deposuna yaz (sqlite-vec, FAISS, pgvector,
   Qdrant). Metadatayı (kaynak, başlık) birlikte tut.
4. **Getir:** sorguyu göm → en yakın k parçayı bul (kosinüs). Tipik k=4–8.
5. **Yeniden sırala (ops.):** bir cross-encoder ile ilk k'yi rerank et.
6. **Üret:** getirilen parçaları promta **kaynak olarak** ver; modele
   "yalnızca verilen bağlama dayan, yoksa bilmiyorum de" talimatı ver.

## Kalite ipuçları
- **Chunk boyutu** en kritik parametre: çok büyük → gürültü, çok küçük → bağlam kopar.
- **Hibrit arama:** vektör + anahtar kelime (BM25) birleştir; kesin terimlerde iyidir.
- **Kaynak göster:** cevapta hangi parçadan geldiğini belirt (güven + denetim).
- **Değerlendir:** soru-cevap seti üzerinde "getirme isabeti" ve "cevap doğruluğu"nu ölç.
- Milyonus'ta gömme katmanı opsiyoneldir (`sqlite-vec`); benzerlik dedup/negatif
  bellek için de kullanılır.
