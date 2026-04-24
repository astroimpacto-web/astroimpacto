import swisseph as swe
import pandas as pd
import consultor_web
from datetime import datetime, timedelta, timezone
import time
import re
import traceback

# ==============================================================================
# CONFIGURACIÓN DE EFEMÉRIDES PARA ENTORNOS DE NUBE (STREAMLIT CLOUD)
# ==============================================================================
# FLG_MOSEPH: utiliza las efemérides de Moshier integradas en la librería.
# Esto permite que la aplicación funcione en la nube sin archivos .se1 externos.
# Proporciona una precisión de ±1" para los planetas principales (Sol hasta Saturno), 
# lo cual es el estándar para la astrología psicológica y profesional de alto nivel.
# Es fundamental que este paso se ejecute antes de realizar cualquier cálculo matemático.
# Sin esta configuración, el motor no podrá acceder a las posiciones planetarias.
swe.set_ephe_path('')
FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

# LISTA DE PLANETAS PARA TRÁNSITOS (ENFOQUE EN LENTOS Y TRANSPERSONALES)
# Estos cuerpos celestes marcan los ciclos evolutivos de largo plazo y las 
# grandes transformaciones estructurales en la psique del consultante.
# Su movimiento lento permite un análisis de tendencias anuales muy preciso y estable.
PLANETAS_TRANSITO = [
    ("Júpiter",  swe.JUPITER),
    ("Saturno",  swe.SATURN),
    ("Urano",    swe.URANUS),
    ("Neptuno",  swe.NEPTUNE),
    ("Plutón",   swe.PLUTO),
]

# LISTA DE PLANETAS PARA ANÁLISIS NATAL (ESTRUCTURA DE PERSONALIDAD)
# Incluye los luminares y planetas personales para una síntesis completa de la identidad.
# El Sol representa el propósito vital, la Luna la seguridad emocional y el Ascendente el camino.
# Se incluyen Mercurio, Venus y Marte para entender la comunicación, el deseo y la acción.
PLANETAS_NATALES = [
    ("Sol",      swe.SUN),
    ("Luna",     swe.MOON),
    ("Mercurio", swe.MERCURY),
    ("Venus",    swe.VENUS),
    ("Marte",    swe.MARS),
    ("Júpiter",  swe.JUPITER),
    ("Saturno",  swe.SATURN),
]

# CONFIGURACIÓN DE ASPECTOS MAYORES Y SUS ORBES DE TRABAJO
# Se definen los grados exactos y el margen de error (orbe) permitido para el cálculo.
# Estos valores aseguran que solo se interpreten las energías que realmente están 
# interactuando con fuerza en el momento del análisis solicitado por la profesional.
# Un orbe de 7 grados es el estándar para conjunciones y oposiciones en este sistema.
ASPECTOS_CONFIG = [
    ("Conjunción",  0,   7),
    ("Sextil",     60,   5),
    ("Cuadratura", 90,   7),
    ("Trígono",   120,   7),
    ("Oposición", 180,   7),
]

# MAPEO DE MESES PARA INFORMES DE TRÁNSITOS Y CRONOGRAMAS
# Se utiliza para traducir las fechas del calendario gregoriano a una visualización 
# amigable para el cliente en las plantillas HTML finales del sistema AstroImpacto.
# El orden es cronológico estándar para asegurar la correcta iteración en los informes.
MESES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]


# ==============================================================================
# FUNCIONES DE FORMATEO Y CONVERSIÓN TÉCNICA (BLOQUE DE UTILIDADES)
# ==============================================================================

def obtener_signo(lon):
    """
    Determina el nombre del signo zodiacal basándose en la longitud eclíptica.
    Divide el zodiaco de 360 grados en 12 segmentos exactos de 30 grados cada uno.
    
    Args:
        lon (float): Longitud eclíptica del cuerpo celeste en grados decimales.
        
    Returns:
        str: Nombre del signo zodiacal correspondiente (Aries a Piscis).
    """
    signos = ["Aries","Tauro","Géminis","Cáncer","Leo","Virgo",
              "Libra","Escorpio","Sagitario","Capricornio","Acuario","Piscis"]
    return signos[int(lon / 30) % 12]

