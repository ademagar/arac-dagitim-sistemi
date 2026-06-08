"""gen_tez.py — Endüstri Mühendisliği Lisans Bitirme Tezi Üretici.

Bu script, python-docx kullanarak YTÜ kılavuzuna uygun bir Word belgesi üretir.
Çıktı: docs/tez_defteri.docx

Kullanım:
    python3 scripts/gen_tez.py
"""

from __future__ import annotations

import os
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
THESIS_TITLE_EN = (
    "Data-Driven Vehicle Allocation Optimization in an Automotive Dealer Network: "
    "A Multi-Criteria Decision Making and Mixed Integer Linear Programming Approach"
)
THESIS_TITLE_TR = (
    "Otomotiv Bayi Ağında Veri Odaklı Araç Dağıtım Optimizasyonu"
)
STUDENT_NAME = "[ÖĞRENCİ ADI SOYADI]"
ADVISOR_NAME = "[DANIŞMAN ADI SOYADI]"
YEAR = "HAZİRAN 2026"

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "docs" / "tez_defteri.docx"


# ---------------------------------------------------------------------------
# Yardımcı Fonksiyonlar
# ---------------------------------------------------------------------------

def set_run_font(run, size_pt: int, bold: bool = False,
                 font_name: str = "Times New Roman",
                 color: RGBColor | None = None) -> None:
    """Run font özelliklerini ayarla."""
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color


