import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon, Point, LineString, mapping
import json
import os
import folium 
from streamlit_folium import folium_static 
from pyproj import Transformer

# Set konfigurasi halaman
st.set_page_config(page_title="Sistem Survey Lot PUO", layout="wide")

# ================== FUNGSI TUKAR DMS ==================
def format_dms(decimal_degree):
    d = int(decimal_degree)
    m = int((decimal_degree - d) * 60)
    s = round((((decimal_degree - d) * 60) - m) * 60, 0)
    return f"{d}°{abs(m):02d}'{abs(int(s)):02d}\""

# ================== FUNGSI LOGIN & KEMASKINI ==================
@st.dialog("🔑 Kemaskini Kata Laluan")
def reset_password_dialog():
    st.info("Sila sahkan ID untuk menetapkan semula kata laluan.")
    id_sah = st.text_input("Sahkan ID Pengguna:")
    pass_baru = st.text_input("Kata Laluan Baharu:", type="password")
    pass_sah = st.text_input("Sahkan Kata Laluan Baharu:", type="password")
    
    if st.button("Simpan Kata Laluan", use_container_width=True):
        if id_sah in ["fakhrul", "aniq", "umar"] and pass_baru == pass_sah and pass_baru != "":
            st.success("✅ Kata laluan berjaya dikemaskini!")
            st.rerun()
        else:
            st.error("❌ Maklumat tidak sepadan atau kosong.")

def check_password():
    if "password_correct" not in st.session_state:
        _, col_mid, _ = st.columns([1, 1.5, 1])
        with col_mid:
            st.markdown("<h2 style='text-align: center;'>🔐 Sistem Survey Lot PUO</h2>", unsafe_allow_html=True)
            user_id = st.text_input("👤 Masukkan ID:", key="user_id")
            password = st.text_input("🔑 Masukkan Kata Laluan:", type="password", key="user_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Log Masuk", use_container_width=True):
                if user_id in ["fakhrul", "aniq", "umar"] and password == "123":
                    st.session_state["password_correct"] = True
                    st.session_state["user_id_logged"] = user_id.capitalize()
                    st.rerun()
                else:
                    st.error("😕 ID atau Kata Laluan salah.")
            
            if st.button("❓ Lupa Kata Laluan?", use_container_width=True):
                reset_password_dialog()
        return False
    return True