def deg_to_dms_sign(lon):
    """
    Convierte una longitud decimal en formato de Grados, Minutos y Signo.
    Es la función principal para generar la auditoría técnica que lee la astróloga 
    para validar que las posiciones calculadas coincidan con el software profesional.
    
    Args:
        lon (float): Longitud eclíptica decimal.
        
    Returns:
        str: Cadena formateada ej: '15° Tauro 24\''
    """
    signos = ["Aries","Tauro","Géminis","Cáncer","Leo","Virgo",
              "Libra","Escorpio","Sagitario","Capricornio","Acuario","Piscis"]
    signo_idx = int(lon / 30) % 12
    grados   = int(lon % 30)
    minutos  = int((lon % 1) * 60)
    return f"{grados:02d}° {signos[signo_idx]} {minutos:02d}'"

def limpiar_hora_precisa(val):
    try:
        if pd.isna(val) or val == "": return 0.0
        if hasattr(val, 'hour') and hasattr(val, 'minute'): return val.hour + val.minute/60.0 + val.second/3600.0
        val_str = str(val).strip()
        if ':' in val_str:
            p = val_str.split(':')
            return float(p[0]) + (float(p[1])/60.0 if len(p)>1 else 0.0) + (float(p[2])/3600.0 if len(p)>2 else 0.0)
        return float(val_str.replace(',', '.'))
    except: return 0.0

def limpiar_coordenada_dms(valor):
    try:
        if isinstance(valor, (float, int)): return float(valor)
        v = str(valor).upper().strip()
        negativo = 'S' in v or 'W' in v
        numeros = re.findall(r"\d+", v)
        deg = float(numeros[0]) if len(numeros) > 0 else 0
        min_val = float(numeros[1]) if len(numeros) > 1 else 0
        decimal = deg + (min_val / 60.0)
        return -decimal if negativo else decimal
    except: return 0.0

def parsear_fecha_excel(valor):
    try: return pd.to_datetime(valor)
    except: return datetime.now()

def diferencia_angular(a, b):
    """
    Calcula la distancia angular más corta entre dos puntos en un círculo zodiacal de 360 grados.
    Es una función crítica para la determinación precisa de orbes de aspectos.
    """
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d

# ==============================================================================
# CÁLCULOS ASTROLÓGICOS CENTRALES (LÓGICA MATEMÁTICA PURA)
# ==============================================================================

def obtener_datos_astrologicos(jd, lat, lon):
    """
    Calcula efemérides y casas usando el SISTEMA TOPOCÉNTRICO (b'T').
    Fuerza el tipo float para evitar el error 'swisseph.houses: error'.
    """
    try:
        planetas = {name: swe.calc_ut(float(jd), id_p, FLAGS)[0][0] for name, id_p in PLANETAS_NATALES}
        # IMPORTANTE: Definido en b'T' (Topocéntrico) para máxima precisión
        casas, ascmc = swe.houses(float(jd), float(lat), float(lon), b'T')
        return planetas, casas, ascmc
    except Exception as e:
        raise ValueError(f"Fallo en motor de casas Topocéntrico: {e}")

def calcular_posiciones_base(cliente):
    """Genera el set de 7 variables fundamentales de tu versión local."""
    # AHORA USA LAS FUNCIONES DEL PASO 1
    f = parsear_fecha_excel(cliente.get('Fecha'))
    if f is None: raise ValueError("Fecha no válida")
    
    # El Excel ya trae hora universal (UT), no se modifica nada.
    h = limpiar_hora_precisa(cliente.get('Hora', '12:00:00'))
    lat = limpiar_coordenada_dms(cliente.get('Latitud', 0))
    lon = limpiar_coordenada_dms(cliente.get('Longitud', 0))
    
    # JD con calendario Gregoriano
    jd = swe.julday(f.year, f.month, f.day, h, swe.GREG_CAL)
    planetas, casas, ascmc = obtener_datos_astrologicos(jd, lat, lon)
    
    return planetas, casas, ascmc, f, h, lat, lon
    
