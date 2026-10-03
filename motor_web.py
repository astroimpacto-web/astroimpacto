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
swe.set_ephe_path('')
FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

# Sistema de casas: b'T' = Topocéntrico (Polich-Page). (Antes era b'P' = Placidus.)
# Nota: Ascendente y MC son iguales en todos los sistemas; el sistema solo
# cambia las cúspides intermedias (casas 2, 3, 5, 6, 8, 9, 11, 12).
SISTEMA_CASAS = b'T'
NOMBRE_SISTEMA_CASAS = "Topocéntrico (Polich-Page)"

PLANETAS_TRANSITO = [
    ("Júpiter", swe.JUPITER),
    ("Saturno", swe.SATURN),
    ("Urano", swe.URANUS),
    ("Neptuno", swe.NEPTUNE),
    ("Plutón", swe.PLUTO),
]

PLANETAS_NATALES = [
    ("Sol", swe.SUN),
    ("Luna", swe.MOON),
    ("Mercurio", swe.MERCURY),
    ("Venus", swe.VENUS),
    ("Marte", swe.MARS),
    ("Júpiter", swe.JUPITER),
    ("Saturno", swe.SATURN),
]

ASPECTOS_CONFIG = [
    ("Conjunción", 0, 7),
    ("Sextil", 60, 5),
    ("Cuadratura", 90, 7),
    ("Trígono", 120, 7),
    ("Oposición", 180, 7),
]

MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# ==============================================================================
# FUNCIONES DE FORMATEO Y CONVERSIÓN TÉCNICA (BLOQUE DE UTILIDADES)
# ==============================================================================
def obtener_signo(lon):
    """Determina el signo zodiacal (30° por signo)."""
    signos = ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"]
    return signos[int(lon / 30) % 12]

def deg_to_dms_sign(lon):
    """Formatea la longitud para la auditoría técnica."""
    signos = ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"]
    signo_idx = int(lon / 30) % 12
    grados, minutos = int(lon % 30), int((lon % 1) * 60)
    return f"{grados:02d}° {signos[signo_idx]} {minutos:02d}'"

def hora_decimal_a_hms(h):
    """Convierte horas decimales a 'HH:MM:SS' para mostrar en la auditoría."""
    total = int(round(h * 3600))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"

def _vacio(v):
    """True si el valor está vacío (None, NaN, pd.NA o texto en blanco)."""
    if v is None:
        return True
    if not isinstance(v, str):
        try:
            if pd.isna(v):
                return True
        except (TypeError, ValueError):
            pass
    return str(v).strip() == ""

def limpiar_hora_precisa(val):
    """Convierte horas de Excel/Drive a decimal (versión tolerante: devuelve 0.0 si falla)."""
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.0
        if hasattr(val, 'hour'): return val.hour + val.minute/60.0 + val.second/3600.0
        v = str(val).strip()
        if ':' in v:
            p = v.split(':')
            h = float(p[0])
            m = float(p[1]) if len(p) > 1 else 0.0
            s = float(p[2]) if len(p) > 2 else 0.0
            return h + m/60.0 + s/3600.0
        return float(v.replace(',', '.'))
    except: return 0.0

def limpiar_hora(val):
    """Alias para mantener compatibilidad con llamadas internas del código."""
    return limpiar_hora_precisa(val)

def hora_a_decimal(valor):
    """Versión ESTRICTA: convierte 'H:MM:SS' (o decimal) a horas decimales.
    Lanza ValueError si el dato falta o es inválido (nunca devuelve 0.0 en silencio)."""
    if _vacio(valor):
        raise ValueError("hora vacía")
    if hasattr(valor, 'hour'):
        return valor.hour + valor.minute / 60.0 + valor.second / 3600.0
    v = str(valor).strip().replace(',', '.')
    if ':' in v:
        p = v.split(':')
        h = float(p[0])
        m = float(p[1]) if len(p) > 1 else 0.0
        s = float(p[2]) if len(p) > 2 else 0.0
        if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60):
            raise ValueError(f"hora fuera de rango: {valor!r}")
        return h + m / 60.0 + s / 3600.0
    h = float(v)
    if not (0 <= h < 24):
        raise ValueError(f"hora fuera de rango: {valor!r}")
    return h

