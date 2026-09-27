import streamlit as st
import uuid
import io
import base64
import re
import unicodedata
import urllib.parse
import urllib.request
from PIL import Image
from google import genai
from google.genai import types

# 1. Configuración de pantalla
st.set_page_config(
    page_title="honey.ia",
    page_icon="🍯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. BLOQUE DE SEGURIDAD PRIVADO (PIN DE ACCESO)
CLAVE_DE_ACCESO = "honey2026"

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.markdown("<h2 style='text-align: center;'>🍯 honey.ia - Acceso Privado</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Proyecto Integrador - Ingrese el PIN de acceso autorizado:</p>", unsafe_allow_html=True)
        pin_ingresado = st.text_input("PIN:", type="password", placeholder="Ingresa el PIN de seguridad...", label_visibility="collapsed")
        if st.button("🔓 Desbloquear honey.ia", use_container_width=True, type="primary"):
            if pin_ingresado == CLAVE_DE_ACCESO:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ PIN incorrecto. Acceso denegado.")
    st.stop()

# 3. Autenticación con Google AI
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "AQ.Ab8RN6I5RFZh3UGj1T7ICYCK918a2qxB2u5P-8zaV6A3F2MMSA"

client = genai.Client(api_key=API_KEY)

# 4. Directivas de honey.ia
SYSTEM_PROMPT = """
Eres honey.ia, una asistente virtual rápida, directa, inteligente y pedagógica.

REGLAS DE VELOCIDAD Y ESTILO:
1. En saludos, charlas cotidianas o preguntas simples ("hola", "cómo estás", "cuánto es 2+2"): responde en 1 o 2 renglones máximo, fresca, natural y de forma inmediata.
2. En problemas de física o matemáticas: Sé directa y didáctica. Muestra las fórmulas en LaTeX ($...$ o $$...$$), datos, desarrollo paso a paso y el resultado final destacado.
3. Si el usuario sube un archivo o imagen: analiza detalladamente lo solicitado con precisión.
"""

def quitar_tildes(texto):
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def es_peticion_de_imagen(texto):
    t = quitar_tildes(texto.lower().strip())
    if re.search(r'^(dibuja|pinta|ilustra|renderiza)', t):
        return True
    has_sustantivo = bool(re.search(r'\b(imagen|imagenes|foto|fotos|dibujo|dibujos|ilustracion|ilustraciones|retrato|render)\b', t))
    has_verbo = bool(re.search(r'\b(crea|gener|haz|hac|dibuj|disen|ilustr|render|pint|dame|muestr)\w*', t))
    return has_sustantivo and has_verbo

def limpiar_prompt_imagen(prompt_usuario):
    t = prompt_usuario.strip()
    patron = r'^(?:por favor\s+|podr[ií]as\s+|puedes\s+|quiero\s+que\s+(?:me\s+)?(?:creas|hagas|generes|dibujes)\s+|dame\s+|hazme\s+|cr[eé]ame\s+|creame\s+|crearme\s+|generame\s+|gen[eé]rame\s+|generarme\s+|crea\s+|genera\s+|haz\s+|dibuja\s+|dib[uú]jame\s+)*(?:(?:un|una|el|la|unos|unas)\s+)?(?:imagen|foto|dibujo|retrato|ilustraci[oó]n|render)?(?:\s+de\s+|\s+sobre\s+|\s+del\s+|\s+de\s+un\s+|\s+de\s+una\s+|\s+)?'
    limpio = re.sub(patron, '', t, flags=re.IGNORECASE).strip()
    return limpio if limpio else prompt_usuario

def generar_imagen_ai(client, prompt_usuario):
    descripcion = limpiar_prompt_imagen(prompt_usuario)
    try:
        resultado = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=descripcion,
            config=dict(number_of_images=1, output_mime_type="image/jpeg")
        )
        if resultado.generated_images:
            return resultado.generated_images[0].image.image_bytes, descripcion
    except Exception:
        pass

    try:
        prompt_codificado = urllib.parse.quote(descripcion)
        url = f"https://image.pollinations.ai/prompt/{prompt_codificado}?width=1024&height=1024&nologo=true"
        peticion = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(peticion, timeout=20) as respuesta:
            return respuesta.read(), descripcion
    except Exception as e:
        return None, str(e)

def compress_image_fast(raw_bytes):
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        max_dim = 900
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.BILINEAR)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=70)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return raw_bytes, "image/jpeg"