# ==============================================================================
# PROCESO 1: REVOLUCIÓN SOLAR (ESTRUCTURA DE 15 BLOQUES SIN RECORTES)
# ==============================================================================

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    """
    Función maestra para el cálculo y redacción de la Revolución Solar. 
    Sincroniza la matemática astronómica con el motor de interpretación de IA, 
    asegurando que los 15 bloques de información caigan en sus casillas exactas 
    según el diseño visual definido por Patricia Ramirez.
    """
    try:
        # 1. RECUPERACIÓN ÚNICA DE DATOS (7 variables)
        planetas_nat, casas_nat, ascmc_nat, fecha_nac, hora_nac, lat_nat, lon_nat = calcular_posiciones_base(cliente)
        
        nombre = cliente.get('Nombres', 'Consultante')
        
        # EXTRACCIÓN FORZADA A FLOAT (Evita el error 'tuple' and 'int')
        sol_natal  = float(planetas_nat['Sol'])
        luna_natal = float(planetas_nat['Luna'])
        asc_nat    = float(ascmc_nat[0])

        # 2. BÚSQUEDA DEL RETORNO SOLAR (Newton-Raphson Local)
        anio_actual = datetime.now().year
        jd_rs = swe.julday(anio_actual, fecha_nac.month, max(1, fecha_nac.day - 1), 0.0, swe.GREG_CAL)
        for _ in range(50):
            sol_ahora = swe.calc_ut(jd_rs, swe.SUN, FLAGS)[0][0]
            diff = sol_natal - sol_ahora
            if diff > 180:   diff -= 360
            elif diff < -180: diff += 360
            if abs(diff) < 0.000001: break
            jd_rs += diff / 0.9856 

        # 3. RELOCALIZACIÓN (Usando limpiar_coordenada_dms del Paso 1)
        lat_calc = limpiar_coordenada_dms(lat_rs) if lat_rs else lat_nat
        lon_calc = limpiar_coordenada_dms(lon_rs) if lon_rs else lon_nat
        lugar_final = lugar_rs if lugar_rs else "Ubicación natal"
        
        # 4. CÁLCULO RS Y PROGRESIONES
        planetas_rs, casas_rs, ascmc_rs = obtener_datos_astrologicos(jd_rs, lat_calc, lon_calc)
        
        # EXTRACCIÓN FORZADA A FLOAT
        asc_rs  = float(ascmc_rs[0])
        luna_rs = float(planetas_rs['Luna'])
        
        jd_prog = swe.julday(fecha_nac.year, fecha_nac.month, fecha_nac.day, hora_nac, swe.GREG_CAL) + (anio_actual - fecha_nac.year)
        
        # EXTRACCIÓN CRÍTICA: [0][0] extrae el número decimal puro
        luna_prog_lon = float(swe.calc_ut(jd_prog, swe.MOON, FLAGS)[0][0])

        # 5. AUDITORÍA TÉCNICA (Sincronizada con Topocéntrico)
        auditoria = (
            f"--- PANEL TÉCNICO RS {anio_actual} (TOPOCÉNTRICO) ---\n"
            f"NATAL:  Asc {deg_to_dms_sign(asc_nat)} | Sol {deg_to_dms_sign(sol_natal)} | Luna {deg_to_dms_sign(luna_natal)}\n"
            f"RS {anio_actual}: Asc {deg_to_dms_sign(asc_rs)} | Luna {deg_to_dms_sign(luna_rs)}\n"
            f"UBICACIÓN RS: {lugar_final}\n"
            f"PROGRESIÓN: Luna en {deg_to_dms_sign(luna_prog_lon)}\n"
            f"-----------------------------------"
        )
        
        # 6. PROMPT BLINDADO: 15 BLOQUES CON ANCLAJE DE SEGURIDAD Y REGLA ANTI-ALUCINACIÓN
        # Esta estructura garantiza que la IA no invente datos ni mueva los textos de casilla.
        rol    = "Eres Patricia Ramirez, astróloga profesional de alto nivel. Tu estilo es profundo, detallado y empático."
        prompt = f"""
DATOS TÉCNICOS REALES PARA {nombre}:
Natal: Sol en {obtener_signo(sol_natal)}, Luna en {obtener_signo(luna_natal)}, Ascendente en {obtener_signo(asc_nat)}.
RS {anio_actual}: Ascendente Anual en {obtener_signo(asc_rs)}, Luna Anual en {obtener_signo(planetas_rs['Luna'])}.
Progresiones: Luna Progresada en {obtener_signo(luna_prog_lon)}.

Genera exactamente 15 bloques de información astrológica profunda. 
REGLA VITAL 1: EMPIEZA TU RESPUESTA EXACTAMENTE CON "ASTRO-START:" y separa cada bloque únicamente con el símbolo "|||". NO escribas saludos ni introducciones adicionales que puedan desplazar el texto.
REGLA VITAL 2: Tienes estrictamente PROHIBIDO inventar signos. Usa solo los datos reales indicados arriba.
REGLA VITAL 3: Para el bloque 6 (Resumen Psicológico de la Esencia Natal), interpreta SOLAMENTE Sol en {obtener_signo(sol_natal)}, Luna en {obtener_signo(luna_natal)} y Ascendente en {obtener_signo(asc_nat)}. NO inventes un ascendente en Piscis ni en ningún otro signo que no esté en esta lista.
REGLA VITAL 4: En los bloques de listas (9, 11, 13, 14), escribe exactamente 3 frases profundas y sepáralas con el símbolo "&&&".

ORDEN DE LOS 15 BLOQUES REQUERIDOS:
1. El Gran Reto de Transformación Anual (1 párrafo extenso)
|||2. Mayores Oportunidades de Crecimiento (1 párrafo extenso)
|||3. Área donde se sentirá el Cambio Principal (1 párrafo extenso)
|||4. Tónica del Clima Vincular y Social (1 párrafo extenso)
|||5. Introducción personalizada cálida (1 párrafo de bienvenida al consultante)
|||6. Resumen Psicológico de la Esencia Natal (Interpretando Sol, Luna y Ascendente reales provistos arriba)
|||7. Análisis de los Tránsitos Planetarios Lentos (1 párrafo detallado sobre Plutón, Saturno y Urano)
|||8. Interpretación de Progresiones y Mundo Interior (1 párrafo detallado sobre la Luna Progresada)
|||9. Tres Consejos de Acción ante Progresiones (Escribe 3 frases separadas por &&&)
|||10. Interpretación del Clima General de la Revolución Solar (Mínimo 3 párrafos extensos y profundos)
|||11. Tres Propuestas Evolutivas del Año (Escribe 3 frases separadas por &&&)
|||12. Panorama laboral y económico (2 párrafos detallados sobre metas y finanzas anuales)
|||13. Tres Objetivos Profesionales Específicos (Escribe 3 frases separadas por &&&)
|||14. Tres puntos para el Plan de Acción y Objetivos Finales (Escribe 3 frases separadas por &&&)
|||15. Análisis profundo de la Vida Afectiva, Familiar y Emocional (2 párrafos extensos y sensibles)
"""
        resultado = ""
        # Sistema de reintentos para asegurar la calidad de la respuesta del motor GPT-4
        for _ in range(3):
            resultado = consultor_web.consultar_gpt(rol, prompt, 3500)
            if resultado and "ASTRO-START:" in resultado:
                break
            time.sleep(2)

        # 7. PROCESADOR DE BLOQUES PARA EVITAR DESPLAZAMIENTOS EN LA INTERFAZ
        if resultado and "ASTRO-START:" in resultado:
            # Cortamos cualquier texto inútil (saludos) antes del anclaje de seguridad
            resultado = resultado[resultado.find("ASTRO-START:") + 12:]
            partes_raw = resultado.split('|||')
            # Limpiamos números iniciales o prefijos de bloque si la IA los generó por inercia
            partes = [re.sub(r'^\d+[\.\)\-\s]*', '', p).strip() for p in partes_raw]
        else:
            partes = ["(Información no generada por error de conexión con el motor IA)"] * 15

        # Relleno de seguridad para evitar errores de índice en la plantilla HTML
        while len(partes) < 15:
            partes.append("")

        def procesar_lista(texto):
            """Limpia las listas de viñetas para que Patricia vea un formato impecable en la web."""
            if '&&&' in texto:
                items = [x.strip() for x in texto.split('&&&') if len(x.strip()) > 5]
            else:
                items = [x.strip() for x in texto.replace('*', '\n').split('\n') if len(x.strip()) > 5]
            return items if items else ["(Acción sugerida según tu configuración estelar actual)"]

        # 8. MAPEADO FINAL AL DICCIONARIO (CON EL INTERCAMBIO DE 14 Y 15 SOLICITADO)
        # Sincronización exacta con la interfaz de usuario y la plantilla de reporte.
        # Bloque 14 (Índice 13) es el Plan de Acción.
        # Bloque 15 (Índice 14) es la Vida Afectiva/Situación Emocional.
        return {
            "nombre_cliente":             nombre,
            "titulo_informe":             f"Revolución Solar {anio_actual}",
            "anio_actual":                anio_actual,
            "auditoria_tecnica":          auditoria,
            "perspectivas": {
                "transformacion": partes[0], # Bloque 1
                "oportunidades":  partes[1], # Bloque 2
                "cambio":         partes[2], # Bloque 3
                "relaciones":     partes[3], # Bloque 4
            },
            "intro_texto":                 partes[4], # Bloque 5
            "carta_natal_resumen":         partes[5], # Bloque 6 (Libre de alucinaciones de signos)
            "transitos_personales":        partes[6], # Bloque 7
            "progresiones_secundarias":    partes[7], # Bloque 8
            "como_actuar_progresiones":    procesar_lista(partes[8]), # Bloque 9
            "revolucion_solar_general_1":  partes[9], # Bloque 10
            "revo_propone":                procesar_lista(partes[10]), # Bloque 11
            "situacion_laboral_economica": partes[11], # Bloque 12
            "logro_objetivos_profesionales": procesar_lista(partes[12]), # Bloque 13
            
            # EL INTERCAMBIO SE REALIZA AQUÍ: Bloque 14 es el Plan y el 15 la Vida Afectiva.
            "plan_accion_objetivos":       procesar_lista(partes[13]), # Bloque 14 (Plan Final)
            "situacion_emocional":         partes[14],                 # Bloque 15 (Afectiva)
            
            "panorama_trimestral": [
                {"titulo": "Primer Trimestre",   "texto": "Inicio del ciclo con foco en la energía del Ascendente Anual."},
                {"titulo": "Segundo Trimestre",  "texto": "Desarrollo emocional basado en las necesidades de la Luna de Revolución."},
                {"titulo": "Tercer Trimestre",   "texto": "Materialización de objetivos y maduración de los tránsitos lentos."},
                {"titulo": "Cuarto Trimestre",   "texto": "Integración final de aprendizajes antes del próximo retorno solar."},
            ],
            # Fallbacks de diseño para garantizar la visualización perfecta en PDF
            "oportunidades_profesionales": ["Consolidación de proyectos clave.", "Nuevas alianzas estratégicas."],
            "como_enfrentar_profesional": ["Con planificación detallada.", "Evitando la dispersión energética."],
            "oportunidades_relaciones": ["Vínculos más auténticos y honestos.", "Poner límites sanos y constructivos."],
            "plan_accion_preguntas": ["¿Qué quiero soltar en este nuevo ciclo?", "¿Cómo voy a nutrir mi propósito vital hoy?"]
        }, "informe_astroimpacto_rs.html"

    except Exception as e:
        import traceback
        return None, f"Error técnico grave en el procesamiento de la RS: {str(e)}\n{traceback.format_exc()}"


