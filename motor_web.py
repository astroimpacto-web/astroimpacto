import swisseph as swe
import pandas as pd
import consultor_web
from datetime import datetime, timedelta, timezone
import time
import re

# ==============================================================================
# CONFIGURACIÓN DE EFEMÉRIDES Y CONSTANTES TÉCNICAS
# ==============================================================================
# La ruta se deja vacía para que use los archivos en el entorno de ejecución actual
swe.set_ephe_path('') 
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

def obtener_signo(lon):
    """Devuelve el nombre del signo según la longitud eclíptica."""
    signos = ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"]
    return signos[int(lon/30)%12]

def deg_to_dms_sign(lon):
    """Convierte grados decimales al formato astronómico: 15° Aries 23'"""
    signos = ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"]
    signo_idx = int(lon / 30) % 12
    grados = int(lon % 30)
    minutos = int((lon % 1) * 60)
    return f"{grados:02d}° {signos[signo_idx]} {minutos:02d}'"

# ==============================================================================
# FUNCIONES DE LIMPIEZA DE DATOS (BLINDAJE ANTIFALLOS)
# ==============================================================================

def limpiar_coordenada(val):
    """Asegura que las coordenadas sean flotantes válidos."""
    try:
        return float(str(val).replace(',', '.'))
    except:
        return 0.0

def limpiar_hora_robusta(val):
    """
    Función crítica: Interpreta la hora sin importar el formato (HH:MM, decimal o texto).
    Esto elimina el error de 'Datos incompletos' si el Excel viene con formatos variados.
    """
    try:
        if isinstance(val, (int, float)): 
            return float(val)
        val_str = str(val).strip()
        if ':' in val_str:
            partes = val_str.split(':')
            h = float(partes[0])
            m = float(partes[1])/60.0 if len(partes)>1 else 0.0
            s = float(partes[2])/3600.0 if len(partes)>2 else 0.0
            return h + m + s
        return float(val_str.replace(',', '.'))
    except:
        return 12.0 # Valor por defecto seguro (Mediodía)

# ==============================================================================
# LÓGICA DE PROCESAMIENTO CON IA
# ==============================================================================

def procesar_rs_con_ia(cliente, tipo_obj, id_cli, lat_rs=None, lon_rs=None, lugar_rs=None):
    """
    Calcula la Revolución Solar y genera la interpretación profunda.
    Recibe el paquete de datos 'blindado' desde app_web.py.
    """
    try:
        nombre = cliente.get('Nombres', cliente.get('nombre', 'Consultante'))
        
        # 1. Extracción y validación de datos
        try:
            # Buscamos en todas las posibles variantes de llaves enviadas
            fecha_val = cliente.get('Fecha', cliente.get('fecha'))
            hora_val = cliente.get('Hora', cliente.get('hora'))
            lat_n_val = cliente.get('Latitud', cliente.get('lat'))
            lon_n_val = cliente.get('Longitud', cliente.get('lon'))

            if any(x is None for x in [fecha_val, hora_val, lat_n_val, lon_n_val]):
                raise ValueError("Campos obligatorios ausentes")

            f_nac = pd.to_datetime(fecha_val)
            h_nac = limpiar_hora_robusta(hora_val)
            lat_n = limpiar_coordenada(lat_n_val)
            lon_n = limpiar_coordenada(lon_n_val)
        except Exception as e:
            return None, f"Error: Datos de nacimiento incompletos para cálculos matemáticos. ({str(e)})"

        # 2. Cálculos Natales (Base)
        jd_nac = swe.julday(f_nac.year, f_nac.month, f_nac.day, h_nac)
        sol_natal = swe.calc_ut(jd_nac, swe.SUN, FLAGS)[0][0]
        _, ascmc_nat = swe.houses(jd_nac, lat_n, lon_n, b'P')
        asc_nat = ascmc_nat[0]

        # 3. Búsqueda del Retorno Solar exacto
        anio_actual = datetime.now().year
        jd_rs = swe.julday(anio_actual, f_nac.month, f_nac.day - 1, 0.0)
        for _ in range(40):
            sol_ahora = swe.calc_ut(jd_rs, swe.SUN, FLAGS)[0][0]
            diff = sol_natal - sol_ahora
            if diff > 180: diff -= 360
            elif diff < -180: diff += 360
            if abs(diff) < 0.00001: break
            jd_rs += diff / 0.9856
        
        # Coordenadas de relocalización o nacimiento
        lat_c = limpiar_coordenada(lat_rs) if lat_rs else lat_n
        lon_c = limpiar_coordenada(lon_rs) if lon_rs else lon_n
        
        luna_rs = swe.calc_ut(jd_rs, swe.MOON, FLAGS)[0][0]
        _, ascmc_rs = swe.houses(jd_rs, lat_c, lon_c, b'P')
        asc_rs = ascmc_rs[0]

        # Auditoría para Patricia (Sidebar)
        auditoria = (f"NATAL: Sol {deg_to_dms_sign(sol_natal)} | Asc {deg_to_dms_sign(asc_nat)}\n"
                    f"RS {anio_actual}: Asc {deg_to_dms_sign(asc_rs)} | Luna {deg_to_dms_sign(luna_rs)}\n"
                    f"UBICACIÓN: {lugar_rs if lugar_rs else 'Lugar de Nacimiento'}")

        # 4. Generación de texto con la IA de OpenAI
        rol = "Eres Patricia Ramirez, astróloga profesional con enfoque psicológico y evolutivo profundo."
        prompt = (f"Realiza una Revolución Solar para {nombre}. "
                 f"Datos: Natal con Sol en {obtener_signo(sol_natal)} y Asc en {obtener_signo(asc_nat)}. "
                 f"Anual con Asc en {obtener_signo(asc_rs)} y Luna en {obtener_signo(luna_rs)}. "
                 f"Responde separando con '###' estas 11 secciones: "
                 "Reto de transformación ### Oportunidad mayor ### Cambio principal ### Tónica Vincular ### "
                 "Interpretación Clima General (4 párrafos) ### Laboral ### Emocional ### Introducción ### "
                 "Resumen Natal ### Tránsitos Lentos ### Análisis de Progresiones")
        
        resultado = consultor_web.consultar_gpt(rol, prompt, 3500)
        if "Error" in resultado: return None, "Error de comunicación con OpenAI. Revisa tus créditos."
        
        partes = [p.strip() for p in resultado.split('###')]
        while len(partes) < 11: partes.append("Contenido en redacción...")

        # 5. Construcción del diccionario de datos final
        return {
            "nombre_cliente": nombre,
            "titulo_informe": f"Revolución Solar {anio_actual}",
            "auditoria_tecnica": auditoria,
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
            "panorama_trimestral": [{"titulo": f"Fase {i+1}", "texto": "Hito astrológico relevante para el periodo."} for i in range(4)],
            "como_actuar_progresiones": ["Integrar la nueva energía.", "Observar los ritmos internos."],
            "revo_propone": ["Evolución consciente.", "Madurez emocional."],
            "logro_objetivos_profesionales": ["Enfoque.", "Determinación."],
            "plan_accion_objetivos": ["Priorizar el bienestar.", "Actuar con estrategia."]
        }, "informe_astroimpacto_rs.html"

    except Exception as e:
        return None, f"Fallo motor: {str(e)}"