def gmt_a_horas(valor):
    """Convierte la columna Gmt ('4:00:00', '-3:30', '4') a horas decimales.
    Convención de tu hoja: Hora_UT = Hora local + Gmt (Chile en invierno = 4:00:00)."""
    if _vacio(valor):
        raise ValueError("Gmt vacío")
    v = str(valor).strip().replace(',', '.')
    signo = -1.0 if v.startswith('-') else 1.0
    v = v.lstrip('+-')
    p = v.split(':')
    h = float(p[0])
    m = float(p[1]) if len(p) > 1 else 0.0
    s = float(p[2]) if len(p) > 2 else 0.0
    return signo * (h + m / 60.0 + s / 3600.0)

def limpiar_fecha(valor):
    """Convierte fechas de la hoja SIEMPRE en formato día-mes-año (dd-mm-aaaa).
    También acepta aaaa-mm-dd y objetos fecha. Lanza ValueError si no es válida
    (antes devolvía la fecha de hoy en silencio)."""
    if _vacio(valor):
        raise ValueError("fecha vacía")
    if isinstance(valor, (datetime, pd.Timestamp)):
        return datetime(valor.year, valor.month, valor.day)
    txt = str(valor).strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", txt)          # ISO: aaaa-mm-dd
    if m:
        y, mo, d = map(int, m.groups())
        return datetime(y, mo, d)
    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", txt)   # dd-mm-aaaa
    if m:
        d, mo, y = map(int, m.groups())
        return datetime(y, mo, d)
    raise ValueError(f"formato de fecha no reconocido: {valor!r} (usa dd-mm-aaaa)")

def parsear_fecha_excel(valor):
    """Alias de compatibilidad."""
    return limpiar_fecha(valor)

def limpiar_coordenada_dms(valor):
    """Soporta formato 34.34.00 S, decimales y grados/minutos."""
    if valor is None or str(valor).strip() == "": return 0.0
    if isinstance(valor, (float, int)): return float(valor)
    try:
        v = str(valor).upper().strip()
        negativo = any(h in v for h in ['S', 'W', '-'])
        v_clean = re.sub(r"[^\d\.]", " ", v).strip()
        if v_clean.count('.') == 2:
            p = v_clean.split('.')
            res = float(p[0]) + float(p[1])/60.0 + float(p[2])/3600.0
        elif v_clean.count('.') == 1 and " " not in v_clean:
            res = float(v_clean)
        else:
            partes = v_clean.split()
            res = float(partes[0]) if len(partes) > 0 else 0.0
            if len(partes) > 1: res += float(partes[1])/60.0
            if len(partes) > 2: res += float(partes[2])/3600.0
        return -res if negativo else res
    except: return 0.0

def limpiar_coordenada(valor):
    """Alias para mantener compatibilidad con llamadas internas del código."""
    return limpiar_coordenada_dms(valor)

def diferencia_angular(a, b):
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d

# ==============================================================================
# MOMENTO DE NACIMIENTO EN UT (CORRECCIÓN CLAVE)
# ==============================================================================
def momento_ut(cliente):
    """Devuelve (fecha_ut: datetime, hora_ut: float, origen: str).

    Prioridad:
      1. Fecha_UT y Hora_UT de la hoja (ya convertidas a Tiempo Universal).
      2. Si faltan, se calculan desde Fecha + Hora local + Gmt.
    Si no hay datos suficientes lanza ValueError (no se calcula con datos a medias).
    """
    f_ut, h_ut = cliente.get('Fecha_UT'), cliente.get('Hora_UT')
    if not _vacio(f_ut) and not _vacio(h_ut):
        return limpiar_fecha(f_ut), hora_a_decimal(h_ut), "Fecha_UT / Hora_UT"

    f_loc, h_loc, gmt = cliente.get('Fecha'), cliente.get('Hora'), cliente.get('Gmt')
    if not _vacio(f_loc) and not _vacio(h_loc) and not _vacio(gmt):
        local = limpiar_fecha(f_loc) + timedelta(hours=hora_a_decimal(h_loc))
        ut = local + timedelta(hours=gmt_a_horas(gmt))
        fecha = datetime(ut.year, ut.month, ut.day)
        hora = ut.hour + ut.minute / 60.0 + ut.second / 3600.0
        return fecha, hora, "Fecha + Hora local + Gmt"

    raise ValueError("Faltan datos de nacimiento: se necesita Fecha_UT y Hora_UT, "
                     "o bien Fecha, Hora y Gmt.")

