import swisseph as swe
import pandas as pd
import consultor_web
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE EFEMÉRIDES PARA LA NUBE
# ==========================================
swe.set_ephe_path('') 

def obtener_datos_astrologicos(dia, mes, anio, hora, minuto, lat, lon):
    """Calcula las posiciones planetarias básicas usando Swiss Ephemeris"""
    # Cálculo de día juliano (ajustado a UT)
    jd = swe.julday(anio, mes, dia, hora + minuto/60.0)
    
    planetas_ids = {
        "Sol": swe.SUN, "Luna": swe.MOON, "Mercurio": swe.MERCURY, 
        "Venus": swe.VENUS, "Marte": swe.MARS, "Jupiter": swe.JUPITER, 
        "Saturno": swe.SATURN, "Urano": swe.URANUS, "Neptuno": swe.NEPTUNE, 
        "Pluton": swe.PLUTO
    }
    
    posiciones = {}
    for nombre, id_p in planetas_ids.items():
        res = swe.calc_ut(jd, id_p)[0]
        posiciones[nombre] = res % 360

    # Cálculo de Casas y Ascendente
    casas, ascmc = swe.houses(jd, lat, lon, b'P')
    posiciones["Ascendente"] = ascmc[0]
    posiciones["Medio Cielo"] = ascmc[2]
    
    return posiciones, casas

def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Genera el informe completo de Carta Natal"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        rol = "Eres Patricia Ramirez, astróloga profesional de Astroimpacto."
        
        # Simulamos o calculamos aspectos (esto debería venir de tu lógica de cálculo)
        # Aquí integramos el fragmento que me pasaste para los aspectos
        aspectos_interpretados = []
        # Nota: Aquí asumo que tienes una lista 'aspectos_calculados_raw' definida previamente
        # Para este ejemplo, generamos una base para que no salga vacío
        
        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": "Análisis de Carta Natal",
            "aspectos_clave": [
                consultor_web.consultar_gpt(rol, f"Dame una palabra clave para la esencia de {nombre}", 50),
                consultor_web.consultar_gpt(rol, f"Dame una palabra clave para el desafío de {nombre}", 50),
                consultor_web.consultar_gpt(rol, f"Dame una palabra clave para el don de {nombre}", 50)
            ],
            "interpretacion_sol_signo": consultor_web.consultar_gpt(rol, f"Interpreta el Sol para {nombre} de forma profunda.", 300),
            "interpretacion_luna_signo": consultor_web.consultar_gpt(rol, f"Interpreta la Luna emocional para {nombre}.", 300),
            "interpretacion_asc_signo": consultor_web.consultar_gpt(rol, f"Interpreta el Ascendente y camino de vida para {nombre}.", 300),
            "interpretacion_personalidad_global": consultor_web.consultar_gpt(rol, f"Haz una síntesis final de la personalidad de {nombre}.", 500),
            "aspectos_interpretados": aspectos_interpretados,
            "foda": {
                "fortalezas": [consultor_web.consultar_gpt(rol, "Escribe 2 fortalezas natales.", 100)],
                "oportunidades": [consultor_web.consultar_gpt(rol, "Escribe 2 oportunidades de crecimiento.", 100)],
                "debilidades": [consultor_web.consultar_gpt(rol, "Escribe 2 desafíos internos.", 100)],
                "amenazas": [consultor_web.consultar_gpt(rol, "Escribe 2 riesgos externos.", 100)]
            }
        }
        
        return datos_para_ia, "informe_astroimpacto.html"
    except Exception as e:
        return None, f"Error en Natal: {str(e)}"

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    """Genera el informe de Revolución Solar"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        rol = "Eres Patricia Ramirez, astróloga profesional."
        
        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": "Revolución Solar",
            "perspectivas": {
                "transformacion": consultor_web.consultar_gpt(rol, "Define el reto de transformación de este año en 2 líneas.", 150),
                "oportunidades": consultor_web.consultar_gpt(rol, "Define la mayor oportunidad en 2 líneas.", 150),
                "cambio": consultor_web.consultar_gpt(rol, "Define dónde estará el cambio principal en 2 líneas.", 150),
                "relaciones": consultor_web.consultar_gpt(rol, "Define el clima vincular en 2 líneas.", 150)
            },
            "revolucion_solar_general_1": consultor_web.consultar_gpt(rol, f"Clima general de la Revolución Solar para {nombre} en {lugar_rs}.", 400),
            "situacion_laboral_economica": consultor_web.consultar_gpt(rol, "Analiza el panorama laboral y económico.", 300),
            "situacion_emocional": consultor_web.consultar_gpt(rol, "Analiza el panorama emocional y afectivo.", 300),
            "panorama_trimestral": [
                {"titulo": "Trimestre 1", "texto": consultor_web.consultar_gpt(rol, "Proyección para los meses 1-3.", 150)},
                {"titulo": "Trimestre 2", "texto": consultor_web.consultar_gpt(rol, "Proyección para los meses 4-6.", 150)},
                {"titulo": "Trimestre 3", "texto": consultor_web.consultar_gpt(rol, "Proyección para los meses 7-9.", 150)},
                {"titulo": "Trimestre 4", "texto": consultor_web.consultar_gpt(rol, "Proyección para los meses 10-12.", 150)}
            ]
        }
        return datos_para_ia, "informe_astroimpacto_rs.html"
    except Exception as e:
        return None, f"Error en RS: {str(e)}"

def procesar_transitos_con_ia(cliente, tipo_obj, id_cli):
    """Genera el informe de Tránsitos Anuales"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        rol = "Patricia Ramirez, Astróloga."
        
        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": "Pronóstico de Tránsitos",
            "frase_anual_corta": consultor_web.consultar_gpt(rol, "Dame un lema de 5 palabras para el año.", 50),
            "analisis_clima_anual": consultor_web.consultar_gpt(rol, "Análisis del clima astrológico anual.", 400),
            "oportunidad_anual": consultor_web.consultar_gpt(rol, "La gran oportunidad del año.", 200),
            "atencion_anual": consultor_web.consultar_gpt(rol, "A qué debe prestar atención.", 200),
            "habito_recomendado": consultor_web.consultar_gpt(rol, "Un hábito espiritual sugerido.", 100),
            "calendario_por_meses": {
                "Enero": [{"fecha": "15/01", "texto_efecto": "Inicio con fuerza Marte-Júpiter..."}],
                "Febrero": [{"fecha": "10/02", "texto_efecto": "Revisión emocional con Venus..."}]
                # Se llenaría con el bucle de tránsitos reales
            }
        }
        return datos_para_ia, "informe_astroimpacto_transitos.html"
    except Exception as e:
        return None, f"Error en Tránsitos: {str(e)}"
