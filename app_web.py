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
        return ""

# CONFIGURACIÓN INICIAL DE LA PÁGINA
st.set_page_config(
    page_title="Astroimpacto - Gestión Astrológica Profesional",
    page_icon="apple-icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# IDENTIDAD VISUAL PARA DISPOSITIVOS MÓVILES
st.markdown('<link rel="apple-touch-icon" href="apple-icon.png">', unsafe_allow_html=True)
st.markdown('<link rel="manifest" href="./manifest.json">', unsafe_allow_html=True)

try:
    icono_base64 = get_base_64_of_bin_file('apple-icon.png')
    if icono_base64:
        st.markdown(f'<link rel="icon" href="{icono_base64}">', unsafe_allow_html=True)
except Exception:
    pass

# ESTILOS CSS PERSONALIZADOS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    [data-testid="stSidebar"] {
        background-color: #fdfcf9;
        border-right: 1px solid #e8e3d8;
    }
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
    h1, h2, h3, h4 {
        font-family: 'Playfair Display', serif !important;
        color: #4A4A4A !important;
    }
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
    }
    div[data-testid="stExpander"] {
        background-color: white;
        border: 1px solid #f0ebe1;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    .stTextArea textarea {
        font-size: 0.95rem;
        line-height: 1.6;
        color: #333;
        background-color: #fafafa;
        border-radius: 8px;
        border: 1px solid #eee;
    }
    .stSelectbox div[data-baseweb="select"] {
        white-space: normal !important;
        border-radius: 8px;
    }
    .stAlert { border-radius: 12px; }
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

# LOGOTIPO Y ENCABEZADO
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
# 2. GESTIÓN DEL ESTADO DE SESIÓN
# ==============================================================================
if 'textos_generados' not in st.session_state:
    st.session_state.update({
        'textos_generados':      False,
        'datos_diccionario':     {},
        'plantilla_usar':        'informe_astroimpacto.html',
        'tipo_reporte_actual':   "NATAL",
        'lat_rs_auto':           "",
        'lon_rs_auto':           "",
        'lugar_rs_confirmado':   "",
        'idx_prog_actual':       None
    })

# ==============================================================================
# 3. CARGA ROBUSTA DE BASES DE DATOS (GOOGLE SHEETS)
# CORRECCIÓN: ttl cambiado de 5 segundos a 300 segundos para evitar
# sobrecargar Google Sheets en cada interacción del usuario.
# ==============================================================================
@st.cache_data(ttl=300)
def cargar_bases_web():
    """
    Descarga datos de Sheets y unifica nombres de columnas.
    """
    try:
        url_secreta = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id    = url_secreta.split("/d/")[1].split("/")[0] if "/d/" in url_secreta else url_secreta

        u_cli  = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Consultantes"
        u_prog = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Informes_Programados"

        df_c = pd.read_csv(u_cli).dropna(how="all")
        df_p = pd.read_csv(u_prog).dropna(how="all")

        mapa_columnas = {
            'id_consultante': ['id', 'Id', 'ID', 'IDENTIFICADOR', 'id_cli', 'id_consultante', 'CODIGO'],
            'Fecha':    ['fecha', 'FECHA', 'BirthDate', 'Nacimiento', 'Fecha_Nac', 'FECHA NACIMIENTO', 'FECHA_NACIMIENTO'],
            'Hora':     ['hora', 'HORA', 'BirthTime', 'Hora_Nac', 'HORA NACIMIENTO', 'HORA_NACIMIENTO', 'TIEMPO'],
            'Latitud':  ['lat', 'latitud', 'LATITUD', 'Lat', 'LAT', 'COOR_LAT', 'LAT_NAC'],
            'Longitud': ['lon', 'longitud', 'LONGITUD', 'Lon', 'Lng', 'lng', 'LON', 'COOR_LON', 'LON_NAC'],
            'Nombres':  ['Nombre', 'NOMBRE', 'Nombres', 'NAME', 'Consultante', 'CLIENTE']
        }

        for df in [df_c, df_p]:
            if not df.empty:
                df.columns = df.columns.str.strip()
                for destino, sinonimos in mapa_columnas.items():
                    for s in sinonimos:
                        if s in df.columns and destino not in df.columns:
                            df.rename(columns={s: destino}, inplace=True)
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
        n_col = 'Nombres' if 'Nombres' in df_cli.columns else df_cli.columns[1]
        opciones_cli = [f"{row[n_col]} (ID: {row['id_consultante']})" for _, row in df_cli.iterrows() if 'id_consultante' in df_cli.columns]
        st.selectbox("1. Selecciona el Cliente:", opciones_cli)
        st.selectbox("2. Tipo de Informe:", ["Carta Natal", "Tránsitos Anuales", "Revolución Solar"])
        if st.button("➕ Programar", type="primary"):
            st.info("Nota: En esta versión web, agrega la fila en tu Google Sheet y recarga la página para procesarla.")
    else:
        st.warning("No se cargaron consultantes. Revisa tu archivo de Google Sheets.")

