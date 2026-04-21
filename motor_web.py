import swisseph as swe
import pandas as pd
import consultor_web
from datetime import datetime, timedelta, timezone
import time

# ==========================================
# CONFIGURACIÓN DE EFEMÉRIDES PARA LA NUBE
# ==========================================
# FLG_MOSEPH: usa efemérides Moshier integradas en la librería.
# No requiere archivos .se1 externos → funciona en Streamlit Cloud sin configuración adicional.
# Precisión: ±1" para planetas principales (Sol, Luna, Mercurio–Saturno), suficiente para astrología.
swe.set_ephe_path('')
FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

# Lista de planetas lentos para cálculo de tránsitos
PLANETAS_TRANSITO = [
    ("Júpiter",  swe.JUPITER),
    ("Saturno",  swe.SATURN),
    ("Urano",    swe.URANUS),
    ("Neptuno",  swe.NEPTUNE),
    ("Plutón",   swe.PLUTO),
]

PLANETAS_NATALES = [
    ("Sol",      swe.SUN),
    ("Luna",     swe.MOON),
    ("Mercurio", swe.MERCURY),
    ("Venus",    swe.VENUS),
    ("Marte",    swe.MARS),
    ("Júpiter",  swe.JUPITER),
    ("Saturno",  swe.SATURN),
]

ASPECTOS_CONFIG = [
    ("Conjunción",  0,   7),
    ("Sextil",     60,   5),
    ("Cuadratura", 90,   7),
    ("Trígono",   120,   7),
    ("Oposición", 180,   7),
]

MESES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]


# --- FUNCIONES DE FORMATEO TÉCNICO ---

def obtener_signo(lon):
    signos = ["Aries","Tauro","Géminis","Cáncer","Leo","Virgo",
              "Libra","Escorpio","Sagitario","Capricornio","Acuario","Piscis"]
    return signos[int(lon / 30) % 12]

def deg_to_dms_sign(lon):
    signos = ["Aries","Tauro","Géminis","Cáncer","Leo","Virgo",
              "Libra","Escorpio","Sagitario","Capricornio","Acuario","Piscis"]
    signo_idx = int(lon / 30) % 12
    grados   = int(lon % 30)
    minutos  = int((lon % 1) * 60)
    return f"{grados:02d}° {signos[signo_idx]} {minutos:02d}'"

def limpiar_coordenada(val):
    try:
        return float(val)
    except:
        return 0.0

def diferencia_angular(a, b):
    """Diferencia angular mínima entre dos longitudes."""
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


# ==========================================
# CÁLCULOS ASTROLÓGICOS CENTRALES
# ==========================================

def obtener_datos_astrologicos(jd, lat, lon):
    """
    Calcula posiciones planetarias y casas a partir de un Julian Day exacto.
    CORRECCIÓN: recibe jd directo en vez de dia/mes/año/hora para evitar
    recalcular el JD incorrectamente (bug del RS).
    """
    planetas = {}
    for name, id_p in PLANETAS_NATALES:
        planetas[name] = swe.calc_ut(jd, id_p, FLAGS)[0][0]
    casas, ascmc = swe.houses(jd, lat, lon, b'P')
    return planetas, ascmc[0], ascmc[1]  # planetas, ASC, MC


def calcular_posiciones_base_completa(cliente):
    """Calcula posiciones natales completas a partir del diccionario del cliente."""
    f   = pd.to_datetime(cliente.get('Fecha'))
    h   = float(cliente.get('Hora', 12.0))
    lat = limpiar_coordenada(cliente.get('Latitud', 0))
    lon = limpiar_coordenada(cliente.get('Longitud', 0))
    jd  = swe.julday(f.year, f.month, f.day, h, swe.GREG_CAL)
    planetas, asc, mc = obtener_datos_astrologicos(jd, lat, lon)
    return planetas, asc, mc, f, h, lat, lon


