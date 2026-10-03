import json
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
    """Función central de consulta a la API de OpenAI (devuelve texto; en error devuelve un <p> con el aviso)."""
    if not client:
        return "<p>Error de conexión IA: cliente no inicializado.</p>"
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario}
            ],
            temperature=0.7,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Error IA: {e}")
        return f"<p>Error técnico: {e}</p>"


def consultar_gpt_json(sistema, usuario, max_tokens=4000):
    """Consulta con salida JSON garantizada. A diferencia de consultar_gpt, LANZA una excepción si algo falla
    (así un error técnico nunca termina escrito dentro del informe del cliente)."""
    if not client:
        raise RuntimeError("Cliente OpenAI no inicializado (revisa OPENAI_API_KEY en Secrets).")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": sistema + " Responde siempre con un único objeto JSON válido."},
            {"role": "user", "content": usuario}
        ],
        temperature=0.7,
        max_tokens=max_tokens,
        response_format={"type": "json_object"}
    )
    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise ValueError("La respuesta de la IA se cortó por límite de longitud.")
    return json.loads(choice.message.content)


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
    ausente = min(elementos, key=elementos.get)
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
