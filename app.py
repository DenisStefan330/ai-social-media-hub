import os
import requests
import json
import re
import streamlit as st
from bs4 import BeautifulSoup
import groq
from duckduckgo_search import DDGS

# ==========================================
# 1. CONFIGURARE PAGINĂ & STATE
# ==========================================
st.set_page_config(
    page_title="Nexus Social AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
# 2. DIȚIONAR i18n COMPLET
# ==========================================
UI_TEXTS = {
    "Română": {
        "app_title": "Nexus Social AI",
        "app_sub": "Platformă Enterprise de Generare Conținut Multi-Platformă",
        "input_label": "🔗 Subiect detaliat sau URL Articol:",
        "input_placeholder": "Ex: https://techcrunch.com/... SAU Analiză despre agentic AI",
        "lang_label": "🌐 Limba Conținutului",
        "tone_label": "⚡ Tonul Campaniei",
        "toggle_img": "🎨 Generare Imagine (FLUX AI)",
        "btn_gen": "✨ Generează Postările",
        "sidebar_title": "💬 Meniul Tău",
        "new_chat": "➕ Postare Nouă",
        "settings_title": "⚙️ Setări & Preferințe",
        "ui_lang_label": "🌐 Limba Interfeței",
        "save_close": "Salvează & Închide",
        "energy_label": "⚡ Energie Zilnică",
        "unlimited_badge": "🌟 Mod Nelimitat Activat",
        "config_title": "🎯 Configurare Campanie",
        "results_title": "📱 Vizualizare și Export",
        "brand_persona": "🎭 Brand Persona (Opțional)"
    },
    "English": {
        "app_title": "Nexus Social AI",
        "app_sub": "Enterprise Multi-Platform Content Generator",
        "input_label": "🔗 Detailed Subject or Article URL:",
        "input_placeholder": "Ex: https://techcrunch.com/... OR Deep dive into agentic AI",
        "lang_label": "🌐 Content Language",
        "tone_label": "⚡ Campaign Tone",
        "toggle_img": "🎨 Generate Image (FLUX AI)",
        "btn_gen": "✨ Generate Posts",
        "sidebar_title": "💬 Your Menu",
        "new_chat": "➕ New Post",
        "settings_title": "⚙️ Settings & Preferences",
        "ui_lang_label": "🌐 Interface Language",
        "save_close": "Save & Close",
        "energy_label": "⚡ Daily Energy",
        "unlimited_badge": "🌟 Unlimited Mode Active",
        "config_title": "🎯 Campaign Configuration",
        "results_title": "📱 View & Export",
        "brand_persona": "🎭 Brand Persona (Optional)"
    }
}

t = UI_TEXTS[st.session_state.ui_lang]

# ==========================================
# 3. GESTIONARE SECURE & AUTO-HEALING GROQ
# ==========================================
def get_secret(key_name: str) -> str:
    try:
        return st.secrets[key_name]
    except Exception:
        return os.environ.get(key_name, "")

is_unlimited = bool(st.session_state.user_api_key.strip())
ACTIVE_GROQ_KEY = st.session_state.user_api_key if is_unlimited else get_secret("GROQ_API_KEY")
HUGGINGFACE_API_KEY = get_secret("HUGGINGFACE_API_KEY")

def select_best_groq_model(client) -> str:
    try:
        models = client.models.list()
        model_ids = [m.id for m in models.data]
        
        for pattern in ["llama-3.3", "llama-3.1", "mixtral", "gemma"]:
            for m_id in model_ids:
                if pattern in m_id.lower():
                    return m_id
    except Exception:
        pass
    
    return "llama3-8b-8192"

def generate_groq_json(prompt: str, api_key: str):
    if not api_key.startswith("gsk_"):
        raise Exception("Cheia Groq API lipsește sau este invalidă.")

    client = groq.Groq(api_key=api_key)
    chosen_model = select_best_groq_model(client)
    
    system_prompt = (
        "You are an elite B2B Social Media Content Strategist. "
        "Write hyper-engaging, data-backed social media posts. "
        "YOU MUST RESPOND ONLY IN VALID JSON FORMAT with exactly these keys: "
        "'linkedin' (string), 'twitter' (string), 'instagram' (string), 'img_prompt' (string for FLUX image generator)."
    )
    
    stream = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": system_prompt}, 
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=512,  # Corectat la 512 pentru compatibilitate universală cu toate modelele Groq
        response_format={"type": "json_object"},
        stream=True
    )
    
    full_response = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            full_response += chunk.choices[0].delta.content
            yield chunk.choices[0].delta.content, full_response

def sanitize_json_output(raw_text: str) -> dict:
    cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1)
        
    return json.loads(cleaned)

# ==========================================
# 4. EXTRAGERE CONTEXT (Jina / DuckDuckGo)
# ==========================================
def extract_context(topic_input: str) -> str:
    cleaned_input = topic_input.strip()
    if cleaned_input.startswith("http://") or cleaned_input.startswith("https://"):
        try:
            res = requests.get(f"https://r.jina.ai/{cleaned_input}", timeout=10)
            res.raise_for_status()
            return f"ARTICOL DIN URL:\n{res.text[:3000]}"
        except Exception:
            return f"Subiect bazat pe URL: {cleaned_input}"
    else:
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(cleaned_input, max_results=3):
                    results.append(r.get("body", ""))
            search_context = "\n".join(results)
            return f"SUBIECT: {cleaned_input}\nDATE LIVE:\n{search_context}"
        except Exception:
            return f"SUBIECT: {cleaned_input}"

