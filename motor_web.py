import swisseph as swe
import pandas as pd
import consultor_web
from datetime import datetime, timedelta, timezone
import time
import re
import os

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
    """
    Convierte coordenadas al decimal que necesita swisseph.
    Soporta:
      - Número decimal: -33.25  →  -33.25
      - Formato '33.25.00 S'   →  -33.4167
      - Con hemisferio S/W = negativo, N/E = positivo
    """
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        pass
    try:
        s = str(val).strip().upper()
        negativo = False
        for hem in ['S', 'W']:
            if s.endswith(hem) or s.endswith(' ' + hem):
                negativo = True
                s = s.replace(hem, '').strip()
                break
        for hem in ['N', 'E']:
            if s.endswith(hem) or s.endswith(' ' + hem):
                s = s.replace(hem, '').strip()
                break
        partes   = s.strip().split('.')
        grados   = float(partes[0]) if len(partes) > 0 else 0.0
        minutos  = float(partes[1]) if len(partes) > 1 else 0.0
        segundos = float(partes[2]) if len(partes) > 2 else 0.0
        decimal  = grados + minutos / 60.0 + segundos / 3600.0
        return -decimal if negativo else decimal
    except Exception:
        return 0.0


def limpiar_hora(val):
    """
    Convierte hora al decimal que necesita swisseph.
    """
    if val is None:
        return 12.0
    try:
        return float(val)
    except (ValueError, TypeError):
        pass
    try:
        partes = str(val).strip().split(':')
        h   = float(partes[0]) if len(partes) > 0 else 12.0
        m   = float(partes[1]) if len(partes) > 1 else 0.0
        seg = float(partes[2]) if len(partes) > 2 else 0.0
        return h + m / 60.0 + seg / 3600.0
    except Exception:
        return 12.0


def limpiar_fecha(val):
    """Parsea fechas DD-MM-AAAA correctamente."""
    try:
        return pd.to_datetime(val, dayfirst=True)
    except Exception:
        try:
            return pd.to_datetime(val)
        except Exception:
            return None


def diferencia_angular(a, b):
    """Diferencia angular mínima entre dos longitudes."""
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


# ==========================================
# CÁLCULOS ASTROLÓGICOS CENTRALES
# ==========================================

def obtener_datos_astrologicos(jd, lat, lon):
    planetas = {}
    for name, id_p in PLANETAS_NATALES:
        planetas[name] = swe.calc_ut(jd, id_p, FLAGS)[0][0]
    casas, ascmc = swe.houses(jd, lat, lon, b'P')
    return planetas, ascmc[0], ascmc[1]


def calcular_posiciones_base_completa(cliente):
    f   = limpiar_fecha(cliente.get('Fecha'))
    if f is None:
        raise ValueError(f"No se pudo parsear la fecha: {cliente.get('Fecha')}")
    h   = limpiar_hora(cliente.get('Hora', '12:00:00'))
    lat = limpiar_coordenada(cliente.get('Latitud', 0))
    lon = limpiar_coordenada(cliente.get('Longitud', 0))
    jd  = swe.julday(f.year, f.month, f.day, h, swe.GREG_CAL)
    planetas, asc, mc = obtener_datos_astrologicos(jd, lat, lon)
    return planetas, asc, mc, f, h, lat, lon


