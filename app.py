import streamlit as st
import uuid
import io
import base64
import time
import re
import unicodedata
import urllib.parse
import urllib.request
from PIL import Image
from google import genai

# 1. Configuración de pantalla
st.set_page_config(
    page_title="honey.ia",
    page_icon="🍯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. BLOQUE DE SEGURIDAD PRIVADO (PIN DE ACCESO)
CLAVE_DE_ACCESO = "honey2026"  # PIN para desbloquear el chat

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
    st.stop()  # Detiene la pantalla si no ha iniciado sesión

# 3. Tu API Key de Google AI Studio (compatible con local y con la nube)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "AQ.Ab8RN6I5RFZh3UGj1T7ICYCK918a2qxB2u5P-8zaV6A3F2MMSA"

client = genai.Client(api_key=API_KEY)

# 4. Directivas de honey.ia: Asistente Multitarea Universal
SYSTEM_PROMPT = """
Eres honey.ia (Honey AI), una asistente virtual inteligente, rápida, amigable y completamente multitarea.

DIRECTIVAS PRINCIPALES:
1. ASISTENTE MULTITAREA:
   - Responde dudas de cualquier materia, cálculo, física, programación, redacción o cultura general.
   - En conversaciones casuales, saludos o preguntas cotidianas (como "hola", "cómo estás", "cuánto es 1 + 1"): responde de forma fresca, breve, amigable y directa.

2. EXPERTA EN CIENCIAS, FÍSICA Y MATEMÁTICAS:
   - Cuando te pidan resolver un ejercicio o analizar una tabla (cálculo de integrales, derivadas, leyes de Coulomb, circuitos de Kirchhoff, capacitores, etc.):
     * Identifica los datos, fórmulas e incógnitas con claridad.
     * Cita las fórmulas y reglas matemáticas en notación formal LaTeX ($...$ o $$...$$).
     * Desarrolla el procedimiento algebraico paso a paso.
     * Entrega el resultado final destacado con su interpretación.

3. ANÁLISIS MULTIMODAL (IMÁGENES, DOCUMENTOS PDF Y VOZ):
   - Si el usuario sube un archivo (como un PDF de fórmulas o tabla de integrales) o una captura: examina a detalle el contenido y responde con precisión.
"""

def quitar_tildes(texto):
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def es_peticion_de_imagen(texto):
    """Detecta de forma flexible si el usuario pide crear, dibujar o generar una imagen"""
    t = quitar_tildes(texto.lower().strip())
    if re.search(r'^(dibuja|pinta|ilustra|renderiza)', t):
        return True
    has_sustantivo = bool(re.search(r'\b(imagen|imagenes|foto|fotos|dibujo|dibujos|ilustracion|ilustraciones|retrato|render)\b', t))
    has_verbo = bool(re.search(r'\b(crea|gener|haz|hac|dibuj|disen|ilustr|render|pint|dame|muestr)\w*', t))
    return has_sustantivo and has_verbo

def limpiar_prompt_imagen(prompt_usuario):
    """Limpia frases introductorias para entregar solo la descripción visual"""
    t = prompt_usuario.strip()
    patron = r'^(?:por favor\s+|podr[ií]as\s+|puedes\s+|quiero\s+que\s+(?:me\s+)?(?:creas|hagas|generes|dibujes)\s+|dame\s+|hazme\s+|cr[eé]ame\s+|creame\s+|crearme\s+|generame\s+|gen[eé]rame\s+|generarme\s+|crea\s+|genera\s+|haz\s+|dibuja\s+|dib[uú]jame\s+)*(?:(?:un|una|el|la|unos|unas)\s+)?(?:imagen|foto|dibujo|retrato|ilustraci[oó]n|render)?(?:\s+de\s+|\s+sobre\s+|\s+del\s+|\s+de\s+un\s+|\s+de\s+una\s+|\s+)?'
    limpio = re.sub(patron, '', t, flags=re.IGNORECASE).strip()
    return limpio if limpio else prompt_usuario

def generar_imagen_ai(client, prompt_usuario):
    """Genera imágenes con motor de alta resolución gratuito y sin límites de cuota"""
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
        with urllib.request.urlopen(peticion, timeout=25) as respuesta:
            return respuesta.read(), descripcion
    except Exception as e:
        return None, str(e)

def compress_image_fast(raw_bytes):
    """Comprime imágenes y capturas para envío instantáneo"""
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        max_dim = 1000
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.BILINEAR)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=75)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return raw_bytes, "image/jpeg"

