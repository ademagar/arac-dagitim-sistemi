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
    "Marmara":              "#1565C0",   # Koyu mavi
    "Ege":                  "#2E7D32",   # Koyu yeşil
    "Akdeniz":              "#E65100",   # Turuncu
    "İç Anadolu":           "#6A1B9A",   # Mor
    "Karadeniz":            "#00695C",   # Teal
    "Güneydoğu Anadolu":   "#B71C1C",   # Kırmızı
    "Doğu Anadolu":         "#4E342E",   # Kahve
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


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------
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
        records.append({"name": name, "lat": lat, "lon": lon})
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

# Dağıtım sonuçları varsa birleştir (opsiyonel)
alloc_path = ROOT / "outputs" / "allocation" / "2026_01" / "dealer_summary.csv"
df_alloc: pd.DataFrame | None = None
if alloc_path.exists():
    df_alloc = pd.read_csv(alloc_path, sep=";", encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# Başlık
# ---------------------------------------------------------------------------
st.title("🗺️ Bayi Bölge Haritası")
st.caption("Türkiye genelindeki bayilerin coğrafi bölge bazında dağılımı")

# ---------------------------------------------------------------------------
# Üst özet metrikler
# ---------------------------------------------------------------------------
region_counts = df_loc["region"].value_counts()
total_dealers = len(df_loc)

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
        options=sorted(df_loc["region"].unique()),
        default=sorted(df_loc["region"].unique()),
        key="region_filter",
    )
    show_labels = st.toggle("Bayi isimlerini göster", value=True)

df_filtered = df_loc[df_loc["region"].isin(selected_regions)].copy()

# ---------------------------------------------------------------------------
# Harita oluştur
# ---------------------------------------------------------------------------
with left:
    m = folium.Map(
        location=[39.2, 34.0],
        zoom_start=6,
        tiles="CartoDB positron",
        prefer_canvas=True,
    )

    # Bölge bazında katmanlar (legend için)
    feature_groups: dict[str, folium.FeatureGroup] = {}
    for region in sorted(df_filtered["region"].unique()):
        fg = folium.FeatureGroup(name=region, show=True)
        feature_groups[region] = fg
        m.add_child(fg)

    for _, row in df_filtered.iterrows():
        region  = row["region"]
        color   = REGION_COLORS.get(region, "#666666")
        fg      = feature_groups[region]

        # Ek bilgi varsa popup'a ekle
        extra = ""
        if df_alloc is not None:
            match = df_alloc[df_alloc["dealer_name"] == row["name"]]
            if not match.empty:
                r = match.iloc[0]
                extra = (
                    f"<br><b>Hedef:</b> {int(r['target'])} araç"
                    f"<br><b>Atanan:</b> {int(r['allocated'])} araç"
                    f"<br><b>Doluluk:</b> %{r['fill_rate']}"
                )

        popup_html = f"""
        <div style="font-family:sans-serif;min-width:160px;">
          <div style="background:{color};color:white;padding:8px 12px;
               border-radius:6px 6px 0 0;font-weight:700;font-size:14px;">
            {row['name']}
          </div>
          <div style="padding:8px 12px;border:1px solid #eee;border-top:none;
               border-radius:0 0 6px 6px;font-size:13px;">
            <b>Bölge:</b> {region}
            <br><b>Konum:</b> {row['lat']:.4f}, {row['lon']:.4f}
            {extra}
          </div>
        </div>
        """

        # Büyük daire + iç nokta (pin efekti)
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=14,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.18,
            weight=2,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=row["name"],
        ).add_to(fg)

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=6,
            color="white",
            fill=True,
            fill_color=color,
            fill_opacity=1.0,
            weight=2,
        ).add_to(fg)

        # Bayi ismi etiketi
        if show_labels:
            folium.Marker(
                location=[row["lat"] + 0.18, row["lon"]],
                icon=folium.DivIcon(
                    html=f"""<div style="font-size:10px;font-weight:700;
                        color:{color};white-space:nowrap;
                        text-shadow:1px 1px 0 white,-1px -1px 0 white,
                        1px -1px 0 white,-1px 1px 0 white;">{row['name']}</div>""",
                    icon_size=(90, 20),
                    icon_anchor=(45, 0),
                ),
            ).add_to(fg)

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
