import streamlit as st
import streamlit.components.v1 as components 
import pandas as pd
import os
import base64
from jinja2 import Environment, FileSystemLoader
import motor_web
from geopy.geocoders import Nominatim

# ==============================================================================
# 1. FUNCIONES DE APOYO, SEGURIDAD TÉCNICA E IDENTIDAD VISUAL
# ==============================================================================

@st.cache_data
def get_base_64_of_bin_file(bin_file):
    """
    Convierte una imagen local a formato Base64 para inyectarla en el HTML.
    Es fundamental para logos y favicons sin depender de rutas de servidor externas,
    asegurando que el diseño sea portable y profesional en cualquier dispositivo.
    """
    try:
        if os.path.exists(bin_file):
            with open(bin_file, 'rb') as f:
                data = f.read()
            return f"data:image/png;base64,{base64.b64encode(data).decode()}"
        return ""
    except Exception:
        # Fallo silencioso para no interrumpir la ejecución de la App si falta una imagen
        return ""

# CONFIGURACIÓN INICIAL DE LA PÁGINA (ESTADO EXPANDIDO Y LAYOUT ANCHO)
# El layout 'wide' es vital para que el panel de edición de Patricia sea cómodo en iPad/iPhone.
st.set_page_config(
    page_title="Astroimpacto - Gestión Astrológica Profesional",
    page_icon="apple-icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# IDENTIDAD VISUAL PARA DISPOSITIVOS MÓVILES (IPHONE) Y NAVEGADORES
# Esto permite que la web se comporte como una aplicación nativa en el dispositivo.
st.markdown('<link rel="apple-touch-icon" href="apple-icon.png">', unsafe_allow_html=True)
st.markdown('<link rel="manifest" href="./manifest.json">', unsafe_allow_html=True)

# --- BLOQUE DE SEGURIDAD PARA EL ÍCONO WEB (VITAL PARA LA MARCA) ---
# Recuperamos la inyección del favicon para que la pestaña del navegador muestre el logo.
try:
    icono_base64 = get_base_64_of_bin_file('apple-icon.png')
    if icono_base64:
        st.markdown(f'<link rel="icon" href="{icono_base64}">', unsafe_allow_html=True)
except Exception:
    pass

# ESTILOS CSS PERSONALIZADOS (DISEÑO PREMIUM ASTROIMPACTO)
# Definimos la paleta de colores corporativa y tipografías elegantes (Playfair Display).
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    /* Configuración de la barra lateral (Sidebar) */
    [data-testid="stSidebar"] {
        background-color: #fdfcf9;
        border-right: 1px solid #e8e3d8;
    }
    
    /* Personalización de Botones de Acción Principal (Rosa Humo) */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        width: 100%;
        height: 3.5rem;
        margin-top: 10px;
    }
    .stButton>button[kind="primary"] {
        background-color: #B48E92 !important;
        border: none !important;
        color: white !important;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #967074 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(180, 142, 146, 0.3);
    }
    
    /* Tipografías y Títulos Elegantes */
    h1, h2, h3, h4 {
        font-family: 'Playfair Display', serif !important;
        color: #4A4A4A !important;
    }
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    /* Paneles de Edición (Expanders) con sombra suave */
    div[data-testid="stExpander"] {
        background-color: white;
        border: 1px solid #f0ebe1;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    
    /* Cajas de Texto de Interpretación IA (Lógica de Escritura) */
    .stTextArea textarea {
        font-size: 0.95rem;
        line-height: 1.6;
        color: #333;
        background-color: #fafafa;
        border-radius: 8px;
        border: 1px solid #eee;
    }
    
    /* Selectores de Clientes para evitar cortes visuales */
    .stSelectbox div[data-baseweb="select"] {
        white-space: normal !important;
        border-radius: 8px;
    }
    
    /* Estilo de Mensajes de Alerta y Error */
    .stAlert {
        border-radius: 12px;
    }

    /* Métrica de Diagnóstico en Sidebar */
    .diag-box {
        padding: 12px;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        margin-bottom: 15px;
        font-size: 0.85rem;
        color: #495057;
    }
    .diag-item {
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
    }
</style>
""", unsafe_allow_html=True)

# LOGOTIPO Y ENCABEZADO DE MARCA EN EL PANEL LATERAL (DISEÑO SVG)
SIDEBAR_HEADER_HTML = """
<div style="text-align: center; padding-bottom: 1.5rem; border-bottom: 1px solid #e8e3d8; margin-bottom: 1.5rem; margin-top: -2rem;">
    <div style="width: 55px; height: 55px; margin: 0 auto 12px auto; color: #B48E92;">
        <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="100" cy="90" r="50" stroke="currentColor" stroke-width="3"/>
            <path d="M100 20 L110 90 L100 160 L90 90 Z" fill="currentColor"/>
            <path d="M170 90 L100 100 L30 90 L100 80 Z" fill="currentColor"/>
            <line x1="100" y1="140" x2="100" y2="185" stroke="currentColor" stroke-width="4"/>
            <line x1="75" y1="165" x2="125" y2="165" stroke="currentColor" stroke-width="4"/>
        </svg>
    </div>
    <h2 style="font-family: 'Playfair Display', serif; font-size: 1.9rem; color: #4A4A4A; margin: 0; font-weight: 700; letter-spacing: 0.5px;">Astroimpacto</h2>
    <p style="font-family: 'Montserrat', sans-serif; font-size: 0.65rem; letter-spacing: 2.5px; color: #B48E92; text-transform: uppercase; margin-top: 6px;">Plataforma Web Profesional</p>
</div>
"""
st.sidebar.markdown(SIDEBAR_HEADER_HTML, unsafe_allow_html=True)

# ==============================================================================
# 2. GESTIÓN DEL ESTADO DE SESIÓN (PERSISTENCIA DE DATOS)
# ==============================================================================
if 'textos_generados' not in st.session_state:
    st.session_state.update({
        'textos_generados': False,
        'datos_diccionario': {},
        'plantilla_usar': 'informe_astroimpacto.html',
        'tipo_reporte_actual': "NATAL",
        'lat_rs_auto': "",
        'lon_rs_auto': "",
        'lugar_rs_confirmado': "",
        'idx_prog_actual': None
    })

# ==============================================================================
# 3. CARGA Y NORMALIZACIÓN ROBUSTA DE BASES DE DATOS (GOOGLE SHEETS)
# ==============================================================================
@st.cache_data(ttl=5)
def cargar_bases_web():
    """Descarga datos de Sheets y unifica nombres de columnas para evitar KeyError y 'Datos Incompletos'."""
    try:
        url_secreta = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id = url_secreta.split("/d/")[1].split("/")[0] if "/d/" in url_secreta else url_secreta
        
        # Generar URLs de descarga directa CSV
        u_cli = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Consultantes"
        u_prog = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Informes_Programados"
        
        df_c = pd.read_csv(u_cli).dropna(how="all")
        df_p = pd.read_csv(u_prog).dropna(how="all")

        # Normalización Universal de Columnas para asegurar que el motor reciba lo que necesita
        for df in [df_c, df_p]:
            if not df.empty:
                df.columns = df.columns.str.strip()
                # Unificar variantes de Identificador
                for c in ['id', 'Id', 'ID', 'IDENTIFICADOR', 'id_cli', 'id_consultante']:
                    if c in df.columns and 'id_consultante' not in df.columns:
                        df.rename(columns={c: 'id_consultante'}, inplace=True)
                # Unificar variantes de Fecha
                for c in ['fecha', 'FECHA', 'BirthDate', 'Nacimiento', 'Fecha_Nac', 'FECHA NACIMIENTO']:
                    if c in df.columns and 'Fecha' not in df.columns:
                        df.rename(columns={c: 'Fecha'}, inplace=True)
                # Unificar variantes de Hora
                for c in ['hora', 'HORA', 'BirthTime', 'Hora_Nac', 'HORA NACIMIENTO']:
                    if c in df.columns and 'Hora' not in df.columns:
                        df.rename(columns={c: 'Hora'}, inplace=True)
                # Unificar variantes de Latitud
                for c in ['lat', 'latitud', 'LATITUD', 'Lat', 'LAT']:
                    if c in df.columns and 'Latitud' not in df.columns:
                        df.rename(columns={c: 'Latitud'}, inplace=True)
                # Unificar variantes de Longitud
                for c in ['lon', 'longitud', 'LONGITUD', 'Lon', 'Lng', 'lng', 'LON']:
                    if c in df.columns and 'Longitud' not in df.columns:
                        df.rename(columns={c: 'Longitud'}, inplace=True)
                
                if 'id_consultante' in df.columns:
                    df['id_consultante'] = df['id_consultante'].astype(str).str.replace('.0', '', regex=False).str.strip()
        
        return df_c, df_p
    except Exception as e:
        st.sidebar.error(f"⚠️ Error conectando a Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_cli, df_prog = cargar_bases_web()

# ==============================================================================
# 4. NAVEGACIÓN Y PANEL DE AUDITORÍA TÉCNICA
# ==============================================================================
st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700; letter-spacing:1px;'>NAVEGACIÓN</p>", unsafe_allow_html=True)
modo_app = st.sidebar.radio("Menú Principal", ["⚙️ Taller de Informes", "📅 Programar Cliente"], label_visibility="collapsed")
st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

# VISOR DE AUDITORÍA TÉCNICA (Visualiza los grados y minutos exactos para Patricia)
if st.session_state.textos_generados:
    st.sidebar.markdown("### 🔍 Datos Técnicos Exactos")
    st.sidebar.caption("Cálculos matemáticos usados para la interpretación:")
    st.sidebar.code(st.session_state.datos_diccionario.get('auditoria_tecnica', 'Sin datos disponibles'), language='text')
    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

# ==============================================================================
# 5. MODO: PROGRAMAR CLIENTE
# ==============================================================================
if modo_app == "📅 Programar Cliente":
    st.markdown("## 📅 Agenda de Clientes")
    st.markdown("<p style='color: #B48E92; font-weight: 500;'>Asigna un tipo de reporte a un consultante para que aparezca en el Taller.</p>", unsafe_allow_html=True)
    if not df_cli.empty:
        opciones_cli = [f"{row['Nombres']} (ID: {row['id_consultante']})" for _, row in df_cli.iterrows() if 'Nombres' in row]
        st.selectbox("1. Selecciona el Cliente:", opciones_cli)
        st.selectbox("2. Tipo de Informe:", ["Carta Natal", "Tránsitos Anuales", "Revolución Solar"])
        if st.button("➕ Programar", type="primary"):
            st.info("Añade la fila en tu Google Sheet y recarga la página para procesarla.")
    else:
        st.warning("No se cargaron consultantes. Revisa tu archivo de Google Sheets.")

# ==============================================================================
# 6. MODO: TALLER DE INFORMES (PROCESAMIENTO Y EDICIÓN PROFUNDA)
# ==============================================================================
elif modo_app == "⚙️ Taller de Informes":
    if not st.session_state.textos_generados:
        st.markdown("## ⚙️ Taller de Informes")
        st.markdown("<p style='color: #B48E92; font-weight: 500;'>Genera interpretaciones personalizadas basadas en efemérides exactas.</p>", unsafe_allow_html=True)

    pendientes = df_prog[df_prog['Estado'].astype(str).str.upper() == 'PENDIENTE'] if not df_prog.empty and 'Estado' in df_prog.columns else pd.DataFrame()

    if pendientes.empty and not st.session_state.textos_generados:
        st.sidebar.success("✅ ¡Agenda limpia! No hay reportes pendientes.")
    elif not pendientes.empty:
        st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700;'>PENDIENTES</p>", unsafe_allow_html=True)
        opciones_menu = []
        for idx, row in pendientes.iterrows():
            if 'id_consultante' in row:
                id_c = str(row['id_consultante']).strip()
                cli_data = df_cli[df_cli['id_consultante'] == id_c] if not df_cli.empty else pd.DataFrame()
                nombre_cli = cli_data.iloc[0].get('Nombres', 'Consultante') if not cli_data.empty else f"ID: {id_c}"
                id_tipo_inf = str(row.get('Id_Informe', '1')).replace('.0', '').strip()
                tipo_txt = "Natal" if id_tipo_inf == "1" else "Transitos" if id_tipo_inf == "2" else "Revolucion"
                opciones_menu.append(f"{nombre_cli} ({tipo_txt}) | Fila: {idx}")

        if opciones_menu:
            sel_p = st.sidebar.selectbox("Selecciona el informe:", opciones_menu, label_visibility="collapsed")
            idx_p = int(sel_p.split("Fila: ")[1])
            row_p = pendientes.loc[idx_p]
            id_sel = str(row_p['id_consultante'])
            cli_obj = df_cli[df_cli['id_consultante'] == id_sel].iloc[0]
            id_t = str(row_p.get('Id_Informe', '1')).replace('.0', '').strip()

            # --- PANEL DE DIAGNÓSTICO DE DATOS (Mantenemos para seguridad) ---
            st.sidebar.markdown("<p style='font-size:0.7rem; font-weight:700; margin-top:10px;'>📊 DIAGNÓSTICO DE DATOS</p>", unsafe_allow_html=True)
            check_fecha = "✅" if "Fecha" in cli_obj and not pd.isna(cli_obj["Fecha"]) else "❌"
            check_hora = "✅" if "Hora" in cli_obj and not pd.isna(cli_obj["Hora"]) else "❌"
            check_lat = "✅" if "Latitud" in cli_obj and not pd.isna(cli_obj["Latitud"]) else "❌"
            check_lon = "✅" if "Longitud" in cli_obj and not pd.isna(cli_obj["Longitud"]) else "❌"
            
            diag_html = f"""<div class='diag-box'><div class='diag-item'><span>Fecha:</span> <span>{check_fecha}</span></div><div class='diag-item'><span>Hora:</span> <span>{check_hora}</span></div><div class='diag-item'><span>Latitud:</span> <span>{check_lat}</span></div><div class='diag-item'><span>Longitud:</span> <span>{check_lon}</span></div></div>"""
            st.sidebar.markdown(diag_html, unsafe_allow_html=True)

            # --- BUSCADOR DE COORDENADAS PARA REVOLUCIÓN SOLAR ---
            lat_rs, lon_rs, lug_final = None, None, ""
            if id_t == "3" or "Revolucion" in sel_p: 
                st.sidebar.markdown("<hr style='margin-top: 1rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)
                st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700; letter-spacing:1px; margin-bottom:0;'>📍 RELOCALIZACIÓN RS</p>", unsafe_allow_html=True)
                lug_rs_input = st.sidebar.text_input("Ciudad de la Revolución:", placeholder="Ej: Madrid, España", key="ciudad_rs_search")
                if st.sidebar.button("🔍 Buscar en Mapa Global", use_container_width=True):
                    if lug_rs_input:
                        with st.spinner("Buscando coordenadas..."):
                            try:
                                geolocator = Nominatim(user_agent="astroimpacto_premium_final_v500")
                                loc = geolocator.geocode(lug_rs_input)
                                if loc:
                                    st.session_state.lat_rs_auto, st.session_state.lon_rs_auto, st.session_state.lugar_rs_confirmado = str(loc.latitude), str(loc.longitude), loc.address
                                    st.sidebar.success(f"Listo: {loc.address}")
                                else: st.sidebar.error("Lugar no encontrado.")
                            except Exception: st.sidebar.error("Error de conexión.")
                lat_rs = st.sidebar.text_input("Latitud de la RS:", value=st.session_state.lat_rs_auto)
                lon_rs = st.sidebar.text_input("Longitud de la RS:", value=st.session_state.lon_rs_auto)
                lug_final = st.session_state.lugar_rs_confirmado if st.session_state.lugar_rs_confirmado else lug_rs_input
            # --------------------------------------------------------------------------------

            st.sidebar.markdown("<br>", unsafe_allow_html=True)
            if st.sidebar.button("🚀 INICIAR PROCESAMIENTO", type="primary", use_container_width=True):
                # BLINDAJE DE DATOS: Aseguramos que el motor reciba un diccionario con las llaves exactas
                payload_motor = {
                    "Nombres": cli_obj.get("Nombres", "Consultante"),
                    "Fecha": cli_obj.get("Fecha"),
                    "Hora": cli_obj.get("Hora"),
                    "Latitud": cli_obj.get("Latitud"),
                    "Longitud": cli_obj.get("Longitud"),
                    "Genero": cli_obj.get("Genero", "M"),
                    "Ciudad": cli_obj.get("Ciudad", ""),
                    "Pais": cli_obj.get("Pais", "")
                }
                
                faltantes = [k for k in ["Fecha", "Hora", "Latitud", "Longitud"] if pd.isna(payload_motor[k])]
                if faltantes:
                    st.sidebar.error(f"⚠️ Error: Faltan datos en el Excel ({', '.join(faltantes)})")
                else:
                    with st.spinner("Calculando efemérides y redactando informe integral..."):
                        try:
                            datos, plant = None, None
                            if id_t == "2":
                                st.session_state.tipo_reporte_actual = "TRANSITOS"
                                datos, plant = motor_web.procesar_transitos_con_ia(payload_motor, None, id_sel)
                            elif id_t == "3" or "Revolucion" in sel_p:
                                st.session_state.tipo_reporte_actual = "REVOLUCION"
                                datos, plant = motor_web.procesar_rs_con_ia(payload_motor, None, id_sel, lat_rs=lat_rs, lon_rs=lon_rs, lugar_rs=lug_final)
                            else:
                                st.session_state.tipo_reporte_actual = "NATAL"
                                datos, plant = motor_web.procesar_natal_con_ia(payload_motor, None, id_sel)
                            
                            if datos:
                                st.session_state.update({'datos_diccionario': datos, 'plantilla_usar': plant, 'textos_generados': True, 'idx_prog_actual': idx_p})
                                st.rerun()
                            else:
                                st.sidebar.error(f"⚠️ El motor falló: {plant}")
                        except Exception as e:
                            st.sidebar.error(f"❌ Error crítico: {e}")

    # ==============================================================================
    # 7. PANEL DE EDICIÓN INTEGRAL (DETALLE MÁXIMO)
    # ==============================================================================
    if st.session_state.textos_generados:
        d = st.session_state.datos_diccionario
        tipo = st.session_state.tipo_reporte_actual
        st.subheader(f"Editando: {d.get('titulo_informe')} - {d.get('nombre_cliente')}")
        
        if tipo == "REVOLUCION":
            with st.expander("1. Infografía Inicial", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    d['perspectivas']['transformacion'] = st.text_area("Transformación", d['perspectivas'].get('transformacion', ''))
                    d['perspectivas']['cambio'] = st.text_area("Cambio Principal", d['perspectivas'].get('cambio', ''))
                with col2:
                    d['perspectivas']['oportunidades'] = st.text_area("Oportunidades", d['perspectivas'].get('oportunidades', ''))
                    d['perspectivas']['relaciones'] = st.text_area("Relaciones", d['perspectivas'].get('relaciones', ''))
            with st.expander("2. Introducción y Bases Astrológicas", expanded=False):
                d['intro_texto'] = st.text_area("Introducción", d.get('intro_texto',''))
                d['carta_natal_resumen'] = st.text_area("Resumen Natal", d.get('carta_natal_resumen',''), height=150)
                d['transitos_personales'] = st.text_area("Análisis Tránsitos", d.get('transitos_personales',''), height=150)
                d['progresiones_secundarias'] = st.text_area("Interpretación Progresiones", d.get('progresiones_secundarias',''), height=150)
                d['como_actuar_progresiones'] = st.text_area("Consejos (Líneas)", "\n".join(d.get('como_actuar_progresiones', []))).split("\n")
            with st.expander("3. Revolución Solar (Detalle)", expanded=True):
                d['revolucion_solar_general_1'] = st.text_area("Clima RS", d.get('revolucion_solar_general_1',''), height=250)
                d['revo_propone'] = st.text_area("Propuestas (Líneas)", "\n".join(d.get('revo_propone', []))).split("\n")
                d['situacion_laboral_economica'] = st.text_area("Área Laboral", d.get('situacion_laboral_economica',''), height=180)
                d['logro_objetivos_profesionales'] = st.text_area("Objetivos Laborales (Líneas)", "\n".join(d.get('logro_objetivos_profesionales', []))).split("\n")
            with st.expander("4. Emocional y Trimestral", expanded=True):
                d['situacion_emocional'] = st.text_area("Vida Afectiva", d.get('situacion_emocional',''), height=180)
                if 'panorama_trimestral' in d:
                    for i, t in enumerate(d.get('panorama_trimestral', [])):
                        t['texto'] = st.text_area(f"📍 {t.get('titulo')}", t.get('texto', ''), key=f"rs_t_{i}", height=120)
                d['plan_accion_objetivos'] = st.text_area("Plan Acción (Líneas)", "\n".join(d.get('plan_accion_objetivos', []))).split("\n")

        elif tipo == "TRANSITOS":
            with st.expander("1. Energía Natal Base", expanded=False):
                d['interpretacion_sol_signo'] = st.text_area("Sol", d.get('interpretacion_sol_signo',''))
                d['interpretacion_luna_signo'] = st.text_area("Luna", d.get('interpretacion_luna_signo',''))
                d['interpretacion_asc_signo'] = st.text_area("Ascendente", d.get('interpretacion_asc_signo',''))
            with st.expander("2. Clima Anual Astrológico", expanded=True):
                d['frase_anual_corta'] = st.text_input("Lema del Año", d.get('frase_anual_corta',''))
                d['analisis_clima_anual'] = st.text_area("Interpretación Evolutiva", d.get('analisis_clima_anual',''), height=300)
                d['oportunidad_anual'] = st.text_area("Oportunidad", d.get('oportunidad_anual',''), height=120)
                d['atencion_anual'] = st.text_area("Punto de Cuidado", d.get('atencion_anual',''), height=120)
            with st.expander("3. Calendario de Eventos Mensuales", expanded=True):
                for m, evs in d.get('calendario_por_meses', {}).items():
                    st.markdown(f"### 🗓️ {m}")
                    for ev in evs:
                        ev['texto_efecto'] = st.text_area(f"{ev.get('fecha')} | {ev.get('transito')} a {ev.get('natal')}", ev.get('texto_efecto', ''), key=f"tr_{m}_{ev.get('fecha','')}")

        else: # NATAL
            with st.expander("1. Tríada Sagrada de Identidad", expanded=True):
                d['interpretacion_sol_signo'] = st.text_area("☉ Propósito Solar", d.get('interpretacion_sol_signo',''), height=150)
                d['interpretacion_luna_signo'] = st.text_area("☽ Refugio Lunar", d.get('interpretacion_luna_signo',''), height=150)
                d['interpretacion_asc_signo'] = st.text_area("AC Camino del Ascendente", d.get('interpretacion_asc_signo',''), height=150)
            with st.expander("2. Los Gigantes del Cielo", expanded=False):
                if 'gigantes_del_cielo' in d:
                    for i, g in enumerate(d.get('gigantes_del_cielo', [])):
                        g['texto'] = st.text_area(f"{g.get('nombre')} en {g.get('signo', '')}", g.get('texto', ''), key=f"g_{i}", height=120)
            with st.expander("3. Síntesis y FODA Personal", expanded=True):
                d['interpretacion_personalidad_global'] = st.text_area("Relato Final de Integración", d.get('interpretacion_personalidad_global',''), height=350)
                f1, f2 = st.columns(2)
                with f1: d['foda']['fortalezas'] = st.text_area("Fortalezas", "\n".join(d['foda'].get('fortalezas', []))).split("\n")
                with f2: d['foda']['debilidades'] = st.text_area("Debilidades", "\n".join(d['foda'].get('debilidades', []))).split("\n")

        st.divider()
        c1, c2 = st.columns(2)
        d['logo_base64'] = get_base_64_of_bin_file('apple-icon.png')
        try:
            env = Environment(loader=FileSystemLoader('.'))
            tmpl = env.get_template(st.session_state.plantilla_usar)
            with c1:
                if st.button("👁️ VER VISTA PREVIA"):
                    try: components.html(tmpl.render(d), height=900, scrolling=True)
                    except Exception: st.error("Error render.")
            with c2:
                html_final = tmpl.render(d)
                st.download_button("💾 DESCARGAR INFORME HTML FINAL", data=html_final, file_name=f"Informe_{d.get('nombre_cliente', 'Consultante')}.html", mime="text/html", type="primary")
                if st.button("❌ FINALIZAR Y LIMPIAR TALLER"):
                    st.session_state.textos_generados = False
                    st.rerun()
        except Exception as e: st.error(f"Error plantilla: {e}")
