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
# FUNCIONES DE PROCESAMIENTO (MÁXIMA PROFUNDIDAD)
# ==========================================

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    """Genera el informe de Revolución Solar COMPLETO (Incluye Natal, Tránsitos y Progresiones)"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        rol = "Eres Patricia Ramirez, astróloga profesional de Astroimpacto. Tu estilo es profundo, psicológico, evolutivo y muy detallado. No uses listas, escribe párrafos fluidos y elegantes."
        
        # PROMPT MAESTRO AMPLIADO: Pedimos las 11 secciones necesarias
        prompt = f"""
        Realiza una Revolución Solar exhaustiva para {nombre} (Relocalizada en {lugar_rs}).
        Debes generar textos largos y significativos. Responde exactamente en este formato, separando con '###':

        1. Reto de transformación anual (3 líneas profundas) ###
        2. Oportunidad mayor del año (3 líneas profundas) ###
        3. Cambio principal en la estructura de vida (3 líneas profundas) ###
        4. Clima vincular y de relaciones (3 líneas profundas) ###
        5. Interpretación extensa del Clima General de la Revolución Solar. Habla del Ascendente Anual y la posición del Sol. (Mínimo 4 párrafos largos) ###
        6. Panorama Laboral y Económico detallado (Mínimo 3 párrafos) ###
        7. Panorama Emocional, Hogar y Salud interna (Mínimo 3 párrafos) ###
        8. Introducción inspiradora al informe (1 párrafo cálido) ###
        9. Resumen Psicológico de su Carta Natal Base (Mínimo 3 párrafos sobre su esencia) ###
        10. Análisis de los Tránsitos Lentos actuales (Plutón, Saturno, Júpiter) y cómo afectan este año (Mínimo 3 párrafos) ###
        11. Análisis de sus Progresiones Secundarias y su estado de maduración interna actual (Mínimo 3 párrafos)
        """
        
        # Aumentamos los tokens al máximo (3500) para permitir la extensión solicitada
        resultado = consultor_web.consultar_gpt(rol, prompt, 3500)
        
        # Fallback en caso de error de conexión
        if "Error" in resultado or not resultado:
            partes = ["Error de carga"] * 11
        else:
            partes = [p.strip() for p in resultado.split('###')]

        # Construcción del diccionario con todas las llaves que espera la web
        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": f"Revolución Solar {datetime.now().year}",
            "perspectivas": {
                "transformacion": partes[0] if len(partes) > 0 else "",
                "oportunidades": partes[1] if len(partes) > 1 else "",
                "cambio": partes[2] if len(partes) > 2 else "",
                "relaciones": partes[3] if len(partes) > 3 else ""
            },
            "revolucion_solar_general_1": partes[4] if len(partes) > 4 else "Contenido en proceso...",
            "situacion_laboral_economica": partes[5] if len(partes) > 5 else "Contenido en proceso...",
            "situacion_emocional": partes[6] if len(partes) > 6 else "Contenido en proceso...",
            "intro_texto": partes[7] if len(partes) > 7 else "Bienvenido a tu informe.",
            "carta_natal_resumen": partes[8] if len(partes) > 8 else "Resumen natal no disponible.",
            "transitos_personales": partes[9] if len(partes) > 9 else "Tránsitos no disponibles.",
            "progresiones_secundarias": partes[10] if len(partes) > 10 else "Progresiones no disponibles.",
            "panorama_trimestral": [
                {"titulo": "Trimestre 1: Inicios", "texto": "Periodo de gran actividad inicial donde las semillas del año comienzan a brotar."},
                {"titulo": "Trimestre 2: Consolidación", "texto": "Momento de revisar los pasos dados y asentar las bases materiales."},
                {"titulo": "Trimestre 3: Cosecha", "texto": "Fase de visibilidad donde los resultados del esfuerzo anual se manifiestan."},
                {"titulo": "Trimestre 4: Integración", "texto": "Balance final y preparación para el cierre del ciclo solar actual."}
            ]
        }
        
        return datos_para_ia, "informe_astroimpacto_rs.html"
    except Exception as e:
        return None, f"Error en Revolución Solar: {str(e)}"

def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Genera el informe profundo de Carta Natal"""
    try:
        nombre = cliente.get('Nombres', 'Consultante')
        rol = "Eres Patricia Ramirez, astróloga profesional. Redacta de forma extensa y psicológica."
        
        prompt = f"""
        Realiza un análisis natal profundo para {nombre}. Responde separando con '###':
        Palabras Clave ###
        Interpretación extensa del Sol (3 párrafos) ###
        Interpretación extensa de la Luna (3 párrafos) ###
        Interpretación extensa del Ascendente (3 párrafos) ###
        Gran síntesis final de personalidad (4 párrafos)
        """
        
        resultado = consultor_web.consultar_gpt(rol, prompt, 2500)
        partes = [p.strip() for p in resultado.split('###')] if "Error" not in resultado else [""]*5

        datos_para_ia = {
            "nombre_cliente": nombre,
            "titulo_informe": "Análisis de Carta Natal",
            "aspectos_clave": partes[0].split(' - ') if len(partes) > 0 else ["Sol", "Luna", "Asc"],
            "interpretacion_sol_signo": partes[1] if len(partes) > 1 else "",
            "interpretacion_luna_signo": partes[2] if len(partes) > 2 else "",
            "interpretacion_asc_signo": partes[3] if len(partes) > 3 else "",
            "interpretacion_personalidad_global": partes[4] if len(partes) > 4 else "",
            "foda": {"fortalezas": ["Liderazgo"], "oportunidades": ["Crecimiento"], "debilidades": ["Dudas"], "amenazas": ["Presión"]}
        }
        return datos_para_ia, "informe_astroimpacto.html"
    except Exception as e:
        return None, str(e)
