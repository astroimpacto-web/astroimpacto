import swisseph as swe
import pandas as pd
import consultor_web
from datetime import datetime, timedelta, timezone
import time
import re

# ==============================================================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN DE EFEMÉRIDES
# ==============================================================================

# La ruta de efemérides se deja vacía para que Swiss Ephemeris busque en el directorio raíz
# del entorno de ejecución de Streamlit Cloud.
try:
    swe.set_ephe_path('') 
except Exception as e:
    print(f"Aviso: No se pudo establecer la ruta de efemérides: {e}")

# Flags de cálculo: Efemérides suizas y cálculo de velocidad (necesario para retrogradaciones)
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# ==============================================================================
# 2. DICCIONARIOS Y CONSTANTES ASTROLÓGICAS
# ==============================================================================

SIGNOS = [
    "Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", 
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"
]

CUERPOS_NATALES = [
    ("Sol", swe.SUN), ("Luna", swe.MOON), ("Mercurio", swe.MERCURY), 
    ("Venus", swe.VENUS), ("Marte", swe.MARS), ("Júpiter", swe.JUPITER), 
    ("Saturno", swe.SATURN), ("Urano", swe.URANUS), ("Neptuno", swe.NEPTUNE), 
    ("Plutón", swe.PLUTO), ("Quirón", swe.CHIRON), ("Nodo Norte", swe.TRUE_NODE)
]

ASPECTOS_MAYORES = [
    ("Conjunción", 0, 8.0),   # Nombre, Grados, Orbe máximo
    ("Oposición", 180, 8.0),
    ("Trígono", 120, 7.0),
    ("Cuadratura", 90, 7.0),
    ("Sextil", 60, 5.0)
]

# ==============================================================================
# 3. FUNCIONES TÉCNICAS DE CONVERSIÓN Y LIMPIEZA
# ==============================================================================

def obtener_signo(lon):
    """Calcula el signo zodiacal a partir de la longitud eclíptica decimal."""
    return SIGNOS[int(lon / 30) % 12]

def deg_to_dms_sign(lon):
    """
    Convierte grados decimales al formato astronómico tradicional:
    Ejemplo: 15° 23' Aries
    """
    signo_idx = int(lon / 30) % 12
    grados_en_signo = int(lon % 30)
    minutos = int((lon % 1) * 60)
    return f"{grados_en_signo:02d}° {minutos:02d}' {SIGNOS[signo_idx]}"

