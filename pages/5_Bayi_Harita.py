"""Bayi Bölge Haritası sayfası."""

from __future__ import annotations

from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Bayi Bölge Haritası",
    page_icon="🗺️",
    layout="wide",
)

ROOT = Path(__file__).parents[1]

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
REGION_COLORS: dict[str, str] = {
    "Marmara":             "#E53935",   # Kırmızı
    "Ege":                 "#1E88E5",   # Mavi
    "Akdeniz":             "#F57C00",   # Turuncu
    "İç Anadolu":          "#43A047",   # Yeşil
    "Karadeniz":           "#00ACC1",   # Cyan
    "Güneydoğu Anadolu":  "#8E24AA",   # Mor
    "Doğu Anadolu":        "#6D4C41",   # Kahve
}

REGION_ICONS: dict[str, str] = {
    "Marmara":             "building",
    "Ege":                 "leaf",
    "Akdeniz":             "sun-o",
    "İç Anadolu":          "map-marker",
    "Karadeniz":           "tint",
    "Güneydoğu Anadolu":  "star",
    "Doğu Anadolu":        "mountain",
}

# Türkiye bölge sınırlarını gerçek coğrafyaya yakın koordinatlarla tanımlar.
# İç seam'lar _classify() kurallarını izler; dış sınırlar Türkiye kıyı/sınır
# hatlarına yaklaşık olarak uydurulmuştur.
REGION_POLYGONS: dict[str, list[tuple[float, float]]] = {
    # Kuzeybatı: Edirne–Karadeniz kıyısı–Bolu–Bursa–Çanakkale
    "Marmara": [
        (40.0, 26.2), (40.6, 26.3), (41.7, 26.6),
        (41.9, 27.5), (41.8, 28.5), (41.4, 29.1),
        (41.1, 30.2), (41.5, 32.0),
        (40.0, 32.0),
    ],
    # Kuzey: Zonguldak'tan Artvin'e Karadeniz kıyısı
    "Karadeniz": [
        (40.0, 32.0), (41.5, 32.0),
        (41.7, 33.5), (41.5, 35.0), (41.3, 36.5),
        (41.1, 38.0), (41.3, 40.5), (41.5, 41.5),
        (41.5, 43.5), (40.3, 44.5),
        (40.0, 44.5),
    ],
    # Batı: Çanakkale'den Fethiye'ye Ege kıyısı
    "Ege": [
        (40.0, 26.2), (40.0, 30.5),
        (37.5, 30.5), (36.4, 30.5),
        (36.5, 29.5), (36.8, 27.5), (37.0, 27.0),
        (37.8, 27.0), (38.3, 26.5), (39.0, 26.3), (39.5, 26.2),
    ],
    # İç: Ankara–Konya–Kayseri–Doğu Anadolu dahil
    "İç Anadolu": [
        (40.0, 30.5), (40.0, 44.5),
        (38.5, 44.5), (37.5, 43.5),
        (37.5, 30.5),
    ],
    # Güney: Antalya'dan Hatay'a Akdeniz kıyısı
    "Akdeniz": [
        (37.5, 30.5), (37.5, 37.0),
        (36.7, 37.0), (36.5, 36.5), (36.5, 35.5),
        (36.2, 33.5), (36.0, 32.5), (36.1, 31.0), (36.4, 30.5),
    ],
    # Güneydoğu: Gaziantep–Diyarbakır–Mardin–Hakkari
    "Güneydoğu Anadolu": [
        (37.5, 37.0), (37.5, 43.5),
        (37.2, 43.5), (37.0, 42.5), (36.8, 41.5),
        (36.7, 40.0), (36.6, 38.5), (36.7, 37.0),
    ],
}


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------
# DEALER 23 ve sonrası aktif değil
INACTIVE_FROM = 23


@st.cache_data
def load_locations() -> pd.DataFrame:
    path = ROOT / "data" / "raw" / "Dealer-Location.csv"
    records = []
    with open(path, encoding="utf-8-sig") as f:
        lines = f.readlines()
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(";")
        if len(parts) < 2:
            continue
        name = parts[0].strip()
        lat_lon = parts[1].strip().split(",")
        try:
            lat = float(lat_lon[0])
            lon = float(lat_lon[1])
        except (ValueError, IndexError):
            continue
        # Aktif / pasif belirle (DEALER N → N'i ayıkla)
        try:
            num = int(name.split()[-1])
            active = num < INACTIVE_FROM
        except ValueError:
            active = True
        records.append({"name": name, "lat": lat, "lon": lon, "active": active})
    df = pd.DataFrame(records)
    df["region"] = df.apply(lambda r: _classify(r["lat"], r["lon"]), axis=1)
    return df