def stream_ultra_rapido(client, contents_to_send, media_items_interactions):
    """Prueba primero el streaming nativo de alta velocidad chunk por chunk"""
    # 1. Intento por streaming directo (empieza a escribir en menos de 1 segundo)
    try:
        cfg = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3
        )
        stream = client.models.generate_content_stream(
            model="gemini-3.8-flash",
            contents=contents_to_send,
            config=cfg
        )
        for chunk in stream:
            if chunk.text:
                yield chunk.text
        return
    except Exception:
        pass

    # 2. Respaldo por Interactions API
    try:
        payload = [{"type": "text", "text": SYSTEM_PROMPT + "\n\n" + str(contents_to_send[-1])}] + media_items_interactions
        interaction = client.interactions.create(
            model="models/gemini-3.8-flash",
            input=payload,
            generation_config={"temperature": 0.3}
        )
        txt = getattr(interaction, "output_text", "") or getattr(interaction, "text", "") or str(interaction)
        yield txt
    except Exception as e:
        yield f"⚠️ Error: {e}"

# 5. Estado de sesión
DEFAULT_WELCOME = "¡Hola! Soy **honey.ia** 🍯, tu asistente inteligente multitarea. ¿En qué te ayudo hoy?"

if "chats" not in st.session_state:
    st.session_state.chats = {
        "chat_1": {
            "title": "Nuevo chat",
            "pinned": False,
            "messages": [{"role": "assistant", "content": DEFAULT_WELCOME, "images": [], "files": []}]
        }
    }
    st.session_state.current_chat_id = "chat_1"

if st.session_state.current_chat_id not in st.session_state.chats:
    st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]

current_chat = st.session_state.chats[st.session_state.current_chat_id]

# 6. Sidebar
with st.sidebar:
    st.markdown("### 🍯 honey.ia")
    if st.button("✏️ Nuevo chat", use_container_width=True, type="primary"):
        nid = f"chat_{uuid.uuid4().hex[:6]}"
        st.session_state.chats[nid] = {
            "title": "Nuevo chat",
            "pinned": False,
            "messages": [{"role": "assistant", "content": DEFAULT_WELCOME, "images": [], "files": []}]
        }
        st.session_state.current_chat_id = nid
        st.rerun()

    filtro = st.text_input("🔍 Buscar chats...", placeholder="Buscar...", label_visibility="collapsed").strip().lower()
    st.markdown("---")
    st.caption("**Recientes**")

    chats_ordenados = sorted(
        st.session_state.chats.items(),
        key=lambda x: not x[1].get("pinned", False)
    )

    if filtro:
        chats_ordenados = [
            (cid, c) for cid, c in chats_ordenados
            if filtro in c["title"].lower() or any(filtro in m.get("content", "").lower() for m in c["messages"])
        ]

    for cid, cdata in chats_ordenados:
        is_active = (cid == st.session_state.current_chat_id)
        is_pinned = cdata.get("pinned", False)

        col_t, col_o = st.columns([0.82, 0.18])
        with col_t:
            badge = " 📌" if is_pinned else ""
            prefix = "👉 " if is_active else ""
            if st.button(f"{prefix}{cdata['title']}{badge}", key=f"nav_{cid}", use_container_width=True):
                st.session_state.current_chat_id = cid
                st.rerun()

        with col_o:
            with st.popover("⋮"):
                chat_txt = "\n\n".join([f"[{m['role'].upper()}]: {m['content']}" for m in cdata["messages"]])
                st.download_button("🔗 Compartir", data=chat_txt, file_name=f"{cdata['title']}.txt", mime="text/plain", use_container_width=True, key=f"dl_{cid}")
                txt_pin = "📌 Quitar fijado" if is_pinned else "📌 Fijar chat"
                if st.button(txt_pin, key=f"pin_{cid}", use_container_width=True):
                    cdata["pinned"] = not is_pinned
                    st.rerun()
                nuevo_nom = st.text_input("Renombrar:", value=cdata["title"], key=f"nom_{cid}")
                if st.button("✏️ Guardar", key=f"save_{cid}", use_container_width=True):
                    if nuevo_nom.strip():
                        cdata["title"] = nuevo_nom.strip()
                        st.rerun()
                if st.button("🗑️ Borrar", key=f"del_{cid}", use_container_width=True):
                    del st.session_state.chats[cid]
                    if st.session_state.current_chat_id == cid:
                        st.session_state.current_chat_id = list(st.session_state.chats.keys())[0] if st.session_state.chats else "chat_1"
                    st.rerun()

# 7. Encabezado
st.title(f"🍯 {current_chat['title']}")
st.caption("honey.ia: Tu asistente inteligente multitarea de alta velocidad")
st.markdown("---")

# 8. Renderizado del historial
for msg in current_chat["messages"]:
    with st.chat_message(msg["role"]):
        if msg.get("images"):
            for img in msg["images"]:
                st.image(img, width=400)
        if msg.get("files"):
            for f_name in msg["files"]:
                st.caption(f"📄 Archivo: `{f_name}`")
        if msg.get("content"):
            st.markdown(msg["content"])