# ================== MAIN APP (SELEPAS LOGIN) ==================
if check_password():
    
    display_name = st.session_state.get("user_id_logged", "Fakhrul")
    
    st.sidebar.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #00B4DB, #0083B0); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
            <img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png" width="80" style="border-radius: 50%; border: 3px solid white;">
            <h3 style="color: white; margin-top: 10px; font-family: sans-serif;">Hai, {display_name}!</h3>
            <p style="color: #e0e0e0; font-size: 0.8em; margin-bottom: 0px;">Surveyor Berdaftar</p>
        </div>
        """, unsafe_allow_html=True
    )

    col_logo, col_text = st.columns([1.2, 4])
    with col_logo:
        if os.path.exists("logo_puo.png"):
            st.image("logo_puo.png", width=220)
        else:
            st.markdown("<div style='padding:25px; background:#333; border-radius:10px; text-align:center; color:white; border: 2px dashed #666;'>LOGO PUO<br>(Sila Upload fail logo_puo.png)</div>", unsafe_allow_html=True)

    with col_text:
        st.markdown("""
            <style>
                .main-title { font-family: 'Arial Black', Gadget, sans-serif; font-size: 45px; font-weight: 900; margin-bottom: -10px; line-height: 1; letter-spacing: -1px; }
                .sub-title { font-size: 18px; color: #888; margin-top: 5px; }
            </style>
            <div>
                <h1 class="main-title">SISTEM SURVEY LOT</h1>
                <p class="sub-title">Politeknik Ungku Omar | Jabatan Kejuruteraan Awam</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 1px solid #333; margin-top: 0px;'>", unsafe_allow_html=True)

    # ================== SIDEBAR SETTINGS ==================
    st.sidebar.header("⚙️ Tetapan Paparan")
    uploaded_file = st.sidebar.file_uploader("Upload fail CSV", type=["csv"])

    st.sidebar.markdown("---")
    st.sidebar.subheader("🌍 Mod Peta Interaktif")
    show_interactive_map = st.sidebar.toggle("On/Off Peta Satelit", value=True)
    map_provider = st.sidebar.radio("Pilih Jenis Peta:", ["Satelit (Hybrid)", "Standard Map"], disabled=not show_interactive_map)

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎨 Pilihan Warna")
    poly_color = st.sidebar.color_picker("Warna Kawasan (Poligon)", "#6036AF") 
    line_color = st.sidebar.color_picker("Warna Garisan Sempadan", "#FFFF00") 
    poly_opacity = st.sidebar.slider("Kelegapan Kawasan", 0.0, 1.0, 0.3)

    st.sidebar.markdown("---")
    st.sidebar.subheader("🖋️ Gaya Label")
    show_luas_label = st.sidebar.checkbox("Papar Label LUAS", value=True)
    label_size_stn = st.sidebar.slider("Saiz Bulatan Stesen", 15, 30, 22) 
    label_size_data = st.sidebar.slider("Saiz Bearing/Jarak", 5, 12, 7)
    label_size_luas = st.sidebar.slider("Saiz Tulisan LUAS", 5, 20, 10)

    # ================== PEMPROSESAN DATA ==================
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            if all(col in df.columns for col in ['STN', 'E', 'N']):
                transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)
                df['lon'], df['lat'] = transformer.transform(df['E'].values, df['N'].values)
                
                coords_en = list(zip(df['E'], df['N']))
                poly_geom = Polygon(coords_en)
                area = poly_geom.area
                centroid_ll = Polygon(list(zip(df['lon'], df['lat']))).centroid 

                st.markdown("### 📊 Ringkasan Lot")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Luas (m²)", f"{area:.2f}")
                col2.metric("Luas (Ekar)", f"{area/4046.856:.4f}")
                col3.metric("Bilangan Stesen", len(df))
                col4.metric("Status", "Tutup" if poly_geom.is_valid else "Ralat")

                st.markdown("---")
                st.subheader("📐 Paparan Pelan Ukur")

                google_map_url = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}'
                if map_provider == "Standard Map":
                    google_map_url = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}'

                m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=19, max_zoom=22, tiles=google_map_url, attr='Google')
                points_map = [[r['lat'], r['lon']] for _, r in df.iterrows()]
                
                folium.Polygon(locations=points_map, color=line_color, weight=3, fill=True, fill_color=poly_color, fill_opacity=poly_opacity).add_to(m)
                
                for i in range(len(df)):
                    p1, p2 = df.iloc[i], df.iloc[(i + 1) % len(df)]
                    dE, dN = p2['E'] - p1['E'], p2['N'] - p1['N']
                    dist, bear = np.sqrt(dE**2 + dN**2), (np.degrees(np.arctan2(dE, dN)) + 360) % 360
                    
                    angle_geo = -np.degrees(np.arctan2(p2['lat'] - p1['lat'], p2['lon'] - p1['lon']))
                    if angle_geo > 90: angle_geo -= 180
                    elif angle_geo < -90: angle_geo += 180
                    
                    v_offset = -20 if dN >= 0 else 5 

                    folium.Marker([ (p1['lat'] + p2['lat']) / 2, (p1['lon'] + p2['lon']) / 2],
                        icon=folium.DivIcon(html=f'''<div style="transform: rotate({angle_geo}deg); text-align: center; width: 160px; margin-left: -80px; margin-top: {v_offset}px;">
                            <div style="font-size: {label_size_data}pt; color: white; text-shadow: 2px 2px 3px black; font-weight: bold;">{format_dms(bear)}<br><span style="color: #FFD700;">{dist:.2f}m</span></div></div>''')).add_to(m)
                    
                    popup_info = f"<b>Stesen {int(p1['STN'])}</b><br>N: {p1['N']:.3f}<br>E: {p1['E']:.3f}"
                    folium.Marker(
                        [p1['lat'], p1['lon']], 
                        popup=folium.Popup(popup_info, max_width=200),
                        icon=folium.DivIcon(html=f'''<div style="background-color: white; border: 2px solid red; border-radius: 50%; width: {label_size_stn}px; height: {label_size_stn}px; display: flex; align-items: center; justify-content: center; font-size: {label_size_stn*0.6}px; font-weight: bold; color: black; margin-left: -{label_size_stn/2}px; margin-top: -{label_size_stn/2}px; box-shadow: 1px 1px 3px rgba(0,0,0,0.5); cursor: pointer;">{int(p1["STN"])}</div>''')
                    ).add_to(m)

                if show_luas_label:
                    folium.Marker(
                        [centroid_ll.y, centroid_ll.x], 
                        icon=folium.DivIcon(html=f'''<div style="font-size: {label_size_luas}pt; color: #00FF00; text-shadow: 2px 2px 4px black; font-weight: 900; width: 200px; text-align: center; margin-left: -100px;">{area:.2f} m²</div>''')
                    ).add_to(m)
                
                folium_static(m, width=1000, height=600)

                st.markdown("---")
                st.subheader("📋 Jadual Data Koordinat")
                st.dataframe(df[['STN', 'E', 'N', 'lat', 'lon']], use_container_width=True)

                # ================== BUTANG DOWNLOAD QGIS (GEOJSON) ==================
                st.subheader("📥 Eksport Data")
                
                # Sediakan data GeoJSON
                features = []
                # Feature Poligon
                poly_feature = {
                    "type": "Feature",
                    "properties": {"Name": "Lot Area", "Area_m2": area},
                    "geometry": mapping(Polygon(list(zip(df['lon'], df['lat']))))
                }
                features.append(poly_feature)
                
                # Feature Point (Stesen)
                for _, row in df.iterrows():
                    point_feature = {
                        "type": "Feature",
                        "properties": {"STN": int(row['STN']), "N": row['N'], "E": row['E']},
                        "geometry": {"type": "Point", "coordinates": [row['lon'], row['lat']]}
                    }
                    features.append(point_feature)
                
                geojson_data = json.dumps({"type": "FeatureCollection", "features": features})
                
                st.download_button(
                    label="💾 Muat Turun Fail untuk QGIS (.geojson)",
                    data=geojson_data,
                    file_name="survey_lot_puo.geojson",
                    mime="application/json",
                    use_container_width=True
                )

            else: st.error("❌ Kolum STN, E, N tak jumpa dalam CSV!")
        except Exception as e: st.error(f"❌ Ada ralat: {e}")
    else:
        st.info("👋 Sila muat naik fail CSV di bar sisi untuk memulakan analisis lot.")

    if st.sidebar.button("Log Keluar"):
        st.session_state.clear()
        st.rerun()
