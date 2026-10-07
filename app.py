import os
import requests
import json
import streamlit as st
from bs4 import BeautifulSoup
import groq

# ==========================================
# 1. CONFIGURARE PAGINĂ & STATE INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="AI Social Media Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inițializare Session State
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "Română"
if "history" not in st.session_state:
    st.session_state.history = []
if "current_posts" not in st.session_state:
    st.session_state.current_posts = None
if "current_image" not in st.session_state:
    st.session_state.current_image = None
if "current_topic" not in st.session_state:
    st.session_state.current_topic = ""
if "quota_count" not in st.session_state:
    st.session_state.quota_count = 0 
if "user_api_key" not in st.session_state:
    st.session_state.user_api_key = ""

# ==========================================
# 2. GESTIONARE SECURE A CHEILOR API
# ==========================================
def get_secret(key_name: str) -> str:
    try:
        return st.secrets[key_name]
    except Exception:
        return os.environ.get(key_name, "")

is_unlimited = bool(st.session_state.user_api_key.strip())
ACTIVE_GROQ_KEY = st.session_state.user_api_key if is_unlimited else get_secret("GROQ_API_KEY")
HUGGINGFACE_API_KEY = get_secret("HUGGINGFACE_API_KEY")

# ==========================================
# 3. FUNCȚII DE BACKEND & ROBUST FALLBACK
# ==========================================
def scrape_url_content(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else "Articol"
        content = " ".join([p.get_text() for p in soup.find_all('p')])
        return f"TITLU: {title}\nCONȚINUT: {content[:4000]}"
    except Exception as e:
        raise Exception(f"Eroare la citirea link-ului: {str(e)}")

def generate_groq_json(prompt: str, api_key: str):
    if not api_key.startswith("gsk_"):
        raise Exception("Cheia Groq API lipsește sau este invalidă.")

    client = groq.Groq(api_key=api_key)
    
    # 🔹 LISTĂ DE BACKUP (Fallback Mechanism) 
    # Dacă primul eșuează cu 404, sistemul trece la următorul automat.
    # Toate aceste modele suportă JSON mode pe Groq.
    candidate_models = [
        "llama3-8b-8192",         # Stabil și rapid
        "llama-3.3-70b-versatile",# Modelul nou, foarte capabil
        "mixtral-8x7b-32768",     # Fallback extrem de robust
        "gemma2-9b-it"            # Ultimul resort
    ]
    
    system_prompt = (
        "You are an elite B2B Social Media Content Strategist. "
        "Write hyper-engaging, data-backed social media posts. "
        "RULES:\n"
        "1. Start with a controversial hook or hard metric.\n"
        "2. Provide actionable insights.\n"
        "3. YOU MUST RESPOND ONLY IN VALID JSON FORMAT with exactly these keys: "
        "'linkedin' (string), 'twitter' (string), 'instagram' (string), 'img_prompt' (string for FLUX image generator)."
    )
    
    last_error = None
    
    for model_name in candidate_models:
        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt}, 
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
                response_format={"type": "json_object"},
                stream=True
            )
            
            full_response = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    yield chunk.choices[0].delta.content, full_response
            
            # Dacă am ajuns aici, stream-ul s-a terminat cu succes; întrerupem fallback-ul
            return 
            
        except groq.NotFoundError as e:
            # Modelul nu există sau a fost retras, salvăm eroarea și încercăm următorul
            last_error = f"Model {model_name} indisponibil."
            continue
        except Exception as e:
            # Alte erori (rate limit, API down etc.)
            last_error = str(e)
            continue
            
    # Dacă bucla se termină fără a returna succes, ridicăm excepția finală
    raise Exception(f"Toate modelele au eșuat. Ultima eroare: {last_error}")


def generate_image_huggingface(image_prompt: str, api_key: str) -> bytes:
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"inputs": image_prompt, "options": {"wait_for_model": True}}
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.content

# ==========================================
# 4. MODAL SETĂRI 
# ==========================================
@st.dialog("⚙️ Setări & Preferințe")
def settings_modal():
    st.session_state.ui_lang = st.selectbox(
        "🌐 Limba Interfeței", 
        ["Română", "English"], 
        index=0 if st.session_state.ui_lang == "Română" else 1
    )
    st.markdown("---")
    st.markdown("🔑 **Custom API Keys (Mod Nelimitat)**")
    st.session_state.user_api_key = st.text_input(
        "Groq API Key (opțional):", 
        value=st.session_state.user_api_key, 
        type="password",
        placeholder="gsk_..."
    )
    
    if st.button("Salvează & Închide", use_container_width=True):
        st.rerun()

# ==========================================
# 5. UI PRINCIPAL: BARA LATERALĂ & HEADER
# ==========================================
with st.sidebar:
    st.markdown("### 💬 Meniul Tău")
    st.markdown("---")
    
    if is_unlimited:
        st.success('🌟 Mod Nelimitat Activat')
    else:
        count = st.session_state.quota_count
        ramase = max(0, 3 - count)
        delta_val = '-1 consumată' if count > 0 else None
        
        st.metric(label='⚡ Energie Zilnică', value=f'{ramase} rămase', delta=delta_val)
        progress_val = max(0.0, float(ramase) / 3.0)
        st.progress(progress_val)
        
    st.markdown("---")
    if st.button("➕ Postare Nouă", use_container_width=True):
        st.session_state.current_posts = None
        st.session_state.current_image = None
        st.session_state.current_topic = ""
        st.rerun()