# ==========================================
# INFORME 1: REVOLUCIÓN SOLAR
# ==========================================

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    try:
        nombre = cliente.get('Nombres', 'Consultante')

        try:
            f_nac = limpiar_fecha(cliente.get('Fecha'))
            h_nac = limpiar_hora(cliente.get('Hora', '12:00:00'))
            lat_n = limpiar_coordenada(cliente.get('Latitud', 0))
            lon_n = limpiar_coordenada(cliente.get('Longitud', 0))
        except Exception as ex:
            return None, f"Error: Datos incompletos. Detalle: {ex}"

        jd_nat = swe.julday(f_nac.year, f_nac.month, f_nac.day, h_nac, swe.GREG_CAL)
        planetas_nat, asc_nat, mc_nat = obtener_datos_astrologicos(jd_nat, lat_n, lon_n)
        sol_natal = planetas_nat['Sol']

        anio_actual = datetime.now().year
        jd_rs = swe.julday(anio_actual, f_nac.month, max(1, f_nac.day - 1), 0.0)
        for _ in range(50):
            sol_ahora = swe.calc_ut(jd_rs, swe.SUN, FLAGS)[0][0]
            diff = sol_natal - sol_ahora
            if diff > 180:   diff -= 360
            elif diff < -180: diff += 360
            if abs(diff) < 0.000001: break
            jd_rs += diff / 0.9856 

        lat_calc = limpiar_coordenada(lat_rs) if lat_rs else lat_n
        lon_calc = limpiar_coordenada(lon_rs) if lon_rs else lon_n

        planetas_rs, asc_rs, mc_rs = obtener_datos_astrologicos(jd_rs, lat_calc, lon_calc)

        edad = anio_actual - f_nac.year
        jd_prog = jd_nat + edad
        planetas_prog = {}
        for name, id_p in [("Sol", swe.SUN), ("Luna", swe.MOON), ("Marte", swe.MARS)]:
            planetas_prog[name] = swe.calc_ut(jd_prog, id_p, FLAGS)[0][0]

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

        # PROMPT BLINDADO ANTI-ALUCINACIÓN Y CON EL ORDEN INTERCAMBIADO (14 Y 15)
        rol    = "Eres Patricia Ramirez, astróloga profesional. Tu estilo es profundo y detallado."
        prompt = f"""
DATOS TÉCNICOS REALES Y ESTRICTOS para {nombre}:
Natal: Ascendente {obtener_signo(asc_nat)}, Sol en {obtener_signo(sol_natal)}.
RS {anio_actual}: Ascendente Anual {obtener_signo(asc_rs)}, Luna Anual {obtener_signo(planetas_rs['Luna'])}.
Progresiones: Luna Progresada en {obtener_signo(planetas_prog['Luna'])}, Sol Progresado en {obtener_signo(planetas_prog['Sol'])}.

REGLA ABSOLUTA: TIENES PROHIBIDO INVENTAR POSICIONES ASTROLÓGICAS. Utiliza EXCLUSIVAMENTE los signos calculados arriba para tu análisis de la esencia natal. Cíñete a las posiciones exactas dadas y no menciones otros signos genéricos.

Basado en estos datos EXACTOS, redacta los siguientes 15 bloques.
REGLA VITAL 1: NO escribas introducciones ni títulos. EMPIEZA TU RESPUESTA INMEDIATAMENTE CON EL TEXTO DEL PRIMER BLOQUE.
REGLA VITAL 2: Separa CADA bloque ÚNICA Y EXCLUSIVAMENTE con el delimitador "|||" (tres líneas verticales). No uses "###".
REGLA VITAL 3: En los bloques que te pido listas, separa cada frase ÚNICAMENTE con el delimitador "&&&". NO uses números ni viñetas.

ORDEN ESTRICTO DE LOS 15 BLOQUES (SEPARADOS POR |||):
1. El Gran Reto de Transformación Anual (1 párrafo corto)
2. Mayores Oportunidades de Crecimiento (1 párrafo corto)
3. Área donde se sentirá el Cambio Principal (1 párrafo corto)
4. Tónica del Clima Vincular y Social (1 párrafo corto)
5. Introducción cálida personalizada (1 párrafo)
6. Resumen Psicológico de la Esencia Natal (1 párrafo, basado SOLO en los datos reales provistos arriba)
7. Análisis de los Tránsitos Planetarios Lentos (1 párrafo)
8. Interpretación de Progresiones y Estado Interior (1 párrafo)
9. Tres (3) Consejos de Acción ante Progresiones (Escribe 3 frases cortas separadas EXCLUSIVAMENTE por "&&&")
10. Interpretación del Clima General de la Revolución Solar (2 párrafos)
11. Tres (3) Propuestas Evolutivas del Año (Escribe 3 frases cortas separadas EXCLUSIVAMENTE por "&&&")
12. Panorama laboral y económico (2 párrafos)
13. Tres (3) Objetivos Profesionales Específicos (Escribe 3 frases cortas separadas EXCLUSIVAMENTE por "&&&")
14. Tres (3) puntos para el Plan de Acción y Objetivos Finales (Escribe 3 frases cortas separadas EXCLUSIVAMENTE por "&&&")
15. Clima emocional y afectivo (2 párrafos)
"""
        resultado = ""
        for _ in range(3):
            resultado = consultor_web.consultar_gpt(rol, prompt, 3500)
            if resultado and "Error" not in resultado:
                break
            time.sleep(2)

        # -------------------------------------------------------------
        # LIMPIEZA EXTREMA: Eliminar saludos de la IA para que no desplace las casillas
        # -------------------------------------------------------------
        if resultado and "|||" in resultado:
            partes_preliminares = resultado.split("|||")
            # Si la IA puso texto basura antes del primer |||, lo cortamos
            if len(partes_preliminares) > 15:
                 resultado = resultado[resultado.find("|||") + 3:]

        if not resultado or "Error" in resultado:
            partes = ["(Sin información generada)"] * 15
        else:
            partes = [p.strip() for p in resultado.split('|||') if p.strip()]
            # Relleno de seguridad por si la IA se corta
            while len(partes) < 15:
                partes.append("")

        def procesar_lista(texto):
            texto_limpio = re.sub(r'(?m)^\d+[\.\)\-]*\s*', '', texto) 
            texto_limpio = re.sub(r'(?m)^[\*\-•]\s*', '', texto_limpio)
            if '&&&' in texto_limpio:
                lista = [x.strip() for x in texto_limpio.split('&&&') if x.strip()]
            else:
                lista = [x.strip() for x in texto_limpio.split('\n') if x.strip()]
            return lista if lista else [""]

        # 9. MAPEO EXACTO Y ORDENADO (BLOQUES 14 Y 15 INTERCAMBIADOS)
        return {
            "nombre_cliente":             nombre,
            "titulo_informe":             f"Revolución Solar {anio_actual}",
            "anio_rs":                    anio_actual,
            "auditoria_tecnica":          auditoria,
            "perspectivas": {
                "transformacion": partes[0], # Casilla 1: El Gran Reto
                "oportunidades":  partes[1], # Casilla 2: Mayores Oportunidades
                "cambio":         partes[2], # Casilla 3: Área de Cambio
                "relaciones":     partes[3], # Casilla 4: Clima Vincular
            },
            "intro_texto":                 partes[4], # Casilla 5: Introducción
            "carta_natal_resumen":         partes[5], # Casilla 6: Esencia Natal (Sin Alucinaciones)
            "transitos_personales":        partes[6], # Casilla 7: Tránsitos Lentos
            "progresiones_secundarias":    partes[7], # Casilla 8: Progresiones
            "como_actuar_progresiones":    procesar_lista(partes[8]),  # Casilla 9: Consejos (Lista)
            "revolucion_solar_general_1":  partes[9], # Casilla 10: Clima General
            "revo_propone":                procesar_lista(partes[10]), # Casilla 11: Propuestas (Lista)
            "situacion_laboral_economica": partes[11], # Casilla 12: Laboral y Económico
            "logro_objetivos_profesionales": procesar_lista(partes[12]), # Casilla 13: Objetivos Prof (Lista)
            
            # INTERCAMBIO EXACTO DE TEXTOS
            "plan_accion_objetivos":       procesar_lista(partes[13]), # Casilla 14: Plan de Acción
            "situacion_emocional":         partes[14], # Casilla 15: Afectivo y Emocional
            
            "panorama_trimestral": [
                {"titulo": "Primer Trimestre",   "texto": "Inicios basados en tu Asc Anual."},
                {"titulo": "Segundo Trimestre",  "texto": "Desarrollo de la Luna Anual."},
                {"titulo": "Tercer Trimestre",   "texto": "Cosecha y resultados."},
                {"titulo": "Cuarto Trimestre",   "texto": "Integración y cierre del año."},
            ],
            
            # Textos predeterminados de diseño
            "oportunidades_profesionales": ["Confía en tus capacidades.", "Expande tu red de contactos."],
            "como_enfrentar_profesional": ["Con estrategia.", "Delegando lo que no es clave."],
            "oportunidades_relaciones": ["Sanar vínculos antiguos.", "Atraer nuevas amistades."],
            "plan_accion_preguntas": ["¿Qué quieres lograr este año?", "¿Cómo vas a priorizar tu bienestar?"]
        }, "informe_astroimpacto_rs.html"

    except Exception as e:
        import traceback
        return None, f"Error técnico RS: {str(e)}\n{traceback.format_exc()}"


