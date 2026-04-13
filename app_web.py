import streamlit as st
import streamlit.components.v1 as components 
import pandas as pd
import os
from jinja2 import Environment, FileSystemLoader
import motor_web
from geopy.geocoders import Nominatim

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTÉTICA
# ==========================================
st.set_page_config(page_title="Astroimpacto", page_icon="logo_astro.jpg", layout="wide", initial_sidebar_state="expanded")

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&display=swap');

    :root {
        --color-accent: #B48E92;       
        --color-accent-dark: #967074; 
        --color-bg-tint: #Fdfbf7;      
        --color-text: #4A4A4A;         
    }

    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
        color: var(--color-text);
    }
    
    h1, h2, h3, .st-emotion-cache-10trblm {
        font-family: 'Playfair Display', serif !important;
        color: var(--color-text) !important;
    }

    /* ELIMINAR EL ROJO DE STREAMLIT */
    div[data-baseweb="select"] > div, input, textarea { border-color: #e2dcd0 !important; }
    div[data-baseweb="select"] > div:hover, input:hover, textarea:hover { border-color: var(--color-accent) !important; }
    div[data-baseweb="select"] > div:focus-within, input:focus, textarea:focus { border-color: var(--color-accent) !important; box-shadow: 0 0 0 1px var(--color-accent) !important; }
    ul[role="listbox"] li[aria-selected="true"] { background-color: #f7f3f4 !important; color: var(--color-accent-dark) !important; }
    div[data-baseweb="radio"] > div:first-child { background-color: transparent !important; border-color: var(--color-accent) !important; }
    div[data-baseweb="radio"] > div:first-child > div { background-color: var(--color-accent) !important; }
    div[role="radiogroup"] label > div:last-child { background-color: transparent !important; }

    /* BOTONES */
    .stButton>button { border-radius: 6px !important; font-family: 'Montserrat', sans-serif !important; font-weight: 600 !important; letter-spacing: 0.5px; transition: all 0.3s ease !important; border: 1px solid var(--color-accent) !important; color: var(--color-accent) !important; }
    .stButton>button:hover, .stButton>button:focus:not(:active) { background-color: #f7f3f4 !important; color: var(--color-accent-dark) !important; border-color: var(--color-accent-dark) !important; outline: none !important; box-shadow: none !important; }
    .stButton>button:active { background-color: var(--color-accent-dark) !important; color: white !important; border-color: var(--color-accent-dark) !important; }
    
    .stButton>button[kind="primary"] { background-color: var(--color-accent) !important; color: white !important; border: none !important; box-shadow: 0 4px 6px rgba(180, 142, 146, 0.2) !important; }
    .stButton>button[kind="primary"]:hover, .stButton>button[kind="primary"]:focus:not(:active) { background-color: var(--color-accent-dark) !important; color: white !important; box-shadow: 0 6px 12px rgba(180, 142, 146, 0.4) !important; transform: translateY(-1px); outline: none !important; }
    .stButton>button[kind="primary"]:active { background-color: var(--color-text) !important; color: white !important; }

    [data-testid="stSidebar"] { background-color: var(--color-bg-tint) !important; border-right: 1px solid #f0ebe1; }
    .streamlit-expanderHeader { background-color: var(--color-bg-tint); border-radius: 6px; color: var(--color-text) !important; font-family: 'Playfair Display', serif !important; font-size: 1.1rem !important; border: 1px solid #f0ebe1; }
    .streamlit-expanderHeader:hover, .streamlit-expanderHeader:focus { color: var(--color-accent-dark) !important; outline: none !important; }
    hr { border-color: #e8e3d8 !important; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# MARCA Y ENCABEZADO LATERAL
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
    <h2 style="font-family: 'Playfair Display', serif; font-size: 1.8rem; color: #4A4A4A; margin: 0; font-weight: 700; letter-spacing: 0.5px;">Astroimpacto</h2>
    <p style="font-family: 'Montserrat', sans-serif; font-size: 0.65rem; letter-spacing: 2px; color: #B48E92; text-transform: uppercase; margin-top: 5px;">Plataforma Web</p>
</div>
"""
st.sidebar.markdown(SIDEBAR_HEADER_HTML, unsafe_allow_html=True)

if 'textos_generados' not in st.session_state:
    st.session_state.textos_generados = False
    st.session_state.datos_diccionario = {}
    st.session_state.plantilla_usar = 'informe_astroimpacto.html'
    st.session_state.tipo_reporte_actual = "NATAL"
    st.session_state.idx_prog_actual = None 

if 'lat_rs_auto' not in st.session_state: st.session_state.lat_rs_auto = ""
if 'lon_rs_auto' not in st.session_state: st.session_state.lon_rs_auto = ""

# --- FUNCIÓN DEFINITIVA: LEER GOOGLE SHEETS (Método Pandas Directo) ---
@st.cache_data(ttl=5)
def cargar_bases_web():
    try:
        # Obtenemos la URL del archivo secrets
        url_secreta = st.secrets["connections"]["gsheets"]["spreadsheet"]
        
        # Extraemos el ID mágico del documento
        if "/d/" in url_secreta:
            sheet_id = url_secreta.split("/d/")[1].split("/")[0]
        else:
            sheet_id = url_secreta

        # Construimos URLs de descarga directa (Invencibles contra el Error 400)
        url_cli = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Consultantes"
        url_prog = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Informes_Programados"
        url_tipos = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Informes_Tipo"

        # Leemos directamente
        df_cli = pd.read_csv(url_cli).dropna(how="all")
        df_prog = pd.read_csv(url_prog).dropna(how="all")
        try: df_tipos = pd.read_csv(url_tipos).dropna(how="all")
        except: df_tipos = pd.DataFrame()
        
        df_cli.columns = df_cli.columns.str.strip()
        df_prog.columns = df_prog.columns.str.strip()
        if not df_tipos.empty: df_tipos.columns = df_tipos.columns.str.strip()
        df_cli = df_cli.loc[:, ~df_cli.columns.duplicated()]
        df_prog = df_prog.loc[:, ~df_prog.columns.duplicated()]

        if 'id_consultante' not in df_prog.columns and 'Id' in df_prog.columns: df_prog.rename(columns={'Id': 'id_consultante'}, inplace=True)
        if 'id_consultante' not in df_cli.columns:
            if 'id' in df_cli.columns: df_cli.rename(columns={'id': 'id_consultante'}, inplace=True)
            elif 'Id' in df_cli.columns: df_cli.rename(columns={'Id': 'id_consultante'}, inplace=True)

        if 'id_consultante' in df_cli.columns: df_cli['id_consultante'] = df_cli['id_consultante'].astype(str).str.replace('.0', '', regex=False).str.strip()
        if 'id_consultante' in df_prog.columns: df_prog['id_consultante'] = df_prog['id_consultante'].astype(str).str.replace('.0', '', regex=False).str.strip()
        
        return df_cli, df_prog, df_tipos
    except KeyError:
        st.sidebar.error("⚠️ No se encontró la conexión. Revisa tu archivo .streamlit/secrets.toml")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"⚠️ Error conectando a Google Sheets. Revisa que el enlace sea 'Cualquier usuario con el vínculo'. Detalle: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_cli, df_prog, df_tipos = cargar_bases_web()

# --- MENÚ DE NAVEGACIÓN ---
st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700; letter-spacing:1px; margin-bottom:0;'>NAVEGACIÓN</p>", unsafe_allow_html=True)
modo_app = st.sidebar.radio("Navegación", ["⚙️ Taller de Informes", "📅 Programar Cliente"], label_visibility="collapsed")
st.sidebar.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)

# ==========================================
# MODO 1: PROGRAMAR (GUARDAR EN GOOGLE SHEETS)
# ==========================================
if modo_app == "📅 Programar Cliente":
    st.markdown("<h2 style='font-family: Playfair Display, serif; color: #4A4A4A; border-bottom: 2px solid #e8e3d8; padding-bottom: 10px;'>📅 Agenda de Clientes</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #B48E92; font-weight: 500; margin-bottom: 2rem;'>Agrega un cliente a tu cola de trabajo en la plataforma.</p>", unsafe_allow_html=True)
    
    if not df_cli.empty:
        opciones_cli = [f"{row['Nombres']} {row.get('Apellido_Paterno','')} (ID: {row['id_consultante']})" for _, row in df_cli.iterrows()]
        cliente_sel = st.selectbox("1. Selecciona el Cliente:", opciones_cli)
        
        opciones_tipo = []
        if not df_tipos.empty and 'Id_Informe' in df_tipos.columns:
            for _, row in df_tipos.iterrows():
                id_tipo = str(row['Id_Informe']).replace('.0', '').strip()
                nombre_tipo = id_tipo
                for col in ['Nombre', 'Nombre_Informe', 'Tipo', 'Tipo_Informe', 'Descripcion']:
                    if col in df_tipos.columns:
                        nombre_tipo = str(row[col])
                        break
                if nombre_tipo == id_tipo or nombre_tipo.lower() == 'nan':
                    if id_tipo == "1": nombre_tipo = "Carta Natal"
                    elif id_tipo == "2": nombre_tipo = "Tránsitos"
                    elif id_tipo == "3": nombre_tipo = "Revolución Solar"
                    else: nombre_tipo = f"Reporte Tipo {id_tipo}"
                opciones_tipo.append(f"{nombre_tipo} (ID: {id_tipo})")
        else:
            opciones_tipo = ["Carta Natal (ID: 1)", "Tránsitos (ID: 2)", "Revolución Solar (ID: 3)"]
            
        tipo_sel = st.selectbox("2. Selecciona el Tipo de Informe:", opciones_tipo)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Guardar en Agenda", type="primary"):
            st.info("⚠️ NOTA: Al estar conectada a la web, Google requiere una Clave de Seguridad avanzada para *escribir* en tu hoja. Por ahora, por favor agrega los clientes nuevos directamente en tu pestaña 'Informes_Programados' de Google Sheets.")

# ==========================================
# MODO 2: GENERAR (EL TALLER DE INFORMES)
# ==========================================
elif modo_app == "⚙️ Taller de Informes":
    if not st.session_state.textos_generados:
        st.markdown("<h2 style='font-family: Playfair Display, serif; color: #4A4A4A; border-bottom: 2px solid #e8e3d8; padding-bottom: 10px;'>⚙️ Taller de Informes</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #B48E92; font-weight: 500; margin-bottom: 2rem;'>Calcula y redacta usando la información de tu base de datos global.</p>", unsafe_allow_html=True)
    
    if df_prog.empty or 'Estado' not in df_prog.columns:
        pendientes = pd.DataFrame()
    else:
        df_prog['Estado_Norm'] = df_prog['Estado'].astype(str).str.strip().str.upper()
        pendientes = df_prog[df_prog['Estado_Norm'] == 'PENDIENTE']

    if pendientes.empty:
        st.sidebar.success("✅ ¡Agenda limpia!")
    else:
        st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700; letter-spacing:1px; margin-bottom:0;'>COLA DE TRABAJO</p>", unsafe_allow_html=True)
        opciones_menu = []
        for idx, row in pendientes.iterrows():
            id_cli = str(row['id_consultante']).strip()
            id_tipo_bruto = str(row.get('Id_Informe', '1'))
            id_tipo = id_tipo_bruto.replace('.0', '').strip()

            nombre_tipo = None
            if not df_tipos.empty and 'Id_Informe' in df_tipos.columns:
                match_tipo = df_tipos[df_tipos['Id_Informe'].astype(str).str.replace('.0', '', regex=False).str.strip() == id_tipo]
                if not match_tipo.empty:
                    for col in ['Nombre', 'Nombre_Informe', 'Tipo', 'Tipo_Informe', 'Descripcion']:
                        if col in df_tipos.columns: nombre_tipo = str(match_tipo.iloc[0][col]); break
            
            if not nombre_tipo or nombre_tipo == id_tipo or nombre_tipo == id_tipo_bruto or nombre_tipo.lower() == "nan":
                if id_tipo == "1": nombre_tipo = "Carta Natal"
                elif id_tipo == "2": nombre_tipo = "Tránsitos"
                elif id_tipo == "3": nombre_tipo = "Revolución Solar"
                else: nombre_tipo = f"Reporte Tipo {id_tipo}"

            cli_data = df_cli[df_cli['id_consultante'] == id_cli]
            if not cli_data.empty:
                nombre_cli = cli_data.iloc[0].get('Nombres', 'Consultante')
                opciones_menu.append(f"{nombre_cli} | ID: {id_cli} | Informe: {nombre_tipo} (Fila: {idx})")

        if opciones_menu:
            cliente_seleccionado = st.sidebar.selectbox("Informes Pendientes:", opciones_menu, label_visibility="collapsed")

            idx_prog = int(cliente_seleccionado.split("(Fila: ")[1].replace(")", ""))
            row_prog = pendientes.loc[idx_prog]
            id_seleccionado = str(row_prog['id_consultante'])
            id_tipo = str(row_prog.get('Id_Informe', '1')).replace('.0', '').strip()
            cliente_obj = df_cli[df_cli['id_consultante'] == id_seleccionado].iloc[0]

            tipo_obj = None
            nombre_tipo_sel = "natal"
            if not df_tipos.empty and 'Id_Informe' in df_tipos.columns:
                match_tipo = df_tipos[df_tipos['Id_Informe'].astype(str).str.replace('.0', '', regex=False).str.strip() == id_tipo]
                if not match_tipo.empty:
                    tipo_obj = match_tipo.iloc[0]
                    for col in ['Nombre', 'Nombre_Informe', 'Tipo', 'Tipo_Informe', 'Descripcion']:
                        if col in df_tipos.columns: nombre_tipo_sel = str(tipo_obj[col]).lower(); break

            es_revo = (id_tipo == "3" or "solar" in nombre_tipo_sel or "rs" in nombre_tipo_sel or "revoluci" in nombre_tipo_sel)
            es_transito = (id_tipo == "2" or "transito" in nombre_tipo_sel or "tránsito" in nombre_tipo_sel)

            lugar_rs, lat_rs, lon_rs = None, None, None
            if es_revo:
                st.sidebar.markdown("<hr style='margin-top: 1rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)
                st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700; letter-spacing:1px; margin-bottom:0;'>📍 RELOCALIZACIÓN RS</p>", unsafe_allow_html=True)
                lugar_rs = st.sidebar.text_input("Ubicación actual:", placeholder="Ej: Madrid, España")
                if st.sidebar.button("🔍 Buscar en Mapa", use_container_width=True):
                    if lugar_rs:
                        with st.spinner("Buscando en el mapa global..."):
                            try:
                                location = Nominatim(user_agent="astroimpacto_geocoder").geocode(lugar_rs)
                                if location:
                                    st.session_state.lat_rs_auto = str(location.latitude)
                                    st.session_state.lon_rs_auto = str(location.longitude)
                                    st.sidebar.success(f"¡Listo! {location.address}")
                                else: st.sidebar.error("Lugar no encontrado.")
                            except: st.sidebar.error("Error de conexión con el mapa.")
                lat_rs = st.sidebar.text_input("Latitud:", value=st.session_state.lat_rs_auto)
                lon_rs = st.sidebar.text_input("Longitud:", value=st.session_state.lon_rs_auto)
            
            st.sidebar.markdown("<hr style='margin-top: 1rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)

            if st.sidebar.button("🚀 Procesar Informe", type="primary", use_container_width=True):
                st.session_state.idx_prog_actual = idx_prog 
                lat_final, lon_final = None, None
                if es_revo:
                    try:
                        lat_final = float(lat_rs) if lat_rs and lat_rs.strip() else None
                        lon_final = float(lon_rs) if lon_rs and lon_rs.strip() else None
                    except: pass

                with st.spinner(f"interpretando y calculando posiciones..."):
                    if es_transito: st.session_state.tipo_reporte_actual = "TRANSITOS"; datos, plantilla = motor_web.procesar_transitos_con_ia(cliente_obj, tipo_obj, id_seleccionado)
                    elif es_revo: st.session_state.tipo_reporte_actual = "REVOLUCION"; datos, plantilla = motor_web.procesar_rs_con_ia(cliente_obj, tipo_obj, id_seleccionado, lat_rs=lat_final, lon_rs=lon_final, lugar_rs=lugar_rs)
                    else: st.session_state.tipo_reporte_actual = "NATAL"; datos, plantilla = motor_web.procesar_natal_con_ia(cliente_obj, tipo_obj, id_seleccionado)

                    if datos:
                        st.session_state.datos_diccionario = datos
                        st.session_state.plantilla_usar = plantilla
                        st.session_state.textos_generados = True
                        st.sidebar.success("¡Análisis completado! Edita y genera la vista previa.")
                    else: st.sidebar.error(f"Error calculando. Razón: {plantilla}")

    # ==========================================
    # PANTALLA PRINCIPAL DE EDICIÓN Y VISTA PREVIA
    # ==========================================
    if st.session_state.textos_generados:
        d = st.session_state.datos_diccionario
        tipo_actual = st.session_state.tipo_reporte_actual

        st.markdown(f"<h2 style='text-align: center; color: #4A4A4A; font-family: Playfair Display, serif;'>{d.get('titulo_informe', 'Informe')} - {d.get('nombre_cliente', 'Consultante')}</h2>", unsafe_allow_html=True)
        st.divider()

        if tipo_actual == "REVOLUCION":
            st.markdown("<h3 style='color: #B48E92; font-family: Montserrat, sans-serif; font-size: 1.2rem; margin-bottom: 15px;'>📝 Edición - Revolución Solar</h3>", unsafe_allow_html=True)
            with st.expander("1. Infografía (Perspectivas)", expanded=False):
                d['perspectivas']['transformacion'] = st.text_area("Transformación", d['perspectivas']['transformacion'])
                d['perspectivas']['oportunidades'] = st.text_area("Oportunidades", d['perspectivas']['oportunidades'])
                d['perspectivas']['cambio'] = st.text_area("Cambio", d['perspectivas']['cambio'])
                d['perspectivas']['relaciones'] = st.text_area("Relaciones", d['perspectivas']['relaciones'])
            with st.expander("2. Base: Natal, Tránsitos y Progresiones", expanded=False):
                d['intro_texto'] = st.text_area("Introducción", d.get('intro_texto',''))
                d['carta_natal_resumen'] = st.text_area("Resumen Natal", d.get('carta_natal_resumen',''), height=100)
                d['transitos_personales'] = st.text_area("Tránsitos Lentos", d.get('transitos_personales',''), height=100)
                d['progresiones_secundarias'] = st.text_area("Progresiones", d.get('progresiones_secundarias',''), height=100)
            with st.expander("3. Revolución Solar (General y Laboral)", expanded=True):
                d['revolucion_solar_general_1'] = st.text_area("Clima General RS", d.get('revolucion_solar_general_1',''), height=150)
                d['situacion_laboral_economica'] = st.text_area("Laboral y Económica", d.get('situacion_laboral_economica',''), height=150)
            with st.expander("4. Emocional y Trimestral", expanded=True):
                d['situacion_emocional'] = st.text_area("Situación Emocional", d.get('situacion_emocional',''), height=150)
                if 'panorama_trimestral' in d:
                    for i, trim in enumerate(d['panorama_trimestral']): trim['texto'] = st.text_area(trim['titulo'], trim['texto'], key=f"trim_{i}", height=80)

        elif tipo_actual == "TRANSITOS":
            st.markdown("<h3 style='color: #B48E92; font-family: Montserrat, sans-serif; font-size: 1.2rem; margin-bottom: 15px;'>📝 Edición - Pronóstico Anual</h3>", unsafe_allow_html=True)
            with st.expander("Resumen de Energía Base", expanded=False):
                d['interpretacion_sol_signo'] = st.text_area("Sol", d.get('interpretacion_sol_signo',''), height=80)
                d['interpretacion_luna_signo'] = st.text_area("Luna", d.get('interpretacion_luna_signo',''), height=80)
                d['interpretacion_asc_signo'] = st.text_area("Ascendente", d.get('interpretacion_asc_signo',''), height=80)
            with st.expander("👁️ Visión del Año y Astróloga", expanded=True):
                d['frase_anual_corta'] = st.text_input("Lema corto", d.get('frase_anual_corta',''))
                d['analisis_clima_anual'] = st.text_area("Análisis General", d.get('analisis_clima_anual',''), height=200)
            with st.expander("📍 Hoja de Ruta", expanded=True):
                col1, col2 = st.columns(2)
                with col1: d['oportunidad_anual'] = st.text_area("✅ Gran Oportunidad", d.get('oportunidad_anual',''), height=100)
                with col2: d['atencion_anual'] = st.text_area("🛑 Atención a Esto", d.get('atencion_anual',''), height=100)
                d['habito_recomendado'] = st.text_input("💡 Hábito Recomendado", d.get('habito_recomendado',''))
            with st.expander("📅 Eventos Mensuales", expanded=True):
                if 'calendario_por_meses' in d:
                    for mes, eventos in d['calendario_por_meses'].items():
                        st.markdown(f"<h4 style='color:#B48E92; margin-top:20px;'>{mes}</h4>", unsafe_allow_html=True)
                        for ev in eventos: ev['texto_efecto'] = st.text_area(f"{ev['fecha']} - {ev['transito']} {ev['aspecto']} {ev['natal']}", ev.get('texto_efecto',''), height=60, key=f"tr_{mes}_{ev['transito']}_{ev['natal']}_{ev['fecha']}")

        else:
            st.markdown("<h3 style='color: #B48E92; font-family: Montserrat, sans-serif; font-size: 1.2rem; margin-bottom: 15px;'>📝 Edición - Carta Natal</h3>", unsafe_allow_html=True)
            with st.expander("Palabras Clave", expanded=False):
                col1, col2, col3 = st.columns(3)
                aspectos = d.get('aspectos_clave', ["", "", ""])
                with col1: aspectos[0] = st.text_input("Palabra 1", aspectos[0] if len(aspectos)>0 else "")
                with col2: aspectos[1] = st.text_input("Palabra 2", aspectos[1] if len(aspectos)>1 else "")
                with col3: aspectos[2] = st.text_input("Palabra 3", aspectos[2] if len(aspectos)>2 else "")
                d['aspectos_clave'] = aspectos
            with st.expander("☉ Sol / ☽ Luna / AC", expanded=False):
                d['interpretacion_sol_signo'] = st.text_area("Sol", d.get('interpretacion_sol_signo',''), height=80)
                d['interpretacion_luna_signo'] = st.text_area("Luna", d.get('interpretacion_luna_signo',''), height=80)
                d['interpretacion_asc_signo'] = st.text_area("Ascendente", d.get('interpretacion_asc_signo',''), height=80)
            with st.expander("🪐 Gigantes del Cielo", expanded=False):
                if 'gigantes_del_cielo' in d:
                    for i, gigante in enumerate(d['gigantes_del_cielo']): gigante['texto'] = st.text_area(f"Texto {gigante['nombre']}", gigante.get('texto',''), height=80, key=f"gig_{i}")
            with st.expander("✨ Análisis Global", expanded=True):
                d['interpretacion_personalidad_global'] = st.text_area("Síntesis Final", d.get('interpretacion_personalidad_global',''), height=250)

        st.divider()

        # ==========================================
        # BOTONES FINALES 
        # ==========================================
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1: btn_preview = st.button("👁️ VER VISTA PREVIA (No guarda)", use_container_width=True)
        with col_btn2: btn_guardar = st.button("💾 GUARDAR DEFINITIVO", type="primary", use_container_width=True)

        if btn_preview:
            try:
                env = Environment(loader=FileSystemLoader('.'))
                html_final = env.get_template(st.session_state.plantilla_usar).render(d)
                st.markdown("<h3 style='text-align:center; color:#B48E92; margin-top:30px; font-family: Playfair Display, serif;'>🔍 Vista Previa</h3>", unsafe_allow_html=True)
                components.html(html_final, height=900, scrolling=True)
            except Exception as e: st.error(f"Error generando vista previa: {e}")

        if btn_guardar:
            try:
                env = Environment(loader=FileSystemLoader('.'))
                html_final = env.get_template(st.session_state.plantilla_usar).render(d)

                OUTPUT_DIR = r'C:\Astroimpacto\Informes'
                sufijo = "Transitos" if tipo_actual == "TRANSITOS" else "Revolucion_Solar" if tipo_actual == "REVOLUCION" else "Carta_Natal"
                ruta_final = os.path.join(OUTPUT_DIR, f"Informe_{str(d.get('nombre_cliente', 'Cliente')).replace(' ', '_')}_{sufijo}.html")

                with open(ruta_final, "w", encoding="utf-8") as f:
                    f.write(html_final)

                st.success(f"✅ ¡Tu reporte PDF fue generado con éxito!")
                st.warning("⚠️ Recuerda abrir tu Google Sheet y cambiar el estado del cliente a 'Procesado' manualmente.")
                st.balloons()
            except Exception as e:
                st.error(f"Error guardando el documento final: {e}")
