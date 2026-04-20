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
# El layout 'wide' es vital para que el panel de edición sea cómodo en iPad/iPhone.
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
    
    /* Tipografías y Títulos Elegantes con Playfair Display */
    h1, h2, h3, h4 {
        font-family: 'Playfair Display', serif !important;
        color: #4A4A4A !important;
    }
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    /* Paneles de Edición (Expanders) con sombra suave para profundidad visual */
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
    
    /* Selectores de Clientes para evitar cortes visuales en móviles */
    .stSelectbox div[data-baseweb="select"] {
        white-space: normal !important;
        border-radius: 8px;
    }
    
    /* Estilo de Mensajes de Alerta y Error */
    .stAlert {
        border-radius: 12px;
    }

    /* Métrica de Diagnóstico en Sidebar (Cuadros de Estado) */
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

# LOGOTIPO Y ENCABEZADO DE MARCA EN EL PANEL LATERAL (DISEÑO SVG PERSONALIZADO)
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
# 2. GESTIÓN DEL ESTADO DE SESIÓN (PERSISTENCIA DE DATOS EN LA WEB)
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
    """
    Descarga datos de Sheets y unifica nombres de columnas.
    Esta función mapea todas las posibles variaciones de nombres de columnas 
    para evitar el error de 'Datos Incompletos' mapeando sinónimos comunes.
    """
    try:
        url_secreta = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id = url_secreta.split("/d/")[1].split("/")[0] if "/d/" in url_secreta else url_secreta
        
        # Generar URLs de descarga directa CSV para velocidad y compatibilidad
        u_cli = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Consultantes"
        u_prog = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Informes_Programados"
        
        df_c = pd.read_csv(u_cli).dropna(how="all")
        df_p = pd.read_csv(u_prog).dropna(how="all")

        # Diccionario de Mapeo Inteligente (Sinónimos de encabezados de Excel que Patricia podría usar)
        mapa_columnas = {
            'id_consultante': ['id', 'Id', 'ID', 'IDENTIFICADOR', 'id_cli', 'id_consultante', 'CODIGO', 'ID_CONSULTANTE'],
            'Fecha': ['fecha', 'FECHA', 'BirthDate', 'Nacimiento', 'Fecha_Nac', 'FECHA NACIMIENTO', 'FECHA_NACIMIENTO', 'DATE'],
            'Hora': ['hora', 'HORA', 'BirthTime', 'Hora_Nac', 'HORA NACIMIENTO', 'HORA_NACIMIENTO', 'TIME', 'TIEMPO'],
            'Latitud': ['lat', 'latitud', 'LATITUD', 'Lat', 'LAT', 'COOR_LAT', 'LAT_NAC', 'latitude', 'LATITUD NACIMIENTO'],
            'Longitud': ['lon', 'longitud', 'LONGITUD', 'Lon', 'Lng', 'lng', 'LON', 'COOR_LON', 'LON_NAC', 'longitude', 'LONGITUD NACIMIENTO'],
            'Nombres': ['Nombre', 'NOMBRE', 'Nombres', 'NAME', 'Consultante', 'CLIENTE', 'nombre']
        }

        # Aplicar Mapeo a ambos DataFrames para asegurar que el motor reciba las llaves correctas
        for df in [df_c, df_p]:
            if not df.empty:
                df.columns = df.columns.str.strip()
                for destino, sinonimos in mapa_columnas.items():
                    for s in sinonimos:
                        if s in df.columns and destino not in df.columns:
                            df.rename(columns={s: destino}, inplace=True)
                
                # Limpieza de IDs para evitar fallos de búsqueda por decimales accidentales en Excel
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
st.sidebar.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)

# VISOR DE AUDITORÍA TÉCNICA (Visualiza los grados y minutos exactos para tu control de calidad)
if st.session_state.textos_generados:
    st.sidebar.markdown("### 🔍 Datos Técnicos Exactos")
    st.sidebar.caption("Cálculos matemáticos usados para la interpretación:")
    st.sidebar.code(st.session_state.datos_diccionario.get('auditoria_tecnica', 'Sin datos disponibles'), language='text')
    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

