import swisseph as swe
import pandas as pd
import consultor_web
from datetime import datetime, timedelta, timezone
import time
import re

# ==========================================
# CONFIGURACIÓN DE EFEMÉRIDES PARA LA NUBE
# ==========================================
swe.set_ephe_path('') 
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# --- FUNCIONES DE FORMATEO TÉCNICO ---
def obtener_signo(lon):
    return ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"][int(lon/30)%12]

def deg_to_dms_sign(lon):
    """Convierte grados decimales al formato: 15° Aries 23'"""
    signos = ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"]
    signo_idx = int(lon / 30) % 12
    grados = int(lon % 30)
    minutos = int((lon % 1) * 60)
    return f"{grados:02d}° {signos[signo_idx]} {minutos:02d}'"

def limpiar_coordenada(val):
    try: return float(val)
    except: return 0.0

# ==========================================
# CÁLCULOS ASTROLÓGICOS DE PRECISIÓN
# ==========================================

def obtener_datos_astrologicos(dia, mes, anio, hora, lat, lon):
    jd = swe.julday(anio, mes, dia, hora, swe.GREG_CAL)
    planetas = {}
    for name, id_p in [("Sol", swe.SUN), ("Luna", swe.MOON), ("Mercurio", swe.MERCURY), ("Venus", swe.VENUS), ("Marte", swe.MARS), ("Júpiter", swe.JUPITER), ("Saturno", swe.SATURN)]:
        planetas[name] = swe.calc_ut(jd, id_p, FLAGS)[0][0]
    casas, ascmc = swe.houses(jd, lat, lon, b'P')
    return planetas, ascmc[0], ascmc[1]

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    """Genera el informe de RS con Auditoría Técnica detallada"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        
        # 1. RECUPERAR DATOS NATALES
        # Asumimos que el Excel tiene columnas Fecha, Hora, Latitud, Longitud
        # Si no existen, usamos valores por defecto (evita crash)
        try:
            f_nac = pd.to_datetime(cliente.get('Fecha'))
            h_nac = float(cliente.get('Hora', 12.0)) # Formato decimal 14.5 = 14:30
            lat_n = limpiar_coordenada(cliente.get('Latitud', 0))
            lon_n = limpiar_coordenada(cliente.get('Longitud', 0))
        except:
            return None, "Error: Datos de nacimiento incompletos para cálculos matemáticos."

        # 2. CÁLCULO DE POSICIONES NATALES
        planetas_nat, asc_nat, mc_nat = obtener_datos_astrologicos(f_nac.day, f_nac.month, f_nac.year, h_nac, lat_n, lon_n)

        # 3. CÁLCULO DE REVOLUCIÓN SOLAR (Búsqueda del Retorno Solar)
        anio_actual = datetime.now().year
        jd_inicio_busqueda = swe.julday(anio_actual, f_nac.month, f_nac.day - 1, 0.0)
        sol_natal = planetas_nat['Sol']
        
        jd_rs = jd_inicio_busqueda
        for _ in range(30): # Iteración Newton-Raphson para hallar el segundo exacto
            sol_ahora = swe.calc_ut(jd_rs, swe.SUN, FLAGS)[0][0]
            diff = sol_natal - sol_ahora
            if diff > 180: diff -= 360
            elif diff < -180: diff += 360
            if abs(diff) < 0.00001: break
            jd_rs += diff / 0.9856 # El sol se mueve aprox 1 grado por día
        
        # Posiciones en el momento de la RS
        lat_calc = lat_rs if lat_rs is not None else lat_n
        lon_calc = lon_rs if lon_rs is not None else lon_n
        planetas_rs, asc_rs, mc_rs = obtener_datos_astrologicos(1, 1, 2000, 0, lat_calc, lon_calc) # El JD ya define el tiempo
        # Recalcular con el JD exacto de la RS
        for name, id_p in [("Sol", swe.SUN), ("Luna", swe.MOON), ("Mercurio", swe.MERCURY), ("Venus", swe.VENUS), ("Marte", swe.MARS)]:
            planetas_rs[name] = swe.calc_ut(jd_rs, id_p, FLAGS)[0][0]
        _, ascmc_rs = swe.houses(jd_rs, lat_calc, lon_calc, b'P')
        asc_rs = ascmc_rs[0]

        # 4. PROGRESIONES SECUNDARIAS (1 Día = 1 Año)
        edad = anio_actual - f_nac.year
        jd_progresado = swe.julday(f_nac.year, f_nac.month, f_nac.day, h_nac, swe.GREG_CAL) + edad
        planetas_prog = {}
        for name, id_p in [("Sol", swe.SUN), ("Luna", swe.MOON), ("Marte", swe.MARS)]:
            planetas_prog[name] = swe.calc_ut(jd_progresado, id_p, FLAGS)[0][0]

        # 5. CONSTRUCCIÓN DEL PANEL DE AUDITORÍA (Lo que antes veías en VS Code)
        auditoria = f"""
        --- PANEL TÉCNICO DE AUDITORÍA ---
        NATAL: Asc {deg_to_dms_sign(asc_nat)} | Sol {deg_to_dms_sign(sol_natal)}
        REVOLUCIÓN SOLAR {anio_actual}:
        Ubicación: {lugar_rs if lugar_rs else 'Nacimiento'}
        Asc Anual: {deg_to_dms_sign(asc_rs)}
        Luna Anual: {deg_to_dms_sign(planetas_rs['Luna'])}
        PROGRESIONES (Edad {edad}):
        Luna Prog: {deg_to_dms_sign(planetas_prog['Luna'])}
        Sol Prog: {deg_to_dms_sign(planetas_prog['Sol'])}
        ----------------------------------
        """

        # 6. LLAMADA A IA CON DATOS TÉCNICOS REALES
        rol = "Eres Patricia Ramirez, astróloga profesional. Tu estilo es profundo y detallado."
        prompt = f"""
        DATOS TÉCNICOS REALES:
        Natal: Asc {obtener_signo(asc_nat)}, Sol {obtener_signo(sol_natal)}.
        RS: Asc Anual {obtener_signo(asc_rs)}, Luna Anual {obtener_signo(planetas_rs['Luna'])}.
        Progresiones: Luna Progresada en {obtener_signo(planetas_prog['Luna'])}.

        Basado en estos datos EXACTOS, redacta:
        1. Reto de transformación ###
        2. Oportunidad mayor ###
        3. Cambio principal ###
        4. Vínculos ###
        5. Interpretación Clima General (Mínimo 4 párrafos profundos) ###
        6. Laboral ###
        7. Emocional ###
        8. Introducción ###
        9. Resumen Natal ###
        10. Tránsitos Lentos ###
        11. Análisis de Progresiones
        """

        resultado = ""
        for i in range(3):
            resultado = consultor_web.consultar_gpt(rol, prompt, 3500)
            if resultado and "Error" not in resultado: break
            time.sleep(2)

        if "Error" in resultado or not resultado:
            partes = ["Error de conexión"] * 11
        else:
            partes = [p.strip() for p in resultado.split('###')]

        # Diccionario final para Streamlit
        return {
            "nombre_cliente": nombre,
            "titulo_informe": f"Revolución Solar {anio_actual}",
            "auditoria_tecnica": auditoria, # Enviamos la auditoría para mostrarla en la web
            "perspectivas": {
                "transformacion": partes[0], "oportunidades": partes[1], "cambio": partes[2], "relaciones": partes[3]
            },
            "revolucion_solar_general_1": partes[4],
            "situacion_laboral_economica": partes[5],
            "situacion_emocional": partes[6],
            "intro_texto": partes[7],
            "carta_natal_resumen": partes[8],
            "transitos_personales": partes[9],
            "progresiones_secundarias": partes[10],
            "panorama_trimestral": [
                {"titulo": "Trimestre 1", "texto": "Inicios basados en tu Asc Anual."},
                {"titulo": "Trimestre 2", "texto": "Desarrollo de la Luna Anual."},
                {"titulo": "Trimestre 3", "texto": "Cosecha y resultados."},
                {"titulo": "Trimestre 4", "texto": "Integración final."}
            ]
        }, "informe_astroimpacto_rs.html"

    except Exception as e:
        import traceback
        return None, f"Error técnico: {str(e)}\n{traceback.format_exc()}"

def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Genera el informe profundo de Carta Natal con cálculos exactos"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        planetas, casas, mc, f_nac, h_nac, lat, lon = calcular_posiciones_base_completa(cliente)
        
        rol = "Eres Patricia Ramirez, astróloga profesional. Redacta de forma extensa y psicológica."
        prompt = f"Analiza Natal para {nombre}: Sol {obtener_signo(planetas['Sol'])}, Luna {obtener_signo(planetas['Luna'])}, Asc {obtener_signo(casas[0])}. Separa con ###"
        
        resultado = consultor_web.consultar_gpt(rol, prompt, 2500)
        partes = [p.strip() for p in resultado.split('###')] if "Error" not in resultado else [""]*5

        return {
            "nombre_cliente": nombre,
            "titulo_informe": "Análisis de Carta Natal",
            "auditoria_tecnica": f"Sol: {deg_to_dms_sign(planetas['Sol'])} | Luna: {deg_to_dms_sign(planetas['Luna'])} | Asc: {deg_to_dms_sign(casas[0])}",
            "aspectos_clave": ["Esencia", "Emoción", "Camino"],
            "interpretacion_sol_signo": partes[1] if len(partes) > 1 else "",
            "interpretacion_luna_signo": partes[2] if len(partes) > 2 else "",
            "interpretacion_asc_signo": partes[3] if len(partes) > 3 else "",
            "interpretacion_personalidad_global": partes[4] if len(partes) > 4 else "",
            "foda": {"fortalezas": ["Liderazgo"], "oportunidades": ["Crecimiento"], "debilidades": ["Dudas"], "amenazas": ["Presión"]}
        }, "informe_astroimpacto.html"
    except Exception as e:
        return None, str(e)

def calcular_posiciones_base_completa(cliente):
    """Función de apoyo para cálculos natales básicos"""
    f = pd.to_datetime(cliente.get('Fecha'))
    h = float(cliente.get('Hora', 12.0))
    lat = limpiar_coordenada(cliente.get('Latitud', 0))
    lon = limpiar_coordenada(cliente.get('Longitud', 0))
    jd = swe.julday(f.year, f.month, f.day, h, swe.GREG_CAL)
    planetas = {}
    for name, id_p in [("Sol", swe.SUN), ("Luna", swe.MOON)]:
        planetas[name] = swe.calc_ut(jd, id_p, FLAGS)[0][0]
    casas, ascmc = swe.houses(jd, lat, lon, b'P')
    return planetas, ascmc, ascmc[1], f, h, lat, lon
