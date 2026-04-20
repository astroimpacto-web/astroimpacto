import streamlit as st
import streamlit.components.v1 as components 
import pandas as pd
import os
import base64
from jinja2 import Environment, FileSystemLoader
import motor_web
from geopy.geocoders import Nominatim

# 1. FUNCIONES DE APOYO
@st.cache_data
def get_base_64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return ""

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Astroimpacto", page_icon="apple-icon.png", layout="wide", initial_sidebar_state="expanded")

# IDENTIDAD VISUAL IPHONE
st.markdown('<link rel="apple-touch-icon" href="apple-icon.png"><link rel="manifest" href="./manifest.json">', unsafe_allow_html=True)

# ESTILOS CSS PERSONALIZADOS (MARCA REGISTRADA)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    [data-testid="stSidebar"] { background-color: #fdfcf9; border-right: 1px solid #e8e3d8; }
    .stButton>button { border-radius: 8px; font-weight: 600; transition: all 0.3s; width: 100%; }
    .stButton>button[kind="primary"] { background-color: #B48E92 !important; border: none !important; color: white !important; }
    h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #4A4A4A; }
    div[data-testid="stExpander"] { background-color: white; border: 1px solid #f0ebe1; border-radius: 8px; margin-bottom: 12px; }
    .stTextArea textarea { font-size: 0.9rem; line-height: 1.5; color: #333; }
    .stSelectbox div[data-baseweb="select"] { white-space: normal !important; }
</style>
""", unsafe_allow_html=True)

# ENCABEZADO SIDEBAR (LOGO)
SIDEBAR_HEADER_HTML = """
<div style="text-align: center; padding-bottom: 1rem; border-bottom: 1px solid #e8e3d8; margin-bottom: 1rem; margin-top: -2rem;">
    <div style="width: 50px; height: 50px; margin: 0 auto 10px auto; color: #B48E92;">
        <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="100" cy="90" r="50" stroke="currentColor" stroke-width="3"/>
            <path d="M100 20 L110 90 L100 160 L90 90 Z" fill="currentColor"/>
            <path d="M170 90 L100 100 L30 90 L100 80 Z" fill="currentColor"/>
            <line x1="100" y1="140" x2="100" y2="185" stroke="currentColor" stroke-width="4"/>
            <line x1="75" y1="165" x2="125" y2="165" stroke="currentColor" stroke-width="4"/>
        </svg>
    </div>
    <h2 style="font-family: 'Playfair Display', serif; font-size: 1.8rem; color: #4A4A4A; margin: 0; font-weight: 700;">Astroimpacto</h2>
    <p style="font-family: 'Montserrat', sans-serif; font-size: 0.65rem; letter-spacing: 2px; color: #B48E92; text-transform: uppercase;">Plataforma Web</p>
</div>
"""
st.sidebar.markdown(SIDEBAR_HEADER_HTML, unsafe_allow_html=True)

# 2. INICIALIZACIÓN DE SESIÓN
if 'textos_generados' not in st.session_state:
    st.session_state.update({
        'textos_generados': False, 'datos_diccionario': {}, 'plantilla_usar': 'informe_astroimpacto.html',
        'tipo_reporte_actual': "NATAL", 'lat_rs_auto': "", 'lon_rs_auto': "", 'idx_prog_actual': None
    })

# 3. CARGA DE GOOGLE SHEETS
@st.cache_data(ttl=5)
def cargar_bases_web():
    try:
        url_secreta = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id = url_secreta.split("/d/")[1].split("/")[0] if "/d/" in url_secreta else url_secreta
        u_cli = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Consultantes"
        u_prog = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Informes_Programados"
        u_tipos = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Informes_Tipo"
        
        df_c = pd.read_csv(u_cli).dropna(how="all")
        df_p = pd.read_csv(u_prog).dropna(how="all")
        try: df_t = pd.read_csv(u_tipos).dropna(how="all")
        except: df_t = pd.DataFrame()

        for df in [df_c, df_p, df_t]:
            if not df.empty:
                df.columns = df.columns.str.strip()
                if 'id_consultante' not in df.columns:
                    if 'id' in df.columns: df.rename(columns={'id': 'id_consultante'}, inplace=True)
                    elif 'Id' in df.columns: df.rename(columns={'Id': 'id_consultante'}, inplace=True)
                df['id_consultante'] = df['id_consultante'].astype(str).str.replace('.0', '', regex=False).str.strip()
        return df_c, df_p, df_t
    except Exception as e:
        st.sidebar.error(f"Error Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_cli, df_prog, df_tipos = cargar_bases_web()

# 4. NAVEGACIÓN Y AUDITORÍA TÉCNICA
st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700; letter-spacing:1px;'>NAVEGACIÓN</p>", unsafe_allow_html=True)
modo_app = st.sidebar.radio("Menu", ["⚙️ Taller de Informes", "📅 Programar Cliente"], label_visibility="collapsed")
st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

# VISOR DE DATOS TÉCNICOS (LO QUE VEÍAS EN VS CODE)
if st.session_state.textos_generados:
    st.sidebar.markdown("### 🔍 Datos Técnicos Exactos")
    st.sidebar.code(st.session_state.datos_diccionario.get('auditoria_tecnica', 'Calculando posiciones...'), language='text')
    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

# 5. MODO PROGRAMAR
if modo_app == "📅 Programar Cliente":
    st.markdown("## 📅 Agenda de Clientes")
    if not df_cli.empty:
        opciones_cli = [f"{row['Nombres']} (ID: {row['id_consultante']})" for _, row in df_cli.iterrows()]
        st.selectbox("1. Selecciona el Cliente:", opciones_cli)
        st.selectbox("2. Tipo de Informe:", ["Carta Natal", "Tránsitos Anuales", "Revolución Solar"])
        if st.button("➕ Programar en Google Sheets", type="primary"):
            st.info("Para esta versión web, agrega la fila directamente en tu Excel de Google y recarga la página.")

# 6. MODO TALLER (LÓGICA PRINCIPAL)
elif modo_app == "⚙️ Taller de Informes":
    if not st.session_state.textos_generados:
        st.markdown("## ⚙️ Taller de Informes")
        st.markdown("<p style='color: #B48E92;'>Procesa efemérides y genera interpretaciones de alto impacto.</p>", unsafe_allow_html=True)

    pendientes = df_prog[df_prog['Estado'].astype(str).str.upper() == 'PENDIENTE'] if not df_prog.empty else pd.DataFrame()

    if pendientes.empty and not st.session_state.textos_generados:
        st.sidebar.success("✅ ¡Agenda limpia!")
    elif not pendientes.empty:
        st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700;'>COLA DE TRABAJO</p>", unsafe_allow_html=True)
        opciones_menu = []
        for idx, row in pendientes.iterrows():
            id_c = str(row['id_consultante']).strip()
            cli_data = df_cli[df_cli['id_consultante'] == id_c]
            nombre = cli_data.iloc[0].get('Nombres', 'Consultante') if not cli_data.empty else "ID " + id_c
            opciones_menu.append(f"{nombre} (ID: {id_c}) | Fila: {idx}")

        if opciones_menu:
            sel_p = st.sidebar.selectbox("Informes:", opciones_menu, label_visibility="collapsed")
            idx_p = int(sel_p.split("Fila: ")[1])
            row_p = pendientes.loc[idx_p]
            id_sel = str(row_p['id_consultante'])
            cli_obj = df_cli[df_cli['id_consultante'] == id_sel].iloc[0]
            id_t = str(row_p.get('Id_Informe', '1')).replace('.0', '').strip()

            lat_rs, lon_rs, lug_rs = None, None, None
            if id_t == "3": # REVOLUCIÓN SOLAR
                st.sidebar.markdown("📍 **RELOCALIZACIÓN RS**")
                lug_rs = st.sidebar.text_input("Ubicación actual:", placeholder="Ej: Buenos Aires, AR")
                if st.sidebar.button("🔍 Buscar Coordenadas", use_container_width=True):
                    if lug_rs:
                        loc = Nominatim(user_agent="astro").geocode(lug_rs)
                        if loc: st.session_state.update({'lat_rs_auto': str(loc.latitude), 'lon_rs_auto': str(loc.longitude)})
                lat_rs = st.sidebar.text_input("Lat:", value=st.session_state.lat_rs_auto)
                lon_rs = st.sidebar.text_input("Lon:", value=st.session_state.lon_rs_auto)

            if st.sidebar.button("🚀 PROCESAR INFORME", type="primary", use_container_width=True):
                with st.spinner("Calculando efemérides y redactando..."):
                    if id_t == "2":
                        st.session_state.tipo_reporte_actual = "TRANSITOS"
                        datos, plant = motor_web.procesar_transitos_con_ia(cli_obj, None, id_sel)
                    elif id_t == "3":
                        st.session_state.tipo_reporte_actual = "REVOLUCION"
                        datos, plant = motor_web.procesar_rs_con_ia(cli_obj, None, id_sel, lat_rs=lat_rs, lon_rs=lon_rs, lugar_rs=lug_rs)
                    else:
                        st.session_state.tipo_reporte_actual = "NATAL"
                        datos, plant = motor_web.procesar_natal_con_ia(cli_obj, None, id_sel)
                    
                    if datos:
                        st.session_state.update({'datos_diccionario': datos, 'plantilla_usar': plant, 'textos_generados': True, 'idx_prog_actual': idx_p})
                        st.rerun()

    # 7. PANEL DE EDICIÓN COMPLETA (MÁXIMA DENSIDAD)
    if st.session_state.textos_generados:
        d = st.session_state.datos_diccionario
        tipo = st.session_state.tipo_reporte_actual
        st.subheader(f"Editando: {d.get('titulo_informe')} - {d.get('nombre_cliente')}")

        # --- REVOLUCIÓN SOLAR ---
        if tipo == "REVOLUCION":
            with st.expander("1. Infografía (Perspectivas)", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    d['perspectivas']['transformacion'] = st.text_area("Transformación", d['perspectivas']['transformacion'], height=100)
                    d['perspectivas']['cambio'] = st.text_area("Cambio", d['perspectivas']['cambio'], height=100)
                with col2:
                    d['perspectivas']['oportunidades'] = st.text_area("Oportunidades", d['perspectivas']['oportunidades'], height=100)
                    d['perspectivas']['relaciones'] = st.text_area("Relaciones", d['perspectivas']['relaciones'], height=100)
            
            with st.expander("2. Base: Natal, Tránsitos y Progresiones", expanded=False):
                d['intro_texto'] = st.text_area("Introducción Cálida", d.get('intro_texto',''), height=100)
                d['carta_natal_resumen'] = st.text_area("Resumen Carta Natal", d.get('carta_natal_resumen',''), height=150)
                d['transitos_personales'] = st.text_area("Análisis Tránsitos Lentos", d.get('transitos_personales',''), height=150)
                d['progresiones_secundarias'] = st.text_area("Estado Interior (Progresiones)", d.get('progresiones_secundarias',''), height=150)
                d['como_actuar_progresiones'] = st.text_area("Acción ante Progresiones (Separar con líneas)", "\n".join(d.get('como_actuar_progresiones', []))).split("\n")

            with st.expander("3. Revolución Solar (General y Laboral)", expanded=True):
                d['revolucion_solar_general_1'] = st.text_area("Clima General del Año", d.get('revolucion_solar_general_1',''), height=250)
                d['revo_propone'] = st.text_area("Propuestas del Año (Separar con líneas)", "\n".join(d.get('revo_propone', []))).split("\n")
                d['situacion_laboral_economica'] = st.text_area("Panorama Laboral", d.get('situacion_laboral_economica',''), height=150)
                d['logro_objetivos_profesionales'] = st.text_area("Objetivos Profesionales", "\n".join(d.get('logro_objetivos_profesionales', []))).split("\n")

            with st.expander("4. Emocional y Trimestral", expanded=True):
                d['situacion_emocional'] = st.text_area("Panorama Emocional", d.get('situacion_emocional',''), height=150)
                st.markdown("**Panorama Trimestral:**")
                for i, t in enumerate(d.get('panorama_trimestral', [])):
                    t['texto'] = st.text_area(f"📍 {t['titulo']}", t['texto'], key=f"t_{i}", height=120)
                d['plan_accion_objetivos'] = st.text_area("Plan de Acción Objetivos", "\n".join(d.get('plan_accion_objetivos', []))).split("\n")

        # --- TRÁNSITOS ANUALES ---
        elif tipo == "TRANSITOS":
            with st.expander("1. Energía Base", expanded=False):
                d['interpretacion_sol_signo'] = st.text_area("Sol Natal", d.get('interpretacion_sol_signo',''), height=100)
                d['interpretacion_luna_signo'] = st.text_area("Luna Natal", d.get('interpretacion_luna_signo',''), height=100)
                d['interpretacion_asc_signo'] = st.text_area("Ascendente Natal", d.get('interpretacion_asc_signo',''), height=100)
            
            with st.expander("2. Clima del Año", expanded=True):
                d['frase_anual_corta'] = st.text_input("Lema del Año", d.get('frase_anual_corta',''))
                d['analisis_clima_anual'] = st.text_area("Interpretación General", d.get('analisis_clima_anual',''), height=300)
                d['oportunidad_anual'] = st.text_area("Oportunidad Clave", d.get('oportunidad_anual',''), height=100)
                d['atencion_anual'] = st.text_area("Punto de Atención", d.get('atencion_anual',''), height=100)

            with st.expander("3. Calendario Mensual Detallado", expanded=True):
                for mes, eventos in d.get('calendario_por_meses', {}).items():
                    st.markdown(f"### 🗓️ {mes}")
                    for ev in eventos:
                        label = f"{ev['fecha']} | {ev['transito']} {ev['aspecto']} {ev['natal']}"
                        ev['texto_efecto'] = st.text_area(label, ev['texto_efecto'], key=f"tr_{mes}_{ev['fecha']}", height=80)

        # --- CARTA NATAL ---
        else:
            with st.expander("1. Tríada Principal (Sol/Luna/AC)", expanded=True):
                d['interpretacion_sol_signo'] = st.text_area("☉ El Sol", d.get('interpretacion_sol_signo',''), height=150)
                d['interpretacion_luna_signo'] = st.text_area("☽ La Luna", d.get('interpretacion_luna_signo',''), height=150)
                d['interpretacion_asc_signo'] = st.text_area("AC Ascendente", d.get('interpretacion_asc_signo',''), height=150)
            
            with st.expander("2. Gigantes del Cielo", expanded=False):
                if 'gigantes_del_cielo' in d:
                    for i, g in enumerate(d['gigantes_del_cielo']):
                        g['texto'] = st.text_area(f"{g['nombre']} en {g['signo']}", g['texto'], key=f"g_{i}", height=100)

            with st.expander("3. Síntesis y FODA", expanded=True):
                d['interpretacion_personalidad_global'] = st.text_area("Análisis Global Evolutivo", d.get('interpretacion_personalidad_global',''), height=300)
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    d['foda']['fortalezas'] = st.text_area("Fortalezas", "\n".join(d['foda'].get('fortalezas', []))).split("\n")
                with col_f2:
                    d['foda']['debilidades'] = st.text_area("Debilidades", "\n".join(d['foda'].get('debilidades', []))).split("\n")

        # 8. FINALIZACIÓN Y DESCARGA
        st.divider()
        c1, c2 = st.columns(2)
        d['logo_base64'] = get_base_64_of_bin_file('apple-icon.png')
        env = Environment(loader=FileSystemLoader('.'))
        tmpl = env.get_template(st.session_state.plantilla_usar)

        with c1:
            if st.button("👁️ VER VISTA PREVIA"):
                try: components.html(tmpl.render(d), height=800, scrolling=True)
                except Exception as e: st.error(f"Error render: {e}")

        with c2:
            html_f = tmpl.render(d)
            st.download_button("💾 DESCARGAR INFORME", data=html_f, file_name=f"Informe_{d.get('nombre_cliente')}.html", mime="text/html", type="primary")
            if st.button("❌ LIMPIAR Y FINALIZAR"):
                st.session_state.textos_generados = False
                st.rerun()
