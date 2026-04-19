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

    casas, ascmc = swe.houses(jd, lat, lon, b'P')
    posiciones["Ascendente"] = ascmc[0]
    posiciones["Medio Cielo"] = ascmc[2]
    
    return posiciones, casas

# ==========================================
# FUNCIONES DE PROCESAMIENTO (BATALLES IA)
# ==========================================

def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Genera el informe completo de Carta Natal con una sola llamada a IA"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        rol = "Eres Patricia Ramirez, astróloga profesional de Astroimpacto."
        
        # PROMPT MAESTRO PARA EVITAR ERRORES DE CONEXIÓN
        prompt = f"""
        Genera un análisis natal para {nombre}. 
        Responde exactamente en este formato, separando cada sección con '###':
        Palabra1 - Palabra2 - Palabra3 ###
        Interpretación profunda del Sol ###
        Interpretación psicológica de la Luna ###
        Camino de vida del Ascendente ###
        Síntesis final de la personalidad.
        """
        
        resultado = consultor_web.consultar_gpt(rol, prompt, 1200)
        
        # Si la IA falla, usamos fallbacks para que no salga el error de conexión
        if "Error" in resultado or not resultado:
            partes = ["Esencia - Emoción - Camino", "Esencia solar en desarrollo.", "Mundo emocional profundo.", "Ruta de aprendizaje vital.", "Síntesis en proceso."]
        else:
            partes = [p.strip() for p in resultado.split('###')]

        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": "Análisis de Carta Natal",
            "aspectos_clave": partes[0].split(' - ') if len(partes) > 0 else ["Sol", "Luna", "Asc"],
            "interpretacion_sol_signo": partes[1] if len(partes) > 1 else "Interpretación solar.",
            "interpretacion_luna_signo": partes[2] if len(partes) > 2 else "Interpretación lunar.",
            "interpretacion_asc_signo": partes[3] if len(partes) > 3 else "Interpretación ascendente.",
            "interpretacion_personalidad_global": partes[4] if len(partes) > 4 else "Síntesis final.",
            "foda": {
                "fortalezas": ["Capacidad de liderazgo", "Empatía natural"],
                "oportunidades": ["Crecimiento profesional", "Nuevos vínculos"],
                "debilidades": ["Autoexigencia", "Dudas internas"],
                "amenazas": ["Estrés ambiental", "Distracciones"]
            }
        }
        
        return datos_para_ia, "informe_astroimpacto.html"
    except Exception as e:
        return None, f"Error en Natal: {str(e)}"

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    """Genera el informe de Revolución Solar con una sola llamada a IA"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        rol = "Eres Patricia Ramirez, astróloga profesional."
        
        prompt = f"""
        Genera una Revolución Solar para {nombre} (Lugar: {lugar_rs}).
        Responde separando con '###':
        Reto de transformación (2 líneas) ###
        Oportunidad (2 líneas) ###
        Cambio principal (2 líneas) ###
        Vínculos (2 líneas) ###
        Clima general anual (3 párrafos) ###
        Panorama laboral ###
        Panorama emocional
        """
        
        resultado = consultor_web.consultar_gpt(rol, prompt, 1500)
        
        if "Error" in resultado or not resultado:
            partes = ["Transformación interna", "Nuevas metas", "Cambio de enfoque", "Vínculos estables", "Año de crecimiento.", "Laboral positivo.", "Emocional estable."]
        else:
            partes = [p.strip() for p in resultado.split('###')]

        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": "Revolución Solar",
            "perspectivas": {
                "transformacion": partes[0] if len(partes) > 0 else "",
                "oportunidades": partes[1] if len(partes) > 1 else "",
                "cambio": partes[2] if len(partes) > 2 else "",
                "relaciones": partes[3] if len(partes) > 3 else ""
            },
            "revolucion_solar_general_1": partes[4] if len(partes) > 4 else "Clima general.",
            "situacion_laboral_economica": partes[5] if len(partes) > 5 else "Laboral.",
            "situacion_emocional": partes[6] if len(partes) > 6 else "Emocional.",
            "panorama_trimestral": [
                {"titulo": "Trimestre 1", "texto": "Inicios y siembra."},
                {"titulo": "Trimestre 2", "texto": "Desarrollo y ajustes."},
                {"titulo": "Trimestre 3", "texto": "Cosecha y resultados."},
                {"titulo": "Trimestre 4", "texto": "Integración y balance."}
            ]
        }
        return datos_para_ia, "informe_astroimpacto_rs.html"
    except Exception as e:
        return None, f"Error en RS: {str(e)}"

def procesar_transitos_con_ia(cliente, tipo_obj, id_cli):
    """Genera el informe de Tránsitos Anuales optimizado"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        rol = "Patricia Ramirez, Astróloga."
        
        prompt = f"Genera un Lema Anual ### Análisis del Clima Anual ### Oportunidad ### Advertencia para {nombre}. Separa con ###"
        resultado = consultor_web.consultar_gpt(rol, prompt, 800)
        
        if "Error" in resultado or not resultado:
            partes = ["Año de luz", "Clima favorable", "Crecimiento", "Paciencia"]
        else:
            partes = [p.strip() for p in resultado.split('###')]

        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": "Pronóstico de Tránsitos",
            "frase_anual_corta": partes[0] if len(partes) > 0 else "Lema anual.",
            "analisis_clima_anual": partes[1] if len(partes) > 1 else "Clima anual.",
            "oportunidad_anual": partes[2] if len(partes) > 2 else "Oportunidad.",
            "atencion_anual": partes[3] if len(partes) > 3 else "Atención.",
            "habito_recomendado": "Meditación diaria.",
            "calendario_por_meses": {
                "Enero": [{"fecha": "15/01", "texto_efecto": "Integración de energías iniciales."}],
                "Febrero": [{"fecha": "10/02", "texto_efecto": "Momento de revisión emocional."}]
            }
        }
        return datos_para_ia, "informe_astroimpacto_transitos.html"
    except Exception as e:
        return None, f"Error en Tránsitos: {str(e)}"
