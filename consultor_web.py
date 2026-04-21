import openai
import streamlit as st

# ==========================================
# CONFIGURACIÓN DEL CLIENTE OPENAI
# ==========================================
# Lee la clave desde st.secrets (configurada en Streamlit Cloud)
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
    client = openai.OpenAI(api_key=API_KEY)
except Exception as e:
    print(f"⚠️ No se pudo inicializar cliente OpenAI: {e}")
    client = None


def consultar_gpt(sistema, usuario, max_tokens=250):
    """Función central de consulta a la API de OpenAI."""
    if not client:
        return "<p>Error de conexión IA: cliente no inicializado.</p>"
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user",   "content": usuario}
            ],
            temperature=0.7,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Error IA: {e}")
        return f"<p>Error técnico: {e}</p>"


def generar_interpretacion_modos_ia(modos):
    """Interpreta el balance de modalidades (Cardinal / Fijo / Mutable)."""
    rol = "Eres Patricia Ramirez, astróloga experta. Tono analítico pero cercano. Usa HTML simple (<p>)."
    dominante = max(modos, key=modos.get)
    puntaje_dom = modos[dominante]
    prompt = f"""
    Analiza este Balance de Modalidades (Sistema de 50 Puntos):
    Cardinal: {modos['Cardinal']} puntos
    Fijo: {modos['Fijo']} puntos
    Mutable: {modos['Mutable']} puntos
    (El equilibrio ideal es aprox 16.6 puntos).

    Interpreta el modo dominante ({dominante}) y qué significa tener {puntaje_dom} puntos en él.
    No menciones los números en el texto final; habla solo de temperamento y conducta.
    """
    return consultar_gpt(rol, prompt, 400)


def generar_interpretacion_elementos_ia(elementos):
    """Interpreta el balance de elementos (Fuego / Tierra / Aire / Agua)."""
    rol = "Eres Patricia Ramirez, astróloga humanística. Usa HTML simple (<p>)."
    dominante = max(elementos, key=elementos.get)
    ausente   = min(elementos, key=elementos.get)
    valor_ausente = elementos[ausente]
    prompt = f"""
    Interpreta el Balance de Elementos:
    Fuego: {elementos['Fuego']} - Tierra: {elementos['Tierra']}
    Aire: {elementos['Aire']} - Agua: {elementos['Agua']}

    Elemento Dominante: {dominante}.
    Elemento Menor: {ausente} ({valor_ausente} puntos).

    Instrucciones:
    1. Interpreta la psicología del elemento dominante ({dominante}) sin mencionar "puntos".
    2. Si el elemento menor ({ausente}) tiene menos de 5 puntos, explica el desafío de esa carencia.
    3. Redacta como un consejo fluido para el cliente.
    """
    return consultar_gpt(rol, prompt, 450)


def generar_interpretacion_natal_ia(datos, nombre, genero, lista_aspectos_nombres):
    """
    Genera 8 bloques de interpretación natal completos vía IA.
    Retorna: txt_sol, txt_luna, detalles_luna, txt_asc, txt_global,
             aspectos_interpretados, txt_modos, txt_elementos
    """
    if client is None:
        vacio = "<p>Error: sin conexión IA.</p>"
        return vacio, vacio, {"mecanismo": "-", "talento": "-", "necesidad": "-"}, vacio, vacio, [], vacio, vacio

    print(f"   🤖 Consultando IA para {nombre}...")
    rol = "Eres Patricia Ramirez, astróloga de Astroimpacto. Tono empático, profundo y claro. Usa HTML <p>."

    # 1. SOL
    txt_sol = consultar_gpt(rol,
        f"Interpreta Sol en {datos['sol_signo']} Casa {datos['sol_casa']} para {nombre}. "
        f"Enfócate en su identidad y brillo personal. Termina la idea completa.", 500)

    # 2. LUNA
    txt_luna = consultar_gpt(rol,
        f"Interpreta Luna en {datos['luna_signo']} para {nombre}. "
        f"Explica su mundo emocional y refugio. Asegúrate de cerrar la frase final.", 500)

    # 3. DETALLES LUNA (3 frases estructuradas)
    prompt_detalles = f"""
    Para una Luna en {datos['luna_signo']}, necesito 3 frases cortas y directas.
    Responde EXACTAMENTE en este formato de 3 líneas (sin títulos, sin guiones):
    [Frase sobre su mecanismo de defensa]
    [Frase sobre su talento emocional]
    [Frase sobre lo que más necesita para sentirse seguro]
    """
    resp_items = consultar_gpt(rol, prompt_detalles, 200)
    detalles_luna = {
        "mecanismo": "Refugio en lo conocido.",
        "talento":   "Sensibilidad profunda.",
        "necesidad": "Seguridad emocional."
    }
    try:
        lines = [l.strip().replace("- ", "").replace("* ", "")
                 for l in resp_items.split('\n') if l.strip()]
        if len(lines) >= 3:
            detalles_luna = {"mecanismo": lines[0], "talento": lines[1], "necesidad": lines[2]}
    except Exception as e:
        print(f"⚠️ Error procesando detalles luna: {e}")

    # 4. ASCENDENTE
    txt_asc = consultar_gpt(rol,
        f"Interpreta Ascendente en {datos['asc_signo']} para {nombre}. "
        f"Su aprendizaje y cómo lo ven los demás. Termina la idea.", 500)

    # 5. SÍNTESIS GLOBAL
    txt_global = consultar_gpt(rol,
        f"Haz una síntesis integrando Sol en {datos['sol_signo']}, "
        f"Luna en {datos['luna_signo']} y Ascendente en {datos['asc_signo']}. "
        f"¿Cómo interactúan estas tres energías?", 600)

    # 6. ASPECTOS (máximo 6)
    aspectos_interpretados = []
    for asp in lista_aspectos_nombres[:6]:
        txt = consultar_gpt(rol, f"Interpreta brevemente el aspecto: {asp}. Qué reto o ventaja da.", 250)
        aspectos_interpretados.append({"titulo": asp, "interpretacion": txt})

    # 7. MODOS
    txt_modos = generar_interpretacion_modos_ia(datos['modos'])

    # 8. ELEMENTOS
    txt_elementos = generar_interpretacion_elementos_ia(datos['elementos'])

    return txt_sol, txt_luna, detalles_luna, txt_asc, txt_global, aspectos_interpretados, txt_modos, txt_elementos