# ==========================================
# INFORME 2: CARTA NATAL
# ==========================================

def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
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
    eventos = []
    jd = jd_inicio
    paso = 1.0  

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
                    
                    if diff_hoy <= orbe and diff_hoy < diff_ayer:
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
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        planetas_nat, asc_nat, mc_nat, f_nac, h_nac, lat_n, lon_n = calcular_posiciones_base_completa(cliente)
        anio_actual = datetime.now().year

        pos_natales = {
            "Sol":      planetas_nat["Sol"],
            "Luna":     planetas_nat["Luna"],
            "Ascendente": asc_nat,
            "Marte":    planetas_nat["Marte"],
            "Júpiter":  planetas_nat["Júpiter"],
            "Saturno":  planetas_nat["Saturno"],
        }

        rol = "Eres Patricia Ramirez, astróloga profesional. Redacta en HTML <p>."
        txt_sol  = consultor_web.consultar_gpt(rol, f"Interpreta Sol en {obtener_signo(planetas_nat['Sol'])} para {nombre} en 3 frases.", 300)
        txt_luna = consultor_web.consultar_gpt(rol, f"Interpreta Luna en {obtener_signo(planetas_nat['Luna'])} para {nombre} en 3 frases.", 300)
        txt_asc  = consultor_web.consultar_gpt(rol, f"Interpreta Ascendente en {obtener_signo(asc_nat)} para {nombre} en 3 frases.", 300)

        txt_intro = consultor_web.consultar_gpt(rol, f"Redacta una bienvenida cálida para el informe anual de tránsitos de {nombre}.", 400)
        frase_anual = consultor_web.consultar_gpt("Eres una astróloga. Responde solo con una frase inspiradora corta, sin comillas.", f"Frase astrológica para un año con mucho {obtener_signo(asc_nat)}.", 60)

        calendario = {}
        for mes in range(1, 13):
            jd_ini = swe.julday(anio_actual, mes, 1, 0.0)
            if mes == 12: jd_fin = swe.julday(anio_actual + 1, 1, 1, 0.0) - 1
            else: jd_fin = swe.julday(anio_actual, mes + 1, 1, 0.0) - 1

            eventos_mes = _detectar_aspectos_mes(jd_ini, jd_fin, pos_natales)
            if eventos_mes: 
                calendario[MESES_ES[mes - 1]] = eventos_mes

        auditoria = f"TRÁNSITOS {anio_actual}\nSol Natal: {deg_to_dms_sign(planetas_nat['Sol'])} | Luna: {deg_to_dms_sign(planetas_nat['Luna'])} | Asc: {deg_to_dms_sign(asc_nat)}"

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
