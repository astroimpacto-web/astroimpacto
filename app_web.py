import streamlit as st
import streamlit.components.v1 as components 
import pandas as pd
import os
import base64
import re
from jinja2 import Environment, FileSystemLoader
import motor_web
from geopy.geocoders import ArcGIS

# ==============================================================================
# 1. FUNCIONES DE APOYO Y SEGURIDAD TÉCNICA (IDENTIDAD VISUAL)
# ==============================================================================

@st.cache_data
def get_base_64_of_bin_file(bin_file):
    """
    Convierte una imagen local a formato Base64 para inyectarla en el HTML.
    Esto asegura que los informes descargados conserven el logo de Astroimpacto
    sin depender de que el cliente tenga conexión a las carpetas del servidor.
    """
    try:
        if os.path.exists(bin_file):
            with open(bin_file, 'rb') as f:
                data = f.read()
            return f"data:image/png;base64,{base64.b64encode(data).decode()}"
        else:
            return ""
    except Exception as e:
        # Fallo silencioso para no interrumpir el flujo de la aplicación
        return ""

# ==============================================================================
# 2. CONFIGURACIÓN INICIAL DE LA PÁGINA Y ESTÉTICA (STREAMLIT)
# ==============================================================================
# Definimos el modo ancho para facilitar la edición de textos largos en el Taller.
st.set_page_config(
    page_title="Astroimpacto - Gestión Astrológica Profesional",
    page_icon="apple-icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# IDENTIDAD VISUAL PARA DISPOSITIVOS MÓVILES (IPHONE / IPAD)
st.markdown('<link rel="apple-touch-icon" href="apple-icon.png">', unsafe_allow_html=True)
st.markdown('<link rel="manifest" href="./manifest.json">', unsafe_allow_html=True)

# BLOQUE DE SEGURIDAD PARA EL ÍCONO WEB (FAVICON)
try:
    icono_base64 = get_base_64_of_bin_file('apple-icon.png')
    if icono_base64 != "":
        st.markdown(f'<link rel="icon" href="{icono_base64}">', unsafe_allow_html=True)
except Exception:
    pass

# ESTILOS CSS PERSONALIZADOS (DISEÑO PREMIUM ASTROIMPACTO)
# Se definen todas las reglas de forma explícita para evitar recortes visuales.
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    /* Personalización de la barra lateral (Sidebar) */
    [data-testid="stSidebar"] {
        background-color: #fdfcf9;
        border-right: 1px solid #e8e3d8;
    }
    
    /* Botones de Acción (Rosa Humo) */
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
    
    /* Tipografías de Títulos */
    h1, h2, h3, h4 {
        font-family: 'Playfair Display', serif !important;
        color: #4A4A4A !important;
    }
    
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    /* Expanders de Edición (Sombra suave) */
    div[data-testid="stExpander"] {
        background-color: white;
        border: 1px solid #f0ebe1;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    
    /* Cajas de Texto (Text Area) */
    .stTextArea textarea {
        font-size: 0.95rem;
        line-height: 1.6;
        color: #333;
        background-color: #fafafa;
        border-radius: 8px;
    }
    
    /* Cuadro de Diagnóstico de Datos */
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
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)

# LOGOTIPO SIDEBAR (DISEÑO SVG)
st.sidebar.markdown("""
<div style="text-align: center; margin-top: -2rem; padding-bottom: 1.5rem; border-bottom: 1px solid #e8e3d8; margin-bottom: 1.5rem;">
    <div style="width: 55px; height: 55px; margin: 0 auto 12px auto; color: #B48E92;">
        <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="100" cy="90" r="50" stroke="currentColor" stroke-width="3"/>
            <path d="M100 20 L110 90 L100 160 L90 90 Z" fill="currentColor"/>
            <path d="M170 90 L100 100 L30 90 L100 80 Z" fill="currentColor"/>
            <line x1="100" y1="140" x2="100" y2="185" stroke="currentColor" stroke-width="4"/>
            <line x1="75" y1="165" x2="125" y2="165" stroke="currentColor" stroke-width="4"/>
        </svg>
    </div>
    <h2 style="font-family: 'Playfair Display', serif; font-size: 1.8rem; color: #4A4A4A; margin: 0; font-weight: 700;">Astroimpacto</h2>
    <p style="font-family: 'Montserrat', sans-serif; font-size: 0.65rem; letter-spacing: 2.5px; color: #B48E92; text-transform: uppercase;">Plataforma Web Profesional</p>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. GESTIÓN DEL ESTADO DE SESIÓN (PERSISTENCIA DE DATOS)
# ==============================================================================
# Se definen explícitamente todas las variables necesarias para que no se pierdan 
# al recargar la página.
if 'textos_generados' not in st.session_state:
    st.session_state.textos_generados = False

if 'datos_diccionario' not in st.session_state:
    st.session_state.datos_diccionario = {}

if 'plantilla_usar' not in st.session_state:
    st.session_state.plantilla_usar = 'informe_astroimpacto.html'

if 'tipo_reporte_actual' not in st.session_state:
    st.session_state.tipo_reporte_actual = "NATAL"

if 'lat_rs_auto' not in st.session_state:
    st.session_state.lat_rs_auto = ""

if 'lon_rs_auto' not in st.session_state:
    st.session_state.lon_rs_auto = ""

if 'lugar_rs_confirmado' not in st.session_state:
    st.session_state.lugar_rs_confirmado = ""

if 'idx_prog_actual' not in st.session_state:
    st.session_state.idx_prog_actual = None

# ==============================================================================
# 4. CARGA Y NORMALIZACIÓN ROBUSTA DE BASES DE DATOS (GOOGLE SHEETS)
# ==============================================================================
@st.cache_data(ttl=5)
def normalizar_columnas(df):
    """
    Mapea las columnas del Drive a nombres internos, 
    asegurando que Hora_UT nunca sea confundida con la hora local.
    """
    # 1. Limpieza inicial: quitamos espacios y carácteres especiales como ":"
    # Esto transforma "Hora:UT" en "Hora_UT" automáticamente.
    df.columns = [c.replace(':', '_').replace(' ', '_').strip() for c in df.columns]
    
    mapa_columnas = {
        'id_consultante': ['id', 'Id', 'ID', 'IDENTIFICADOR', 'id_cli', 'CODIGO'],
        'Fecha_UT': ['Fecha_UT', 'FECHA_UT', 'Fecha_Ut', 'Fecha_Universal'],
        'Hora_UT': ['Hora_UT', 'HORA_UT', 'Hora_Ut', 'Hora_Universal'],
        'Fecha': ['fecha', 'FECHA', 'BirthDate', 'Nacimiento', 'Fecha_Nac'],
        'Hora': ['hora', 'HORA', 'BirthTime', 'Hora_Nac', 'TIME'],
        'Latitud': ['lat', 'latitud', 'LATITUD', 'Lat', 'COOR_LAT'],
        'Longitud': ['lon', 'longitud', 'LONGITUD', 'Lon', 'COOR_LON'],
        'Nombres': ['Nombre', 'NOMBRE', 'Nombres', 'NAME', 'Consultante']
    }
    
    for interno, alias_list in mapa_columnas.items():
        for col in df.columns:
            if col in alias_list and interno not in df.columns:
                df.rename(columns={col: interno}, inplace=True)
    return df
    
@st.cache_data(ttl=5)
def cargar_bases_web():
    try:
        url_secreta = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id = url_secreta.split("/d/")[1].split("/")[0]
        u_cli = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Consultantes"
        df_c = pd.read_csv(u_cli).dropna(how="all")
        
        # Aplicamos el mapeo corregido para proteger la Hora_UT
        df_c = normalizar_columnas(df_c)
        
        if 'id_consultante' in df_c.columns:
            df_c['id_consultante'] = df_c['id_consultante'].astype(str).str.replace('.0', '', regex=False).strip()
        return df_c
    except Exception as e:
        st.sidebar.error(f"Error cargando datos: {e}")
        return pd.DataFrame()
# ==============================================================================
# 5. NAVEGACIÓN Y PANEL DE AUDITORÍA TÉCNICA
# ==============================================================================
st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700; letter-spacing:1px;'>NAVEGACIÓN</p>", unsafe_allow_html=True)

# Radio button explícito
modo_app = st.sidebar.radio(
    label="Menú Principal",
    options=["⚙️ Taller de Informes", "📅 Programar Cliente"],
    label_visibility="collapsed"
)

st.sidebar.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)

# Visor técnico expandido
if st.session_state.textos_generados == True:
    st.sidebar.markdown("### 🔍 Datos Técnicos Exactos")
    st.sidebar.caption("Cálculos matemáticos detallados usados para la interpretación:")
    
    auditoria_texto = st.session_state.datos_diccionario.get('auditoria_tecnica', 'Sin datos disponibles')
    st.sidebar.code(auditoria_texto, language='text')
    
    st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

# ==============================================================================
# 6. MODO: PROGRAMAR CLIENTE (AGENDA)
# ==============================================================================
if modo_app == "📅 Programar Cliente":
    st.markdown("## 📅 Agenda de Clientes")
    st.markdown("<p style='color: #B48E92; font-weight: 500; margin-bottom: 2rem;'>Asigna un tipo de reporte a un consultante para que aparezca en el Taller de trabajo.</p>", unsafe_allow_html=True)
    
    if not df_cli.empty:
        if 'Nombres' in df_cli.columns:
            n_col = 'Nombres'
        else:
            n_col = df_cli.columns[0]
            
        opciones_cli = []
        for index, row in df_cli.iterrows():
            if 'id_consultante' in df_cli.columns:
                nombre_formateado = f"{row[n_col]} (ID: {row['id_consultante']})"
                opciones_cli.append(nombre_formateado)
                
        st.selectbox("1. Selecciona el Cliente de la base de datos:", opciones_cli)
        st.selectbox("2. Selecciona el Tipo de Informe a realizar:", ["Carta Natal", "Tránsitos Anuales", "Revolución Solar"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Registrar en Agenda de Trabajo", type="primary"):
            st.info("Nota: En esta versión web, agrega la fila manualmente en tu Google Sheet y recarga la página.")
    else:
        st.warning("No se cargaron consultantes. Revisa tu archivo de Google Sheets.")

# ==============================================================================
# 7. MODO: TALLER DE INFORMES (PROCESAMIENTO Y EDICIÓN PROFUNDA)
# ==============================================================================
elif modo_app == "⚙️ Taller de Informes":
    
    if st.session_state.textos_generados == False:
        st.markdown("## ⚙️ Taller de Informes")
        st.markdown("<p style='color: #B48E92; font-weight: 500; margin-bottom: 2rem;'>Genera interpretaciones personalizadas basadas en efemérides exactas y tu propio estilo.</p>", unsafe_allow_html=True)

    # Filtrado explícito de informes PENDIENTES
    pendientes = pd.DataFrame()
    if not df_prog.empty:
        if 'Estado' in df_prog.columns:
            df_prog['Estado_Upper'] = df_prog['Estado'].astype(str).str.upper()
            pendientes = df_prog[df_prog['Estado_Upper'] == 'PENDIENTE']

    if pendientes.empty:
        if st.session_state.textos_generados == False:
            st.sidebar.success("✅ ¡Agenda limpia! No hay reportes pendientes.")
    else:
        st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700;'>PENDIENTES</p>", unsafe_allow_html=True)
        
        opciones_menu = []
        for idx, row in pendientes.iterrows():
            if 'id_consultante' in row:
                id_c = str(row['id_consultante']).strip()
                cli_data = df_cli[df_cli['id_consultante'] == id_c]
                
                if not cli_data.empty:
                    if 'Nombres' in cli_data.columns:
                        n_col_cli = 'Nombres'
                    else:
                        n_col_cli = cli_data.columns[0]
                    nombre_cli = str(cli_data.iloc[0][n_col_cli])
                else:
                    nombre_cli = f"ID: {id_c}"
                
                # --- DETECCIÓN RESILIENTE DEL TIPO DE INFORME (EXTENDIDA) ---
                # Aquí evitamos el resumen automático que rompía el código anterior.
                id_tipo_raw = str(row.get('Id_Informe', '1'))
                id_tipo_lower = id_tipo_raw.lower().strip()
                id_tipo_clean = id_tipo_lower.replace('.0', '')
                
                tipo_txt = "Reporte Desconocido"
                
                if id_tipo_clean == "1" or "natal" in id_tipo_lower:
                    tipo_txt = "Natal"
                elif id_tipo_clean == "2" or "transito" in id_tipo_lower:
                    tipo_txt = "Transitos"
                elif id_tipo_clean == "3" or id_tipo_clean == "4" or "revolucion" in id_tipo_lower or "solar" in id_tipo_lower or "rs" in id_tipo_lower:
                    tipo_txt = "Revolucion"
                else:
                    tipo_txt = f"Informe ({id_tipo_raw})"
                
                opciones_menu.append(f"{nombre_cli} ({tipo_txt}) | Fila: {idx}")

        if len(opciones_menu) > 0:
            sel_p = st.sidebar.selectbox(
                label="Selecciona el informe a procesar:", 
                options=opciones_menu, 
                label_visibility="collapsed"
            )
            
            # Extracción explícita de variables
            partes_seleccion = sel_p.split("Fila: ")
            idx_p = int(partes_seleccion[1].replace(")", "").strip())
            
            row_p = pendientes.loc[idx_p]
            id_sel = str(row_p['id_consultante'])
            cli_obj = df_cli[df_cli['id_consultante'] == id_sel].iloc[0]
            
            # Bandera clara para mostrar el buscador de revolución solar
            es_revolucion_final = False
            if "Revolucion" in sel_p:
                es_revolucion_final = True
            elif "Solar" in sel_p:
                es_revolucion_final = True

# --- PANEL DE DIAGNÓSTICO DE DATOS (VALORES REALES) ---

# --- PANEL DE DIAGNÓSTICO DE DATOS (VALORES REALES) ---
            st.sidebar.markdown("<p style='font-size:0.75rem; font-weight:700; margin-top:10px;'>📊 VISTA PREVIA DE DATOS CRUDA</p>", unsafe_allow_html=True)
            
            # Captura con prioridad absoluta a lo que diga UT gracias al mapeo
            f_final = cli_obj.get('Fecha_UT', cli_obj.get('Fecha', '---'))
            h_final = cli_obj.get('Hora_UT', cli_obj.get('Hora', '---'))
            lat_raw = cli_obj.get('Latitud', '0.0')
            lon_raw = cli_obj.get('Longitud', '0.0')
            
            # Procesamiento técnico para ver qué número usará el motor SwissEph
            lat_dec = motor_web.limpiar_coordenada_dms(lat_raw)
            lon_dec = motor_web.limpiar_coordenada_dms(lon_raw)
            h_dec = motor_web.limpiar_hora_precisa(h_final)
            
            diag_html = f"""
            <div class='diag-box'>
                <div class='diag-item'><span>📅 Fecha:</span> <span class='diag-val'>{f_final}</span></div>
                <div class='diag-item'><span>⏰ Hora UT:</span> <span class='diag-val'>{h_final} ({h_dec:.2f}h)</span></div>
                <div class='diag-item'><span>📍 Latitud:</span> <span class='diag-val'>{lat_dec:.4f}</span></div>
                <div class='diag-item'><span>📍 Longitud:</span> <span class='diag-val'>{lon_dec:.4f}</span></div>
            </div>
            """
            st.sidebar.markdown(diag_html, unsafe_allow_html=True)
            
            # Alertas de seguridad
            if h_dec == 0.0 and str(h_final) != "0":
                st.sidebar.warning("⚠️ La hora no se reconoce. Revisa el formato en el Drive.")
            elif h_dec < 10.0 and "10:" in str(h_final):
                st.sidebar.error("⚠️ Error de lectura crítico: Se detectó hora local en lugar de UT.")
            # --- BUSCADOR DE COORDENADAS PARA REVOLUCIÓN SOLAR ---
            lat_rs = None
            lon_rs = None
            lug_final = ""
            
            if es_revolucion_final == True: 
                st.sidebar.markdown("<hr style='margin-top: 1rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)
                st.sidebar.markdown("<p style='font-size:0.75rem; color:#B48E92; font-weight:700; letter-spacing:1px; margin-bottom:0;'>📍 RELOCALIZACIÓN RS</p>", unsafe_allow_html=True)
                st.sidebar.caption("Busca la ciudad donde el consultante pasará su retorno solar.")
                
                lug_rs_input = st.sidebar.text_input("Ciudad de la Revolución:", placeholder="Ej: Madrid, España", key="ciudad_rs_search")
                
                if st.sidebar.button("🔍 Buscar en Mapa Global", use_container_width=True):
                    if lug_rs_input != "":
                        with st.spinner("Conectando con el servidor de mapas..."):
                            try:
                                from geopy.geocoders import ArcGIS
                                geolocator = ArcGIS(timeout=15)
                                loc = geolocator.geocode(lug_rs_input)
                                if loc is not None:
                                    st.session_state.lat_rs_auto = str(loc.latitude)
                                    st.session_state.lon_rs_auto = str(loc.longitude)
                                    st.session_state.lugar_rs_confirmado = loc.address
                                    st.sidebar.success(f"Listo: {loc.address}")
                                else:
                                    st.sidebar.error("Lugar no encontrado. Revisa la ortografía.")
                            except Exception as error_mapa:
                                st.sidebar.error(f"Error temporal de conexión con el mapa: {error_mapa}")
                
                lat_rs = st.sidebar.text_input("Latitud de la RS:", value=st.session_state.lat_rs_auto)
                lon_rs = st.sidebar.text_input("Longitud de la RS:", value=st.session_state.lon_rs_auto)
                
                if st.session_state.lugar_rs_confirmado != "":
                    lug_final = st.session_state.lugar_rs_confirmado
                else:
                    lug_final = lug_rs_input
            # --------------------------------------------------------------------------------

            st.sidebar.markdown("<br>", unsafe_allow_html=True)
            
            if st.sidebar.button("🚀 INICIAR PROCESAMIENTO", type="primary", use_container_width=True):
                # Construimos el payload explícitamente sin atajos
                payload_motor = {}
                payload_motor["Nombres"] = cli_obj.get("Nombres", "Consultante")
                payload_motor["nombre"] = cli_obj.get("Nombres", "Consultante")
                payload_motor["Fecha"] = cli_obj.get("Fecha")
                payload_motor["fecha"] = cli_obj.get("Fecha")
                payload_motor["Hora"] = cli_obj.get("Hora")
                payload_motor["hora"] = cli_obj.get("Hora")
                payload_motor["Latitud"] = cli_obj.get("Latitud")
                payload_motor["lat"] = cli_obj.get("Latitud")
                payload_motor["Longitud"] = cli_obj.get("Longitud")
                payload_motor["lon"] = cli_obj.get("Longitud")

                with st.spinner("Calculando efemérides y redactando informe integral..."):
                    try:
                        datos_resultantes = None
                        plantilla_resultante = None
                        
                        if "Transitos" in sel_p:
                            st.session_state.tipo_reporte_actual = "TRANSITOS"
                            datos_resultantes, plantilla_resultante = motor_web.procesar_transitos_con_ia(payload_motor, None, id_sel)
                        
                        elif "Revolucion" in sel_p:
                            st.session_state.tipo_reporte_actual = "REVOLUCION"
                            datos_resultantes, plantilla_resultante = motor_web.procesar_rs_con_ia(payload_motor, None, id_sel, lat_rs=lat_rs, lon_rs=lon_rs, lugar_rs=lug_final)
                        
                        else:
                            st.session_state.tipo_reporte_actual = "NATAL"
                            datos_resultantes, plantilla_resultante = motor_web.procesar_natal_con_ia(payload_motor, None, id_sel)
                        
                        if datos_resultantes is not None:
                            st.session_state.datos_diccionario = datos_resultantes
                            st.session_state.plantilla_usar = plantilla_resultante
                            st.session_state.textos_generados = True
                            st.session_state.idx_prog_actual = idx_p
                            st.rerun()
                        else:
                            st.sidebar.error(f"⚠️ El motor falló: {plantilla_resultante}")
                            st.sidebar.info("Consejo: Verifica tu conexión a OpenAI y que las columnas del Excel no tengan ceros.")
                    except Exception as e:
                        st.sidebar.error(f"❌ Error crítico en el procesamiento: {e}")

    # ==============================================================================
    # 8. PANEL DE EDICIÓN INTEGRAL (DETALLE MÁXIMO EXTENDIDO)
    # ==============================================================================
    if st.session_state.textos_generados == True:
        d_actual = st.session_state.datos_diccionario
        tipo_actual = st.session_state.tipo_reporte_actual
        
        titulo_mostrar = d_actual.get('titulo_informe', 'Informe')
        nombre_mostrar = d_actual.get('nombre_cliente', 'Consultante')
        
        st.subheader(f"Editando: {titulo_mostrar} - {nombre_mostrar}")
        st.info("Revisa y personaliza cada sección del borrador generado por la IA antes de finalizar.")

        # --- SECCIONES REVOLUCIÓN SOLAR ---
        if tipo_actual == "REVOLUCION":
            with st.expander("1. Infografía Inicial (Cuadros de Perspectiva)", expanded=False):
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    d_actual['perspectivas']['transformacion'] = st.text_area("El Gran Reto de Transformación Anual", d_actual['perspectivas'].get('transformacion', ''), height=120)
                    d_actual['perspectivas']['cambio'] = st.text_area("Área donde se sentirá el Cambio Principal", d_actual['perspectivas'].get('cambio', ''), height=120)
                with col_info2:
                    d_actual['perspectivas']['oportunidades'] = st.text_area("Mayores Oportunidades de Crecimiento", d_actual['perspectivas'].get('oportunidades', ''), height=120)
                    d_actual['perspectivas']['relaciones'] = st.text_area("Tónica del Clima Vincular y Social", d_actual['perspectivas'].get('relaciones', ''), height=120)
            
            with st.expander("2. Introducción y Análisis de Base (Natal / Tránsitos / Progresiones)", expanded=False):
                d_actual['intro_texto'] = st.text_area("Texto de Introducción Cálida al Informe", d_actual.get('intro_texto',''), height=100)
                d_actual['carta_natal_resumen'] = st.text_area("Resumen Psicológico de la Esencia Natal", d_actual.get('carta_natal_resumen',''), height=150)
                d_actual['transitos_personales'] = st.text_area("Análisis de los Tránsitos Planetarios Lentos", d_actual.get('transitos_personales',''), height=150)
                d_actual['progresiones_secundarias'] = st.text_area("Interpretación de Progresiones y Estado Interior", d_actual.get('progresiones_secundarias',''), height=150)
                
                texto_tips = "\n".join(d_actual.get('como_actuar_progresiones', []))
                tips_editados = st.text_area("Consejos de Acción ante Progresiones (Uno por línea)", texto_tips)
                
                lista_tips_final = []
                for x in tips_editados.split("\n"):
                    if x.strip() != "":
                        lista_tips_final.append(x.strip())
                d_actual['como_actuar_progresiones'] = lista_tips_final

            with st.expander("3. Revolución Solar (General y Profesional)", expanded=True):
                d_actual['revolucion_solar_general_1'] = st.text_area("Interpretación del Clima General de la Revolución Solar", d_actual.get('revolucion_solar_general_1',''), height=250)
                
                texto_prop = "\n".join(d_actual.get('revo_propone', []))
                prop_editadas = st.text_area("Propuestas Evolutivas del Año (Uno por línea)", texto_prop)
                
                lista_prop_final = []
                for x in prop_editadas.split("\n"):
                    if x.strip() != "":
                        lista_prop_final.append(x.strip())
                d_actual['revo_propone'] = lista_prop_final
                
                d_actual['situacion_laboral_economica'] = st.text_area("Panorama Vocacional, Económico y Profesional", d_actual.get('situacion_laboral_economica',''), height=180)
                
                texto_obj = "\n".join(d_actual.get('logro_objetivos_profesionales', []))
                obj_editados = st.text_area("Objetivos Profesionales Específicos (Uno por línea)", texto_obj)
                
                lista_obj_final = []
                for x in obj_editados.split("\n"):
                    if x.strip() != "":
                        lista_obj_final.append(x.strip())
                d_actual['logro_objetivos_profesionales'] = lista_obj_final

            with st.expander("4. Emocional, Trimestral y Cierre", expanded=True):
                d_actual['situacion_emocional'] = st.text_area("Análisis Profundo de la Vida Afectiva y Familiar", d_actual.get('situacion_emocional',''), height=180)
                st.markdown("**Cronograma Anual de Proyección Trimestral:**")
                
                if 'panorama_trimestral' in d_actual:
                    for i, trim in enumerate(d_actual['panorama_trimestral']):
                        titulo_trim = trim.get('titulo', f'Trimestre {i+1}')
                        texto_trim = trim.get('texto', '')
                        trim['texto'] = st.text_area(f"📍 {titulo_trim}", texto_trim, key=f"rs_t_{i}", height=120)
                
                texto_plan = "\n".join(d_actual.get('plan_accion_objetivos', []))
                plan_editado = st.text_area("Plan de Acción y Objetivos Finales (Uno por línea)", texto_plan)
                
                lista_plan_final = []
                for x in plan_editado.split("\n"):
                    if x.strip() != "":
                        lista_plan_final.append(x.strip())
                d_actual['plan_accion_objetivos'] = lista_plan_final

        # --- SECCIONES TRÁNSITOS ANUALES ---
        elif tipo_actual == "TRANSITOS":
            with st.expander("1. Energía Base del Consultante", expanded=False):
                d_actual['interpretacion_sol_signo'] = st.text_area("Interpretación Natal del Sol", d_actual.get('interpretacion_sol_signo',''), height=100)
                d_actual['interpretacion_luna_signo'] = st.text_area("Interpretación Natal de la Luna", d_actual.get('interpretacion_luna_signo',''), height=100)
                d_actual['interpretacion_asc_signo'] = st.text_area("Interpretación Natal del Ascendente", d_actual.get('interpretacion_asc_signo',''), height=100)
            
            with st.expander("2. Análisis del Clima Astrológico Anual", expanded=True):
                d_actual['frase_anual_corta'] = st.text_input("Lema Inspirador del Año (Título Principal)", d_actual.get('frase_anual_corta',''))
                d_actual['analisis_clima_anual'] = st.text_area("Interpretación General Evolutiva para los 12 meses", d_actual.get('analisis_clima_anual',''), height=300)
                d_actual['oportunidad_anual'] = st.text_area("La Gran Oportunidad de Crecimiento Anual", d_actual.get('oportunidad_anual',''), height=120)
                d_actual['atencion_anual'] = st.text_area("Punto de Atención Crítico y Cuidado Psicológico", d_actual.get('atencion_anual',''), height=120)

            with st.expander("3. Calendario Detallado de Eventos Mensuales", expanded=True):
                st.markdown("<p style='color: #666;'>Edita los efectos de los tránsitos específicos mes a mes:</p>", unsafe_allow_html=True)
                if 'calendario_por_meses' in d_actual:
                    for mes_nombre, lista_eventos in d_actual.get('calendario_por_meses', {}).items():
                        st.markdown(f"### 🗓️ {mes_nombre}")
                        for idx_ev, evento in enumerate(lista_eventos):
                            f_ev = evento.get('fecha', '')
                            t_ev = evento.get('transito', '')
                            a_ev = evento.get('aspecto', '')
                            n_ev = evento.get('natal', '')
                            etiqueta = f"{f_ev} | {t_ev} {a_ev} a {n_ev}"
                            texto_previo = evento.get('texto_efecto', '')
                            evento['texto_efecto'] = st.text_area(etiqueta, texto_previo, key=f"tr_{mes_nombre}_{idx_ev}_{f_ev}", height=100)

        # --- SECCIONES CARTA NATAL ---
        else:
            with st.expander("1. Tríada Sagrada de Identidad (Sol, Luna y AC)", expanded=True):
                d_actual['interpretacion_sol_signo'] = st.text_area("☉ El Propósito Solar y la Esencia Vital", d_actual.get('interpretacion_sol_signo',''), height=150)
                d_actual['interpretacion_luna_signo'] = st.text_area("☽ El Refugio Emocional y el Mecanismo de Seguridad", d_actual.get('interpretacion_luna_signo',''), height=150)
                d_actual['interpretacion_asc_signo'] = st.text_area("AC El Camino de Integración del Ascendente", d_actual.get('interpretacion_asc_signo',''), height=150)
            
            with st.expander("2. Análisis de los Gigantes del Cielo", expanded=False):
                if 'gigantes_del_cielo' in d_actual:
                    for idx_g, gigante in enumerate(d_actual.get('gigantes_del_cielo', [])):
                        nom_g = gigante.get('nombre', 'Cuerpo')
                        sig_g = gigante.get('signo', '')
                        txt_g = gigante.get('texto', '')
                        gigante['texto'] = st.text_area(f"{nom_g} en {sig_g}", txt_g, key=f"natal_g_{idx_g}", height=100)

            with st.expander("3. Síntesis Evolutiva Global y FODA Personal", expanded=True):
                d_actual['interpretacion_personalidad_global'] = st.text_area("Relato Final de Integración de Personalidad", d_actual.get('interpretacion_personalidad_global',''), height=350)
                st.markdown("**Matriz de Potencial (FODA):**")
                
                col_f1, col_f2 = st.columns(2)
                
                with col_f1:
                    fort_previas = "\n".join(d_actual['foda'].get('fortalezas', []))
                    fort_editadas = st.text_area("Fortalezas (Una por línea)", fort_previas)
                    lista_f = []
                    for x in fort_editadas.split("\n"):
                        if x.strip() != "":
                            lista_f.append(x.strip())
                    d_actual['foda']['fortalezas'] = lista_f
                    
                with col_f2:
                    deb_previas = "\n".join(d_actual['foda'].get('debilidades', []))
                    deb_editadas = st.text_area("Debilidades (Una por línea)", deb_previas)
                    lista_d = []
                    for x in deb_editadas.split("\n"):
                        if x.strip() != "":
                            lista_d.append(x.strip())
                    d_actual['foda']['debilidades'] = lista_d

        # ==============================================================================
        # 9. PANEL DE ACCIONES FINALES (DESCARGA Y VISTA PREVIA)
        # ==============================================================================
        st.divider()
        c_fin1, c_fin2 = st.columns(2)
        
        # Preparación de imágenes y logo antes de la generación final
        d_actual['logo_base64'] = get_base_64_of_bin_file('apple-icon.png')
        
        try:
            env_jinja = Environment(loader=FileSystemLoader('.'))
            plantilla_final = env_jinja.get_template(st.session_state.plantilla_usar)
            
            with c_fin1:
                if st.button("👁️ VER VISTA PREVIA DEL DISEÑO"):
                    try: 
                        html_render = plantilla_final.render(d_actual)
                        components.html(html_render, height=900, scrolling=True)
                    except Exception as error_render: 
                        st.error(f"Error al renderizar el diseño visual: {error_render}")

            with c_fin2:
                html_para_descargar = plantilla_final.render(d_actual)
                
                # Determinamos el sufijo del archivo explícitamente
                if tipo_actual == "TRANSITOS":
                    sufijo = "Transitos"
                elif tipo_actual == "REVOLUCION":
                    sufijo = "Revolucion"
                else:
                    sufijo = "Natal"
                    
                nombre_cliente_limpio = str(d_actual.get('nombre_cliente', 'Cliente')).replace(" ", "_")
                nombre_archivo = f"Informe_Astroimpacto_{nombre_cliente_limpio}_{sufijo}.html"
                
                st.download_button(
                    label="💾 DESCARGAR INFORME HTML FINAL", 
                    data=html_para_descargar, 
                    file_name=nombre_archivo, 
                    mime="text/html", 
                    type="primary"
                )
                
                if st.button("❌ FINALIZAR Y LIMPIAR TALLER"):
                    st.session_state.textos_generados = False
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error cargando la plantilla HTML: {e}")