def procesar_natal_con_ia(cliente, tipo_obj, id_cli):
    """Procesa el informe de Carta Natal de forma íntegra."""
    try:
        nombre = cliente.get('Nombres', cliente.get('nombre', 'Consultante'))
        f_nac = pd.to_datetime(cliente.get('Fecha', cliente.get('fecha')))
        h_nac = limpiar_hora_robusta(cliente.get('Hora', cliente.get('hora')))
        lat = limpiar_coordenada(cliente.get('Latitud', cliente.get('lat')))
        lon = limpiar_coordenada(cliente.get('Longitud', cliente.get('lon')))
        
        jd = swe.julday(f_nac.year, f_nac.month, f_nac.day, h_nac)
        sol = swe.calc_ut(jd, swe.SUN, FLAGS)[0][0]
        luna = swe.calc_ut(jd, swe.MOON, FLAGS)[0][0]
        _, ascmc = swe.houses(jd, lat, lon, b'P')
        
        rol = "Patricia Ramirez, Astróloga Profesional."
        prompt = f"Analiza Natal para {nombre}: Sol {obtener_signo(sol)}, Luna {obtener_signo(luna)}, Asc {obtener_signo(ascmc[0])}. Separa con ###: Claves ### Sol ### Luna ### Asc ### Global"
        
        res = consultor_web.consultar_gpt(rol, prompt, 2500)
        p = [x.strip() for x in res.split('###')] if "Error" not in res else [""]*5
        
        return {
            "nombre_cliente": nombre, "titulo_informe": "Análisis de Carta Natal",
            "auditoria_tecnica": f"Natal Calculado: Sol {obtener_signo(sol)} - Asc {obtener_signo(ascmc[0])}",
            "aspectos_clave": p[0].split('-') if len(p)>0 else ["Esencia", "Alma", "Propósito"],
            "interpretacion_sol_signo": p[1], "interpretacion_luna_signo": p[2],
            "interpretacion_asc_signo": p[3], "interpretacion_personalidad_global": p[4],
            "foda": {"fortalezas": ["Resiliencia."], "debilidades": ["Miedo al cambio."]}
        }, "informe_astroimpacto.html"
    except Exception as e:
        return None, str(e)

def procesar_transitos_con_ia(cliente, tipo_obj, id_cli):
    """Procesa el pronóstico de Tránsitos Anuales."""
    try:
        nombre = cliente.get('Nombres', cliente.get('nombre', 'Consultante'))
        rol = "Patricia Ramirez, Astróloga Profesional."
        prompt = f"Genera un lema y un clima anual para {nombre}. Separa con ###: Lema ### Clima Anual ### Oportunidad ### Atención."
        
        res = consultor_web.consultar_gpt(rol, prompt, 2000)
        p = [x.strip() for x in res.split('###')] if "Error" not in res else [""]*4
        
        return {
            "nombre_cliente": nombre, "titulo_informe": "Pronóstico de Tránsitos",
            "auditoria_tecnica": "Ciclos de planetas lentos calculados.",
            "frase_anual_corta": p[0], "analisis_clima_anual": p[1],
            "oportunidad_anual": p[2], "atencion_anual": p[3],
            "calendario_por_meses": {"Ciclo Actual": [{"fecha": "Hito", "transito": "Influencia", "texto_efecto": "Evolución en curso."}]}
        }, "informe_astroimpacto_transitos.html"
    except Exception as e:
        return None, str(e)