def verificar_consistencia_ut(cliente, tolerancia_min=2):
    """Compara Fecha_UT/Hora_UT contra Fecha + Hora + Gmt.
    Devuelve un texto de advertencia, o None si todo calza (o no se puede comparar)."""
    claves = ('Fecha_UT', 'Hora_UT', 'Fecha', 'Hora', 'Gmt')
    if any(_vacio(cliente.get(k)) for k in claves):
        return None
    try:
        ut_hoja = limpiar_fecha(cliente['Fecha_UT']) + timedelta(hours=hora_a_decimal(cliente['Hora_UT']))
        local = limpiar_fecha(cliente['Fecha']) + timedelta(hours=hora_a_decimal(cliente['Hora']))
        esperado = local + timedelta(hours=gmt_a_horas(cliente['Gmt']))
        dif = abs((ut_hoja - esperado).total_seconds()) / 60.0
        if dif > tolerancia_min:
            return (f"Fecha_UT/Hora_UT ({ut_hoja:%d-%m-%Y %H:%M}) no coincide con "
                    f"Fecha + Hora + Gmt ({esperado:%d-%m-%Y %H:%M}). Revisa la hoja.")
    except ValueError as e:
        return f"Dato inválido en la hoja: {e}"
    return None

# ==============================================================================
# CÁLCULOS ASTROLÓGICOS CENTRALES
# ==============================================================================
def obtener_datos_astrologicos(jd, lat, lon):
    """
    Realiza la consulta de efemérides. Forzamos float para evitar el error
    técnico del motor de casas en el servidor. Extrae los valores puros de las tuplas.
    """
    try:
        planetas = {}
        for name, id_p in PLANETAS_NATALES:
            # swe.calc_ut devuelve una tupla, [0][0] extrae la longitud eclíptica (float)
            planetas[name] = float(swe.calc_ut(float(jd), id_p, FLAGS)[0][0])
        # Sistema de casas configurable (b'T' = Topocéntrico). lat/lon como floats puros.
        casas, ascmc = swe.houses(float(jd), float(lat), float(lon), SISTEMA_CASAS)
        return planetas, float(ascmc[0]), float(ascmc[1])
    except Exception as e:
        raise ValueError(f"Error en motor de casas: {e}")

def calcular_posiciones_base(cliente):
    """
    Genera el set de 7 valores fundamentales (planetas, asc, mc, f, h, lat, lon).
    IMPORTANTE: 'f' y 'h' son SIEMPRE fecha y hora en Tiempo Universal (UT).
    """
    f, h, _origen = momento_ut(cliente)
    lat = limpiar_coordenada(cliente.get('Latitud', 0))
    lon = limpiar_coordenada(cliente.get('Longitud', 0))
    # Usamos GREG_CAL para máxima precisión histórica
    jd = swe.julday(f.year, f.month, f.day, h, swe.GREG_CAL)
    planetas, asc, mc = obtener_datos_astrologicos(jd, lat, lon)
    return planetas, asc, mc, f, h, lat, lon