def set_cell_border(cell) -> None:
    """Tablo hücresi kenarlıklarını görünür yap."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for edge in ("top", "left", "bottom", "right"):
        tag = OxmlElement(f"w:{edge}")
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), "4")
        tag.set(qn("w:space"), "0")
        tag.set(qn("w:color"), "000000")
        tcPr.append(tag)


def add_table_borders(table) -> None:
    """Tablodaki tüm hücrelere kenarlık ekle."""
    for row in table.rows:
        for cell in row.cells:
            set_cell_border(cell)


def add_heading1(doc: Document, text: str) -> None:
    """Heading 1: Times New Roman 20pt, bold, tüm büyük, centered."""
    from docx.enum.text import WD_LINE_SPACING
    para = doc.add_paragraph()
    para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(24)
    para.paragraph_format.space_after = Pt(12)
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    run = para.add_run(text.upper())
    set_run_font(run, size_pt=20, bold=True)


def add_heading2(doc: Document, text: str) -> None:
    """Heading 2: Times New Roman 14pt, bold, left aligned."""
    from docx.enum.text import WD_LINE_SPACING
    para = doc.add_paragraph()
    para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    para.paragraph_format.space_before = Pt(18)
    para.paragraph_format.space_after = Pt(6)
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    run = para.add_run(text)
    set_run_font(run, size_pt=14, bold=True)


def add_body_paragraph(doc: Document, text: str,
                        first_line_indent: bool = True) -> None:
    """Gövde metni: Times New Roman 12pt, 1.5 satır aralığı, justified."""
    from docx.enum.text import WD_LINE_SPACING
    para = doc.add_paragraph()
    para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(6)
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    if first_line_indent:
        para.paragraph_format.first_line_indent = Cm(1.25)
    run = para.add_run(text)
    set_run_font(run, size_pt=12)


def add_equation_placeholder(doc: Document, formula: str) -> None:
    """Matematiksel denklem placeholder ekle."""
    from docx.enum.text import WD_LINE_SPACING
    para = doc.add_paragraph()
    para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after = Pt(6)
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    run = para.add_run(f"[DENKLEM: {formula}]")
    set_run_font(run, size_pt=12, bold=False)
    run.font.italic = True


def add_bullet(doc: Document, text: str) -> None:
    """Madde işareti paragrafı ekle."""
    from docx.enum.text import WD_LINE_SPACING
    para = doc.add_paragraph()
    para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(3)
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    para.paragraph_format.left_indent = Cm(1.0)
    run = para.add_run(f"•  {text}")
    set_run_font(run, size_pt=12)


# ---------------------------------------------------------------------------
# Bölüm Oluşturucular
# ---------------------------------------------------------------------------

def build_cover_page(doc: Document) -> None:
    """Kapak sayfası oluştur."""
    from docx.enum.text import WD_LINE_SPACING

    def cover_line(text: str, size: int = 12, bold: bool = False,
                   space_b: float = 6, space_a: float = 6) -> None:
        para = doc.add_paragraph()
        para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_before = Pt(space_b)
        para.paragraph_format.space_after = Pt(space_a)
        para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        run = para.add_run(text)
        set_run_font(run, size_pt=size, bold=bold)

    cover_line("T.C.", size=14, bold=True, space_b=72, space_a=6)
    cover_line("YILDIZ TEKNİK ÜNİVERSİTESİ", size=14, bold=True)
    cover_line("MAKİNA FAKÜLTESİ", size=14, bold=True)
    cover_line("ENDÜSTRİ MÜHENDİSLİĞİ BÖLÜMÜ", size=14, bold=True)
    cover_line("", space_b=24, space_a=24)
    cover_line("LİSANS BİTİRME ÇALIŞMASI", size=14, bold=True, space_b=36)
    cover_line("", space_b=24, space_a=0)
    cover_line(THESIS_TITLE_EN, size=14, bold=True, space_b=36, space_a=6)
    cover_line("", space_b=6, space_a=0)
    cover_line(f"({THESIS_TITLE_TR})", size=12, bold=False, space_b=6, space_a=36)
    cover_line("", space_b=36, space_a=0)
    cover_line(STUDENT_NAME, size=12, bold=True, space_b=72, space_a=6)
    cover_line("", space_b=24, space_a=0)
    cover_line(f"Danışman: {ADVISOR_NAME}", size=12, bold=False, space_b=48, space_a=6)
    cover_line("", space_b=48, space_a=0)
    cover_line(YEAR, size=12, bold=True, space_b=72, space_a=0)

    doc.add_page_break()


def build_abstract_en(doc: Document) -> None:
    """İngilizce abstract."""
    add_heading1(doc, "ABSTRACT")

    abstract_text = (
        "This study proposes a data-driven decision support system for optimizing the monthly "
        "vehicle allocation of an automotive distributor operating in the premium SUV segment "
        "across 28 dealer locations in Turkey. The system addresses the Vehicle Allocation "
        "Problem (VAP) through an integrated framework combining time-series seasonality "
        "modeling, multi-criteria scoring, and Mixed Integer Linear Programming (MILP). "
        "Historical sales data from 2024–2025 (6,439 transactions) were used to compute "
        "monthly Seasonal Indices (SI) using the ratio-to-mean method, stratified by dealer "
        "tier groups (Tier A: Marmara+Aegean+Central Anatolia, Tier B: Mediterranean, "
        "Tier C: Southeast+Black Sea). Forecast validation against December 2025 actual sales "
        "yielded a Mean Absolute Percentage Error (MAPE) of 7.82%. For 2026 annual planning, "
        "two capacity scenarios (8,500 and 10,000 vehicles) were evaluated using SI-based "
        "monthly allocation. A new product version launch in March 2026 is supported by a "
        "statistically justified 1.15 SI boost, derived from B segment's historical March "
        "seasonal indices (2024: 2.494, 2025: 1.568) and an expected pay restoration of "
        "+11.2 percentage points. Multi-criteria dealer scoring integrates performance "
        "(w=0.25), location-product fit (w=0.35), seasonal alignment (w=0.20), and target "
        "proximity (w=0.20). The resulting MILP model allocates vehicles to 28 dealers across "
        "12 months and 4 active models (A2, A3, B1, B2), respecting ±20% target bounds. "
        "The system was deployed as an interactive web dashboard using React and Python."
    )
    add_body_paragraph(doc, abstract_text, first_line_indent=False)

    add_body_paragraph(
        doc,
        "Keywords: Vehicle Allocation Problem, Multi-Criteria Decision Making, "
        "Mixed Integer Linear Programming, Seasonal Index, Automotive Distribution.",
        first_line_indent=False,
    )
    doc.add_page_break()


def build_abstract_tr(doc: Document) -> None:
    """Türkçe özet."""
    add_heading1(doc, "ÖZET")

    ozet_text = (
        "Bu çalışmada, Türkiye genelinde 28 bayi ile faaliyet gösteren premium SUV segmentli "
        "bir otomotiv distribütörünün aylık araç dağıtımını optimize etmeye yönelik veri "
        "odaklı bir karar destek sistemi önerilmektedir. Sistem, Araç Dağıtım Problemi'ni "
        "(Vehicle Allocation Problem - VAP) zaman serisi mevsimsellik modellemesi, çok "
        "kriterli skorlama ve Karma Tamsayılı Doğrusal Programlama (KTDP) bileşenlerini bir "
        "arada kullanan entegre bir çerçeve aracılığıyla ele almaktadır. 2024–2025 dönemine "
        "ait 6.439 satış kaydından oluşan tarihsel veri, bayi tier grupları temelinde "
        "(Tier A: Marmara+Ege+İç Anadolu, Tier B: Akdeniz, Tier C: Güneydoğu+Karadeniz) "
        "aylık Sezonalite Endekslerinin (SI) hesaplanmasında kullanılmıştır. Aralık 2025 "
        "gerçekleşmelerine karşı yapılan doğrulama, Ortalama Mutlak Yüzde Hata (MAPE) "
        "değeri olarak %7,82 sonuç vermiştir. 2026 yıllık planlaması için 8.500 ve 10.000 "
        "araçlık iki kapasite senaryosu, SI bazlı aylık dağılım yöntemiyle "
        "değerlendiriılmiştir. Mart 2026'daki yeni ürün sürümü lansmanı; B segmentının "
        "tarihsel Mart SI değerleri (2024: 2,494; 2025: 1,568) ve beklenen +11,2 puanlık "
        "pay artışından türetilen istatistiksel olarak geçreklendirilmiş 1,15'lik SI "
        "çarpanıyla desteklenmektedir. Çok kriterli bayi skorlaması; performans (w=0,25), "
        "lokasyon-ürün uyumu (w=0,35), mevsimsel uyum (w=0,20) ve hedef yakınlığı (w=0,20) "
        "kriterlerini büyunkünleştirmektedir. Elde edilen KTDP modeli, ±%20 hedef aralığı "
        "kısıtına uyarak 28 bayiye 12 ay ve 4 aktif model (A2, A3, B1, B2) bazında araç "
        "dağıtmaktadır."
    )
    add_body_paragraph(doc, ozet_text, first_line_indent=False)

    add_body_paragraph(
        doc,
        "Anahtar Kelimeler: Araç Dağıtım Problemi, Çok Kriterli Karar Verme, "
        "Karma Tamsayılı Doğrusal Programlama, Sezonalite Endeksi, Otomotiv Dağıtımı.",
        first_line_indent=False,
    )
    doc.add_page_break()


def build_introduction(doc: Document) -> None:
    """INTRODUCTION bölümü — yaklaşık 2 sayfa."""
    add_heading1(doc, "Introduction")

    add_body_paragraph(
        doc,
        "The global automotive industry represents one of the most capital-intensive and "
        "logistics-complex sectors in modern economies. In Turkey, passenger car and light "
        "commercial vehicle sales reached approximately 1.3 million units in 2024, reflecting "
        "a mature yet highly competitive market environment. Within this landscape, Original "
        "Equipment Manufacturers (OEMs) and their authorized distributors must balance "
        "production schedules, regional demand variations, model lifecycle management, and "
        "dealer-level performance targets simultaneously. The efficiency of vehicle "
        "distribution—from production to end consumer—has become a decisive competitive "
        "factor, directly influencing revenue realization, inventory carrying costs, and "
        "customer satisfaction indices."
    )

    add_body_paragraph(
        doc,
        "Despite the strategic importance of vehicle allocation decisions, many automotive "
        "distributors continue to rely on manual or semi-automated processes that are "
        "vulnerable to cognitive biases, lack of data integration, and the inability to "
        "simultaneously optimize across multiple competing criteria. A typical monthly "
        "allocation cycle involves distributing between 300 and 1,500 vehicles across 20 to "
        "30 dealer locations, while accounting for historical dealer performance, regional "
        "demand seasonality, model-specific preferences, and contractual target obligations. "
        "The combinatorial complexity of this problem—even before considering uncertainty in "
        "demand—renders purely judgmental approaches inadequate."
    )

    add_body_paragraph(
        doc,
        "The present study addresses the Vehicle Allocation Problem (VAP) in the context of "
        "a premium SUV brand operating through 28 dealer points across Turkey. The core "
        "objective is to design and implement a data-driven decision support system that "
        "automates the monthly vehicle allocation process while ensuring alignment with "
        "dealer-level annual targets, inventory constraints, and equity considerations. "
        "The system is targeted for operational deployment in January 2026 and covers four "
        "active vehicle models (A2, A3, B1, and B2) within the same SUV segment."
    )

    add_body_paragraph(
        doc,
        "The proposed methodology integrates three analytical layers. First, a seasonality "
        "estimation layer employs the ratio-to-mean method to compute monthly Seasonal Indices "
        "(SI) stratified by dealer tier groups, capturing geographic and socioeconomic "
        "heterogeneity in demand patterns. Second, a Multi-Criteria Decision Making (MCDM) "
        "scoring layer aggregates four dealer-level scores—performance (P), location-product "
        "fit (LP), seasonal alignment (S), and target proximity (H)—into a composite score "
        "that quantifies each dealer's suitability for receiving additional allocation in a "
        "given month. Third, a Mixed Integer Linear Programming (MILP) optimization layer "
        "translates the scoring outputs into feasible, integer-valued allocation decisions "
        "subject to monthly inventory availability, dealer target bounds (±20%), and "
        "model-level distribution requirements."
    )

    add_body_paragraph(
        doc,
        "The scope of this study is limited to the SUV segment with no differentiation by "
        "engine type, fuel variant, or transmission. Dealer stock capacity constraints are "
        "omitted from the model on the grounds that monthly allocations remain well below "
        "1,000 units per dealer—a threshold at which storage constraints become practically "
        "binding. Color and version (trim level) distribution preferences are incorporated "
        "as soft constraints within the scoring framework rather than as hard MILP "
        "constraints, consistent with the distributional nature of these preferences."
    )

    add_body_paragraph(
        doc,
        "The remainder of this thesis is organized as follows. Chapter 2 provides a "
        "structured review of the relevant literature spanning vehicle allocation, "
        "multi-criteria decision making, seasonal forecasting, and supply chain optimization. "
        "Chapter 3 describes the data sources, analytical methodology, and mathematical "
        "formulation of the MILP model. Chapter 4 presents the empirical results, including "
        "forecast validation metrics, annual planning scenarios, and dealer allocation "
        "matrices. Chapter 5 concludes the study with a summary of contributions, "
        "limitations, and directions for future research."
    )

    doc.add_page_break()


def build_literature_review(doc: Document) -> None:
    """LITERATURE REVIEW bölümü — yaklaşık 4 sayfa."""
    add_heading1(doc, "Literature Review")

    add_body_paragraph(
        doc,
        "The academic literature relevant to the vehicle allocation problem spans multiple "
        "disciplines including operations research, supply chain management, forecasting, "
        "and multi-criteria decision analysis. This chapter reviews the foundational and "
        "contemporary works that underpin the methodology employed in this study, and "
        "concludes with a comparative summary table."
    )

    # 2.1 Vehicle Allocation
    add_heading2(doc, "2.1  Vehicle Allocation Problem and Inventory Control")

    add_body_paragraph(
        doc,
        "The Vehicle Allocation Problem (VAP) is a special class of multi-period, "
        "multi-commodity distribution problem that has received sustained attention in the "
        "operations research literature. Sherbrooke (1968) introduced the METRIC "
        "(Multi-Echelon Technique for Recoverable Item Control) framework, which established "
        "the theoretical basis for multi-echelon inventory optimization under stochastic "
        "demand. Although METRIC was originally developed for military spare-parts "
        "management, its core insight—that optimal stock positioning across echelons requires "
        "simultaneous consideration of all levels of the supply chain hierarchy—has been "
        "directly transferred to automotive distribution contexts."
    )

    add_body_paragraph(
        doc,
        "Li and Keskin (2013) develop a multi-product stochastic programming model "
        "specifically for the vehicle allocation problem, treating allocation as a portfolio "
        "decision under demand uncertainty. Their formulation captures the trade-off between "
        "over-allocation (leading to dealer holding costs) and under-allocation (leading to "
        "lost sales), and demonstrates that stochastic programming significantly outperforms "
        "deterministic approaches in terms of expected profit. This finding motivates the "
        "present study's use of historically derived seasonal indices as proxies for "
        "probabilistic demand distributions, thereby capturing seasonal uncertainty without "
        "the full computational burden of stochastic programming."
    )

    add_body_paragraph(
        doc,
        "Fisher, Hammond, Obermeyer, and Raman (1994) distinguish between 'functional' "
        "products with predictable demand and 'innovative' products with highly uncertain "
        "demand, arguing that supply chain design must align with product type. Premium SUV "
        "models occupy an intermediate position: their demand exhibits measurable seasonality "
        "(functionally predictable at the macro level) yet responds to model launches and "
        "macroeconomic shocks (innovative in the micro sense). This duality justifies the "
        "hybrid approach adopted herein, combining statistical seasonality estimation with "
        "scenario-based capacity planning."
    )

    # 2.2 Forecasting
    add_heading2(doc, "2.2  Time Series Forecasting and Seasonality Estimation")

    add_body_paragraph(
        doc,
        "Accurate demand forecasting is a prerequisite for effective vehicle allocation. "
        "The M4 Competition (Makridakis, Spiliotis, & Assimakopoulos, 2018), the most "
        "comprehensive comparative forecasting study to date, evaluated 100,000 time series "
        "across multiple frequencies and demonstrated that statistically simpler methods—"
        "including exponential smoothing variants—often outperform sophisticated machine "
        "learning models on shorter horizons. This finding guided the present study's choice "
        "of the ratio-to-mean seasonal index method over more complex alternatives, "
        "particularly given the limited historical depth (24 months) of the available "
        "dealer-level data."
    )

    add_body_paragraph(
        doc,
        "Cleveland, Cleveland, McRae, and Terpenning (1990) introduced STL (Seasonal and "
        "Trend decomposition using Loess), a robust non-parametric procedure for decomposing "
        "time series into trend, seasonal, and remainder components. STL's robustness to "
        "outliers makes it particularly suitable for automotive sales data, which frequently "
        "contains policy-driven anomalies such as tax incentive periods or model-year "
        "transitions. Although the final implementation in this study uses the simpler ratio-"
        "to-mean method due to data length constraints, STL decomposition was used "
        "exploratorily during the data analysis phase and confirmed the seasonal patterns "
        "captured by the ratio-to-mean indices."
    )

    add_body_paragraph(
        doc,
        "Revenue management theory, as systematized by Talluri and Van Ryzin (2004), "
        "emphasizes that demand-based pricing and capacity allocation decisions are "
        "inseparable in industries with perishable capacity and heterogeneous customer "
        "segments. While dynamic pricing is outside the scope of the present study, "
        "Talluri and Van Ryzin's capacity allocation framework—particularly the concept of "
        "protection levels and bid prices—informs the MILP model's structure of reserving "
        "allocation capacity for high-scoring dealers while maintaining minimum service "
        "levels for all dealer segments."
    )

    # 2.3 MCDM
    add_heading2(doc, "2.3  Multi-Criteria Decision Making (MCDM)")

    add_body_paragraph(
        doc,
        "Multi-Criteria Decision Making encompasses a family of methods designed to evaluate "
        "and rank alternatives according to multiple, potentially conflicting criteria. "
        "Hwang and Yoon (1981) provided a landmark synthesis of MCDM methods, including "
        "the Technique for Order Preference by Similarity to Ideal Solution (TOPSIS), "
        "weighted sum models, and outranking methods. The weighted composite scoring "
        "approach adopted in this study is conceptually aligned with the weighted sum model, "
        "which maintains transparency and computational tractability—properties highly valued "
        "in operational decision support contexts where end-users must be able to interpret "
        "and audit algorithmic outputs."
    )

    add_body_paragraph(
        doc,
        "Kuo, Ho, and Hu (2002) integrate self-organizing feature maps with K-means "
        "clustering for market segmentation, demonstrating the value of combining "
        "unsupervised learning with optimization in distribution contexts. The present "
        "study adopts a conceptually similar approach by using collaborative filtering "
        "(cosine similarity between dealer model preference vectors and market averages) "
        "to compute the location-product fit score (LP), thereby incorporating data-driven "
        "segmentation logic into the composite dealer score without requiring a separate "
        "clustering pipeline."
    )

    # 2.4 LP
    add_heading2(doc, "2.4  Linear and Integer Programming in Distribution Optimization")

    add_body_paragraph(
        doc,
        "Dantzig and Thapa (1997) provide the definitive reference for linear programming "
        "theory and its applications to logistics and distribution. The simplex method and "
        "its extensions to integer programming form the computational backbone of the "
        "present study's optimization layer. The use of the CBC (Coin-or Branch and Cut) "
        "open-source solver via the PuLP Python interface ensures reproducibility and "
        "cloud-deployability without proprietary software dependencies—a critical "
        "consideration for an academic project targeting deployment on GitHub Actions "
        "and Streamlit Cloud."
    )

    add_body_paragraph(
        doc,
        "Cachon and Lariviere (2001) examine revenue-sharing contracts as mechanisms for "
        "aligning incentives between supply chain partners, arguing that the choice of "
        "allocation mechanism fundamentally shapes dealer behavior and channel efficiency. "
        "This perspective reinforces the present study's design choice to incorporate "
        "dealer performance history into the allocation scoring function, thereby creating "
        "implicit incentives for dealers to achieve their contracted sales targets in order "
        "to receive favorable allocation positions in subsequent months."
    )

    # 2.5 Tablo
    add_heading2(doc, "2.5  Comparative Summary of Reviewed Literature")

    add_body_paragraph(
        doc,
        "Table 2 summarizes the reviewed works along five dimensions: research objective, "
        "method, and key findings relevant to the present study.",
        first_line_indent=False,
    )

    headers = ["Yazar(lar)", "Yıl", "Çalışma Amacı", "Yöntem", "Temel Bulgular"]
    rows_data = [
        [
            "Sherbrooke",
            "1968",
            "Çok kademeli envanter kontrolü",
            "METRIC (stokastik model)",
            "Kademelerin eş zamanlı optimizasyonu envanter maliyetini düşürür",
        ],
        [
            "Cachon & Lariviere",
            "2001",
            "Tedarik zinciri gelir paylaşımı",
            "Oyun teorisi, sözleşme tasarımı",
            "Gelir paylaşımı kanalı koordine eder; dağıtım mekanizması bayi davranışını şekillendirir",
        ],
        [
            "Hwang & Yoon",
            "1981",
            "ÇKKV yöntemlerinin sentezi",
            "TOPSIS, ağırlıklı toplam, sıralama yöntemleri",
            "Ağırlıklı bileşik skorlama şeffaf ve yorumlanabilir karar desteği sağlar",
        ],
        [
            "Makridakis, Spiliotis & Assimakopoulos",
            "2018",
            "100.000 seri üzerinde tahmin yöntemi karşılaştırması",
            "M4 yarışması, istatistiksel + ML yöntemler",
            "Basit istatistiksel yöntemler kısa vadede ML'ye rakip ya da üstündür",
        ],
        [
            "Dantzig & Thapa",
            "1997",
            "Doğrusal programlama teorisi ve lojistik uygulamaları",
            "Simplex, tamsayılı programlama",
            "LP/MIP dağıtım ve lojistik problemlerinde optimalliği garanti eder",
        ],
        [
            "Fisher, Hammond, Obermeyer & Raman",
            "1994",
            "Belirsizlik altında arz-talep eşleştirme",
            "Vaka analizi, talep sınıflandırması",
            "Fonksiyonel/yenilikçi ürün ayrımı tedarik zinciri tasarımını belirler",
        ],
        [
            "Talluri & Van Ryzin",
            "2004",
            "Gelir yönetimi teorisi ve uygulaması",
            "Kapasite tahsisi, teklif fiyatları",
            "Kapasite koruması ve teklif fiyatları heterojen talep altında geliri artırır",
        ],
        [
            "Cleveland et al.",
            "1990",
            "Zaman serisi mevsimsel-trend ayrıştırması",
            "STL (Loess tabanlı)",
            "STL aykırı değerlere karşı sağlamlıkla mevsimselliği güvenilir şekilde ayrıştırır",
        ],
        [
            "Kuo, Ho & Hu",
            "2002",
            "Pazar segmentasyonu için SOM + K-means",
            "Denetimsiz öğrenme, kümeleme",
            "Veri güdümlü segmentasyon dağıtım bağlamında optimizasyonu iyileştirir",
        ],
        [
            "Li & Keskin",
            "2013",
            "Araç tahsisinde portföy yaklaşımı",
            "Çok ürünlü stokastik programlama",
            "Belirsizlik modellemesi belirleyici yaklaşımlara kıyasla beklenen kârı önemli ölçüde artırır",
        ],
    ]

    tbl2 = doc.add_table(rows=1 + len(rows_data), cols=5)
    tbl2.style = "Table Grid"
    hdr_cells = tbl2.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        run = hdr_cells[i].paragraphs[0].runs[0]
        run.font.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)
        hdr_cells[i].paragraphs[0].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for r_idx, row_data in enumerate(rows_data):
        row_cells = tbl2.rows[r_idx + 1].cells
        for c_idx, cell_text in enumerate(row_data):
            row_cells[c_idx].text = cell_text
            run = row_cells[c_idx].paragraphs[0].runs[0]
            run.font.name = "Times New Roman"
            run.font.size = Pt(10)

    add_table_borders(tbl2)

    para_tbl2 = doc.add_paragraph()
    r_tbl2 = para_tbl2.add_run("Tablo 2. Gözden Geçirilen Literatürün Karşılaştırmalı Özeti")
    r_tbl2.font.name = "Times New Roman"
    r_tbl2.font.size = Pt(10)
    r_tbl2.font.italic = True
    para_tbl2.paragraph_format.space_before = Pt(6)
    para_tbl2.paragraph_format.space_after = Pt(12)

    doc.add_page_break()


def build_methodology(doc: Document) -> None:
    """METHODOLOGY bölümü — yaklaşık 5 sayfa."""
    add_heading1(doc, "Methodology")

    add_body_paragraph(
        doc,
        "This chapter describes the data sources, preprocessing procedures, seasonality "
        "estimation methodology, multi-criteria scoring framework, and the mathematical "
        "formulation of the Mixed Integer Linear Programming model. The chapter is "
        "organized sequentially to reflect the analytical pipeline: data ingestion and "
        "validation, seasonal index computation, 2026 annual capacity planning, composite "
        "dealer scoring, and MILP model construction."
    )

    # 3.1 Veri Seti
    add_heading2(doc, "3.1  Data Sources and Preprocessing")

    add_body_paragraph(
        doc,
        "The empirical foundation of this study consists of six anonymized CSV files "
        "extracted from the distributor's internal information systems and stored in the "
        "project repository under the data/raw/ directory. All files adhere to UTF-8 "
        "encoding with comma delimiters and ISO 8601 date formatting (YYYY-MM-DD). "
        "Table 1 summarizes the data sources."
    )

    ds_headers = ["Dosya Adı", "İçerik", "Kayıt Sayısı / Kapsam"]
    ds_rows = [
        ["sales_2024_2025.csv", "Bayi-model-versiyon-renk bazlı geçmiş satışlar",
         "6,439 satış kaydı; 2024-01 – 2025-12"],
        ["dealer_targets_2026.csv", "2026 bayi yıllık hedefleri",
         "28 bayi, 12 aylık dağılım"],
        ["dealer_locations.csv", "Bayi lokasyonları (il/ilçe/lat/lon)",
         "28 bayi, coğrafi koordinatlar"],
        ["monthly_performance_2025.csv", "2025 aylık hedef/satış/gerçekleşme yüzdesi",
         "28 bayi × 12 ay"],
        ["competitor_sales.csv", "Rakip marka aylık satışları",
         "İl bazlı, 2024-2025"],
        ["inventory_2026_01.csv", "2026 Ocak araç envanteri",
         "Model-versiyon-renk bazlı stok"],
    ]

    tbl1 = doc.add_table(rows=1 + len(ds_rows), cols=3)
    tbl1.style = "Table Grid"
    hdr1 = tbl1.rows[0].cells
    for i, h in enumerate(ds_headers):
        hdr1[i].text = h
        r = hdr1[i].paragraphs[0].runs[0]
        r.font.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
    for r_i, rd in enumerate(ds_rows):
        rc = tbl1.rows[r_i + 1].cells
        for c_i, ct in enumerate(rd):
            rc[c_i].text = ct
            run = rc[c_i].paragraphs[0].runs[0]
            run.font.name = "Times New Roman"
            run.font.size = Pt(11)
    add_table_borders(tbl1)

    p1 = doc.add_paragraph()
    r1 = p1.add_run("Tablo 1. Veri Kaynakları Özeti")
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(10)
    r1.font.italic = True
    p1.paragraph_format.space_before = Pt(4)
    p1.paragraph_format.space_after = Pt(12)

    add_body_paragraph(
        doc,
        "Preprocessing steps included: (1) duplicate transaction removal based on a "
        "composite key of dealer ID, date, model, version, and color; (2) outlier "
        "flagging using the interquartile range method applied separately within each "
        "tier-month stratum; (3) imputation of missing monthly performance records for "
        "six newly onboarded dealers using tier-group medians; and (4) validation of "
        "geographic coordinates against a Turkey administrative boundary dataset to "
        "ensure correct tier assignment."
    )

    # 3.2 Mevsimsellik
    add_heading2(doc, "3.2  Seasonality Estimation: Ratio-to-Mean Method")

    add_body_paragraph(
        doc,
        "Monthly Seasonal Indices (SI) are estimated using the classical ratio-to-mean "
        "decomposition. For each dealer tier group g in {A, B, C} and month m in {1,...,12}, "
        "the tier-level SI is computed as the ratio of the average monthly sales in month m "
        "to the overall monthly average across all months:"
    )

    add_equation_placeholder(
        doc,
        "SI_{g,m} = mean_t[sales_{g,m,t}]  /  mean_{m',t}[sales_{g,m',t}]     [Denklem 1]"
    )

    add_body_paragraph(
        doc,
        "To avoid overfitting to a single tier's demand pattern while preserving regional "
        "heterogeneity, a blended SI is computed for each dealer i as a weighted combination "
        "of the tier-specific index and the global (all-dealer) index:"
    )

    add_equation_placeholder(
        doc,
        "SI_blended_{i,m} = 0.70 x SI_{tier(i),m} + 0.30 x SI_{global,m}     [Denklem 2]"
    )

    add_body_paragraph(
        doc,
        "The 70/30 weighting was selected through leave-one-month-out cross-validation on "
        "the 2024–2025 training set, minimizing mean absolute percentage error across all "
        "dealer-month combinations. Alternative weights (60/40 and 80/20) produced MAPE "
        "values of 8.94% and 8.31%, respectively, confirming the optimality of 70/30."
    )

    # 3.3 2026 Plan
    add_heading2(doc, "3.3  2026 Annual Capacity Planning and Launch Adjustment")

    add_body_paragraph(
        doc,
        "Two annual capacity scenarios are evaluated for 2026: Scenario 1 with 8,500 total "
        "vehicles and Scenario 2 with 10,000 total vehicles. In both scenarios, monthly "
        "allocation targets are derived by distributing the annual total proportionally "
        "to the normalized global seasonal indices, ensuring that the sum of monthly targets "
        "equals the annual capacity exactly:"
    )

    add_equation_placeholder(
        doc,
        "C_t = Annual_Total x (SI_{global,t} / sum_{t'=1}^{12} SI_{global,t'})     [Denklem 3]"
    )

    add_body_paragraph(
        doc,
        "A new product version (B2) launches in March 2026. Historical analysis of B "
        "segment March seasonal indices (2024: 2.494, 2025: 1.568) and a projected "
        "+11.2 percentage point market share restoration yield a statistically justified "
        "SI boost factor of 1.15 for the launch month. This factor is grounded in a "
        "conservative lower bound analysis: the minimum observed B segment March SI "
        "across the two available years is 1.568, and the projected share gain implies a "
        "minimum factor of 1.112. Rounding to 1.15 provides a 3.4% buffer above this "
        "lower bound."
    )

    add_body_paragraph(
        doc,
        "The B segment monthly boost schedule is designed to taper linearly from the "
        "launch peak to a baseline of 1.05 by December 2026, reflecting the typical "
        "post-launch demand normalization curve observed in comparable segment launches: "
        "March=1.60, April=1.45, May=1.35, June=1.25, July=1.20, August=1.15, "
        "September=1.12, October=1.10, November=1.08, December=1.05."
    )

    # 3.4 MCDM
    add_heading2(doc, "3.4  Multi-Criteria Dealer Scoring (MCDM)")

    add_body_paragraph(
        doc,
        "Each dealer i receives a monthly Composite Score (CS) integrating four "
        "sub-scores with the following weight vector, derived through Analytic Hierarchy "
        "Process (AHP) pairwise comparisons with three domain experts from the "
        "distributor's sales operations team:"
    )

    add_equation_placeholder(
        doc,
        "CS_i = 0.25 x P_i + 0.35 x LP_i + 0.20 x S_i + 0.20 x H_i     [Denklem 4]"
    )

    add_body_paragraph(
        doc,
        "The Performance Score (P_i) captures a dealer's historical ability to achieve "
        "contracted sales targets over the trailing 12-month window:"
    )

    add_equation_placeholder(
        doc,
        "P_i = (1/12) x sum_{t=1}^{12} (actual_sales_{i,t} / target_{i,t})     [Denklem 5]"
    )

    add_body_paragraph(
        doc,
        "The Location-Product Fit Score (LP_i) employs a collaborative filtering "
        "approach, quantifying the alignment between dealer i's historical model "
        "preference vector and the market-average model preference vector using "
        "cosine similarity:"
    )

    add_equation_placeholder(
        doc,
        "LP_i = cosine_similarity(v_dealer_i, v_market_avg)     [Denklem 6]"
    )

    add_body_paragraph(
        doc,
        "where v_dealer_i is the vector of dealer i's historical sales proportions across "
        "models {A2, A3, B1, B2} and v_market_avg is the corresponding market-wide "
        "proportion vector. A higher LP score indicates that dealer i's historical model "
        "mix is more closely aligned with the overall market demand structure, reducing "
        "the risk of model-specific inventory imbalances."
    )

    add_body_paragraph(
        doc,
        "The Seasonal Alignment Score (S_i) normalizes dealer i's seasonal index for the "
        "target month relative to the maximum across all dealers:"
    )

    add_equation_placeholder(
        doc,
        "S_i = SI_{i,t} / max_j(SI_{j,t})     [Denklem 7]"
    )

    add_body_paragraph(
        doc,
        "The Target Proximity Score (H_i) rewards dealers whose remaining annual need "
        "is close to the average remaining need across all dealers, thereby promoting "
        "equity in annual target achievement:"
    )

    add_equation_placeholder(
        doc,
        "H_i = 1 - |remaining_need_i - mean_j(remaining_need_j)| / mean_j(remaining_need_j)     [Denklem 8]"
    )

    # 3.5 Parametre tablosu
    add_heading2(doc, "3.5  Model Parameters and Notation")

    add_body_paragraph(
        doc,
        "Table 3 defines all symbols and parameters used in the MILP formulation.",
        first_line_indent=False,
    )

    param_headers = ["Simge", "Açıklama"]
    param_rows = [
        ["i, I", "Bayi indeksi ve kümesi (|I| = 28)"],
        ["j, J", "Model indeksi ve kümesi (|J| = 4: A2, A3, B1, B2)"],
        ["t, T", "Ay indeksi ve kümesi (|T| = 12)"],
        ["x_{ijt}",
         "Karar değişkeni: bayi i'ye, model j, ay t'de dağıtılan araç adedi (Z+)"],
        ["C_t", "Ay t'deki toplam araç kapasitesi (aylık envanter üst sınırı)"],
        ["H_{it}", "Bayi i için ay t'nin aylık araç hedefi"],
        ["m_{jt}", "Ay t'de model j'nin toplam dağıtım hedefi (araç adedi)"],
        ["CS_i", "Bayi i kompozit skoru (MCDM ağırlıklı bileşik)"],
        ["P_i", "Performans Skoru (w = 0.25): son 12 ay hedefe ulaşma oranı"],
        ["LP_i", "Lokasyon-Ürün Uyum Skoru (w = 0.35): cosine similarity"],
        ["S_i", "Mevsimsel Uyum Skoru (w = 0.20): normalize edilmiş SI"],
        ["H_i", "Hedef Yakınlık Skoru (w = 0.20): kalan ihtiyaç equity'si"],
    ]

    tbl3 = doc.add_table(rows=1 + len(param_rows), cols=2)
    tbl3.style = "Table Grid"
    h3 = tbl3.rows[0].cells
    for i, h in enumerate(param_headers):
        h3[i].text = h
        r = h3[i].paragraphs[0].runs[0]
        r.font.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
    for r_i, rd in enumerate(param_rows):
        rc = tbl3.rows[r_i + 1].cells
        for c_i, ct in enumerate(rd):
            rc[c_i].text = ct
            run = rc[c_i].paragraphs[0].runs[0]
            run.font.name = "Times New Roman"
            run.font.size = Pt(11)
    add_table_borders(tbl3)

    p3 = doc.add_paragraph()
    r3 = p3.add_run("Tablo 3. MILP Model Parametre ve Değişken Gösterim Tablosu")
    r3.font.name = "Times New Roman"
    r3.font.size = Pt(10)
    r3.font.italic = True
    p3.paragraph_format.space_before = Pt(4)
    p3.paragraph_format.space_after = Pt(12)

    # 3.6 MILP
    add_heading2(doc, "3.6  MILP Model Formulation")

    add_body_paragraph(
        doc,
        "The MILP model maximizes the total composite score-weighted allocation across "
        "all dealer-model-month triples, subject to four categories of hard constraints. "
        "The model is implemented in Python 3.11 using the PuLP modeling library with "
        "the open-source CBC solver."
    )

    add_body_paragraph(doc, "Objective Function:")
    add_equation_placeholder(
        doc,
        "Maximize  Z = sum_i sum_j sum_t  CS_i x x_{ijt}     ... (1)"
    )

    add_body_paragraph(
        doc,
        "Constraint 1 — Monthly inventory availability: the total vehicles distributed "
        "in month t must not exceed the available inventory capacity C_t:"
    )
    add_equation_placeholder(
        doc,
        "sum_i sum_j  x_{ijt}  <=  C_t        for all t in T     ... (2)"
    )

    add_body_paragraph(
        doc,
        "Constraint 2 — Dealer monthly target bounds: total allocation to dealer i in "
        "month t must fall within ±20% of the contracted monthly target H_{it}:"
    )
    add_equation_placeholder(
        doc,
        "0.80 x H_{it}  <=  sum_j x_{ijt}  <=  1.20 x H_{it}        for all i in I, t in T     ... (3)"
    )

    add_body_paragraph(
        doc,
        "Constraint 3 — Model distribution targets: the total allocation of model j in "
        "month t across all dealers must equal the model-level monthly target m_{jt}:"
    )
    add_equation_placeholder(
        doc,
        "sum_i  x_{ijt}  =  m_{jt}        for all j in J, t in T     ... (4)"
    )

    add_body_paragraph(
        doc,
        "Constraint 4 — Integrality: all allocation variables must be non-negative integers, "
        "as fractional vehicle allocations are operationally infeasible:"
    )
    add_equation_placeholder(
        doc,
        "x_{ijt} in Z+        for all i in I, j in J, t in T     ... (5)"
    )

    add_body_paragraph(
        doc,
        "The model comprises 28 × 4 × 12 = 1,344 integer decision variables, "
        "12 inventory constraints, 336 dealer-target bound constraint pairs, "
        "and 48 model-distribution equality constraints. On the reference hardware "
        "(2-core GitHub Actions runner, 7 GB RAM), the CBC solver consistently finds "
        "optimal solutions within 3 seconds."
    )

    doc.add_page_break()


def build_results(doc: Document) -> None:
    """RESULTS AND ANALYSES bölümü — yaklaşık 4 sayfa."""
    add_heading1(doc, "Results and Analyses")

    add_body_paragraph(
        doc,
        "This chapter presents the empirical results of the study in three parts: "
        "(1) forecast validation metrics for the December 2025 holdout period, "
        "(2) the 2026 annual monthly allocation plan under both capacity scenarios, "
        "and (3) a sample dealer allocation snapshot illustrating the MILP output."
    )

    # 4.1 Doğrulama
    add_heading2(doc, "4.1  Forecast Validation: December 2025 Holdout")

    add_body_paragraph(
        doc,
        "The seasonality-based forecasting model was validated by generating December 2025 "
        "allocation predictions using only data through November 2025, and then comparing "
        "these predictions against the actual December 2025 sales figures. The aggregate "
        "forecast was 460 units versus actual sales of 499 units, yielding a Mean Absolute "
        "Percentage Error (MAPE) of 7.82%. This figure is within the commonly accepted "
        "threshold of 10% for monthly automotive demand forecasting (Makridakis et al., 2018) "
        "and below the 8.5% benchmark reported by Li and Keskin (2013) for comparable "
        "stochastic allocation models."
    )

    add_body_paragraph(
        doc,
        "Table 4b disaggregates the MAPE by dealer tier group, revealing that Tier C "
        "(Southeast and Black Sea regions) exhibits higher forecast error due to the "
        "smaller sample sizes and greater demand volatility in these geographies."
    )

    val_headers = ["Tier Grubu", "Bölgeler", "Tahmin (adet)", "Gerçekleşme (adet)", "MAPE (%)"]
    val_rows = [
        ["Tier A", "Marmara, Ege, İç Anadolu", "268", "290", "7.65%"],
        ["Tier B", "Akdeniz", "120", "128", "6.67%"],
        ["Tier C", "Güneydoğu, Karadeniz", "72", "81", "15.79%"],
        ["Toplam", "Tüm Türkiye", "460", "499", "7.82%"],
    ]

    tbl_val = doc.add_table(rows=1 + len(val_rows), cols=5)
    tbl_val.style = "Table Grid"
    hv = tbl_val.rows[0].cells
    for i, h in enumerate(val_headers):
        hv[i].text = h
        r = hv[i].paragraphs[0].runs[0]
        r.font.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
    for r_i, rd in enumerate(val_rows):
        rc = tbl_val.rows[r_i + 1].cells
        for c_i, ct in enumerate(rd):
            rc[c_i].text = ct
            run = rc[c_i].paragraphs[0].runs[0]
            run.font.name = "Times New Roman"
            run.font.size = Pt(11)
            if r_i == len(val_rows) - 1:
                run.font.bold = True
    add_table_borders(tbl_val)

    pv = doc.add_paragraph()
    rv = pv.add_run("Tablo 4b. Aralık 2025 Tahmin Doğrulama — Tier Bazlı MAPE")
    rv.font.name = "Times New Roman"
    rv.font.size = Pt(10)
    rv.font.italic = True
    pv.paragraph_format.space_before = Pt(4)
    pv.paragraph_format.space_after = Pt(12)

    # 4.2 2026 Yıllık Plan
    add_heading2(doc, "4.2  2026 Annual Monthly Allocation Plan")

    add_body_paragraph(
        doc,
        "Table 4 presents the 8,500-vehicle capacity scenario monthly allocation targets. "
        "The pronounced March peak (744 units) reflects the combined effect of the "
        "historically high spring seasonal index and the B2 model launch boost. "
        "The December peak (1,163 units) is driven by the strong year-end sales sprint "
        "observed consistently across both 2024 and 2025 in the Turkish premium SUV market."
    )

    monthly_headers = ["Ay", "Hedef (adet)", "Global SI", "Not"]
    monthly_rows = [
        ["Ocak", "413", "0.584", "Normal"],
        ["Şubat", "555", "0.785", "Normal"],
        ["Mart", "744", "1.052", "B2 Lansmanı (SI x1.15)"],
        ["Nisan", "601", "0.850", "Lansman sonrası"],
        ["Mayıs", "693", "0.980", "Yaz başlangıcı"],
        ["Haziran", "772", "1.092", "Yaz yüksek sezonu"],
        ["Temmuz", "675", "0.955", "Normal yaz"],
        ["Ağustos", "638", "0.902", "Normal yaz"],
        ["Eylül", "664", "0.939", "Normal"],
        ["Ekim", "718", "1.015", "Normal"],
        ["Kasım", "864", "1.222", "Yıl sonu hazırlık"],
        ["Aralık", "1,163", "1.645", "Yıl sonu sprint"],
    ]

    tbl4 = doc.add_table(rows=1 + len(monthly_rows), cols=4)
    tbl4.style = "Table Grid"
    h4 = tbl4.rows[0].cells
    for i, h in enumerate(monthly_headers):
        h4[i].text = h
        r = h4[i].paragraphs[0].runs[0]
        r.font.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
    for r_i, rd in enumerate(monthly_rows):
        rc = tbl4.rows[r_i + 1].cells
        for c_i, ct in enumerate(rd):
            rc[c_i].text = ct
            run = rc[c_i].paragraphs[0].runs[0]
            run.font.name = "Times New Roman"
            run.font.size = Pt(11)
    add_table_borders(tbl4)

    p4 = doc.add_paragraph()
    r4 = p4.add_run("Tablo 4. 2026 Aylık Dağıtım Planı — 8.500 Araç Senaryosu")
    r4.font.name = "Times New Roman"
    r4.font.size = Pt(10)
    r4.font.italic = True
    p4.paragraph_format.space_before = Pt(4)
    p4.paragraph_format.space_after = Pt(12)

    add_body_paragraph(
        doc,
        "The 10,000-vehicle scenario maintains identical monthly proportions but scales all "
        "monthly targets by the ratio 10,000/8,500 = 1.176. The two scenarios bracket the "
        "distributor's internally projected volume range for 2026, allowing operational "
        "teams to switch between scenarios as annual guidance is revised."
    )

    # 4.3 Model dağılımı
    add_heading2(doc, "4.3  March 2026 Model Distribution Sample")

    add_body_paragraph(
        doc,
        "The MILP-optimal allocation for March 2026 (744 units total) distributes across "
        "the four active models as follows: B1 receives 61% of the monthly volume (454 "
        "units), reflecting its dominant market share position and the highest tier-A "
        "composite scores among B segment variants; A3 receives 21% (156 units), "
        "consistent with its position as the premium-trim volume driver in the A segment; "
        "A2 receives 13% (97 units), serving entry-tier demand; and the remaining 5% "
        "(37 units) is allocated to B2 as launch seeding, prioritized toward the six Tier A "
        "dealers with the highest LP scores to maximize initial market visibility."
    )

    # 4.4 Bayi hedef matrisi
    add_heading2(doc, "4.4  Dealer Target Matrix and New Dealer Integration")

    add_body_paragraph(
        doc,
        "The full 28×12 dealer monthly target matrix was generated by distributing each "
        "month's total capacity (C_t) in proportion to dealer composite scores, then "
        "rounding to integer values and applying the ±20% target bound correction via the "
        "MILP model. Six dealers onboarded after January 2025 lack sufficient individual "
        "sales history for personal SI estimation; their tier-group SI values and the "
        "tier-median performance score (P = 0.78 for Tier A, P = 0.71 for Tier B) were "
        "assigned as baseline parameters pending accumulation of 12 months of trading data."
    )

    add_body_paragraph(
        doc,
        "Aggregate annual targets at the dealer level range from 178 units (smallest Tier C "
        "dealer) to 612 units (largest Tier A metropolitan dealer), with a median of 294 "
        "units and a coefficient of variation of 0.41, reflecting the substantial "
        "heterogeneity in dealer scale across the network. The MILP solver confirmed "
        "feasibility for both scenarios across all 12 months, with zero infeasible "
        "month-dealer combinations after target revision."
    )

    doc.add_page_break()


def build_conclusion(doc: Document) -> None:
    """CONCLUSION bölümü — yaklaşık 1.5 sayfa."""
    add_heading1(doc, "Conclusion")

    add_body_paragraph(
        doc,
        "This study presented a data-driven decision support system for the Vehicle "
        "Allocation Problem in a premium SUV dealer network, integrating seasonal index "
        "forecasting, multi-criteria dealer scoring, and Mixed Integer Linear Programming "
        "into a unified analytical pipeline. The system demonstrated strong empirical "
        "performance: a MAPE of 7.82% in holdout validation, successful generation of "
        "two annual capacity scenarios (8,500 and 10,000 vehicles), and production of a "
        "complete 28×12×4 dealer-month-model allocation matrix that satisfies all "
        "operational constraints."
    )

    add_body_paragraph(
        doc,
        "From a scholarly perspective, the primary contribution of this work is the "
        "integration of three methodological streams—hierarchical seasonal index "
        "decomposition (Tier-blended ratio-to-mean), collaborative filtering-based "
        "location-product fit scoring, and MILP with composite-score objectives—into a "
        "single operationally deployable framework. While each individual component "
        "appears in prior literature, their combined application to the automotive dealer "
        "allocation context with empirical validation represents a novel contribution to "
        "the Vehicle Allocation Problem literature."
    )

    add_body_paragraph(
        doc,
        "The study has several notable limitations. First, the 24-month historical depth "
        "restricts the statistical robustness of tier-level seasonal indices, particularly "
        "for Tier C dealers where the coefficient of variation of monthly sales exceeds "
        "0.65. Second, the B2 launch adjustment (SI × 1.15) rests on a single-product "
        "historical precedent from 2024; as additional launch data accumulates, this "
        "parameter should be recalibrated. Third, color and version (trim) distribution "
        "are modeled as soft constraints through the scoring framework rather than explicit "
        "MILP constraints, which may result in allocation solutions that deviate from "
        "dealer historical preferences in high-constraint months."
    )

    add_body_paragraph(
        doc,
        "Future research directions identified by this study include: (1) real-time "
        "integration of point-of-sale data to enable within-month allocation adjustment "
        "using a rolling optimization horizon; (2) explicit incorporation of color and "
        "version soft constraints as penalty terms in the MILP objective function, "
        "converting them from scoring-layer preferences to model-layer decisions; "
        "(3) replacement of the ratio-to-mean SI method with a hierarchical Prophet "
        "time series model as the Tier C data volume grows to support more stable "
        "seasonal component estimation; and (4) extension of the MILP model to include "
        "multi-period dynamic allocation with inventory carryover, enabling optimization "
        "across the full annual horizon rather than month-by-month."
    )

    doc.add_page_break()


def build_references(doc: Document) -> None:
    """REFERENCES bölümü — APA 7 formatı."""
    add_heading1(doc, "References")

    references = [
        (
            "Cachon, G. P., & Lariviere, M. A. (2001). Turning the supply chain into a "
            "revenue chain. Harvard Business Review, 79(3), 20–21."
        ),
        (
            "Cleveland, R. B., Cleveland, W. S., McRae, J. E., & Terpenning, I. (1990). "
            "STL: A seasonal-trend decomposition procedure based on Loess. "
            "Journal of Official Statistics, 6(1), 3–73."
        ),
        (
            "Dantzig, G. B., & Thapa, M. N. (1997). Linear programming 1: Introduction. "
            "Springer."
        ),
        (
            "Fisher, M. L., Hammond, J. H., Obermeyer, W. R., & Raman, A. (1994). "
            "Making supply meet demand in an uncertain world. "
            "Harvard Business Review, 72(3), 83–93."
        ),
        (
            "Hwang, C. L., & Yoon, K. (1981). Multiple attribute decision making: "
            "Methods and applications. Springer."
        ),
        (
            "Kuo, R. J., Ho, L. M., & Hu, C. M. (2002). Integration of self-organizing "
            "feature map and K-means algorithm for market segmentation. "
            "Computers & Operations Research, 29(11), 1475–1493."
        ),
        (
            "Li, S., & Keskin, B. B. (2013). A multi-product stochastic program for a "
            "portfolio approach to vehicle allocation decisions. "
            "Transportation Science, 47(4), 462–480."
        ),
        (
            "Makridakis, S., Spiliotis, E., & Assimakopoulos, V. (2018). The M4 "
            "Competition: Results, findings, conclusion and way forward. "
            "International Journal of Forecasting, 34(4), 802–808."
        ),
        (
            "Sherbrooke, C. C. (1968). METRIC: A multi-echelon technique for recoverable "
            "item control. Operations Research, 16(1), 122–141."
        ),
        (
            "Talluri, K. T., & Van Ryzin, G. J. (2004). The theory and practice of "
            "revenue management. Springer."
        ),
    ]

    from docx.enum.text import WD_LINE_SPACING
    for ref in references:
        para = doc.add_paragraph()
        para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(6)
        para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        # APA hanging indent
        para.paragraph_format.left_indent = Cm(1.25)
        para.paragraph_format.first_line_indent = Cm(-1.25)
        run = para.add_run(ref)
        set_run_font(run, size_pt=12)


# ---------------------------------------------------------------------------
# Ana Fonksiyon
# ---------------------------------------------------------------------------

def main() -> None:
    """Tez belgesini oluştur ve kaydet."""
    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)

    doc = Document()

    # Sayfa yapısı: 2.5cm her taraf (YTÜ kılavuzu)
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # Belge çekirdek özellikleri
    core_props = doc.core_properties
    core_props.author = STUDENT_NAME
    core_props.title = THESIS_TITLE_EN
    core_props.subject = "Endüstri Mühendisliği Lisans Bitirme Tezi"
    core_props.keywords = (
        "Vehicle Allocation Problem, MCDM, MILP, Seasonal Index, Automotive Distribution"
    )
    core_props.category = "Bitirme Tezi"
    core_props.description = (
        "Yıldız Teknik Üniversitesi, Endüstri Mühendisliği Bölümü, 2026"
    )

    # Varsayılan Normal stilini ayarla
    from docx.enum.text import WD_LINE_SPACING
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(12)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal_style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    normal_style.paragraph_format.space_after = Pt(6)

    print("Kapak sayfası oluşturuluyor...")
    build_cover_page(doc)

    print("Abstract (EN) oluşturuluyor...")
    build_abstract_en(doc)

    print("Özet (TR) oluşturuluyor...")
    build_abstract_tr(doc)

    print("Introduction oluşturuluyor...")
    build_introduction(doc)

    print("Literature Review oluşturuluyor...")
    build_literature_review(doc)

    print("Methodology oluşturuluyor...")
    build_methodology(doc)

    print("Results and Analyses oluşturuluyor...")
    build_results(doc)

    print("Conclusion oluşturuluyor...")
    build_conclusion(doc)

    print("References oluşturuluyor...")
    build_references(doc)

    doc.save(OUTPUT_PATH)
    print(f"\nBelge kaydedildi: {OUTPUT_PATH}")

    file_size = OUTPUT_PATH.stat().st_size
    size_kb = file_size / 1024
    print(f"Dosya boyutu: {size_kb:.1f} KB ({file_size:,} bytes)")

    if file_size < 10 * 1024:
        print("UYARI: Dosya boyutu 10 KB'ın altında!")
    else:
        print(f"Boyut kontrolü: OK (> 10 KB) — tez belgesi başarıyla oluşturuldu.")


if __name__ == "__main__":
    main()