def _classify(lat: float, lon: float) -> str:
    if lat >= 40.0 and lon < 32.0:  return "Marmara"
    if lat >= 40.0 and lon >= 32.0: return "Karadeniz"
    if lon < 30.5 and lat < 40:     return "Ege"
    if lat < 37.5 and lon >= 37.0:  return "Güneydoğu Anadolu"
    if lat < 37.5:                  return "Akdeniz"
    return "İç Anadolu"


df_loc = load_locations()
df_active   = df_loc[df_loc["active"]].copy()
df_inactive = df_loc[~df_loc["active"]].copy()

# Dağıtım sonuçları varsa birleştir (opsiyonel)
alloc_path = ROOT / "outputs" / "allocation" / "2026_01" / "dealer_summary.csv"
df_alloc: pd.DataFrame | None = None
if alloc_path.exists():
    df_alloc = pd.read_csv(alloc_path, sep=";", encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# Başlık
# ---------------------------------------------------------------------------
st.title("🗺️ Bayi Bölge Haritası")
st.caption(
    f"Türkiye genelindeki bayilerin coğrafi bölge bazında dağılımı · "
    f"**{len(df_active)} aktif**, {len(df_inactive)} pasif bayi"
)

# ---------------------------------------------------------------------------
# Üst özet metrikler (sadece aktif bayiler)
# ---------------------------------------------------------------------------
region_counts = df_active["region"].value_counts()
total_dealers = len(df_active)

st.markdown("#### Bölge Özeti")
cols = st.columns(len(region_counts))
for col, (region, count) in zip(cols, region_counts.items()):
    color = REGION_COLORS.get(region, "#666")
    col.markdown(
        f"""<div style="background:{color};border-radius:10px;padding:12px 10px;
            text-align:center;color:white;">
          <div style="font-size:22px;font-weight:800;">{count}</div>
          <div style="font-size:11px;opacity:0.9;margin-top:2px;">{region}</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Filtre
# ---------------------------------------------------------------------------
left, right = st.columns([3, 1])
with right:
    selected_regions = st.multiselect(
        "Bölge filtrele",
        options=sorted(df_active["region"].unique()),
        default=sorted(df_active["region"].unique()),
        key="region_filter",
    )
    show_labels  = st.toggle("Bayi isimlerini göster", value=True)
    show_passive = st.toggle("Pasif bayileri göster", value=False)

df_filtered = df_active[df_active["region"].isin(selected_regions)].copy()

# ---------------------------------------------------------------------------
# Harita oluştur
# ---------------------------------------------------------------------------
with left:
    # tiles=None → TileLayer'ı control=False ile ekle → LayerControl'de görünmez
    m = folium.Map(
        location=[39.2, 34.0],
        zoom_start=6,
        tiles=None,
        prefer_canvas=True,
    )
    folium.TileLayer("CartoDB positron", control=False).add_to(m)

    # Bölge arka plan poligonları — doğrudan haritaya ekle (LayerControl dışı)
    for _region, _coords in REGION_POLYGONS.items():
        _color = REGION_COLORS.get(_region, "#999999")
        folium.Polygon(
            locations=_coords,
            color=_color,
            weight=2,
            opacity=0.6,
            fill=True,
            fill_color=_color,
            fill_opacity=0.14,
            dash_array="5 4",
            tooltip=folium.Tooltip(_region),
        ).add_to(m)

    # Bölge bazında katmanlar
    feature_groups: dict[str, folium.FeatureGroup] = {}
    for region in sorted(df_filtered["region"].unique()):
        fg = folium.FeatureGroup(name=region, show=True)
        feature_groups[region] = fg
        m.add_child(fg)

    # Pasif bayi katmanı
    fg_passive = folium.FeatureGroup(name="Pasif Bayiler", show=show_passive)
    m.add_child(fg_passive)

    def _add_dealer_marker(row: pd.Series, fg: folium.FeatureGroup,
                           color: str, is_active: bool) -> None:
        extra = ""
        if is_active and df_alloc is not None:
            match = df_alloc[df_alloc["dealer_name"] == row["name"]]
            if not match.empty:
                r = match.iloc[0]
                extra = (
                    f"<br><b>Hedef:</b> {int(r['target'])} araç"
                    f"<br><b>Atanan:</b> {int(r['allocated'])} araç"
                    f"<br><b>Doluluk:</b> %{r['fill_rate']}"
                )

        status_tag = "" if is_active else "<br><i style='color:#999'>Pasif bayi</i>"
        popup_html = f"""
        <div style="font-family:sans-serif;min-width:160px;">
          <div style="background:{color};color:white;padding:8px 12px;
               border-radius:6px 6px 0 0;font-weight:700;font-size:14px;">
            {row['name']}
          </div>
          <div style="padding:8px 12px;border:1px solid #eee;border-top:none;
               border-radius:0 0 6px 6px;font-size:13px;">
            <b>Bölge:</b> {row['region']}
            <br><b>Konum:</b> {row['lat']:.4f}, {row['lon']:.4f}
            {extra}{status_tag}
          </div>
        </div>"""

        r_outer = 14 if is_active else 10
        r_inner = 6  if is_active else 4
        opacity = 0.30 if is_active else 0.08

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=r_outer, color=color, fill=True,
            fill_color=color, fill_opacity=opacity, weight=2,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=row["name"],
        ).add_to(fg)

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=r_inner, color="white", fill=True,
            fill_color=color, fill_opacity=1.0, weight=2,
        ).add_to(fg)

        # Etiket: aynı koordinat, pixel offset ile işaretçinin üstüne konumlandır
        # icon_anchor=(w/2, h+r_outer+4) → metnin alt-ortası, dairenin tam üstünde
        if show_labels and is_active:
            label_w = 100
            label_h = 18
            folium.Marker(
                location=[row["lat"], row["lon"]],
                icon=folium.DivIcon(
                    html=f"""<div style="font-size:10px;font-weight:700;
                        color:{color};white-space:nowrap;text-align:center;
                        text-shadow:1px 1px 0 white,-1px -1px 0 white,
                                    1px -1px 0 white,-1px  1px 0 white;">
                        {row['name']}</div>""",
                    icon_size=(label_w, label_h),
                    # merkezle yatayda, dairenin üstüne otur
                    icon_anchor=(label_w // 2, label_h + r_outer + 4),
                ),
            ).add_to(fg)

    # Aktif bayiler
    for _, row in df_filtered.iterrows():
        region = row["region"]
        color  = REGION_COLORS.get(region, "#666666")
        _add_dealer_marker(row, feature_groups[region], color, is_active=True)

    # Pasif bayiler (opsiyonel)
    if show_passive:
        for _, row in df_inactive.iterrows():
            _add_dealer_marker(row, fg_passive, "#9E9E9E", is_active=False)

    # Renk göstergesi (custom legend)
    legend_items = "".join(
        f"""<div style="display:flex;align-items:center;margin-bottom:6px;">
              <div style="width:14px;height:14px;border-radius:50%;background:{REGION_COLORS.get(r,'#666')};
                   margin-right:8px;flex-shrink:0;"></div>
              <span style="font-size:12px;">{r} ({region_counts.get(r,0)})</span>
            </div>"""
        for r in sorted(df_filtered["region"].unique())
    )
    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
         background:white;padding:14px 18px;border-radius:10px;
         box-shadow:0 2px 12px rgba(0,0,0,0.15);font-family:sans-serif;">
      <div style="font-weight:700;font-size:13px;margin-bottom:10px;
           color:#1A1A2E;">🗺️ Bölge Göstergesi</div>
      {legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl(collapsed=False).add_to(m)

    st_folium(m, width="100%", height=580, returned_objects=[])

# ---------------------------------------------------------------------------
# Bölge detay tablosu
# ---------------------------------------------------------------------------
st.divider()
st.markdown("#### Bölge Bazında Bayi Listesi")

tab_cols = st.tabs(sorted(df_filtered["region"].unique()))
for tab, region in zip(tab_cols, sorted(df_filtered["region"].unique())):
    with tab:
        sub = df_filtered[df_filtered["region"] == region][["name", "lat", "lon"]].copy()
        sub.columns = ["Bayi", "Enlem", "Boylam"]
        sub["Durum"] = "Aktif"

        if df_alloc is not None:
            sub = sub.merge(
                df_alloc[["dealer_name", "target", "allocated", "fill_rate"]].rename(
                    columns={"dealer_name": "Bayi", "target": "Hedef",
                             "allocated": "Atanan", "fill_rate": "Doluluk %"}
                ),
                on="Bayi", how="left",
            )

        color = REGION_COLORS.get(region, "#666")
        st.markdown(
            f"<span style='background:{color};color:white;padding:4px 12px;"
            f"border-radius:20px;font-size:13px;font-weight:600'>"
            f"{region} — {len(sub)} Bayi</span>",
            unsafe_allow_html=True,
        )
        st.dataframe(sub, use_container_width=True, hide_index=True)