def extract_clean_text(response_obj):
    """Extrae el texto puro de la IA sin metadatos técnicos"""
    if hasattr(response_obj, "output_text") and response_obj.output_text:
        return response_obj.output_text
    if hasattr(response_obj, "text") and response_obj.text:
        return response_obj.text
    if hasattr(response_obj, "steps") and response_obj.steps:
        for s in reversed(response_obj.steps):
            if hasattr(s, "text") and s.text:
                return s.text
            if hasattr(s, "content") and hasattr(s.content, "parts"):
                txts = [p.text for p in s.content.parts if hasattr(p, "text") and p.text]
                if txts:
                    return "".join(txts)
    s = str(response_obj)
    if "output_text='" in s:
        start = s.find("output_text='") + len("output_text='")
        end = s.find("'", start)
        if end != -1:
            return s[start:end].replace("\\n", "\n")
    return s

def smooth_stream(text):
    """Efecto de escritura fluido palabra por palabra"""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.008)

# 5. Estado de los chats en memoria
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

# 6. Barra Lateral estilo Gemini
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

    filtro = st.text_input("🔍 Buscar chats...", placeholder="Buscar en conversaciones...", label_visibility="collapsed").strip().lower()
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
                st.download_button(
                    label="🔗 Compartir conversación",
                    data=chat_txt,
                    file_name=f"{cdata['title']}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"dl_{cid}"
                )

                txt_pin = "📌 Dejar de fijar" if is_pinned else "📌 Fijar chat"
                if st.button(txt_pin, key=f"pin_{cid}", use_container_width=True):
                    cdata["pinned"] = not is_pinned
                    st.rerun()

                nuevo_nom = st.text_input("Cambiar nombre:", value=cdata["title"], key=f"nom_{cid}")
                if st.button("✏️ Guardar nombre", key=f"save_{cid}", use_container_width=True):
                    if nuevo_nom.strip():
                        cdata["title"] = nuevo_nom.strip()
                        st.rerun()

                if st.button("🗑️ Borrar", key=f"del_{cid}", use_container_width=True):
                    del st.session_state.chats[cid]
                    if st.session_state.current_chat_id == cid:
                        if st.session_state.chats:
                            st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
                        else:
                            nid = f"chat_{uuid.uuid4().hex[:6]}"
                            st.session_state.chats[nid] = {
                                "title": "Nuevo chat",
                                "pinned": False,
                                "messages": [{"role": "assistant", "content": DEFAULT_WELCOME, "images": [], "files": []}]
                            }
                            st.session_state.current_chat_id = nid
                    st.rerun()

# 7. Título del chat actual
st.title(f"🍯 {current_chat['title']}")
st.caption("honey.ia: Tu asistente inteligente multitarea")
st.markdown("---")

# 8. Renderizado del historial de mensajes
for msg in current_chat["messages"]:
    with st.chat_message(msg["role"]):
        if msg.get("images"):
            for img in msg["images"]:
                st.image(img, width=420)
        if msg.get("files"):
            for f_name in msg["files"]:
                st.caption(f"📄 Archivo: `{f_name}`")
        if msg.get("content"):
            st.markdown(msg["content"])

# 9. Entrada de chat principal
try:
    user_input = st.chat_input(
        "Escribe un mensaje, pide una imagen ('crea una imagen de...'), sube fotos o PDFs...",
        accept_file="multiple",
        accept_audio=True
    )
except TypeError:
    try:
        user_input = st.chat_input("Escribe tu consulta o pide una imagen...", accept_file=True)
    except TypeError:
        user_input = st.chat_input("Escribe tu consulta aquí...")