def generate_image_huggingface(image_prompt: str, api_key: str) -> bytes:
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"inputs": image_prompt, "options": {"wait_for_model": True}}
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.content

# ==========================================
# 5. MODAL SETĂRI NATIV
# ==========================================
@st.dialog("⚙️ Setări & Preferințe")
def settings_modal():
    st.session_state.ui_lang = st.selectbox(
        t['ui_lang_label'], 
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
    
    if st.button(t['save_close'], use_container_width=True):
        st.rerun()

# ==========================================
# 6. BARA LATERALĂ
# ==========================================
with st.sidebar:
    st.markdown(f"### {t['sidebar_title']}")
    st.markdown("---")
    
    if is_unlimited:
        st.success(t['unlimited_badge'])
    else:
        count = st.session_state.quota_count
        ramase = max(0, 3 - count)
        delta_val = '-1 consumată' if count > 0 else None
        
        st.metric(label=t['energy_label'], value=f'{ramase} rămase', delta=delta_val)
        st.progress(max(0.0, float(ramase) / 3.0))
        
    st.markdown("---")
    if st.button(t['new_chat'], use_container_width=True):
        st.session_state.current_posts = None
        st.session_state.current_image = None
        st.session_state.current_topic = ""
        st.rerun()

# ==========================================
# 7. INTERFAȚĂ PRINCIPALĂ & CARD LAYOUTS
# ==========================================
head_col1, head_col2 = st.columns([11, 1])
with head_col1:
    st.markdown(f"<h1 style='margin:0; font-size: 2.2rem; color: #2563eb;'>{t['app_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='opacity:0.7; margin-top:0.3rem; margin-bottom:1.8rem;'>{t['app_sub']}</p>", unsafe_allow_html=True)
with head_col2:
    if st.button("⚙️", help="Setări"):
        settings_modal()

with st.container(border=True):
    st.markdown(f"#### {t['config_title']}")
    
    topic_input = st.text_input(
        t['input_label'], 
        value=st.session_state.current_topic, 
        placeholder=t['input_placeholder']
    )
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        lang = st.selectbox(t['lang_label'], ["Română", "English", "Français", "Deutsch"])
    with col_opt2:
        tone = st.selectbox(t['tone_label'], ["Profesional & Analitic", "Casual & Prietenos", "Provocator", "Educațional"])
        
    with st.expander(t['brand_persona']):
        brand_persona = st.text_area("Instrucțiuni speciale:", height=75)
        
    generate_image_toggle = st.toggle(t['toggle_img'], value=True)
    generate_btn = st.button(t['btn_gen'], type="primary")

# ==========================================
# 8. LOGICA DE GENERARE & VALIDARE
# ==========================================
if generate_btn:
    if not is_unlimited and st.session_state.quota_count >= 3:
        st.error("❌ Ai atins limita de 3 generări zilnice. Introdu propria cheie Groq în Setări!")
        st.stop()
        
    if not topic_input.strip():
        st.warning("⚠️ Introdu un subiect sau un link valid.")
        st.stop()
        
    st.session_state.current_topic = topic_input
    
    with st.spinner("🌍 Colectăm contextul..."):
        context_data = extract_context(topic_input)

    stream_container = st.empty()
    user_prompt = f"CONTEXT:\n{context_data}\n\nLANG: {lang}\nTONE: {tone}\nPERSONA: {brand_persona}"
    
    try:
        final_json_string = ""
        with st.spinner("🧠 AI-ul generează campania..."):
            for _, accumulated_text in generate_groq_json(user_prompt, ACTIVE_GROQ_KEY):
                final_json_string = accumulated_text
                stream_container.markdown("```json\n" + accumulated_text + "▌\n```")
        
        stream_container.empty()
        parsed_data = sanitize_json_output(final_json_string)
        
        st.session_state.current_posts = {
            "linkedin": parsed_data.get("linkedin", ""),
            "twitter": parsed_data.get("twitter", ""),
            "instagram": parsed_data.get("instagram", ""),
            "img_prompt": parsed_data.get("img_prompt", f"Corporate illustration of {topic_input}, 8k")
        }
    except Exception as api_err:
        st.error(f"Eroare generare: {str(api_err)}")
        st.stop()

    st.session_state.current_image = None
    if generate_image_toggle and HUGGINGFACE_API_KEY:
        with st.spinner("🎨 Se generează imaginea prin FLUX..."):
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
# 9. REZULTATE CAMPANIE (Tabs & Container)
# ==========================================
if st.session_state.current_posts:
    with st.container(border=True):
        st.markdown(f"#### {t['results_title']}")
        
        tab_li, tab_tw, tab_ig, tab_img = st.tabs(["💼 LinkedIn", "🐦 Twitter", "📸 Instagram", "🖼️ Vizual Generat"])
        
        with tab_li:
            st.text_area("LinkedIn", value=st.session_state.current_posts['linkedin'], height=250, key="ta_li", label_visibility="collapsed")
            
        with tab_tw:
            st.text_area("Twitter", value=st.session_state.current_posts['twitter'], height=150, key="ta_tw", label_visibility="collapsed")
            
        with tab_ig:
            ig_full = f"social_hub_official {st.session_state.current_topic}\n\n{st.session_state.current_posts['instagram']}"
            st.text_area("Instagram", value=ig_full, height=200, key="ta_ig", label_visibility="collapsed")
            
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
