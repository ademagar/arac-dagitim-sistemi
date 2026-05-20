# Proje: Otomotiv Bayi Araç Dağıtım Sistemi

## Bağlam
Bu bir endüstri mühendisliği bitirme projesidir. Bir otomotiv markasının
(SUV segmenti) 20-30 bayisine aylık 300-1500 araç dağıtımını otomatize
eden karar destek sistemidir. Sistem 2026 Ocak ayında devreye girecek.

## ÖNEMLİ: Tamamen Bulut Tabanlı Geliştirme
Bu projede LOKAL geliştirme yapılmıyor. Tüm akış:
- Kod: GitHub repo'da
- Veri: Private repo'da data/raw/ altında (anonimleştirilmiş CSV)
- Test: GitHub Actions
- Çalıştırma: GitHub Codespaces (gerektiğinde)
- Notebook: Google Colab veya Codespaces
- Dashboard: Streamlit Cloud

Bu nedenle:
- Tüm kod cloud ortamında çalışabilmeli (path'lar relative, pathlib.Path)
- CSV dosyaları repo içinde data/raw/ altında bulunuyor
- Hiçbir kod "lokal makine"ye varsayım yapmamalı
- Streamlit Cloud için secrets.toml hazırlığı yapılmalı
- Notebook'lar Codespaces ve Colab uyumlu olmalı

## Metodoloji
1. STL Decomposition + Prophet ile mevsimsellik modelleme
2. Çok kriterli skorlama:
   - Performans Skoru (P, w=0.25): Son 12 ay EW hedef gerçekleştirme
   - Lokasyon-Ürün Uyum Skoru (LP, w=0.35): Cosine similarity ile
     collaborative filtering yaklaşımı
   - Mevsimsel Uyum Skoru (S, w=0.20): Bayi bazında seasonal_index
   - Hedef Yakınlık Skoru (H, w=0.20): Yıllık hedefe göre kalan miktar
3. Mixed Integer Linear Programming (PuLP + CBC solver) ile optimal dağıtım

## Veri Yapısı
data/raw/ içinde anonimleştirilmiş CSV dosyaları:
- sales_2024_2025.csv           (geçmiş satışlar, bayi-model-versiyon-renk)
- dealer_targets_2026.csv        (2026 bayi hedefleri)
- dealer_locations.csv           (bayi lokasyonları, il/ilçe/lat/lon)
- monthly_performance_2025.csv   (2025 aylık hedef/satış/yüzde)
- competitor_sales.csv           (rakip marka satışları)
- inventory_2026_01.csv          (2026 Ocak araç envanteri)

CSV formatı: UTF-8 encoding, virgül delimiter, ISO tarih (YYYY-MM-DD)
Marka adı = "Marka X", bayiler = "Bayi 01" - "Bayi 30"

## Araç Özellikleri
Tüm araçlar SUV segmentinde. Model, versiyon (donanım paketi) ve renk
ayrımı var. Motor/şanzıman/yakıt tipi detayına girilmiyor.

## Teknik Stack
- Python 3.11
- pandas, numpy, sqlalchemy (veri)
- statsmodels, prophet, pmdarima (zaman serisi)
- pulp + CBC solver (optimizasyon)
- scikit-learn (cosine similarity, segmentasyon)
- streamlit, plotly, folium, streamlit-folium (dashboard)
- pytest, ruff (test ve linting)

## Veritabanı Şeması (SQLite, data/arac_dagitim.db)
- dim_bayi (bayi master)
- dim_arac (araç master: model/versiyon/renk)
- fact_satis (geçmiş satışlar)
- fact_hedef (aylık hedefler ve gerçekleşmeler)
- fact_envanter (her ay araç envanteri)
- dim_rakip_satis (rakip marka satışları)

## Kısıtlar
- Bayi stok kapasitesi YOK (1000 araçtan az olduğu için)
- Sistem aylık çalışacak, satış verisi her ay güncellenebilir olmalı
- Renk dağılımı bayinin geçmiş profiline yakın olmalı (soft constraint)
- Versiyon dağılımı bayinin geçmiş profiline yakın olmalı (soft constraint)
- Bayi 2026 aylık hedefi ±%20 aralığında olmalı

## Kod Standartları
- Yorum satırları Türkçe (Türkçe karakter OK, kod içinde)
- Değişken/fonksiyon isimleri İngilizce (snake_case)
- Type hints zorunlu (Python 3.11+ syntax)
- Her modül için docstring (Google style)
- pytest ile minimum %70 coverage
- Tüm path'lar pathlib.Path ile relative
- Ruff ile linting

## Anonimleştirme
- Marka adı kodda parametrik (config.py'den BRAND_NAME)
- Bayi isimleri config.py'den ANONYMIZE=True ile "Bayi XX" formatında
- Dashboard'da DEMO_MODE flag ile demo modu

## Branch Stratejisi
- main: production (Streamlit Cloud bu branch'i izler)
- feature/<gorev-no>-<aciklama>: her görev için ayrı branch

## PR Disiplini
- Her PR tek görevi tamamlar
- GitHub Actions yeşil olmadan merge yok
- PR açıklaması Türkçe: özet + değişiklikler + nasıl test edilir
- Commit mesajları İngilizce (Conventional Commits: feat/fix/docs/test)

## Çalışma Prensibi
- Veri yapısını gördükten SONRA kod yaz, varsayım yapma
- CSV sütun isimlerini önce kontrol et
- Önemli kararları Issue veya PR'da soru olarak sor
- Hassas/etik karar gerektiren noktada kullanıcıya danış
- Her görev sonunda ne yaptığını ve hangi dosyaların oluştuğunu özetle

## Akademik Bağlam
Bu bir bitirme projesi (endüstri mühendisliği). Hocanın değerlendirmesi
için akademik dokümantasyon önemli. Şu kavramların kodda ve dokümantasyonda
açıkça yer alması gerekir:
- Vehicle Allocation Problem (VAP)
- Multi-Criteria Decision Making (MCDM)
- Mixed Integer Linear Programming (MILP)
- Hierarchical Time Series Forecasting
- Collaborative Filtering
- Assortment Optimization