# 10. Procesamiento
if user_input:
    texto = getattr(user_input, "text", "") or (user_input if isinstance(user_input, str) else "")
    archivos = getattr(user_input, "files", []) or []
    audio_obj = getattr(user_input, "audio", None)

    saved_images = []
    saved_filenames = []
    media_items = []

    # Procesar archivos adjuntos (imágenes o PDFs)
    if archivos:
        for f in archivos:
            raw_b = f.getvalue()
            m = f.type or "application/octet-stream"
            if m.startswith("image/"):
                opt_b, opt_m = compress_image_fast(raw_b)
                saved_images.append(opt_b)
                b64_img = base64.b64encode(opt_b).decode("utf-8")
                media_items.append({"type": "image", "data": b64_img, "mime_type": opt_m})
            else:
                saved_filenames.append(f.name)
                mime_final = "application/pdf" if f.name.lower().endswith(".pdf") else m
                b64_doc = base64.b64encode(raw_b).decode("utf-8")
                media_items.append({"type": "document", "data": b64_doc, "mime_type": mime_final})

    # Procesar notas de voz
    if audio_obj:
        aud_bytes = audio_obj.getvalue()
        aud_mime = getattr(audio_obj, "type", "audio/webm") or "audio/webm"
        b64_aud = base64.b64encode(aud_bytes).decode("utf-8")
        media_items.append({"type": "audio", "data": b64_aud, "mime_type": aud_mime})

    prompt_texto = texto.strip()
    display_user_text = texto.strip()
    if not display_user_text:
        if audio_obj:
            display_user_text = "🎙️ *(Nota de voz enviada)*"
        elif saved_images:
            display_user_text = "📷 *(Captura enviada para análisis)*"
        elif saved_filenames:
            display_user_text = f"📄 *{saved_filenames[0]}*"

    # Guardar mensaje del usuario
    current_chat["messages"].append({
        "role": "user",
        "content": display_user_text,
        "images": saved_images,
        "files": saved_filenames
    })

    if current_chat["title"] == "Nuevo chat":
        if texto.strip():
            clean_t = texto.strip().replace("\n", " ")
            current_chat["title"] = clean_t[:25] + ("..." if len(clean_t) > 25 else "")
        elif saved_images:
            current_chat["title"] = "📷 Captura de ejercicio"
        elif saved_filenames:
            current_chat["title"] = f"📄 {saved_filenames[0][:20]}"

    # Mostrar mensaje del usuario en pantalla
    with st.chat_message("user"):
        if saved_images:
            for img in saved_images:
                st.image(img, width=350)
        if saved_filenames:
            for fn in saved_filenames:
                st.caption(f"📄 Archivo: `{fn}`")
        if display_user_text:
            st.markdown(display_user_text)

    # 11. Generación de Respuesta o Creación de Imágenes
    with st.chat_message("assistant"):
        # CASO A: Crear una imagen
        if es_peticion_de_imagen(prompt_texto) and not saved_images:
            with st.spinner("🎨 honey.ia está creando tu imagen..."):
                img_data, info = generar_imagen_ai(client, prompt_texto)
                if img_data:
                    texto_resp = f"✨ ¡Aquí tienes la imagen generada sobre: **{info}**!"
                    st.markdown(texto_resp)
                    st.image(img_data, caption=info, width=450)
                    st.download_button(
                        label="📥 Descargar imagen",
                        data=img_data,
                        file_name=f"honey_ia_{uuid.uuid4().hex[:5]}.jpg",
                        mime="image/jpeg"
                    )
                    current_chat["messages"].append({
                        "role": "assistant",
                        "content": texto_resp,
                        "images": [img_data],
                        "files": []
                    })
                else:
                    err_msg = f"⚠️ No se pudo generar la imagen: {info}"
                    st.markdown(err_msg)
                    current_chat["messages"].append({
                        "role": "assistant",
                        "content": err_msg,
                        "images": [],
                        "files": []
                    })

        # CASO B: Respuesta textual, física, matemáticas o lectura de documentos
        else:
            placeholder = st.empty()
            placeholder.markdown("*(honey.ia está respondiendo...)*")
            
            if not prompt_texto:
                if audio_obj:
                    prompt_texto = "Por favor responde con amabilidad a esta nota de voz."
                elif saved_images:
                    prompt_texto = "Analiza detalladamente el ejercicio de esta imagen y resuélvelo paso a paso con fórmulas en LaTeX."
                elif saved_filenames:
                    prompt_texto = "Lee y resume detalladamente los puntos clave de este documento."

            full_prompt = f"{SYSTEM_PROMPT}\n\nConsulta del usuario:\n{prompt_texto}"
            
            if not media_items:
                payload = full_prompt
            else:
                payload = [{"type": "text", "text": full_prompt}] + media_items

            modelos_recomendados = [
                "models/gemini-3.8-flash",
                "gemini-3.8-flash",
                "models/gemini-3-flash-preview"
            ]

            respuesta_texto = None
            ultimo_error = None

            for mod in modelos_recomendados:
                try:
                    interaction = client.interactions.create(
                        model=mod,
                        input=payload,
                        generation_config={"temperature": 0.35}
                    )
                    respuesta_texto = extract_clean_text(interaction)
                    if respuesta_texto:
                        break
                except Exception as err:
                    ultimo_error = err
                    continue

            if not respuesta_texto:
                respuesta_texto = f"⚠️ Error al conectar con la IA: {ultimo_error}"

            placeholder.empty()
            st.write_stream(smooth_stream(respuesta_texto))

            current_chat["messages"].append({
                "role": "assistant",
                "content": respuesta_texto,
                "images": [],
                "files": []
            })

    st.rerun()