head_col1, head_col2 = st.columns([11, 1])
with head_col1:
    st.markdown("<h1 style='margin:0; font-size: 2.2rem; color: #2563eb;'>AI Social Media Hub</h1>", unsafe_allow_html=True)
    st.markdown("<p style='opacity:0.7; margin-top:0.3rem; margin-bottom:1.8rem;'>Enterprise Multi-Platform Content Generator</p>", unsafe_allow_html=True)
with head_col2:
    if st.button("⚙️", help="Setări"):
        settings_modal()

# ==========================================
# 6. UI: CONFIGURARE CAMPANIE
# ==========================================
with st.container(border=True):
    st.markdown('#### 🎯 Configurare Campanie')
    
    topic_input = st.text_input(
        "🔗 Subiect detaliat sau URL Articol:", 
        value=st.session_state.current_topic, 
        placeholder="Ex: https://techcrunch.com/... SAU Analiză despre agentic AI"
    )
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        lang = st.selectbox("🌐 Limba Conținutului", ["Română", "English", "Français", "Deutsch"])
    with col_opt2:
        tone = st.selectbox("⚡ Tonul Campaniei", ["Profesional & Analitic", "Casual & Prietenos", "Provocator", "Educațional"])
        
    with st.expander("🎭 Brand Persona (Opțional)"):
        brand_persona = st.text_area("Instrucțiuni speciale de ton", height=70)
        
    generate_image_toggle = st.toggle("🎨 Generare Imagine (FLUX AI)", value=True)
    generate_btn = st.button("✨ Generează Postările", type="primary")

# ==========================================
# 7. LOGICA DE GENERARE & ERROR HANDLING
# ==========================================
if generate_btn:
    if not is_unlimited and st.session_state.quota_count >= 3:
        st.error("❌ Ai atins limita de 3 generări zilnice. Adaugă propria cheie Groq în Setări!")
        st.stop()
        
    if not topic_input.strip():
        st.warning("⚠️ Introdu un subiect sau un link valid.")
        st.stop()
        
    st.session_state.current_topic = topic_input
    context_data = topic_input

    if topic_input.strip().startswith("http"):
        with st.spinner("🌍 Extragem datele din URL..."):
            try:
                context_data = scrape_url_content(topic_input.strip())
            except Exception as e:
                st.error(str(e))
                st.stop()
    else:
        context_data = f"SUBIECT: {topic_input}."

    st.markdown("### ✍️ Se generează conținutul...")
    stream_container = st.empty()
    
    user_prompt = f"CONTEXT:\n{context_data}\n\nLANG: {lang}\nTONE: {tone}\nPERSONA: {brand_persona}"
    
    try:
        final_json_string = ""
        with st.spinner("🧠 AI-ul gândește și scrie postările..."):
            # Apelăm funcția refăcută cu fallback
            for chunk_char, accumulated_text in generate_groq_json(user_prompt, ACTIVE_GROQ_KEY):
                final_json_string = accumulated_text
                stream_container.markdown("```json\n" + accumulated_text + "▌\n```")
        
        stream_container.empty()
        
        parsed_data = json.loads(final_json_string)
        
        st.session_state.current_posts = {
            "linkedin": parsed_data.get("linkedin", ""),
            "twitter": parsed_data.get("twitter", ""),
            "instagram": parsed_data.get("instagram", ""),
            "img_prompt": parsed_data.get("img_prompt", f"Corporate illustration of {topic_input}, 8k")
        }
        
    except json.JSONDecodeError:
        st.error("Eroare: AI-ul nu a returnat un JSON valid.")
        st.stop()
    except Exception as api_err:
        st.error(f"Eroare API: {str(api_err)}")
        st.stop()

    st.session_state.current_image = None
    if generate_image_toggle and HUGGINGFACE_API_KEY:
        with st.spinner("🎨 Se sintetizează vizualul (Hugging Face FLUX)..."):
            try:
                st.session_state.current_image = generate_image_huggingface(
                    st.session_state.current_posts['img_prompt'], 
                    HUGGINGFACE_API_KEY
                )
            except Exception as e:
                st.warning(f"Imaginea nu a putut fi generată: {str(e)}")

    if not is_unlimited:
        st.session_state.quota_count += 1
        
    st.toast('🚀 Postările au fost generate cu succes!', icon='✅')
    st.rerun()

# ==========================================
# 8. UI: REZULTATE CAMPANIE
# ==========================================
if st.session_state.current_posts:
    with st.container(border=True):
        st.markdown("#### 📱 Vizualizare și Export")
        
        tab_li, tab_tw, tab_ig, tab_img = st.tabs(["💼 LinkedIn", "🐦 Twitter", "📸 Instagram", "🖼️ Vizual Generat"])
        
        with tab_li:
            st.text_area("Copy:", value=st.session_state.current_posts['linkedin'], height=250, key="ta_li", label_visibility="collapsed")
            
        with tab_tw:
            st.text_area("Copy:", value=st.session_state.current_posts['twitter'], height=150, key="ta_tw", label_visibility="collapsed")
            
        with tab_ig:
            ig_full = f"social_hub_official {st.session_state.current_topic}\n\n{st.session_state.current_posts['instagram']}"
            st.text_area("Copy:", value=ig_full, height=200, key="ta_ig", label_visibility="collapsed")
            
        with tab_img:
            if st.session_state.current_image:
                col_img_1, col_img_2 = st.columns([2, 1])
                with col_img_1:
                    st.image(st.session_state.current_image, use_container_width=True)
                with col_img_2:
                    st.markdown("**Prompt vizual AI:**")
                    st.caption(st.session_state.current_posts['img_prompt'])
                    st.download_button("📥 Descarcă JPG", st.session_state.current_image, "campanie.jpg", "image/jpeg", use_container_width=True)
            else:
                st.info("Generarea de imagini a fost dezactivată sau a eșuat.")