# ==============================================================================
# PROCESO 1: REVOLUCIÓN SOLAR (ESTRUCTURA DE 15 BLOQUES SIN RECORTES)
# ==============================================================================
def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    try:
        planetas_nat, asc_nat, mc_nat, fecha_nac, hora_nac, lat_nat, lon_nat = calcular_posiciones_base(cliente)
        nombre = cliente.get('Nombres', 'Consultante')
        sol_natal = planetas_nat['Sol']
        luna_natal = planetas_nat['Luna']
        anio_actual = datetime.now().year

        jd_rs = swe.julday(anio_actual, fecha_nac.month, max(1, fecha_nac.day - 1), 0.0, swe.GREG_CAL)
        for _ in range(50):
            sol_ahora = swe.calc_ut(jd_rs, swe.SUN, FLAGS)[0][0]
            diff = sol_natal - sol_ahora
            if diff > 180: diff -= 360
            elif diff < -180: diff += 360
            if abs(diff) < 0.000001: break
            jd_rs += diff / 0.9856

        lat_calc = limpiar_coordenada(lat_rs) if lat_rs else lat_nat
        lon_calc = limpiar_coordenada(lon_rs) if lon_rs else lon_nat
        lugar_final = lugar_rs if lugar_rs else "Ubicación natal"

        planetas_rs, asc_rs, mc_rs = obtener_datos_astrologicos(jd_rs, lat_calc, lon_calc)
        luna_rs = planetas_rs['Luna']

        # Progresión secundaria (un día = un año), calculada por fechas reales:
        # días transcurridos entre el nacimiento y la RS, divididos por la duración del año.
        jd_nat = swe.julday(fecha_nac.year, fecha_nac.month, fecha_nac.day, hora_nac, swe.GREG_CAL)
        jd_prog = jd_nat + (jd_rs - jd_nat) / 365.2422
        luna_prog_lon = float(swe.calc_ut(jd_prog, swe.MOON, FLAGS)[0][0])

        auditoria = (
            f"--- PANEL TÉCNICO RS {anio_actual} ---\n"
            f"NACIMIENTO UT: {fecha_nac:%d-%m-%Y} {hora_decimal_a_hms(hora_nac)} | Lat {lat_nat:.4f} | Lon {lon_nat:.4f}\n"
            f"CASAS: {NOMBRE_SISTEMA_CASAS}\n"
            f"NATAL: Asc {deg_to_dms_sign(asc_nat)} | Sol {deg_to_dms_sign(sol_natal)} | Luna {deg_to_dms_sign(luna_natal)}\n"
            f"RS {anio_actual}: Asc {deg_to_dms_sign(asc_rs)} | Luna {deg_to_dms_sign(luna_rs)}\n"
            f"UBICACIÓN RS: {lugar_final}\n"
            f"PROGRESIÓN: Luna en {deg_to_dms_sign(luna_prog_lon)}\n"
            f"-----------------------------------"
        )

        rol = "Eres Patricia Ramirez, astróloga profesional de alto nivel. Tu estilo es profundo, detallado y empático."
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
        for _ in range(3):
            resultado = consultor_web.consultar_gpt(rol, prompt, 3500)
            if resultado and "ASTRO-START:" in resultado:
                break
            time.sleep(2)

        if resultado and "ASTRO-START:" in resultado:
            resultado = resultado[resultado.find("ASTRO-START:") + 12:]
            partes_raw = resultado.split('|||')
            partes = [re.sub(r'^\d+[\.\)\-\s]*', '', p).strip() for p in partes_raw]
        else:
            partes = ["(Información no generada por error de conexión con el motor IA)"] * 15

        while len(partes) < 16:
            partes.append("")

        def procesar_lista(texto):
            if '&&&' in texto:
                items = [x.strip() for x in texto.split('&&&') if len(x.strip()) > 5]
            else:
                items = [x.strip() for x in texto.replace('*', '\n').split('\n') if len(x.strip()) > 5]
            return items if items else ["(Acción sugerida según tu configuración estelar actual)"]

        return {
            "nombre_cliente": nombre,
            "titulo_informe": f"Revolución Solar {anio_actual}",
            "anio_actual": anio_actual,
            "auditoria_tecnica": auditoria,
            "perspectivas": {
                "transformacion": partes[0],
                "oportunidades": partes[1],
                "cambio": partes[2],
                "relaciones": partes[3]
            },
            "intro_texto": partes[4],
            "carta_natal_resumen": partes[5],
            "transitos_personales": partes[6],
            "progresiones_secundarias": partes[7],
            "como_actuar_progresiones": procesar_lista(partes[8]),
            "revolucion_solar_general_1": partes[9],
            "revo_propone": procesar_lista(partes[10]),
            # --- ASIGNACIÓN EXACTA AL ORDEN DEL PROMPT ---
            "situacion_laboral_economica": partes[11],
            "logro_objetivos_profesionales": procesar_lista(partes[12]),
            "plan_accion_objetivos": procesar_lista(partes[13]),
            "situacion_emocional": partes[14],
            # -----------------------------------------------------------
            "panorama_trimestral": [
                {"titulo": "Primer Trimestre", "texto": "Inicio del ciclo con foco en la energía del Ascendente Anual."},
                {"titulo": "Segundo Trimestre", "texto": "Desarrollo emocional basado en las necesidades de la Luna de Revolución."},
                {"titulo": "Tercer Trimestre", "texto": "Materialización de objetivos y maduración de los tránsitos lentos."},
                {"titulo": "Cuarto Trimestre", "texto": "Integración final de aprendizajes antes del próximo retorno solar."},
            ],
            "oportunidades_profesionales": ["Consolidación de proyectos clave.", "Nuevas alianzas estratégicas."],
            "como_enfrentar_profesional": ["Con planificación detallada.", "Evitando la dispersión energética."],
            "oportunidades_relaciones": ["Vínculos más auténticos y honestos.", "Poner límites sanos y constructivos."],
            "plan_accion_preguntas": ["¿Qué quiero soltar en este nuevo ciclo?", "¿Cómo voy a nutrir mi propósito vital hoy?"]
        }, "informe_astroimpacto_rs.html"
    except Exception as e:
        return None, f"Error técnico grave en el procesamiento de la RS: {str(e)}\n{traceback.format_exc()}"