# ==============================================================================
# 5. MODO: PROGRAMAR CLIENTE (GESTIÓN DE AGENDA DE TRABAJO)
# ==============================================================================
if modo_app == "📅 Programar Cliente":
    st.markdown("## 📅 Agenda de Clientes")
    st.markdown("<p style='color: #B48E92; font-weight: 500;'>Asigna un tipo de reporte a un consultante para que aparezca en el Taller de trabajo.</p>", unsafe_allow_html=True)
    if not df_cli.empty:
        # Usamos nombres normalizados por el mapeo anterior
        n_col = 'Nombres' if 'Nombres' in df_cli.columns else df_cli.columns[0]
        opciones_cli = [f"{row[n_col]} (ID: {row['id_consultante']})" for _, row in df_cli.iterrows() if 'id_consultante' in df_cli.columns]
        st.selectbox("1. Selecciona el Cliente de la base de datos:", opciones_cli)
        st.selectbox("2. Selecciona el Tipo de Informe a realizar:", ["Carta Natal", "Tránsitos Anuales", "Revolución Solar"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Registrar en Agenda de Trabajo", type="primary"):
            st.info("Nota: En esta versión web, agrega la fila manualmente en tu Google Sheet y recarga la página para verla en el Taller.")
    else:
        st.warning("No se cargaron consultantes. Revisa tu archivo de Google Sheets.")

# ==============================================================================
# 6. MODO: TALLER DE INFORMES (PROCESAMIENTO Y EDICIÓN PROFUNDA)
# ==============================================================================
elif modo_app == "⚙️ Taller de Informes":
    if not st.session_state.textos_generados:
        st.markdown("## ⚙️ Taller de Informes")
        st.markdown("<p style='color: #B48E92; font-weight: 500;'>Genera interpretaciones personalizadas basadas en efemérides exactas y tu propio estilo.</p>", unsafe_allow_html=True)

    # Filtramos la cola de trabajo: solo informes en estado PENDIENTE
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
            sel_p = st.sidebar.selectbox("Selecciona el informe a procesar:", opciones_menu, label_visibility="collapsed")
            idx_p = int(sel_p.split("Fila: ")[1])
            row_p = pendientes.loc[idx_p]
            id_sel = str(row_p['id_consultante'])
            cli_obj = df_cli[df_cli['id_consultante'] == id_sel].iloc[0]
            id_t = str(row_p.get('Id_Informe', '1')).replace('.0', '').strip()

            # --- PANEL DE DIAGNÓSTICO DE DATOS (ANTELACIÓN AL ERROR) ---
            # Esto ayuda a Patricia a saber si el Excel tiene huecos antes de apretar el botón de procesar.
            st.sidebar.markdown("<p style='font-size:0.7rem; font-weight:700; margin-top:10px;'>📊 DIAGNÓSTICO DE DATOS</p>", unsafe_allow_html=True)
            check_fecha = "✅" if "Fecha" in cli_obj and not pd.isna(cli_obj["Fecha"]) else "❌"
            check_hora = "✅" if "Hora" in cli_obj and not pd.isna(cli_obj["Hora"]) else "❌"
            check_lat = "✅" if "Latitud" in cli_obj and not pd.isna(cli_obj["Latitud"]) else "❌"
            check_lon = "✅" if "Longitud" in cli_obj and not pd.isna(cli_obj["Longitud"]) else "❌"
            
            diag_html = f"""
            <div class='diag-box'>
                <div class='diag-item'><span>Fecha Nac:</span> <span>{check_fecha}</span></div>
                <div class='diag-item'><span>Hora Nac:</span> <span>{check_hora}</span></div>
                <div class='diag-item'><span>Latitud:</span> <span>{check_lat}</span></div>
                <div class='diag-item'><span>Longitud:</span> <span>{check_lon}</span></div>
            </div>
            """
            st.sidebar.markdown(diag_html, unsafe_allow_html=True)

            # --- BUSCADOR DE COORDENADAS PARA REVOLUCIÓN SOLAR (PARTE CRÍTICA) ---
            lat_rs, lon_rs, lug_final = None, None, ""
            if id_t == "3" or "Revolucion" in sel_p: 
                st.sidebar.markdown("<hr style='margin-top: 1rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)
                st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700; letter-spacing:1px; margin-bottom:0;'>📍 RELOCALIZACIÓN RS</p>", unsafe_allow_html=True)
                st.sidebar.caption("Busca la ciudad donde el consultante pasará su retorno solar.")
                
                lug_rs_input = st.sidebar.text_input("Ciudad de la Revolución:", placeholder="Ej: Madrid, España", key="ciudad_rs_search")
                
                if st.sidebar.button("🔍 Buscar en Mapa Global", use_container_width=True):
                    if lug_rs_input:
                        with st.spinner("Conectando con el servidor de mapas..."):
                            try:
                                geolocator = Nominatim(user_agent="astroimpacto_premium_v520")
                                loc = geolocator.geocode(lug_rs_input)
                                if loc:
                                    st.session_state.lat_rs_auto = str(loc.latitude)
                                    st.session_state.lon_rs_auto = str(loc.longitude)
                                    st.session_state.lugar_rs_confirmado = loc.address
                                    st.sidebar.success(f"Listo: {loc.address}")
                                else:
                                    st.sidebar.error("Lugar no encontrado. Revisa la ortografía.")
                            except Exception:
                                st.sidebar.error("Error temporal de conexión con el mapa.")
                
                lat_rs = st.sidebar.text_input("Latitud de la RS:", value=st.session_state.lat_rs_auto)
                lon_rs = st.sidebar.text_input("Longitud de la RS:", value=st.session_state.lon_rs_auto)
                lug_final = st.session_state.lugar_rs_confirmado if st.session_state.lugar_rs_confirmado else lug_rs_input
            # --------------------------------------------------------------------------------

            st.sidebar.markdown("<br>", unsafe_allow_html=True)
            if st.sidebar.button("🚀 INICIAR PROCESAMIENTO", type="primary", use_container_width=True):
                # BLINDAJE DE DATOS: Creamos un paquete explícito con todas las llaves posibles (Mayus/Minus).
                # Esto asegura que motor_web.py encuentre siempre lo que necesita sin importar el Excel.
                payload_motor = cli_obj.to_dict()
                payload_motor.update({
                    "fecha": payload_motor.get("Fecha"),
                    "hora": payload_motor.get("Hora"),
                    "lat": payload_motor.get("Latitud"),
                    "lon": payload_motor.get("Longitud"),
                    "nombre": payload_motor.get("Nombres")
                })

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
                            st.sidebar.info("Consejo: Verifica tu conexión a OpenAI y que las columnas del Excel no tengan ceros.")
                    except Exception as e:
                        st.sidebar.error(f"❌ Error crítico en el procesamiento: {e}")

    # ==============================================================================
    # 7. PANEL DE EDICIÓN INTEGRAL (DETALLE MÁXIMO - INTEGRIDAD TOTAL)
    # ==============================================================================
    if st.session_state.textos_generados:
        d = st.session_state.datos_diccionario
        tipo = st.session_state.tipo_reporte_actual
        st.subheader(f"Editando: {d.get('titulo_informe')} - {d.get('nombre_cliente')}")
        st.info("Revisa y personaliza cada sección del borrador generado por la IA antes de finalizar.")

        # --- SECCIONES REVOLUCIÓN SOLAR (DETALLE MÁXIMO) ---
        if tipo == "REVOLUCION":
            with st.expander("1. Infografía Inicial (Cuadros de Perspectiva)", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    d['perspectivas']['transformacion'] = st.text_area("El Gran Reto de Transformación Anual", d['perspectivas'].get('transformacion', ''), height=100)
                    d['perspectivas']['cambio'] = st.text_area("Área donde se sentirá el Cambio Principal", d['perspectivas'].get('cambio', ''), height=100)
                with col2:
                    d['perspectivas']['oportunidades'] = st.text_area("Mayores Oportunidades de Crecimiento", d['perspectivas'].get('oportunidades', ''), height=100)
                    d['perspectivas']['relaciones'] = st.text_area("Tónica del Clima Vincular y Social", d['perspectivas'].get('relaciones', ''), height=100)
            
            with st.expander("2. Introducción y Análisis de Base (Natal / Tránsitos / Progresiones)", expanded=False):
                d['intro_texto'] = st.text_area("Texto de Introducción Cálida al Informe", d.get('intro_texto',''), height=100)
                d['carta_natal_resumen'] = st.text_area("Resumen Psicológico de la Esencia Natal", d.get('carta_natal_resumen',''), height=150)
                d['transitos_personales'] = st.text_area("Análisis de los Tránsitos Planetarios Lentos", d.get('transitos_personales',''), height=150)
                d['progresiones_secundarias'] = st.text_area("Interpretación de Progresiones y Estado Interior", d.get('progresiones_secundarias',''), height=150)
                tips_p = st.text_area("Consejos de Acción ante Progresiones (Uno por línea)", "\n".join(d.get('como_actuar_progresiones', [])))
                d['como_actuar_progresiones'] = tips_p.split("\n")

            with st.expander("3. Revolución Solar (General y Profesional)", expanded=True):
                d['revolucion_solar_general_1'] = st.text_area("Interpretación del Clima General de la Revolución Solar", d.get('revolucion_solar_general_1',''), height=250)
                propuestas_revo = st.text_area("Propuestas Evolutivas del Año (Uno por línea)", "\n".join(d.get('revo_propone', [])))
                d['revo_propone'] = propuestas_revo.split("\n")
                d['situacion_laboral_economica'] = st.text_area("Panorama Vocacional, Económico y Profesional", d.get('situacion_laboral_economica',''), height=180)
                objs_lab = st.text_area("Objetivos Profesionales Específicos (Uno por línea)", "\n".join(d.get('logro_objetivos_profesionales', [])))
                d['logro_objetivos_profesionales'] = objs_lab.split("\n")

            with st.expander("4. Clima Emocional y Panorama Trimestral", expanded=True):
                d['situacion_emocional'] = st.text_area("Análisis Profundo de la Vida Afectiva y Familiar", d.get('situacion_emocional',''), height=180)
                st.markdown("**Cronograma Anual de Proyección Trimestral:**")
                if 'panorama_trimestral' in d:
                    for i, t in enumerate(d.get('panorama_trimestral', [])):
                        t['texto'] = st.text_area(f"📍 {t.get('titulo', 'Periodo')}", t.get('texto', ''), key=f"rs_t_{i}", height=120)
                plan_acc = st.text_area("Plan de Acción y Objetivos Finales (Uno por línea)", "\n".join(d.get('plan_accion_objetivos', [])))
                d['plan_accion_objetivos'] = plan_acc.split("\n")

        # --- SECCIONES TRÁNSITOS ANUALES (DETALLE MÁXIMO) ---
        elif tipo == "TRANSITOS":
            with st.expander("1. Energía Base del Consultante", expanded=False):
                d['interpretacion_sol_signo'] = st.text_area("Interpretación Natal del Sol", d.get('interpretacion_sol_signo',''), height=100)
                d['interpretacion_luna_signo'] = st.text_area("Interpretación Natal de la Luna", d.get('interpretacion_luna_signo',''), height=100)
                d['interpretacion_asc_signo'] = st.text_area("Interpretación Natal del Ascendente", d.get('interpretacion_asc_signo',''), height=100)
            
            with st.expander("2. Análisis del Clima Astrológico Anual", expanded=True):
                d['frase_anual_corta'] = st.text_input("Lema Inspirador del Año (Título Principal)", d.get('frase_anual_corta',''))
                d['analisis_clima_anual'] = st.text_area("Interpretación General Evolutiva para los 12 meses", d.get('analisis_clima_anual',''), height=300)
                d['oportunidad_anual'] = st.text_area("La Gran Oportunidad de Crecimiento Anual", d.get('oportunidad_anual',''), height=120)
                d['atencion_anual'] = st.text_area("Punto de Atención Crítico y Cuidado Psicológico", d.get('atencion_anual',''), height=120)

            with st.expander("3. Calendario Detallado de Eventos Mensuales", expanded=True):
                st.markdown("<p style='color: #666;'>Edita los efectos de los tránsitos específicos mes a mes:</p>", unsafe_allow_html=True)
                for mes, eventos in d.get('calendario_por_meses', {}).items():
                    st.markdown(f"### 🗓️ {mes}")
                    for ev in eventos:
                        etiqueta = f"{ev.get('fecha', '')} | {ev.get('transito', '')} {ev.get('aspecto', '')} a {ev.get('natal', '')}"
                        ev['texto_efecto'] = st.text_area(etiqueta, ev.get('texto_efecto', ''), key=f"tr_{mes}_{ev.get('fecha','')}", height=100)

        # --- SECCIONES CARTA NATAL (DETALLE MÁXIMO) ---
        else:
            with st.expander("1. Tríada Sagrada de Identidad (Sol, Luna y AC)", expanded=True):
                d['interpretacion_sol_signo'] = st.text_area("☉ El Propósito Solar y la Esencia Vital", d.get('interpretacion_sol_signo',''), height=150)
                d['interpretacion_luna_signo'] = st.text_area("☽ El Refugio Emocional y el Mecanismo de Seguridad", d.get('interpretacion_luna_signo',''), height=150)
                d['interpretacion_asc_signo'] = st.text_area("AC El Camino de Integración del Ascendente", d.get('interpretacion_asc_signo',''), height=150)
            
            with st.expander("2. Análisis de los Gigantes del Cielo", expanded=False):
                if 'gigantes_del_cielo' in d:
                    for i, g in enumerate(d.get('gigantes_del_cielo', [])):
                        g['texto'] = st.text_area(f"{g.get('nombre', 'Cuerpo')} en {g.get('signo', '')}", g.get('texto', ''), key=f"natal_g_{i}", height=100)

            with st.expander("3. Síntesis Evolutiva Global y FODA Personal", expanded=True):
                d['interpretacion_personalidad_global'] = st.text_area("Relato Final de Integración de Personalidad", d.get('interpretacion_personalidad_global',''), height=350)
                st.markdown("**Matriz de Potencial (FODA):**")
                fcol1, fcol2 = st.columns(2)
                with fcol1:
                    f_text = st.text_area("Fortalezas (Una por línea)", "\n".join(d['foda'].get('fortalezas', [])))
                    d['foda']['fortalezas'] = f_text.split("\n")
                with fcol2:
                    d_text = st.text_area("Debilidades (Una por línea)", "\n".join(d['foda'].get('debilidades', [])))
                    d['foda']['debilidades'] = d_text.split("\n")

        # ==============================================================================
        # 8. PANEL DE ACCIONES FINALES (DESCARGA Y VISTA PREVIA)
        # ==============================================================================
        st.divider()
        c_fin1, c_fin2 = st.columns(2)
        
        # Preparación de imágenes y logo antes de la generación final del diseño
        d['logo_base64'] = get_base_64_of_bin_file('apple-icon.png')
        env_jinja = Environment(loader=FileSystemLoader('.'))
        
        try:
            plantilla_final = env_jinja.get_template(st.session_state.plantilla_usar)
            
            with c_fin1:
                if st.button("👁️ VER VISTA PREVIA DEL DISEÑO"):
                    try: 
                        html_render = plantilla_final.render(d)
                        components.html(html_render, height=900, scrolling=True)
                    except Exception: 
                        st.error("Error al renderizar el diseño visual.")

            with c_fin2:
                html_final = plantilla_final.render(d)
                # Formateo dinámico del nombre del archivo final para Patricia
                sufijo = "Transitos" if tipo == "TRANSITOS" else "Revolucion" if tipo == "REVOLUCION" else "Natal"
                nombre_doc = f"Informe_Astroimpacto_{d.get('nombre_cliente', 'Cliente')}_{sufijo}.html"
                
                st.download_button("💾 DESCARGAR INFORME HTML FINAL", data=html_final, file_name=nombre_doc, mime="text/html", type="primary")
                
                if st.button("❌ FINALIZAR Y LIMPIAR TALLER"):
                    st.session_state.textos_generados = False
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error cargando la plantilla HTML: {e}")
