import swisseph as swe
import pandas as pd
import consultor_ia
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE EFEMÉRIDES PARA LA NUBE
# ==========================================
# En la web dejamos la ruta vacía para que use las efemérides integradas
swe.set_ephe_path('') 

def obtener_datos_astrologicos(dia, mes, anio, hora, minuto, lat, lon):
    """Calcula las posiciones planetarias básicas usando Swiss Ephemeris"""
    # Convertir hora a UT (ajustar según zona horaria si es necesario)
    jd = swe.julday(anio, mes, dia, hora + minuto/60.0)
    
    planetas = {
        "Sol": swe.get_obj_name(swe.SUN),
        "Luna": swe.get_obj_name(swe.MOON),
        "Mercurio": swe.get_obj_name(swe.MERCURY),
        "Venus": swe.get_obj_name(swe.VENUS),
        "Marte": swe.get_obj_name(swe.MARS),
        "Jupiter": swe.get_obj_name(swe.JUPITER),
        "Saturno": swe.get_obj_name(swe.SATURN),
        "Urano": swe.get_obj_name(swe.URANUS),
        "Neptuno": swe.get_obj_name(swe.NEPTUNE),
        "Pluton": swe.get_obj_name(swe.PLUTO)
    }
    
    posiciones = {}
    for nombre, id_planeta in {
        "Sol": swe.SUN, "Luna": swe.MOON, "Mercurio": swe.MERCURY, 
        "Venus": swe.VENUS, "Marte": swe.MARS, "Jupiter": swe.JUPITER, 
        "Saturno": swe.SATURN, "Urano": swe.URANUS, "Neptuno": swe.NEPTUNE, 
        "Pluton": swe.PLUTO
    }.items():
        res = swe.calc_ut(jd, id_planeta)[0]
        posiciones[nombre] = res % 360

    # Cálculo de Casas (Placidus por defecto)
    casas, ascmc = swe.houses(jd, lat, lon, b'P')
    posiciones["Ascendente"] = ascmc[0]
    posiciones["Medio Cielo"] = ascmc[2]
    
    return posiciones

# ==========================================
# FUNCIONES DE PROCESAMIENTO CON IA
# ==========================================

def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Genera el borrador de Carta Natal"""
    try:
        # Extraer datos del cliente (ajustar nombres de columnas según tu Excel)
        nombre = cliente.get('Nombres', 'Consultante')
        
        # Aquí irían tus cálculos matemáticos específicos de Astroimpacto
        # ...
        
        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": "Análisis de Carta Natal",
            "aspectos_clave": ["Propósito", "Estructura", "Evolución"],
            "interpretacion_sol_signo": "Borrador generado por el sistema...",
            "interpretacion_luna_signo": "Borrador generado por el sistema...",
            "interpretacion_asc_signo": "Borrador generado por el sistema...",
            "interpretacion_personalidad_global": "Análisis síntesis en proceso...",
            "foda": {"fortalezas": [""], "oportunidades": [""], "debilidades": [""], "amenazas": [""]}
        }
        
        # Llamada a tu módulo de IA
        # datos_finales = consultor_ia.redactar_natal(datos_para_ia)
        
        return datos_para_ia, "informe_astroimpacto.html"
    except Exception as e:
        return None, str(e)

def procesar_transitos_con_ia(cliente, tipo_obj, id_cli):
    """Genera el borrador de Pronóstico Anual (Tránsitos)"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        
        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": "Pronóstico de Tránsitos Anuales",
            "frase_anual_corta": "Un año de integración y cosecha",
            "analisis_clima_anual": "El clima general del año sugiere...",
            "calendario_por_meses": {} # Estructura para tus eventos mensuales
        }
        
        return datos_para_ia, "informe_astroimpacto_transitos.html"
    except Exception as e:
        return None, str(e)

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    """Genera el borrador de Revolución Solar"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        
        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": "Revolución Solar",
            "perspectivas": {
                "transformacion": "", "oportunidades": "", "cambio": "", "relaciones": ""
            },
            "revolucion_solar_general_1": "El ascendente anual marca un año de...",
            "panorama_trimestral": [
                {"titulo": "Trimestre 1", "texto": ""},
                {"titulo": "Trimestre 2", "texto": ""},
                {"titulo": "Trimestre 3", "texto": ""},
                {"titulo": "Trimestre 4", "texto": ""}
            ]
        }
        
        return datos_para_ia, "informe_astroimpacto_rs.html"
    except Exception as e:
        return None, str(e)