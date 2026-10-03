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
def _jd_retorno_solar(sol_natal, anio, mes, dia):
    """Día juliano (UT) en que el Sol vuelve a su longitud natal durante 'anio'."""
    jd = swe.julday(anio, mes, max(1, dia - 1), 0.0, swe.GREG_CAL)
    for _ in range(50):
        sol_ahora = swe.calc_ut(jd, swe.SUN, FLAGS)[0][0]
        diff = sol_natal - sol_ahora
        if diff > 180: diff -= 360
        elif diff < -180: diff += 360
        if abs(diff) < 0.000001:
            return jd
        jd += diff / 0.9856
    raise ValueError("No se pudo calcular el retorno solar (el cálculo no converge).")

def resolver_retorno_solar(sol_natal, fecha_nac, anio_rs=None, ahora=None):
    """Devuelve (anio, jd_rs).
    - Si se indica anio_rs: calcula la RS de ese año.
    - Si no (automático): elige la PRÓXIMA RS, es decir, la del año en curso si
      todavía no ocurre; si ya ocurrió, la del año siguiente."""
    if anio_rs is not None:
        anio = int(anio_rs)
        return anio, _jd_retorno_solar(sol_natal, anio, fecha_nac.month, fecha_nac.day)
    ahora = ahora or datetime.now(timezone.utc)
    jd_ahora = swe.julday(ahora.year, ahora.month, ahora.day,
                          ahora.hour + ahora.minute / 60.0, swe.GREG_CAL)
    anio = ahora.year
    jd_rs = _jd_retorno_solar(sol_natal, anio, fecha_nac.month, fecha_nac.day)
    if jd_rs < jd_ahora:
        anio += 1
        jd_rs = _jd_retorno_solar(sol_natal, anio, fecha_nac.month, fecha_nac.day)
    return anio, jd_rs

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None, anio_rs=None):
    """anio_rs=None -> calcula automáticamente la PRÓXIMA revolución solar."""
    try:
        planetas_nat, asc_nat, mc_nat, fecha_nac, hora_nac, lat_nat, lon_nat = calcular_posiciones_base(cliente)
        nombre = cliente.get('Nombres', 'Consultante')
        sol_natal = planetas_nat['Sol']
        luna_natal = planetas_nat['Luna']

        anio_rs, jd_rs = resolver_retorno_solar(sol_natal, fecha_nac, anio_rs)

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

        y_rs, m_rs, d_rs, h_rs = swe.revjul(jd_rs, swe.GREG_CAL)
        momento_rs = f"{int(d_rs):02d}-{int(m_rs):02d}-{int(y_rs)} {hora_decimal_a_hms(h_rs)} UT"

        auditoria = (
            f"--- PANEL TÉCNICO RS {anio_rs} ---\n"
            f"NACIMIENTO UT: {fecha_nac:%d-%m-%Y} {hora_decimal_a_hms(hora_nac)} | Lat {lat_nat:.4f} | Lon {lon_nat:.4f}\n"
            f"CASAS: {NOMBRE_SISTEMA_CASAS}\n"
            f"NATAL: Asc {deg_to_dms_sign(asc_nat)} | Sol {deg_to_dms_sign(sol_natal)} | Luna {deg_to_dms_sign(luna_natal)}\n"
            f"MOMENTO RS: {momento_rs}\n"
            f"RS {anio_rs}: Asc {deg_to_dms_sign(asc_rs)} | Luna {deg_to_dms_sign(luna_rs)}\n"
            f"UBICACIÓN RS: {lugar_final}\n"
            f"PROGRESIÓN: Luna en {deg_to_dms_sign(luna_prog_lon)}\n"
            f"-----------------------------------"
        )

        rol = "Eres Patricia Ramirez, astróloga profesional de alto nivel. Tu estilo es profundo, detallado y empático."
        prompt = f"""
DATOS TÉCNICOS REALES PARA {nombre}:
Natal: Sol en {obtener_signo(sol_natal)}, Luna en {obtener_signo(luna_natal)}, Ascendente en {obtener_signo(asc_nat)}.
RS {anio_rs}: Ascendente Anual en {obtener_signo(asc_rs)}, Luna Anual en {obtener_signo(planetas_rs['Luna'])}.
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
            "titulo_informe": f"Revolución Solar {anio_rs}",
            "anio_actual": anio_rs,
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
# PROCESO 2: CARTA NATAL COMPLETA (alineada con informe_astroimpacto.html)
# ==============================================================================
import base64
import copy
import html as _html
import math

SIGNOS = ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", "Libra", "Escorpio",
          "Sagitario", "Capricornio", "Acuario", "Piscis"]
GLIFOS_SIGNOS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]
GLIFOS_PLANETAS = {"Sol": "☉", "Luna": "☽", "Mercurio": "☿", "Venus": "♀", "Marte": "♂",
                   "Júpiter": "♃", "Saturno": "♄", "Urano": "♅", "Neptuno": "♆", "Plutón": "♇",
                   "Ascendente": "AC", "Medio Cielo": "MC"}

PLANETAS_CARTA = [
    ("Sol", swe.SUN), ("Luna", swe.MOON), ("Mercurio", swe.MERCURY), ("Venus", swe.VENUS),
    ("Marte", swe.MARS), ("Júpiter", swe.JUPITER), ("Saturno", swe.SATURN),
    ("Urano", swe.URANUS), ("Neptuno", swe.NEPTUNE), ("Plutón", swe.PLUTO),
]
GIGANTES = ["Júpiter", "Saturno", "Urano", "Neptuno", "Plutón"]
LUMINARES = {"Sol", "Luna"}
TRANSPERSONALES = {"Urano", "Neptuno", "Plutón"}

# Peso de cada punto en el balance de elementos y modos (ajustable a tu criterio).
PESOS_PUNTOS = {"Sol": 4, "Luna": 4, "Ascendente": 4, "Mercurio": 3, "Venus": 3, "Marte": 3,
                "Medio Cielo": 2, "Júpiter": 2, "Saturno": 2, "Urano": 1, "Neptuno": 1, "Plutón": 1}

ASPECTOS_NATAL = [("Conjunción", 0, 8), ("Sextil", 60, 5), ("Cuadratura", 90, 7),
                  ("Trígono", 120, 7), ("Oposición", 180, 8)]

# Completa con tus datos reales (aparecen en la última página del informe).
DATOS_CONTACTO = {"ig": "@tu_instagram", "mail": "tu_correo@ejemplo.com"}
TEXTO_CONECTADOS = "Sigamos conectados"

ROL_NATAL = ("Eres Patricia Ramirez, astróloga profesional de Astroimpacto. Tono empático, profundo, "
             "psicológico y cercano. Escribes en español neutro, sin tecnicismos innecesarios.")


def casa_de(lon, cuspides):
    """Número de casa (1-12) en que cae una longitud, según las cúspides."""
    for i in range(12):
        ini, fin = cuspides[i], cuspides[(i + 1) % 12]
        ancho = (fin - ini) % 360
        if (lon - ini) % 360 < ancho:
            return i + 1
    return 12


def _grados_min(valor):
    g = int(valor)
    m = int(round((valor - g) * 60))
    if m == 60:
        g, m = g + 1, 0
    return f"{g}°{m:02d}'"


def calcular_carta_natal(cliente):
    """Planetas (con casa y retrogradación), cúspides topocéntricas, Asc y MC. Todo en UT."""
    fecha_ut, hora_ut, origen = momento_ut(cliente)
    lat = limpiar_coordenada(cliente.get('Latitud', 0))
    lon = limpiar_coordenada(cliente.get('Longitud', 0))
    jd = float(swe.julday(fecha_ut.year, fecha_ut.month, fecha_ut.day, hora_ut, swe.GREG_CAL))

    planetas = {}
    for nombre, id_p in PLANETAS_CARTA:
        res = swe.calc_ut(jd, id_p, FLAGS)[0]
        planetas[nombre] = {"lon": float(res[0]), "retro": float(res[3]) < 0}

    cusps, ascmc = swe.houses(jd, float(lat), float(lon), SISTEMA_CASAS)
    cusps = [float(c) for c in cusps]
    if len(cusps) == 13:
        cusps = cusps[1:]
    if len(cusps) != 12:
        raise ValueError(f"El motor de casas devolvió {len(cusps)} cúspides (se esperaban 12).")
    asc, mc = float(ascmc[0]), float(ascmc[1])

    for d in planetas.values():
        d["signo"] = obtener_signo(d["lon"])
        d["casa"] = casa_de(d["lon"], cusps)
    return {"planetas": planetas, "cuspides": cusps, "asc": asc, "mc": mc,
            "fecha_ut": fecha_ut, "hora_ut": hora_ut, "lat": lat, "lon": lon}


def calcular_balance(puntos):
    """Elementos y modos (en %, enteros que suman 100) ponderados por PESOS_PUNTOS."""
    elem = {"fuego": 0.0, "tierra": 0.0, "aire": 0.0, "agua": 0.0}
    claves_e = ["fuego", "tierra", "aire", "agua"]
    modos = {"Cardinal": 0.0, "Fijo": 0.0, "Mutable": 0.0}
    claves_m = ["Cardinal", "Fijo", "Mutable"]
    for nombre, lon in puntos.items():
        peso = PESOS_PUNTOS.get(nombre, 1)
        idx = int(lon / 30) % 12
        elem[claves_e[idx % 4]] += peso
        modos[claves_m[idx % 3]] += peso

    def a_porcentaje(d):
        total = sum(d.values())
        crudo = {k: v * 100.0 / total for k, v in d.items()}
        base = {k: int(v) for k, v in crudo.items()}
        faltan = 100 - sum(base.values())
        for k in sorted(crudo, key=lambda k: crudo[k] - base[k], reverse=True)[:faltan]:
            base[k] += 1
        return base
    return a_porcentaje(elem), a_porcentaje(modos)


def calcular_aspectos_natal(puntos, maximo=8):
    """Aspectos mayores entre planetas, Ascendente y Medio Cielo, ordenados por cercanía relativa.
    Se omiten los aspectos entre dos planetas transpersonales (son generacionales) y AC-MC."""
    nombres = list(puntos)
    encontrados = []
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            if {a, b} == {"Ascendente", "Medio Cielo"}:
                continue
            if a in TRANSPERSONALES and b in TRANSPERSONALES:
                continue
            dist = diferencia_angular(puntos[a], puntos[b])
            for nom, ang, orbe in ASPECTOS_NATAL:
                limite = orbe if (a in LUMINARES or b in LUMINARES) else orbe - 2
                desv = abs(dist - ang)
                if desv <= limite:
                    encontrados.append({"a": a, "b": b, "aspecto": nom, "angulo": ang,
                                        "orbe": desv, "rel": desv / limite})
                    break
    encontrados.sort(key=lambda x: x["rel"])
    return encontrados[:maximo]


def dibujar_mandala_svg(carta, aspectos):
    """Rueda natal en SVG (Ascendente a la izquierda). Devuelve texto SVG."""
    cx = cy = 300
    asc = carta["asc"]
    fuente = "'Segoe UI Symbol','Apple Symbols','DejaVu Sans','Noto Sans Symbols',sans-serif"
    acento, oscuro, gris = "#B48E92", "#967074", "#4A4A4A"

    def pt(lon, r):
        th = math.radians(180.0 + (lon - asc))
        return cx + r * math.cos(th), cy - r * math.sin(th)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-25 -25 650 650" width="650" height="650">',
         '<rect x="-25" y="-25" width="650" height="650" fill="#F9F7F2"/>']
    for r, w in ((290, 1.5), (248, 1), (212, 1), (118, 1)):
        s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{acento}" stroke-width="{w}"/>')

    # Signos
    for i in range(12):
        x1, y1 = pt(i * 30, 248)
        x2, y2 = pt(i * 30, 290)
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{acento}" stroke-width="1"/>')
        gx, gy = pt(i * 30 + 15, 269)
        s.append(f'<text x="{gx:.1f}" y="{gy:.1f}" text-anchor="middle" dy=".35em" font-size="22" '
                 f'font-family="{fuente}" fill="{oscuro}">{GLIFOS_SIGNOS[i]}&#xFE0E;</text>')

    # Casas
    for i, c in enumerate(carta["cuspides"]):
        x1, y1 = pt(c, 118)
        x2, y2 = pt(c, 248)
        grueso = 2 if i in (0, 3, 6, 9) else 0.8
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{gris}" '
                 f'stroke-width="{grueso}" opacity="0.55"/>')
        sig = carta["cuspides"][(i + 1) % 12]
        ancho = (sig - c) % 360
        nx, ny = pt(c + ancho / 2.0, 228)
        s.append(f'<text x="{nx:.1f}" y="{ny:.1f}" text-anchor="middle" dy=".35em" font-size="11" '
                 f'font-family="sans-serif" fill="{gris}" opacity="0.7">{i + 1}</text>')

    # Aspectos
    puntos = {n: d["lon"] for n, d in carta["planetas"].items()}
    puntos["Ascendente"], puntos["Medio Cielo"] = carta["asc"], carta["mc"]
    for asp in aspectos:
        x1, y1 = pt(puntos[asp["a"]], 118)
        x2, y2 = pt(puntos[asp["b"]], 118)
        color = {"Conjunción": oscuro, "Sextil": "#6B818C", "Trígono": "#6B818C"}.get(asp["aspecto"], "#B0605F")
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
                 f'stroke-width="1.3" opacity="0.8"/>')

    # Planetas (separación mínima para que los glifos no se pisen)
    items = sorted(((n, d["lon"]) for n, d in carta["planetas"].items()), key=lambda t: t[1])
    disp = [lon for _, lon in items]
    for _ in range(80):
        movido = False
        for i in range(len(items)):
            j = (i + 1) % len(items)
            brecha = (disp[j] - disp[i]) % 360
            if len(items) > 1 and brecha < 9:
                push = (9 - brecha) / 2.0
                disp[i] -= push
                disp[j] += push
                movido = True
        if not movido:
            break
    for (nombre, lon), dlon in zip(items, disp):
        x1, y1 = pt(lon, 212)
        x2, y2 = pt(lon, 204)
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{gris}" stroke-width="1.2"/>')
        gx, gy = pt(dlon, 184)
        s.append(f'<text x="{gx:.1f}" y="{gy:.1f}" text-anchor="middle" dy=".35em" font-size="20" '
                 f'font-family="{fuente}" fill="{gris}">{GLIFOS_PLANETAS[nombre]}&#xFE0E;</text>')
        if carta["planetas"][nombre]["retro"]:
            rx, ry = pt(dlon, 160)
            s.append(f'<text x="{rx:.1f}" y="{ry:.1f}" text-anchor="middle" dy=".35em" font-size="9" '
                     f'font-family="sans-serif" fill="{oscuro}">R</text>')

    # Ejes AC / MC
    for etiqueta, lon in (("AC", carta["asc"]), ("MC", carta["mc"])):
        x, y = pt(lon, 306)
        s.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dy=".35em" font-size="13" '
                 f'font-family="sans-serif" font-weight="bold" fill="{oscuro}">{etiqueta}</text>')
    s.append('</svg>')
    return "".join(s)


def svg_a_data_uri(svg):
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _texto_a_html(texto):
    """Texto plano (párrafos separados por línea en blanco) -> <p>…</p>. Si ya trae HTML, lo respeta."""
    if texto is None:
        return ""
    texto = str(texto).strip()
    if "<p" in texto.lower():
        return texto
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    return "".join(f"<p>{_html.escape(p).replace(chr(10), '<br>')}</p>" for p in parrafos)


CLAVES_TEXTO_NATAL = ["texto_introductorio", "interpretacion_modos", "interpretacion_balance_elementos",
                      "interpretacion_sol_signo", "interpretacion_luna_signo", "interpretacion_asc_signo",
                      "interpretacion_personalidad_global"]


def preparar_para_render(datos, tipo="NATAL"):
    """Copia del diccionario con los textos largos convertidos a párrafos HTML (solo Natal).
    En el editor los textos se mantienen planos; esta conversión ocurre únicamente al renderizar."""
    if tipo != "NATAL" or not isinstance(datos, dict):
        return datos
    d = copy.deepcopy(datos)
    for k in CLAVES_TEXTO_NATAL:
        if k in d:
            d[k] = _texto_a_html(d[k])
    for g in d.get("gigantes_del_cielo", []):
        g["texto"] = _texto_a_html(g.get("texto", ""))
    for a in d.get("aspectos_interpretados", []):
        a["texto"] = _texto_a_html(a.get("texto", ""))
    return d


def _llamar_json(prompt, claves, max_tokens, intentos=2):
    """Pide a la IA un JSON y valida que estén todas las claves. Lanza ValueError si no se logra."""
    ultimo = None
    for _ in range(intentos):
        try:
            datos = consultor_web.consultar_gpt_json(ROL_NATAL, prompt, max_tokens)
            faltan = [k for k in claves if k not in datos or datos[k] in (None, "", [], {})]
            if not faltan:
                return datos
            ultimo = f"la IA no entregó: {', '.join(faltan)}"
        except Exception as e:
            ultimo = str(e)
        time.sleep(2)
    raise ValueError(f"Falló la generación con IA ({ultimo}).")


def _lista_texto(valor, n=4):
    """Normaliza una lista de frases devuelta por la IA."""
    if isinstance(valor, str):
        valor = [x for x in re.split(r"\n|&&&", valor)]
    limpio = [re.sub(r"^[\-\*•\d\.\)\s]+", "", str(x)).strip() for x in (valor or [])]
    return [x for x in limpio if len(x) > 3][:n]


def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Carta natal completa: cálculo real (casas topocéntricas) + textos IA con salida JSON."""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        genero = str(cliente.get('Genero') or cliente.get('genero') or '').strip().lower()
        es_mujer = genero.startswith('f')
        es_hombre = genero.startswith('m')
        concordancia = ("Escribe en femenino (la consultante)." if es_mujer else
                        "Escribe en masculino (el consultante)." if es_hombre else
                        "Usa formulaciones neutras que no dependan del género.")

        carta = calcular_carta_natal(cliente)
        pl = carta["planetas"]
        puntos = {n: d["lon"] for n, d in pl.items()}
        puntos["Ascendente"], puntos["Medio Cielo"] = carta["asc"], carta["mc"]
        elementos, modos = calcular_balance(puntos)
        aspectos = calcular_aspectos_natal(puntos)

        asc_signo, mc_signo = obtener_signo(carta["asc"]), obtener_signo(carta["mc"])
        lineas = [f"- {n} en {d['signo']}, casa {d['casa']}" + (" (retrógrado)" if d["retro"] else "")
                  for n, d in pl.items()]
        lineas.append(f"- Ascendente en {asc_signo}")
        lineas.append(f"- Medio Cielo en {mc_signo}")
        lineas_asp = [f"{i + 1}. {a['a']} {a['aspecto']} {a['b']} (orbe {a['orbe']:.1f}°)"
                      for i, a in enumerate(aspectos)] or ["(sin aspectos mayores cerrados)"]
        datos_txt = (f"CONSULTANTE: {nombre}. {concordancia}\n"
                     f"POSICIONES (casas topocéntricas):\n" + "\n".join(lineas) + "\n"
                     f"BALANCE ELEMENTOS (%): fuego {elementos['fuego']}, tierra {elementos['tierra']}, "
                     f"aire {elementos['aire']}, agua {elementos['agua']}\n"
                     f"BALANCE MODOS (%): cardinal {modos['Cardinal']}, fijo {modos['Fijo']}, mutable {modos['Mutable']}\n")
        reglas = ("REGLAS: usa SOLO los datos entregados, no inventes posiciones ni aspectos. "
                  "Texto plano (sin HTML ni markdown); separa los párrafos con una línea en blanco. "
                  "No menciones porcentajes ni números de puntos. Responde únicamente con un objeto JSON.")

        prompt_a = (datos_txt + "\n" + reglas + "\n\n"
                    "Devuelve un JSON con estas claves exactas:\n"
                    '"texto_introductorio": bienvenida cálida personalizada (1 párrafo),\n'
                    '"frase_destacada_sol", "frase_destacada_luna", "frase_destacada_asc", "frase_destacada_global": '
                    "frases inspiradoras cortas (máx. 18 palabras, sin comillas) sobre Sol, Luna, Ascendente y el conjunto,\n"
                    '"interpretacion_sol_signo": Sol en su signo y casa, identidad y brillo (2 párrafos),\n'
                    '"interpretacion_luna_signo": Luna en su signo y casa, mundo emocional y refugio (2 párrafos),\n'
                    '"luna_mecanismo", "luna_talento", "luna_necesidad": una frase corta cada una '
                    "(mecanismo de defensa, talento emocional, necesidad básica de la Luna),\n"
                    '"interpretacion_asc_signo": Ascendente en su signo, aprendizaje y cómo lo ven los demás (2 párrafos),\n'
                    '"interpretacion_modos": ritmo vital según el modo dominante (1-2 párrafos),\n'
                    '"interpretacion_balance_elementos": elemento dominante y el más débil, como consejo fluido (1-2 párrafos),\n'
                    '"interpretacion_personalidad_global": síntesis integrando Sol, Luna, Ascendente, elementos y '
                    "aspectos principales (3 párrafos),\n"
                    '"foda": objeto con "fortalezas", "debilidades", "oportunidades" y "amenazas", '
                    "cada una con 4 frases cortas y concretas basadas en la carta.")
        claves_a = ["texto_introductorio", "frase_destacada_sol", "frase_destacada_luna", "frase_destacada_asc",
                    "frase_destacada_global", "interpretacion_sol_signo", "interpretacion_luna_signo",
                    "luna_mecanismo", "luna_talento", "luna_necesidad", "interpretacion_asc_signo",
                    "interpretacion_modos", "interpretacion_balance_elementos",
                    "interpretacion_personalidad_global", "foda"]
        a = _llamar_json(prompt_a, claves_a, 5000)

        prompt_b = (datos_txt + "ASPECTOS A INTERPRETAR:\n" + "\n".join(lineas_asp) + "\n\n" + reglas + "\n\n"
                    "Devuelve un JSON con:\n"
                    '"gigantes": objeto con una clave por cada planeta (Júpiter, Saturno, Urano, Neptuno, Plutón) '
                    "y como valor su interpretación en su signo y casa (1 párrafo cada una; para Urano, Neptuno y "
                    "Plutón explica también el matiz generacional),\n"
                    '"aspectos": lista de objetos {"id": número, "texto": interpretación breve (1 párrafo) del reto '
                    "o ventaja del aspecto} con un objeto por cada aspecto listado.")
        b = _llamar_json(prompt_b, ["gigantes"] + (["aspectos"] if aspectos else []), 5000)

        gig_ia = b.get("gigantes", {})
        gigantes = [{"nombre": n, "signo": pl[n]["signo"], "casa": pl[n]["casa"],
                     "texto": str(gig_ia.get(n, "")).strip()} for n in GIGANTES]
        textos_asp = {}
        for item in b.get("aspectos", []) if isinstance(b.get("aspectos"), list) else []:
            try:
                textos_asp[int(item.get("id"))] = str(item.get("texto", "")).strip()
            except (TypeError, ValueError):
                continue
        aspectos_int = [{"titulo": f"{x['a']} {x['aspecto']} {x['b']}",
                         "subtitulo": f"orbe {_grados_min(x['orbe'])}",
                         "texto": textos_asp.get(i + 1, "")} for i, x in enumerate(aspectos)]

        foda_ia = a["foda"] if isinstance(a["foda"], dict) else {}
        foda = {k: _lista_texto(foda_ia.get(k)) for k in ("fortalezas", "debilidades", "oportunidades", "amenazas")}

        # Fecha y lugar tal como los espera la plantilla: "dd-mm-aaaa HH:MM - Lugar"
        try:
            f_loc = limpiar_fecha(cliente.get('Fecha')).strftime("%d-%m-%Y")
            h_loc = hora_decimal_a_hms(hora_a_decimal(cliente.get('Hora')))[:5]
        except ValueError:
            f_loc = carta["fecha_ut"].strftime("%d-%m-%Y")
            h_loc = hora_decimal_a_hms(carta["hora_ut"])[:5] + " UT"
        ciudad = str(cliente.get('Ciudad') or '').replace('_', ', ').replace(' - ', ' ').strip()
        pais = str(cliente.get('Pais') or '').strip()
        lugar = ", ".join(x for x in (ciudad, pais.split('-')[-1] if pais else "") if x) or "Lugar no indicado"

        ahora = datetime.now()
        auditoria = (
            "--- PANEL TÉCNICO NATAL ---\n"
            f"NACIMIENTO UT: {carta['fecha_ut']:%d-%m-%Y} {hora_decimal_a_hms(carta['hora_ut'])} | "
            f"Lat {carta['lat']:.4f} | Lon {carta['lon']:.4f}\n"
            f"CASAS: {NOMBRE_SISTEMA_CASAS}\n"
            f"AC {deg_to_dms_sign(carta['asc'])} | MC {deg_to_dms_sign(carta['mc'])}\n"
            + "\n".join(f"{n}: {deg_to_dms_sign(d['lon'])} (casa {d['casa']})" + (" R" if d["retro"] else "")
                        for n, d in pl.items()) + "\n"
            "CÚSPIDES: " + " | ".join(f"{i + 1}: {deg_to_dms_sign(c)}" for i, c in enumerate(carta["cuspides"])) + "\n"
            f"ELEMENTOS %: {elementos}\nMODOS %: {modos}\n"
            "ASPECTOS: " + "; ".join(f"{x['a']} {x['aspecto']} {x['b']} ({x['orbe']:.1f}°)" for x in aspectos) + "\n"
            "---------------------------")

        return {
            "nombre_cliente": nombre,
            "titulo_informe": "Carta Natal",
            "titulo_bienvenida": "Bienvenida a tu carta natal" if es_mujer else
                                 "Bienvenido a tu carta natal" if es_hombre else "Te damos la bienvenida a tu carta natal",
            "fecha_entrega": f"{MESES_ES[ahora.month - 1]} {ahora.year}",
            "tema_color": "rosa",
            "auditoria_tecnica": auditoria,
            "datos_nacimiento": f"{f_loc} {h_loc} - {lugar}",
            "ruta_imagen_carta": svg_a_data_uri(dibujar_mandala_svg(carta, aspectos)),
            "aspectos_clave": [f"Sol en {pl['Sol']['signo']}", f"Luna en {pl['Luna']['signo']}",
                               f"Ascendente en {asc_signo}"],
            "texto_introductorio": a["texto_introductorio"],
            "interpretacion_modos": a["interpretacion_modos"],
            "elementos": elementos,
            "interpretacion_balance_elementos": a["interpretacion_balance_elementos"],
            "frase_destacada_sol": a["frase_destacada_sol"],
            "frase_destacada_luna": a["frase_destacada_luna"],
            "frase_destacada_asc": a["frase_destacada_asc"],
            "frase_destacada_global": a["frase_destacada_global"],
            "sol": {"signo": pl["Sol"]["signo"], "casa": pl["Sol"]["casa"]},
            "luna": {"signo": pl["Luna"]["signo"], "casa": pl["Luna"]["casa"],
                     "mecanismo": a["luna_mecanismo"], "talento": a["luna_talento"], "necesidad": a["luna_necesidad"]},
            "asc": {"signo": asc_signo},
            "interpretacion_sol_signo": a["interpretacion_sol_signo"],
            "interpretacion_luna_signo": a["interpretacion_luna_signo"],
            "interpretacion_asc_signo": a["interpretacion_asc_signo"],
            "foda": foda,
            "gigantes_del_cielo": gigantes,
            "aspectos_interpretados": aspectos_int,
            "interpretacion_personalidad_global": a["interpretacion_personalidad_global"],
            "datos_contacto": dict(DATOS_CONTACTO),
            "texto_conectados": TEXTO_CONECTADOS,
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