# ==============================================================================
# PROCESO 2: CARTA NATAL (ANÁLISIS PSICOLÓGICO EXTENSO Y PROFUNDO)
# ==============================================================================
def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Genera el análisis profundo y profesional de la Carta Natal del consultante."""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        planetas, asc, mc, f_nac, h_nac, lat, lon = calcular_posiciones_base(cliente)
        rol = "Eres Patricia Ramirez, astróloga profesional de alto nivel. Redacta de forma psicológica y extensa."
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
            "nombre_cliente": nombre,
            "sol": partes[0],
            "luna": partes[1],
            "ascendente": partes[2],
            "global": partes[3]
        }, "informe_astroimpacto.html"
    except Exception as e:
        return None, f"Error técnico grave en el procesamiento de Natal: {str(e)}\n{traceback.format_exc()}"

# ==============================================================================
# PROCESO 3: TRÁNSITOS ANUALES (BITÁCORA ESTELAR COMPLETA)
# ==============================================================================
def _detectar_aspectos_mes(jd_inicio, jd_fin, planetas_natales_pos):
    """Detecta colisiones de planetas lentos con puntos natales durante el mes en curso."""
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
                    diff_hoy = diferencia_angular(lon_t, lon_n + asp_grados)
                    diff_ayer = diferencia_angular(pos_ayer[nombre_t], lon_n + asp_grados)
                    if diff_hoy <= orbe and diff_hoy < diff_ayer:
                        yr, mo, dy, _ = swe.revjul(jd, swe.GREG_CAL)
                        fecha_str = f"{int(dy):02d}/{int(mo):02d}"
                        efecto = consultor_web.consultar_gpt("Eres Patricia Ramirez.", f"Breve efecto práctico de {nombre_t} transitando en {asp_nombre} a su {nombre_n} natal. Máximo 20 palabras.", 100)
                        eventos.append({"fecha": fecha_str, "transito": nombre_t, "aspecto": asp_nombre, "natal": nombre_n, "texto_efecto": efecto})
            pos_ayer[nombre_t] = lon_t
        jd += paso
    return eventos

def procesar_transitos_con_ia(cliente, tipo_obj, id_cli):
    """Genera la bitácora personalizada de tránsitos planetarios anuales."""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        p_nat, asc_nat, mc_nat, f_nac, h_nac, lat_n, lon_n = calcular_posiciones_base(cliente)
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
            "nombre_cliente": nombre,
            "titulo_informe": f"Tránsitos {anio_actual}",
            "fecha_entrega": datetime.now().strftime("%B %Y"),
            "auditoria_tecnica": f"Sol {deg_to_dms_sign(p_nat['Sol'])} | Luna {deg_to_dms_sign(p_nat['Luna'])} | Asc {deg_to_dms_sign(asc_nat)}",
            "texto_introductorio": txt_intro,
            "sol": {"signo": obtener_signo(p_nat["Sol"])},
            "luna": {"signo": obtener_signo(p_nat["Luna"])},
            "asc": {"signo": obtener_signo(asc_nat)},
            "interpretacion_sol_signo": "", "interpretacion_luna_signo": "", "interpretacion_asc_signo": "",
            "analisis_clima_anual": "", "oportunidad_anual": "", "atencion_anual": "",
            "calendario_por_meses": calendario,
        }, "informe_astroimpacto_transitos.html"
    except Exception as e:
        return None, f"Error técnico grave en el cálculo de Tránsitos: {str(e)}\n{traceback.format_exc()}"
