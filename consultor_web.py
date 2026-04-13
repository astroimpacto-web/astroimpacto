import openai
import os

import streamlit as st
openai.api_key = st.secrets["OPENAI_API_KEY"]
try:
    client = openai.OpenAI(api_key=API_KEY)
except:
    client = None

def consultar_gpt(sistema, usuario, max_tokens=250):
    if not client: return "<p>Error de conexión IA</p>"
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
            temperature=0.7, max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Error IA: {e}")
        return f"<p>Error técnico: {e}</p>"

def generar_interpretacion_modos_ia(modos):
    rol = "Eres Patricia Ramirez, astróloga experta. Tono analítico. Usa HTML simple (<p>)."
    
    # Lógica simple para texto
    dominante = max(modos, key=modos.get)
    puntaje_dom = modos[dominante]
    
    prompt = f"""
    Analiza este Balance de Modalidades (Sistema de 50 Puntos):
    Cardinal: {modos['Cardinal']} puntos
    Fijo: {modos['Fijo']} puntos
    Mutable: {modos['Mutable']} puntos
    (El equilibrio ideal es aprox 16.6 puntos).
    
    Interpreta el modo dominante ({dominante}) y qué significa tener {puntaje_dom} puntos en él.
    """
    return consultar_gpt(rol, prompt, 300)

def generar_interpretacion_elementos_ia(elementos):
    rol = "Eres Patricia Ramirez, astróloga humanística. Usa HTML simple (<p>)."
    
    dominante = max(elementos, key=elementos.get)
    ausente = min(elementos, key=elementos.get)
    valor_ausente = elementos[ausente]
    
    prompt = f"""
    Interpreta el Balance de Elementos:
    Fuego: {elementos['Fuego']} - Tierra: {elementos['Tierra']} 
    Aire: {elementos['Aire']} - Agua: {elementos['Agua']}
    
    Elemento Dominante: {dominante}.
    Elemento Menor: {ausente}.
    
    Instrucciones:
    1. Interpreta la psicología del elemento dominante ({dominante}) sin mencionar "puntos".
    2. Si el elemento menor ({ausente}) es muy bajo (menos de 5), explica el desafío de esa carencia o "hambre" energética.
    3. Redacta como un consejo fluido para el cliente.
    """
    return consultar_gpt(rol, prompt, 450)
    rol = "Eres Patricia Ramirez, astróloga humanística. Usa HTML simple (<p>)."
    
    dominante = max(elementos, key=elementos.get)
    ausente = min(elementos, key=elementos.get)
    
    prompt = f"""
    Interpreta el Balance Energético (Sistema de 50 Puntos):
    Fuego: {elementos['Fuego']} puntos
    Tierra: {elementos['Tierra']} puntos
    Aire: {elementos['Aire']} puntos
    Agua: {elementos['Agua']} puntos
    (El equilibrio ideal es 12.5 puntos).
    
    1. Interpreta el elemento dominante ({dominante}).
    2. Si el elemento más bajo ({ausente}) tiene menos de 5 puntos, explica el desafío de esa carencia.
    """
    return consultar_gpt(rol, prompt, 350)