# 9. Entrada de chat
try:
    user_input = st.chat_input("Escribe un mensaje, pide una imagen ('crea una imagen de...'), sube fotos o PDFs...", accept_file="multiple", accept_audio=True)
except TypeError:
    try:
        user_input = st.chat_input("Escribe tu consulta o pide una imagen...", accept_file=True)
    except TypeError:
        user_input = st.chat_input("Escribe tu consulta aquí...")

# 10. Procesamiento veloz
if user_input:
    texto = getattr(user_input, "text", "") or (user_input if isinstance(user_input, str) else "")
    archivos = getattr(user_input, "files", []) or []
    audio_obj = getattr(user_input, "audio", None)

    saved_images = []
    saved_filenames = []
    contents_to_send = []
    media_items_interactions = []

    if archivos:
        for f in archivos:
            raw_b = f.getvalue()
            m = f.type or "application/octet-stream"
            if m.startswith("image/"):
                opt_b, opt_m = compress_image_fast(raw_b)
                saved_images.append(opt_b)
                contents_to_send.append(types.Part.from_bytes(data=opt_b, mime_type=opt_m))
                media_items_interactions.append({"type": "image", "data": base64.b64encode(opt_b).decode("utf-8"), "mime_type": opt_m})
            else:
                saved_filenames.append(f.name)
                mime_final = "application/pdf" if f.name.lower().endswith(".pdf") else m
                contents_to_send.append(types.Part.from_bytes(data=raw_b, mime_type=mime_final))
                media_items_interactions.append({"type": "document", "data": base64.b64encode(raw_b).decode("utf-8"), "mime_type": mime_final})

    if audio_obj:
        aud_bytes = audio_obj.getvalue()
        aud_mime = getattr(audio_obj, "type", "audio/webm") or "audio/webm"
        contents_to_send.append(types.Part.from_bytes(data=aud_bytes, mime_type=aud_mime))
        media_items_interactions.append({"type": "audio", "data": base64.b64encode(aud_bytes).decode("utf-8"), "mime_type": aud_mime})

    prompt_texto = texto.strip()
    display_user_text = texto.strip()
    if not display_user_text:
        if audio_obj:
            display_user_text = "🎙️ *(Nota de voz enviada)*"
        elif saved_images:
            display_user_text = "📷 *(Captura enviada para análisis)*"
        elif saved_filenames:
            display_user_text = f"📄 *{saved_filenames[0]}*"

    current_chat["messages"].append({
        "role": "user",
        "content": display_user_text,
        "images": saved_images,
        "files": saved_filenames
    })

    if current_chat["title"] == "Nuevo chat" and texto.strip():
        clean_t = texto.strip().replace("\n", " ")
        current_chat["title"] = clean_t[:25] + ("..." if len(clean_t) > 25 else "")

    with st.chat_message("user"):
        if saved_images:
            for img in saved_images:
                st.image(img, width=350)
        if saved_filenames:
            for fn in saved_filenames:
                st.caption(f"📄 Archivo: `{fn}`")
        if display_user_text:
            st.markdown(display_user_text)

    # 11. Generación de respuesta
    with st.chat_message("assistant"):
        if es_peticion_de_imagen(prompt_texto) and not saved_images:
            with st.spinner("🎨 Creando imagen..."):
                img_data, info = generar_imagen_ai(client, prompt_texto)
                if img_data:
                    texto_resp = f"✨ ¡Aquí tienes la imagen generada sobre: **{info}**!"
                    st.markdown(texto_resp)
                    st.image(img_data, caption=info, width=420)
                    st.download_button("📥 Descargar imagen", data=img_data, file_name=f"honey_ia_{uuid.uuid4().hex[:5]}.jpg", mime="image/jpeg")
                    current_chat["messages"].append({"role": "assistant", "content": texto_resp, "images": [img_data], "files": []})
                else:
                    err_msg = f"⚠️ No se pudo generar la imagen: {info}"
                    st.markdown(err_msg)
                    current_chat["messages"].append({"role": "assistant", "content": err_msg, "images": [], "files": []})
        else:
            if not prompt_texto:
                prompt_texto = "Analiza el contenido adjunto y responde detalladamente con fórmulas en LaTeX."

            contents_to_send.append(prompt_texto)
            
            # Streaming real token a token
            respuesta_completa = st.write_stream(stream_ultra_rapido(client, contents_to_send, media_items_interactions))
            
            current_chat["messages"].append({
                "role": "assistant",
                "content": respuesta_completa,
                "images": [],
                "files": []
            })

    st.rerun()