# ==============================================================================
# 6. MODO: TALLER DE INFORMES
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
                id_c     = str(row['id_consultante']).strip()
                cli_data = df_cli[df_cli['id_consultante'] == id_c] if not df_cli.empty else pd.DataFrame()
                n_col_cli   = 'Nombres' if 'Nombres' in cli_data.columns else (cli_data.columns[1] if not cli_data.empty else "")
                nombre_cli  = cli_data.iloc[0][n_col_cli] if not cli_data.empty else f"ID: {id_c}"
                id_tipo_inf = str(row.get('Id_Informe', '1')).replace('.0', '').strip()
                tipo_txt    = "Natal" if id_tipo_inf == "1" else "Transitos" if id_tipo_inf == "2" else "Revolucion"
                opciones_menu.append(f"{nombre_cli} ({tipo_txt}) | Fila: {idx}")

        if opciones_menu:
            sel_p  = st.sidebar.selectbox("Selecciona el informe:", opciones_menu, label_visibility="collapsed")
            idx_p  = int(sel_p.split("Fila: ")[1])
            row_p  = pendientes.loc[idx_p]
            id_sel = str(row_p['id_consultante'])
            cli_obj = df_cli[df_cli['id_consultante'] == id_sel].iloc[0]
            id_t   = str(row_p.get('Id_Informe', '1')).replace('.0', '').strip()

            # DIAGNÓSTICO DE DATOS
            st.sidebar.markdown("<p style='font-size:0.7rem; font-weight:700; margin-top:10px;'>📊 DIAGNÓSTICO DE DATOS</p>", unsafe_allow_html=True)
            check_fecha = "✅" if "Fecha"    in cli_obj and not pd.isna(cli_obj["Fecha"])    else "❌"
            check_hora  = "✅" if "Hora"     in cli_obj and not pd.isna(cli_obj["Hora"])     else "❌"
            check_lat   = "✅" if "Latitud"  in cli_obj and not pd.isna(cli_obj["Latitud"])  else "❌"
            check_lon   = "✅" if "Longitud" in cli_obj and not pd.isna(cli_obj["Longitud"]) else "❌"
            diag_html = f"""
            <div class='diag-box'>
                <div class='diag-item'><span>Fecha Nac:</span> <span>{check_fecha}</span></div>
                <div class='diag-item'><span>Hora Nac:</span>  <span>{check_hora}</span></div>
                <div class='diag-item'><span>Latitud:</span>   <span>{check_lat}</span></div>
                <div class='diag-item'><span>Longitud:</span>  <span>{check_lon}</span></div>
            </div>
            """
            st.sidebar.markdown(diag_html, unsafe_allow_html=True)

            # BUSCADOR DE COORDENADAS PARA REVOLUCIÓN SOLAR
            lat_rs, lon_rs, lug_final = None, None, ""
            if id_t == "3" or "Revolucion" in sel_p:
                st.sidebar.markdown("<hr style='margin-top: 1rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)
                st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700; letter-spacing:1px; margin-bottom:0;'>📍 RELOCALIZACIÓN RS</p>", unsafe_allow_html=True)
                st.sidebar.caption("Ingresa ciudad y país para buscar coordenadas exactas.")
                lug_rs_input = st.sidebar.text_input("Ciudad de la Revolución:", placeholder="Ej: Madrid, España", key="ciudad_rs_search")
                if st.sidebar.button("🔍 Buscar en Mapa Global", use_container_width=True):
                    if lug_rs_input:
                        with st.spinner("Buscando coordenadas..."):
                            try:
                                geolocator = Nominatim(user_agent="astroimpacto_premium_v500")
                                loc = geolocator.geocode(lug_rs_input)
                                if loc:
                                    st.session_state.lat_rs_auto       = str(loc.latitude)
                                    st.session_state.lon_rs_auto       = str(loc.longitude)
                                    st.session_state.lugar_rs_confirmado = loc.address
                                    st.sidebar.success(f"Listo: {loc.address}")
                                else:
                                    st.sidebar.error("Lugar no encontrado.")
                            except Exception:
                                st.sidebar.error("Error de conexión.")

                lat_rs    = st.sidebar.text_input("Latitud de la RS:",  value=st.session_state.lat_rs_auto)
                lon_rs    = st.sidebar.text_input("Longitud de la RS:", value=st.session_state.lon_rs_auto)
                lug_final = st.session_state.lugar_rs_confirmado if st.session_state.lugar_rs_confirmado else lug_rs_input

            st.sidebar.markdown("<br>", unsafe_allow_html=True)
            if st.sidebar.button("🚀 INICIAR PROCESAMIENTO", type="primary", use_container_width=True):
                payload_motor = cli_obj.to_dict()

                # Normalizar claves para que el motor siempre encuentre lo que necesita
                campos_clave = {
                    "Fecha": "fecha", "Hora": "hora",
                    "Latitud": "lat", "Longitud": "lon", "Nombres": "nombre"
                }
                for orig, dest in campos_clave.items():
                    if orig in payload_motor:
                        payload_motor[dest] = payload_motor[orig]
                    elif dest in payload_motor:
                        payload_motor[orig] = payload_motor[dest]

                faltantes = [k for k in ["Fecha", "Hora", "Latitud", "Longitud"]
                             if k not in payload_motor or pd.isna(payload_motor[k])]

                if faltantes:
                    st.sidebar.error(f"⚠️ No se puede procesar. Faltan datos en el Google Sheet: {', '.join(faltantes)}")
                else:
                    with st.spinner("Calculando efemérides y redactando informe integral..."):
                        try:
                            datos, plant = None, None

                            if id_t == "2":
                                st.session_state.tipo_reporte_actual = "TRANSITOS"
                                datos, plant = motor_web.procesar_transitos_con_ia(payload_motor, None, id_sel)
                            elif id_t == "3" or "Revolucion" in sel_p:
                                st.session_state.tipo_reporte_actual = "REVOLUCION"
                                datos, plant = motor_web.procesar_rs_con_ia(
                                    payload_motor, None, id_sel,
                                    lat_rs=lat_rs, lon_rs=lon_rs, lugar_rs=lug_final
                                )
                            else:
                                st.session_state.tipo_reporte_actual = "NATAL"
                                datos, plant = motor_web.procesar_natal_con_ia(payload_motor, None, id_sel)

                            if datos:
                                st.session_state.update({
                                    'datos_diccionario': datos,
                                    'plantilla_usar':    plant,
                                    'textos_generados':  True,
                                    'idx_prog_actual':   idx_p
                                })
                                st.rerun()
                            else:
                                st.sidebar.error(f"⚠️ El motor falló: {plant}")
                                st.sidebar.info("Verifica tu conexión a OpenAI y tus créditos API.")
                        except Exception as e:
                            st.sidebar.error(f"❌ Error crítico inesperado: {e}")

    # ==============================================================================
    # 7. PANEL DE EDICIÓN INTEGRAL
    # ==============================================================================
    if st.session_state.textos_generados:
        d    = st.session_state.datos_diccionario
        tipo = st.session_state.tipo_reporte_actual
        st.subheader(f"Editando: {d.get('titulo_informe')} - {d.get('nombre_cliente')}")
        st.info("Revisa y personaliza cada sección del borrador generado por la IA antes de finalizar.")

        # --- REVOLUCIÓN SOLAR ---
        if tipo == "REVOLUCION":
            with st.expander("1. Infografía Inicial (Cuadros de Síntesis)", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    d['perspectivas']['transformacion'] = st.text_area("El Gran Reto Anual",       d['perspectivas'].get('transformacion', ''), height=100)
                    d['perspectivas']['cambio']         = st.text_area("Área de Cambio Principal", d['perspectivas'].get('cambio', ''),         height=100)
                with col2:
                    d['perspectivas']['oportunidades']  = st.text_area("Mayores Oportunidades",    d['perspectivas'].get('oportunidades', ''),  height=100)
                    d['perspectivas']['relaciones']     = st.text_area("Tónica Vincular",           d['perspectivas'].get('relaciones', ''),     height=100)

            with st.expander("2. Introducción y Bases (Natal / Tránsitos / Progresiones)", expanded=False):
                d['intro_texto']             = st.text_area("Texto de Introducción Cálida",  d.get('intro_texto', ''),             height=100)
                d['carta_natal_resumen']     = st.text_area("Esencia Natal Resumida",        d.get('carta_natal_resumen', ''),     height=150)
                d['transitos_personales']    = st.text_area("Análisis de Tránsitos Lentos",  d.get('transitos_personales', ''),    height=150)
                d['progresiones_secundarias']= st.text_area("Interpretación de Progresiones",d.get('progresiones_secundarias',''), height=150)
                tips = st.text_area("Consejos de Acción (Uno por línea)", "\n".join(d.get('como_actuar_progresiones', [])))
                d['como_actuar_progresiones'] = tips.split("\n")

            with st.expander("3. Revolución Solar (General y Profesional)", expanded=True):
                d['revolucion_solar_general_1']       = st.text_area("Clima General RS",           d.get('revolucion_solar_general_1', ''),       height=250)
                revo_prop = st.text_area("Propuestas del Año (Uno por línea)", "\n".join(d.get('revo_propone', [])))
                d['revo_propone']                     = revo_prop.split("\n")
                d['situacion_laboral_economica']      = st.text_area("Panorama Profesional",       d.get('situacion_laboral_economica', ''),      height=180)
                obj_lab = st.text_area("Objetivos Laborales (Uno por línea)", "\n".join(d.get('logro_objetivos_profesionales', [])))
                d['logro_objetivos_profesionales']    = obj_lab.split("\n")

            with st.expander("4. Emocional, Trimestral y Cierre", expanded=True):
                d['situacion_emocional'] = st.text_area("Clima Afectivo", d.get('situacion_emocional', ''), height=180)
                st.markdown("**Cronograma Trimestral:**")
                if 'panorama_trimestral' in d:
                    for i, t in enumerate(d.get('panorama_trimestral', [])):
                        t['texto'] = st.text_area(f"📍 {t.get('titulo')}", t.get('texto', ''), key=f"rs_t_{i}", height=120)
                plan_acc = st.text_area("Plan Acción Final (Uno por línea)", "\n".join(d.get('plan_accion_objetivos', [])))
                d['plan_accion_objetivos'] = plan_acc.split("\n")

        # --- TRÁNSITOS ANUALES ---
        elif tipo == "TRANSITOS":
            with st.expander("1. Energía Natal Base", expanded=False):
                d['interpretacion_sol_signo']  = st.text_area("El Sol",         d.get('interpretacion_sol_signo', ''),  height=100)
                d['interpretacion_luna_signo'] = st.text_area("La Luna",        d.get('interpretacion_luna_signo', ''), height=100)
                d['interpretacion_asc_signo']  = st.text_area("El Ascendente",  d.get('interpretacion_asc_signo', ''),  height=100)

            with st.expander("2. Análisis del Clima Anual", expanded=True):
                d['frase_anual_corta']    = st.text_input("Lema Inspirador",               d.get('frase_anual_corta', ''))
                d['analisis_clima_anual'] = st.text_area("Interpretación Evolutiva General",d.get('analisis_clima_anual', ''), height=300)
                d['oportunidad_anual']    = st.text_area("La Gran Oportunidad",            d.get('oportunidad_anual', ''),    height=120)
                d['atencion_anual']       = st.text_area("Punto de Atención Crítico",      d.get('atencion_anual', ''),       height=120)

            with st.expander("3. Calendario Detallado de Eventos Mensuales", expanded=True):
                for m, evs in d.get('calendario_por_meses', {}).items():
                    st.markdown(f"### 🗓️ {m}")
                    for ev in evs:
                        label = f"{ev.get('fecha', '')} | {ev.get('transito', '')} a {ev.get('natal', '')}"
                        ev['texto_efecto'] = st.text_area(label, ev.get('texto_efecto', ''), key=f"tr_{m}_{ev.get('fecha','')}", height=100)

        # --- CARTA NATAL ---
        else:
            with st.expander("1. Tríada Sagrada de Identidad", expanded=True):
                d['interpretacion_sol_signo']  = st.text_area("☉ El Propósito Solar",      d.get('interpretacion_sol_signo', ''),  height=150)
                d['interpretacion_luna_signo'] = st.text_area("☽ El Refugio Lunar",        d.get('interpretacion_luna_signo', ''), height=150)
                d['interpretacion_asc_signo']  = st.text_area("AC El Camino del Ascendente",d.get('interpretacion_asc_signo', ''), height=150)

            with st.expander("2. Los Gigantes del Cielo", expanded=False):
                if 'gigantes_del_cielo' in d:
                    for i, g in enumerate(d.get('gigantes_del_cielo', [])):
                        g['texto'] = st.text_area(f"{g.get('nombre')} en {g.get('signo', '')}", g.get('texto', ''), key=f"g_{i}", height=120)

            with st.expander("3. Síntesis Evolutiva y FODA Personal", expanded=True):
                d['interpretacion_personalidad_global'] = st.text_area("Relato Final de Integración", d.get('interpretacion_personalidad_global',''), height=350)
                f1, f2 = st.columns(2)
                with f1:
                    forts = st.text_area("Fortalezas (Uno por línea)", "\n".join(d['foda'].get('fortalezas', [])))
                    d['foda']['fortalezas'] = forts.split("\n")
                with f2:
                    debs = st.text_area("Debilidades (Uno por línea)", "\n".join(d['foda'].get('debilidades', [])))
                    d['foda']['debilidades'] = debs.split("\n")

        # ==============================================================================
        # 8. PANEL DE ACCIONES FINALES
        # ==============================================================================
        st.divider()
        c_final1, c_final2 = st.columns(2)
        d['logo_base64'] = get_base_64_of_bin_file('apple-icon.png')

        try:
            env  = Environment(loader=FileSystemLoader('.'))
            tmpl = env.get_template(st.session_state.plantilla_usar)

            with c_final1:
                if st.button("👁️ VER VISTA PREVIA"):
                    try:
                        html_render = tmpl.render(d)
                        components.html(html_render, height=900, scrolling=True)
                    except Exception as e:
                        st.error(f"Error al renderizar el diseño visual: {e}")

            with c_final2:
                html_final  = tmpl.render(d)
                nombre_doc  = f"Informe_{d.get('nombre_cliente', 'Consultante')}.html"
                st.download_button("💾 DESCARGAR INFORME HTML FINAL",
                                   data=html_final, file_name=nombre_doc,
                                   mime="text/html", type="primary")
                if st.button("❌ FINALIZAR Y LIMPIAR TALLER"):
                    st.session_state.textos_generados = False
                    st.rerun()

        except Exception as e:
            st.error(f"Error cargando la plantilla HTML: {e}")