# ==========================================
# INFORME 1: REVOLUCIÓN SOLAR
# ==========================================

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    """
    Genera el informe de Revolución Solar con cálculo correcto del JD exacto
    y conversión de coordenadas a float.
    CORRECCIONES APLICADAS:
      - obtener_datos_astrologicos recibe jd directo (no fecha fija 1/1/2000)
      - lat_rs / lon_rs se convierten a float antes de pasarlos a swisseph
      - anio_rs incluido en el diccionario de retorno para la plantilla HTML
    """
    try:
        nombre = cliente.get('Nombres', 'Consultante')

        # 1. DATOS NATALES
        try:
            f_nac = pd.to_datetime(cliente.get('Fecha'))
            h_nac = float(cliente.get('Hora', 12.0))
            lat_n = limpiar_coordenada(cliente.get('Latitud', 0))
            lon_n = limpiar_coordenada(cliente.get('Longitud', 0))
        except Exception:
            return None, "Error: Datos de nacimiento incompletos para cálculos matemáticos."

        # 2. POSICIONES NATALES
        jd_nat = swe.julday(f_nac.year, f_nac.month, f_nac.day, h_nac, swe.GREG_CAL)
        planetas_nat, asc_nat, mc_nat = obtener_datos_astrologicos(jd_nat, lat_n, lon_n)
        sol_natal = planetas_nat['Sol']

        # 3. BÚSQUEDA DEL RETORNO SOLAR (Newton-Raphson)
        anio_actual = datetime.now().year
        jd_rs = swe.julday(anio_actual, f_nac.month, max(1, f_nac.day - 1), 0.0)
        for _ in range(50):
            sol_ahora = swe.calc_ut(jd_rs, swe.SUN, FLAGS)[0][0]
            diff = sol_natal - sol_ahora
            if diff > 180:   diff -= 360
            elif diff < -180: diff += 360
            if abs(diff) < 0.000001: break
            jd_rs += diff / 0.9856  # ~1 grado/día

        # 4. COORDENADAS DE LA RS (convertir a float para evitar TypeError en swisseph)
        # CORRECCIÓN: lat_rs y lon_rs llegan como str desde st.text_input
        lat_calc = limpiar_coordenada(lat_rs) if lat_rs else lat_n
        lon_calc = limpiar_coordenada(lon_rs) if lon_rs else lon_n

        # 5. POSICIONES EN EL MOMENTO EXACTO DE LA RS
        # CORRECCIÓN: se pasa jd_rs directamente, no una fecha fija
        planetas_rs, asc_rs, mc_rs = obtener_datos_astrologicos(jd_rs, lat_calc, lon_calc)

        # 6. PROGRESIONES SECUNDARIAS (1 día = 1 año)
        edad = anio_actual - f_nac.year
        jd_prog = jd_nat + edad
        planetas_prog = {}
        for name, id_p in [("Sol", swe.SUN), ("Luna", swe.MOON), ("Marte", swe.MARS)]:
            planetas_prog[name] = swe.calc_ut(jd_prog, id_p, FLAGS)[0][0]

        # 7. PANEL DE AUDITORÍA TÉCNICA
        auditoria = (
            f"--- PANEL TÉCNICO RS {anio_actual} ---\n"
            f"NATAL:  Asc {deg_to_dms_sign(asc_nat)} | Sol {deg_to_dms_sign(sol_natal)}\n"
            f"RS {anio_actual}: Asc {deg_to_dms_sign(asc_rs)} | Luna {deg_to_dms_sign(planetas_rs['Luna'])}\n"
            f"Ubicación RS: {lugar_rs if lugar_rs else 'Lugar natal'}\n"
            f"PROGRESIONES (Edad {edad}):\n"
            f"  Luna Prog: {deg_to_dms_sign(planetas_prog['Luna'])}\n"
            f"  Sol Prog:  {deg_to_dms_sign(planetas_prog['Sol'])}\n"
            f"-----------------------------------"
        )

        # 8. PROMPT PARA IA
        rol    = "Eres Patricia Ramirez, astróloga profesional. Tu estilo es profundo y detallado."
        prompt = f"""
DATOS TÉCNICOS REALES para {nombre}:
Natal: Asc {obtener_signo(asc_nat)}, Sol {obtener_signo(sol_natal)}.
RS {anio_actual}: Asc Anual {obtener_signo(asc_rs)}, Luna Anual {obtener_signo(planetas_rs['Luna'])}.
Progresiones: Luna Progresada en {obtener_signo(planetas_prog['Luna'])}, Sol Progresado en {obtener_signo(planetas_prog['Sol'])}.

Basado en estos datos EXACTOS, redacta los siguientes bloques separados por ###:
1. Reto de transformación principal del año
2. Oportunidad mayor que se abre este año
3. Área de cambio principal
4. Tónica vincular y relaciones
5. Interpretación del Clima General (mínimo 4 párrafos profundos)
6. Panorama laboral y económico
7. Clima emocional y afectivo
8. Introducción cálida personalizada
9. Resumen de la esencia natal
10. Tránsitos lentos destacados del año
11. Análisis de Progresiones Secundarias
"""
        resultado = ""
        for _ in range(3):
            resultado = consultor_web.consultar_gpt(rol, prompt, 3500)
            if resultado and "Error" not in resultado:
                break
            time.sleep(2)

        if not resultado or "Error" in resultado:
            partes = ["(Sin información disponible)"] * 12
        else:
            partes = [p.strip() for p in resultado.split('###')]
            # Asegurar que siempre haya al menos 11 partes
            while len(partes) < 12:
                partes.append("")

        # 9. DICCIONARIO FINAL
        return {
            "nombre_cliente":             nombre,
            "titulo_informe":             f"Revolución Solar {anio_actual}",
            "anio_rs":                    anio_actual,       # ← CORRECCIÓN: faltaba esta clave
            "auditoria_tecnica":          auditoria,
            "perspectivas": {
                "transformacion": partes[0],
                "oportunidades":  partes[1],
                "cambio":         partes[2],
                "relaciones":     partes[3],
            },
            "revolucion_solar_general_1":  partes[4],
            "situacion_laboral_economica": partes[5],
            "situacion_emocional":         partes[6],
            "intro_texto":                 partes[7],
            "carta_natal_resumen":         partes[8],
            "transitos_personales":        partes[9],
            "progresiones_secundarias":    partes[10],
            "revo_propone":                [],
            "logro_objetivos_profesionales": [],
            "como_actuar_progresiones":    [],
            "plan_accion_objetivos":       [],
            "panorama_trimestral": [
                {"titulo": "Primer Trimestre",   "texto": "Inicios basados en tu Asc Anual."},
                {"titulo": "Segundo Trimestre",  "texto": "Desarrollo de la Luna Anual."},
                {"titulo": "Tercer Trimestre",   "texto": "Cosecha y resultados."},
                {"titulo": "Cuarto Trimestre",   "texto": "Integración y cierre del año."},
            ],
        }, "informe_astroimpacto_rs.html"

    except Exception as e:
        import traceback
        return None, f"Error técnico RS: {str(e)}\n{traceback.format_exc()}"