def generar_interpretacion_natal_ia(datos, nombre, genero, lista_aspectos_nombres):
    """
    Retorna 8 VALORES CORREGIDOS para evitar cortes y datos vacíos.
    """
    if client is None: return ("Error", "Error", {}, "Error", "Error", [], "Error", "Error")

    print(f"   🤖 Consultando IA (V2 Mejorada) para {nombre}...")
    rol = "Eres Patricia Ramirez, astróloga de Astroimpacto. Tono empático, profundo y claro. Usa HTML <p>."

    # 1. SOL (Aumentamos tokens a 500)
    txt_sol = consultar_gpt(rol, f"Interpreta Sol en {datos['sol_signo']} Casa {datos['sol_casa']} para {nombre}. Enfócate en su identidad y brillo personal. Termina la idea completa.", 500)
    
    # 2. LUNA (Aumentamos tokens a 500)
    txt_luna = consultar_gpt(rol, f"Interpreta Luna en {datos['luna_signo']} para {nombre}. Explica su mundo emocional y refugio. Asegúrate de cerrar la frase final.", 500)
    
    # 3. DETALLES LUNA (LÓGICA NUEVA MÁS ROBUSTA)
    # Pedimos formato estricto sin etiquetas para facilitar la limpieza
    prompt_detalles = f"""
    Para una Luna en {datos['luna_signo']}, necesito 3 frases cortas y directas.
    Responde EXACTAMENTE en este formato de 3 líneas (sin títulos, sin guiones):
    [Frase sobre su mecanismo de defensa]
    [Frase sobre su talento emocional]
    [Frase sobre lo que más necesita para sentirse seguro]
    """
    resp_items = consultar_gpt(rol, prompt_detalles, 200)
    
    # Valores por defecto por si falla
    detalles_luna = {
        "mecanismo": "Refugio en lo conocido.", 
        "talento": "Sensibilidad profunda.", 
        "necesidad": "Seguridad emocional."
    }
    
    try:
        # Limpiamos líneas vacías y quitamos guiones si la IA los puso
        lines = [l.strip().replace("- ", "").replace("* ", "") for l in resp_items.split('\n') if l.strip()]
        if len(lines) >= 3:
            detalles_luna = {
                "mecanismo": lines[0], 
                "talento": lines[1], 
                "necesidad": lines[2]
            }
        else:
            print(f"⚠️ Alerta: La IA devolvió pocas líneas para detalles luna: {lines}")
    except Exception as e: 
        print(f"⚠️ Error procesando detalles luna: {e}")

    # 4. ASCENDENTE (Aumentamos tokens a 500)
    txt_asc = consultar_gpt(rol, f"Interpreta Ascendente en {datos['asc_signo']} para {nombre}. Su aprendizaje y cómo lo ven los demás. Termina la idea.", 500)
    
    # 5. GLOBAL (Aumentamos tokens a 600 - es la síntesis)
    txt_global = consultar_gpt(rol, f"Haz una síntesis breve integrando Sol en {datos['sol_signo']}, Luna en {datos['luna_signo']} y Ascendente en {datos['asc_signo']}. ¿Cómo interactúan estas tres energías?", 600)
    
    # 6. ASPECTOS
    aspectos_interpretados = []
    for asp in lista_aspectos_nombres[:6]:
        # Aumentamos un poco tokens para aspectos complejos
        txt = consultar_gpt(rol, f"Interpreta brevemente el aspecto: {asp}. Qué reto o ventaja da.", 250)
        aspectos_interpretados.append({"titulo": asp, "interpretacion": txt})
        
    # 7. MODOS
    txt_modos = generar_interpretacion_modos_ia(datos['modos'])
    
    # 8. ELEMENTOS
    txt_elementos = generar_interpretacion_elementos_ia(datos['elementos'])

    return txt_sol, txt_luna, detalles_luna, txt_asc, txt_global, aspectos_interpretados, txt_modos, txt_elementos
    """
    Retorna 8 VALORES: Sol, Luna, Detalles, Asc, Global, Aspectos, Modos, Elementos.
    """
    if client is None: return ("Error", "Error", {}, "Error", "Error", [], "Error", "Error")

    print(f"   🤖 Consultando IA para {nombre}...")
    rol = "Eres Patricia Ramirez, astróloga de Astroimpacto. Tono empático y profundo. Usa HTML <p>."

    # 1. SOL
    txt_sol = consultar_gpt(rol, f"Interpreta Sol en {datos['sol_signo']} Casa {datos['sol_casa']} para {nombre}.", 300)
    
    # 2. LUNA
    txt_luna = consultar_gpt(rol, f"Interpreta Luna en {datos['luna_signo']} para {nombre}. Su refugio emocional.", 250)
    
    # 3. DETALLES LUNA
    resp_items = consultar_gpt(rol, f"Para Luna en {datos['luna_signo']}, lista 3 lineas: Mecanismo Defensa, Talento, Necesidad.", 100)
    detalles_luna = {"mecanismo": "-", "talento": "-", "necesidad": "-"}
    try:
        lines = [l.strip() for l in resp_items.split('\n') if l.strip()]
        if len(lines) >= 3:
            detalles_luna = {"mecanismo": lines[0], "talento": lines[1], "necesidad": lines[2]}
    except: pass

    # 4. ASCENDENTE
    txt_asc = consultar_gpt(rol, f"Interpreta Ascendente en {datos['asc_signo']} para {nombre}. Su aprendizaje.", 250)
    
    # 5. GLOBAL
    txt_global = consultar_gpt(rol, f"Sintesis breve Sol {datos['sol_signo']}, Luna {datos['luna_signo']}, Asc {datos['asc_signo']}.", 300)
    
    # 6. ASPECTOS
    aspectos_interpretados = []
    for asp in lista_aspectos_nombres[:6]:
        txt = consultar_gpt(rol, f"Interpreta brevemente aspecto: {asp}", 150)
        aspectos_interpretados.append({"titulo": asp, "interpretacion": txt})
        
    # 7. MODOS (Balance 50 pts)
def generar_interpretacion_modos_ia(modos):
    rol = "Eres Patricia Ramirez, astróloga experta. Tono analítico pero cercano. Usa HTML simple (<p>)."
    
    dominante = max(modos, key=modos.get)
    
    prompt = f"""
    Analiza este Balance de Modalidades del cliente:
    Cardinal: {modos['Cardinal']} - Fijo: {modos['Fijo']} - Mutable: {modos['Mutable']}
    
    El modo dominante es: {dominante}.
    
    Instrucciones:
    1. Explica qué significa psicológicamente que su energía dominante sea {dominante}.
    2. NO menciones los "puntos" ni números matemáticos en el texto final. Habla solo de temperamento y conducta.
    3. Sé breve y directo.
    """
    # Aumentamos max_tokens a 400 para evitar cortes
    return consultar_gpt(rol, prompt, 400)
    
    # 8. ELEMENTOS (Balance 50 pts)
    txt_elementos = generar_interpretacion_elementos_ia(datos['elementos'])

    return txt_sol, txt_luna, detalles_luna, txt_asc, txt_global, aspectos_interpretados, txt_modos, txt_elementos