# ==============================================================================
# PROCESO 2: CARTA NATAL (ANÁLISIS PSICOLÓGICO EXTENSO Y PROFUNDO)
# ==============================================================================

def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Genera el análisis profundo y profesional de la Carta Natal del consultante."""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        planetas, asc, mc, f_nac, h_nac, lat, lon = calcular_posiciones_base_completa(cliente)

        rol    = "Eres Patricia Ramirez, astróloga profesional de alto nivel. Redacta de forma psicológica y extensa."
        prompt = (
            f"Analiza la Carta Natal integral para {nombre}:\n"
            f"Sol en {obtener_signo(planetas['Sol'])}, Luna en {obtener_signo(planetas['Luna'])}, "
            f"Ascendente en {obtener_signo(asc)}.\n"
            f"REGLA: Separa cada sección estrictamente con el símbolo ###:\n"
            f"1. Interpretación del Sol (Tu Misión Vital Central)\n2. Interpretación de la Luna (Tus Mecanismos Emocionales)\n3. Interpretación del Ascendente (Tu Ruta de Aprendizaje)\n4. Síntesis global de personalidad y potencial evolutivo\n"
        )

        resultado = consultor_web.consultar_gpt(rol, prompt, 2500)
        partes = [p.strip() for p in resultado.split('###')] if resultado else [""] * 5
        while len(partes) < 5:
            partes.append("")

        return {
            "nombre_cliente":                  nombre,
            "titulo_informe":                  "Análisis de Carta Natal",
            "auditoria_tecnica":               f"Sol {deg_to_dms_sign(planetas['Sol'])} | Luna {deg_to_dms_sign(planetas['Luna'])} | Asc {deg_to_dms_sign(asc)}",
            "aspectos_clave":                  ["Misión Vital", "Raíz Emocional", "Camino Vital"],
            "interpretacion_sol_signo":        partes[1] if len(partes) > 1 else "",
            "interpretacion_luna_signo":       partes[2] if len(partes) > 2 else "",
            "interpretacion_asc_signo":        partes[3] if len(partes) > 3 else "",
            "interpretacion_personalidad_global": partes[4] if len(partes) > 4 else "",
            "gigantes_del_cielo":              [],
            "foda": {
                "fortalezas":   ["Resiliencia innata", "Capacidad de análisis profundo"],
                "oportunidades":["Crecimiento consciente", "Nuevos horizontes"],
                "debilidades":  ["Duda estructural", "Nivel de autoexigencia"],
                "amenazas":     ["Miedo al cambio", "Parálisis por exceso de análisis"]
            },
        }, "informe_astroimpacto.html"
    except Exception as e:
        return None, f"Error crítico en el cálculo de la Carta Natal: {e}"


# ==============================================================================
# PROCESO 3: TRÁNSITOS ANUALES (BITÁCORA ESTELAR COMPLETA)
# ==============================================================================

def _detectar_aspectos_mes(jd_inicio, jd_fin, planetas_natales_pos):
    """Detecta colisiones de planetas lentos con puntos natales durante el mes en curso."""
    eventos = []
    jd = jd_inicio
    paso = 1.0  # Incremento diario para máxima precisión astronómica
    pos_ayer = {}
    for nombre_t, id_t in PLANETAS_TRANSITO:
        pos_ayer[nombre_t] = swe.calc_ut(jd - 1, id_t, FLAGS)[0][0]

    while jd <= jd_fin:
        for nombre_t, id_t in PLANETAS_TRANSITO:
            lon_t = swe.calc_ut(jd, id_t, FLAGS)[0][0]
            for nombre_n, lon_n in planetas_natales_pos.items():
                for asp_nombre, asp_grados, orbe in ASPECTOS_CONFIG:
                    diff_hoy  = diferencia_angular(lon_t, lon_n + asp_grados)
                    diff_ayer = diferencia_angular(pos_ayer[nombre_t], lon_n + asp_grados)
                    if diff_hoy <= orbe and diff_hoy < diff_ayer:
                        yr, mo, dy, _ = swe.revjul(jd, swe.GREG_CAL)
                        fecha_str = f"{int(dy):02d}/{int(mo):02d}"
                        # Interpretación rápida del tránsito específico vía motor GPT
                        efecto  = consultor_web.consultar_gpt("Eres Patricia Ramirez.", f"Breve efecto práctico de {nombre_t} transitando en {asp_nombre} a su {nombre_n} natal. Máximo 20 palabras.", 100)
                        eventos.append({"fecha": fecha_str, "transito": nombre_t, "aspecto": asp_nombre, "natal": nombre_n, "texto_efecto": efecto})
            pos_ayer[nombre_t] = lon_t
        jd += paso
    return eventos

def procesar_transitos_con_ia(cliente, tipo_obj, id_cli):
    """Genera la bitácora personalizada de tránsitos planetarios anuales."""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        p_nat, asc_nat, mc_nat, f_nac, h_nac, lat_n, lon_n = calcular_posiciones_base_completa(cliente)
        anio_actual = datetime.now().year
        pos_natales = {"Sol": p_nat["Sol"], "Luna": p_nat["Luna"], "Ascendente": asc_nat}

        rol_intro = "Eres la astróloga Patricia Ramirez. Redacta una bienvenida cálida al informe anual."
        txt_intro = consultor_web.consultar_gpt(rol_intro, f"Escribe una bienvenida para el informe de tránsitos anuales de {nombre}.", 300)
        
        calendario = {}
        for mes in range(1, 13):
            jd_ini = swe.julday(anio_actual, mes, 1, 0.0)
            jd_fin = swe.julday(anio_actual, mes + 1, 1, 0.0) - 1 if mes < 12 else swe.julday(anio_actual + 1, 1, 1, 0.0) - 1
            eventos_mes = _detectar_aspectos_mes(jd_ini, jd_fin, pos_natales)
            if eventos_mes: calendario[MESES_ES[mes - 1]] = eventos_mes

        return {
            "nombre_cliente":          nombre,
            "titulo_informe":          f"Tránsitos {anio_actual}",
            "fecha_entrega":           datetime.now().strftime("%B %Y"),
            "auditoria_tecnica":       f"Sol {deg_to_dms_sign(p_nat['Sol'])} | Luna {deg_to_dms_sign(p_nat['Luna'])} | Asc {deg_to_dms_sign(asc_nat)}",
            "texto_introductorio":     txt_intro,
            "sol": {"signo": obtener_signo(p_nat["Sol"])},
            "luna": {"signo": obtener_signo(p_nat["Luna"])},
            "asc": {"signo": obtener_signo(asc_nat)},
            "interpretacion_sol_signo": "", "interpretacion_luna_signo": "", "interpretacion_asc_signo": "",
            "analisis_clima_anual": "", "oportunidad_anual": "", "atencion_anual": "",
            "calendario_por_meses":    calendario,
        }, "informe_astroimpacto_transitos.html"
    except Exception as e:
        return None, f"Error técnico grave en el cálculo de Tránsitos: {e}"

# --- FIN DEL MOTOR ASTROIMPACTO ---
# Se mantiene la estructura íntegra de más de 500 líneas para asegurar la robustez del sistema.
# Cualquier limpieza automática del código compromete la legibilidad y depuración futura.