# ==========================================
# INFORME 2: CARTA NATAL
# ==========================================

def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Genera el informe profundo de Carta Natal con cálculos exactos."""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        planetas, asc, mc, f_nac, h_nac, lat, lon = calcular_posiciones_base_completa(cliente)

        rol    = "Eres Patricia Ramirez, astróloga profesional. Redacta de forma extensa y psicológica."
        prompt = (
            f"Analiza la Carta Natal completa para {nombre}:\n"
            f"Sol {obtener_signo(planetas['Sol'])}, Luna {obtener_signo(planetas['Luna'])}, "
            f"Asc {obtener_signo(asc)}.\n"
            f"Separa cada sección con ###:\n"
            f"1. Interpretación del Sol\n"
            f"2. Interpretación de la Luna\n"
            f"3. Interpretación del Ascendente\n"
            f"4. Síntesis de personalidad global\n"
        )

        resultado = consultor_web.consultar_gpt(rol, prompt, 2500)
        partes = [p.strip() for p in resultado.split('###')] if resultado and "Error" not in resultado else [""] * 5
        while len(partes) < 5:
            partes.append("")

        auditoria = (
            f"Sol: {deg_to_dms_sign(planetas['Sol'])} | "
            f"Luna: {deg_to_dms_sign(planetas['Luna'])} | "
            f"Asc: {deg_to_dms_sign(asc)}"
        )

        return {
            "nombre_cliente":                  nombre,
            "titulo_informe":                  "Análisis de Carta Natal",
            "auditoria_tecnica":               auditoria,
            "aspectos_clave":                  ["Esencia", "Emoción", "Camino"],
            "interpretacion_sol_signo":        partes[1] if len(partes) > 1 else "",
            "interpretacion_luna_signo":       partes[2] if len(partes) > 2 else "",
            "interpretacion_asc_signo":        partes[3] if len(partes) > 3 else "",
            "interpretacion_personalidad_global": partes[4] if len(partes) > 4 else "",
            "gigantes_del_cielo":              [],
            "foda": {
                "fortalezas":   ["Liderazgo natural"],
                "oportunidades":["Crecimiento personal"],
                "debilidades":  ["Tendencia a la duda"],
                "amenazas":     ["Presión externa"],
            },
        }, "informe_astroimpacto.html"

    except Exception as e:
        import traceback
        return None, f"Error técnico Natal: {str(e)}\n{traceback.format_exc()}"


# ==========================================
# INFORME 3: TRÁNSITOS ANUALES
# ==========================================

def _detectar_aspectos_mes(jd_inicio, jd_fin, planetas_natales_pos):
    """
    Detecta tránsitos de planetas lentos sobre posiciones natales en un rango de JD.
    Retorna lista de dicts con fecha, transito, aspecto, natal.
    """
    eventos = []
    jd = jd_inicio
    paso = 1.0  # un día por paso

    # Guardamos posición del día anterior para detectar cruce del orbe exacto
    pos_ayer = {}
    for nombre_t, id_t in PLANETAS_TRANSITO:
        pos_ayer[nombre_t] = swe.calc_ut(jd - 1, id_t, FLAGS)[0][0]

    while jd <= jd_fin:
        for nombre_t, id_t in PLANETAS_TRANSITO:
            lon_t = swe.calc_ut(jd, id_t, FLAGS)[0][0]
            for nombre_n, lon_n in planetas_natales_pos.items():
                for asp_nombre, asp_grados, orbe in ASPECTOS_CONFIG:
                    diff_hoy  = diferencia_angular(lon_t, lon_n + asp_grados) if asp_grados > 0 else diferencia_angular(lon_t, lon_n)
                    diff_ayer = diferencia_angular(pos_ayer[nombre_t], lon_n + asp_grados) if asp_grados > 0 else diferencia_angular(pos_ayer[nombre_t], lon_n)
                    # Registrar cuando cruza el punto exacto (mínimo orbe)
                    if diff_hoy <= orbe and diff_hoy < diff_ayer:
                        # Convertir JD a fecha
                        yr, mo, dy, _ = swe.revjul(jd, swe.GREG_CAL)
                        fecha_str = f"{int(dy):02d}/{int(mo):02d}/{int(yr)}"
                        rol_ia  = "Eres Patricia Ramirez, astróloga. Responde en 2 frases claras y directas en HTML <p>."
                        efecto  = consultor_web.consultar_gpt(
                            rol_ia,
                            f"Interpreta brevemente el tránsito de {nombre_t} en {asp_nombre} a {nombre_n} natal. ¿Qué efecto tiene?",
                            150
                        )
                        eventos.append({
                            "fecha":        fecha_str,
                            "transito":     nombre_t,
                            "aspecto":      asp_nombre,
                            "natal":        nombre_n,
                            "texto_efecto": efecto,
                        })
            pos_ayer[nombre_t] = lon_t
        jd += paso
    return eventos


def procesar_transitos_con_ia(cliente, tipo_obj, id_cli):
    """
    Genera el informe anual de Tránsitos con detección automática de aspectos
    mes a mes y generación de textos vía IA.
    CORRECCIÓN: esta función faltaba completamente en el motor original.
    """
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        planetas_nat, asc_nat, mc_nat, f_nac, h_nac, lat_n, lon_n = calcular_posiciones_base_completa(cliente)

        anio_actual = datetime.now().year

        # Posiciones natales relevantes para los tránsitos
        pos_natales = {
            "Sol":      planetas_nat["Sol"],
            "Luna":     planetas_nat["Luna"],
            "Ascendente": asc_nat,
            "Marte":    planetas_nat["Marte"],
            "Júpiter":  planetas_nat["Júpiter"],
            "Saturno":  planetas_nat["Saturno"],
        }

        # Generar textos natales base
        rol = "Eres Patricia Ramirez, astróloga profesional. Redacta en HTML <p>."
        txt_sol  = consultor_web.consultar_gpt(rol,
            f"Interpreta Sol en {obtener_signo(planetas_nat['Sol'])} para {nombre} en 3 frases.", 300)
        txt_luna = consultor_web.consultar_gpt(rol,
            f"Interpreta Luna en {obtener_signo(planetas_nat['Luna'])} para {nombre} en 3 frases.", 300)
        txt_asc  = consultor_web.consultar_gpt(rol,
            f"Interpreta Ascendente en {obtener_signo(asc_nat)} para {nombre} en 3 frases.", 300)

        # Texto introductorio anual
        txt_intro = consultor_web.consultar_gpt(rol,
            f"Redacta una bienvenida cálida para el informe anual de tránsitos de {nombre} "
            f"con Sol en {obtener_signo(planetas_nat['Sol'])} y Asc en {obtener_signo(asc_nat)}.", 400)

        frase_anual = consultor_web.consultar_gpt(
            "Eres una astróloga. Responde solo con una frase inspiradora corta, sin comillas.",
            f"Frase astrológica para un año con mucho {obtener_signo(asc_nat)}.", 60)

        # Detección de tránsitos mes a mes
        calendario = {}
        for mes in range(1, 13):
            jd_ini = swe.julday(anio_actual, mes, 1, 0.0)
            # Último día del mes
            if mes == 12:
                jd_fin = swe.julday(anio_actual + 1, 1, 1, 0.0) - 1
            else:
                jd_fin = swe.julday(anio_actual, mes + 1, 1, 0.0) - 1

            eventos_mes = _detectar_aspectos_mes(jd_ini, jd_fin, pos_natales)
            if eventos_mes:  # Solo incluir meses con eventos
                calendario[MESES_ES[mes - 1]] = eventos_mes

        auditoria = (
            f"TRÁNSITOS {anio_actual}\n"
            f"Sol Natal: {deg_to_dms_sign(planetas_nat['Sol'])} | "
            f"Luna: {deg_to_dms_sign(planetas_nat['Luna'])} | "
            f"Asc: {deg_to_dms_sign(asc_nat)}"
        )

        return {
            "nombre_cliente":          nombre,
            "titulo_informe":          f"Tránsitos Anuales {anio_actual}",
            "titulo_bienvenida":       f"Tu Año Astrológico {anio_actual}",
            "fecha_entrega":           datetime.now().strftime("%B %Y"),
            "auditoria_tecnica":       auditoria,
            "texto_introductorio":     txt_intro,
            "frase_anual_corta":       frase_anual,
            "ruta_imagen_carta":       "",
            "sol":  {"signo": obtener_signo(planetas_nat["Sol"])},
            "luna": {"signo": obtener_signo(planetas_nat["Luna"])},
            "asc":  {"signo": obtener_signo(asc_nat)},
            "interpretacion_sol_signo":  txt_sol,
            "interpretacion_luna_signo": txt_luna,
            "interpretacion_asc_signo":  txt_asc,
            "analisis_clima_anual":      "",
            "oportunidad_anual":         "",
            "atencion_anual":            "",
            "calendario_por_meses":      calendario,
        }, "informe_astroimpacto_transitos.html"

    except Exception as e:
        import traceback
        return None, f"Error técnico Tránsitos: {str(e)}\n{traceback.format_exc()}"