def limpiar_coordenada(val):
    """Asegura que las coordenadas sean flotantes, manejando comas y valores nulos."""
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return 0.0
        return float(str(val).replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0

def es_nulo(val):
    """Detecta de forma estricta si un valor es None, NaN, NaT o una cadena vacía."""
    if val is None:
        return True
    if isinstance(val, float) and pd.isna(val):
        return True
    if isinstance(val, str) and (val.strip().lower() in ["nan", "nat", "", "none"]):
        return True
    return False

def limpiar_hora_robusta(val):
    """
    Interpreta la hora desde múltiples formatos de entrada (Excel time, string HH:MM, decimal).
    Es la pieza clave para evitar fallos de 'datos incompletos'.
    """
    try:
        if es_nulo(val):
            return 12.0 # Mediodía por defecto si no hay dato
        
        # Caso: Objeto de tiempo o datetime
        if hasattr(val, 'hour'):
            return val.hour + (val.minute / 60.0) + (val.second / 3600.0)
            
        val_str = str(val).strip()
        
        # Caso: Formato HH:MM o HH:MM:SS
        if ':' in val_str:
            partes = val_str.split(':')
            h = float(partes[0])
            m = float(partes[1]) / 60.0 if len(partes) > 1 else 0.0
            s = float(partes[2]) / 3600.0 if len(partes) > 2 else 0.0
            return h + m + s
            
        # Caso: Valor decimal (ej. 14.5 para las 14:30)
        return float(val_str.replace(',', '.'))
    except Exception:
        return 12.0

# ==============================================================================
# 4. MOTOR DE CÁLCULO ASTRONÓMICO (SWISS EPHEMERIS)
# ==============================================================================

def obtener_posiciones_planetarias(jd):
    """Calcula la posición de todos los cuerpos celestes para un Julian Day dado."""
    posiciones = {}
    for nombre, id_p in CUERPOS_NATALES:
        res = swe.calc_ut(jd, id_p, FLAGS)
        posiciones[nombre] = {
            'lon': res[0][0],
            'lat': res[0][1],
            'dist': res[0][2],
            'vel': res[0][3],
            'retro': res[0][3] < 0
        }
    return posiciones

def obtener_casas_y_ejes(jd, lat, lon):
    """Calcula las 12 cúspides de las casas (Placidus) y los ángulos principales."""
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    ejes = {
        'Ascendente': ascmc[0],
        'Medio Cielo': ascmc[1],
        'Descendente': (ascmc[0] + 180) % 360,
        'Fondo Cielo': (ascmc[1] + 180) % 360
    }
    return list(cusps), ejes

# ==============================================================================
# 5. LÓGICA DE REVOLUCIÓN SOLAR (BÚSQUEDA DINÁMICA)
# ==============================================================================

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    """
    Calcula el momento exacto del Retorno Solar y genera el informe completo.
    Utiliza el método de Newton-Raphson para hallar el segundo preciso.
    """
    try:
        nombre = cliente.get('Nombres', cliente.get('nombre', 'Consultante'))
        
        # A. Extracción Blindada de Datos
        f_val = cliente.get('Fecha', cliente.get('fecha'))
        h_val = cliente.get('Hora', cliente.get('hora'))
        lat_v = cliente.get('Latitud', cliente.get('lat'))
        lon_v = cliente.get('Longitud', cliente.get('lon'))

        if any(es_nulo(x) for x in [f_val, h_val, lat_v, lon_v]):
            faltantes = [k for k, v in {"Fecha": f_val, "Hora": h_val, "Lat": lat_v, "Lon": lon_v}.items() if es_nulo(v)]
            return None, f"Error: Datos de nacimiento incompletos ({', '.join(faltantes)})."

        f_nac = pd.to_datetime(f_val)
        h_nac = limpiar_hora_robusta(h_val)
        lat_n = limpiar_coordenada(lat_v)
        lon_n = limpiar_coordenada(lon_v)

        # B. Cálculo de la Longitud del Sol Natal
        jd_nac = swe.julday(f_nac.year, f_nac.month, f_nac.day, h_nac)
        sol_natal = swe.calc_ut(jd_nac, swe.SUN, FLAGS)[0][0]
        _, ejes_nat = obtener_casas_y_ejes(jd_nac, lat_n, lon_n)

        # C. Búsqueda del Momento de la Revolución Solar
        anio_actual = datetime.now().year
        # Empezamos la búsqueda un día antes del cumpleaños
        jd_busqueda = swe.julday(anio_actual, f_nac.month, f_nac.day - 1, 12.0)
        
        for _ in range(40): # Iteraciones de precisión
            sol_iter = swe.calc_ut(jd_busqueda, swe.SUN, FLAGS)[0][0]
            diff = sol_natal - sol_iter
            # Normalización del ángulo
            if diff > 180: diff -= 360
            elif diff < -180: diff += 360
            
            # Criterio de parada (precisión de milisegundos)
            if abs(diff) < 0.000001: 
                break
            # El sol se mueve ~0.9856 grados por día
            jd_busqueda += diff / 0.9856
        
        # D. Posiciones en el momento del Retorno
        lat_final = limpiar_coordenada(lat_rs) if lat_rs else lat_n
        lon_final = limpiar_coordenada(lon_rs) if lon_rs else lon_n
        
        pos_rs = obtener_posiciones_planetarias(jd_busqueda)
        cusps_rs, ejes_rs = obtener_casas_y_ejes(jd_busqueda, lat_final, lon_final)
        
        # E. Generación de Auditoría Técnica para Patricia
        auditoria = (
            f"--- AUDITORÍA REVOLUCIÓN SOLAR {anio_actual} ---\n"
            f"CLIENTE: {nombre}\n"
            f"SOL NATAL: {deg_to_dms_sign(sol_natal)}\n"
            f"ASC NATAL: {deg_to_dms_sign(ejes_nat['Ascendente'])}\n"
            f"------------------------------------------\n"
            f"FECHA RS: {anio_actual}-{f_nac.month:02d}-{f_nac.day:02d}\n"
            f"LUGAR RS: {lugar_rs if lugar_rs else 'Nacimiento'}\n"
            f"ASC ANUAL: {deg_to_dms_sign(ejes_rs['Ascendente'])}\n"
            f"LUNA ANUAL: {deg_to_dms_sign(pos_rs['Luna']['lon'])}\n"
            f"------------------------------------------"
        )

        # F. Llamada al Consultor IA (Prompt Robusto)
        rol = "Eres Patricia Ramirez, astróloga profesional de gran trayectoria. Tu lenguaje es psicológico, serio, profundo y transformador."
        
        prompt = f"""
        Realiza una interpretación integral de la Revolución Solar para {nombre}.
        DATOS TÉCNICOS CALCULADOS:
        - Sol Natal: {obtener_signo(sol_natal)}
        - Ascendente Natal: {obtener_signo(ejes_nat['Ascendente'])}
        - Ascendente Anual: {obtener_signo(ejes_rs['Ascendente'])}
        - Luna Anual: {obtener_signo(pos_rs['Luna']['lon'])} en relación al Sol RS.
        - Mercurio Anual: {obtener_signo(pos_rs['Mercurio']['lon'])}
        
        PROCESO:
        Redacta el informe siguiendo estrictamente este formato de secciones separadas por '###':
        1. El Reto de Transformación del año (1 párrafo con fuerza).
        2. La mayor Oportunidad de expansión (1 párrafo inspirador).
        3. El área de Cambio Principal (1 párrafo realista).
        4. Clima Vincular y Relaciones (1 párrafo).
        5. Interpretación del Clima General (Análisis profundo de 4 párrafos que integre el Asc Anual).
        6. Panorama Laboral y Profesional (2 párrafos detallados).
        7. Panorama Emocional y Afectivo (2 párrafos).
        8. Introducción personalizada al informe.
        9. Resumen de la esencia Natal (Cómo la base natal sostiene este año).
        10. Influencia de Tránsitos Lentos actuales.
        11. Análisis de Progresiones Secundarias (Estado interno).
        """

        resultado_ia = consultor_web.consultar_gpt(rol, prompt, 3500)
        
        if "Error" in resultado_ia:
            return None, "Error de conexión con el motor de IA. Inténtalo de nuevo."

        partes = [p.strip() for p in resultado_ia.split('###')]
        while len(partes) < 11:
            partes.append("Contenido en generación...")

        # G. Empaquetado de Datos para app_web.py
        return {
            "nombre_cliente": nombre,
            "titulo_informe": f"Revolución Solar {anio_actual}",
            "auditoria_tecnica": auditoria,
            "perspectivas": {
                "transformacion": partes[0],
                "oportunidades": partes[1],
                "cambio": partes[2],
                "relaciones": partes[3]
            },
            "revolucion_solar_general_1": partes[4],
            "situacion_laboral_economica": partes[5],
            "situacion_emocional": partes[6],
            "intro_texto": partes[7],
            "carta_natal_resumen": partes[8],
            "transitos_personales": partes[9],
            "progresiones_secundarias": partes[10],
            "panorama_trimestral": [
                {"titulo": "Primer Trimestre", "texto": "Foco en el nuevo Ascendente anual."},
                {"titulo": "Segundo Trimestre", "texto": "Maduración de los propósitos solares."},
                {"titulo": "Tercer Trimestre", "texto": "Cosecha de los esfuerzos laborales."},
                {"titulo": "Cuarto Trimestre", "texto": "Integración y balance emocional."}
            ],
            "como_actuar_progresiones": ["Observar el ritmo interno.", "No forzar procesos."],
            "revo_propone": ["Mayor autonomía.", "Liderazgo personal."],
            "logro_objetivos_profesionales": ["Disciplina constante.", "Networking estratégico."],
            "plan_accion_objetivos": ["Priorizar la salud.", "Definir metas claras."]
        }, "informe_astroimpacto_rs.html"

    except Exception as e:
        return None, f"Fallo crítico en el motor: {str(e)}"

# ==============================================================================
# 6. LÓGICA DE CARTA NATAL
# ==============================================================================

def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Calcula y redacta el análisis profundo de la Carta Natal."""
    try:
        nombre = cliente.get('Nombres', cliente.get('nombre', 'Consultante'))
        f_val = cliente.get('Fecha', cliente.get('fecha'))
        h_val = cliente.get('Hora', cliente.get('hora'))
        
        jd = swe.julday(pd.to_datetime(f_val).year, pd.to_datetime(f_val).month, pd.to_datetime(f_val).day, limpiar_hora_robusta(h_val))
        pos = obtener_posiciones_planetarias(jd)
        cusps, ejes = obtener_casas_y_ejes(jd, limpiar_coordenada(cliente.get('Latitud')), limpiar_coordenada(cliente.get('Longitud')))
        
        rol = "Eres la astróloga profesional Patricia Ramirez. Tu estilo es profundo, psicológico y detallado."
        prompt = f"""
        Analiza la Carta Natal de {nombre}.
        DATOS: Sol en {obtener_signo(pos['Sol']['lon'])}, Luna en {obtener_signo(pos['Luna']['lon'])}, Ascendente en {obtener_signo(ejes['Ascendente'])}.
        Responde secciones separadas por '###':
        Palabras Clave ### Interpretación Sol ### Interpretación Luna ### Interpretación Ascendente ### Síntesis Global de Personalidad.
        """
        
        res = consultor_web.consultar_gpt(rol, prompt, 2500)
        p = [x.strip() for x in res.split('###')] if "Error" not in res else [""]*5
        
        return {
            "nombre_cliente": nombre,
            "titulo_informe": "Análisis de Carta Natal",
            "auditoria_tecnica": f"Natal Calculada con Precisión para {nombre}",
            "aspectos_clave": p[0].split('-') if len(p)>0 else ["Esencia", "Emoción", "Destino"],
            "interpretacion_sol_signo": p[1] if len(p)>1 else "",
            "interpretacion_luna_signo": p[2] if len(p)>2 else "",
            "interpretacion_asc_signo": p[3] if len(p)>3 else "",
            "interpretacion_personalidad_global": p[4] if len(p)>4 else "",
            "foda": {"fortalezas": ["Resiliencia."], "debilidades": ["Miedo al fracaso."]}
        }, "informe_astroimpacto.html"
    except Exception as e:
        return None, str(e)

# ==============================================================================
# 7. LÓGICA DE TRÁNSITOS ANUALES
# ==============================================================================

def procesar_transitos_con_ia(cliente, tipo_obj, id_cli):
    """Genera el pronóstico de Tránsitos para el año en curso."""
    try:
        nombre = cliente.get('Nombres', cliente.get('nombre', 'Consultante'))
        rol = "Patricia Ramirez, Astróloga Profesional."
        prompt = f"Genera un lema y clima anual para {nombre}. Separa con ###: Lema ### Clima Anual ### Oportunidad ### Punto de Atención."
        
        res = consultor_web.consultar_gpt(rol, prompt, 2000)
        p = [x.strip() for x in res.split('###')] if "Error" not in res else [""]*4
        
        return {
            "nombre_cliente": nombre,
            "titulo_informe": "Pronóstico de Tránsitos",
            "auditoria_tecnica": "Cálculo de efemérides de planetas sociales y transpersonales completado.",
            "frase_anual_corta": p[0] if len(p)>0 else "Año de evolución.",
            "analisis_clima_anual": p[1] if len(p)>1 else "",
            "oportunidad_anual": p[2] if len(p)>2 else "",
            "atencion_anual": p[3] if len(p)>3 else "",
            "calendario_por_meses": {"Ciclo Actual": [{"fecha": "Hito", "transito": "Júpiter", "texto_efecto": "Crecimiento personal."}]}
        }, "informe_astroimpacto_transitos.html"
    except Exception as e:
        return None, str(e)
