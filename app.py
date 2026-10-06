import os
import time
import urllib.parse
import requests
import re
from bs4 import BeautifulSoup
import streamlit as st

# ==========================================
# 1. GESTIONARE SECURATĂ A CHEILOR API
# ==========================================
def get_secret(key_name: str) -> str:
    try:
        return st.secrets[key_name]
    except Exception:
        return os.environ.get(key_name, "")

GROQ_API_KEY = get_secret("GROQ_API_KEY")
HUGGINGFACE_API_KEY = get_secret("HUGGINGFACE_API_KEY")

# ==========================================
# 2. FUNCȚII DE BACKEND (Scraping, Groq & FLUX)
# ==========================================

def scrape_url_content(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else "Articol"
        paragraphs = soup.find_all('p')
        content = " ".join([p.get_text() for p in paragraphs])
        return f"TITLU: {title}\nCONȚINUT: {content[:5000]}"
    except Exception as e:
        raise Exception(f"Eroare la citirea link-ului: {str(e)}")

def stream_groq_text(prompt: str, api_key: str):
    from groq import Groq
    client = Groq(api_key=api_key)
    system_prompt = (
        "You are an elite Social Media Copywriter and Content Strategist. "
        "Create viral, insightful posts based on the user's topic or provided article text. "
        "CRITICAL RULES: "
        "1. Format output EXACTLY with these markers:\n"
        "[LINKEDIN]\n...linkedin post here...\n"
        "[TWITTER]\n...twitter post here...\n"
        "[INSTAGRAM]\n...instagram caption here...\n"
        "[IMG_PROMPT]\n...1 highly detailed professional visual prompt in English for FLUX...\n"
        "2. Avoid generic fluff; use strong hooks."
    )
    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=2500, stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception:
        stream_fb = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=2500, stream=True
        )
        for chunk in stream_fb:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

def generate_image_huggingface(image_prompt: str, api_key: str) -> bytes:
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"inputs": image_prompt, "options": {"wait_for_model": True}}
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.content

# ==========================================
# 3. CONFIGURARE PAGINĂ & STATE
# ==========================================

st.set_page_config(
    page_title="AI Social Media Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "Română"
if "font_size" not in st.session_state:
    st.session_state.font_size = "Normal (15px)"
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Sincronizat cu sistemul (Auto)"
if "history" not in st.session_state:
    st.session_state.history = []
if "current_posts" not in st.session_state:
    st.session_state.current_posts = None
if "current_image" not in st.session_state:
    st.session_state.current_image = None
if "current_topic" not in st.session_state:
    st.session_state.current_topic = ""

UI_TEXTS = {
    "Română": {
        "app_title": "AI Social Media Hub",
        "app_sub": "Platformă Enterprise de Generare Campanii Multi-Platformă",
        "input_label": "🔗 Subiect sau URL Articol:",
        "input_placeholder": "Ex: https://techcrunch.com/... SAU Viitorul AI-ului în medicină",
        "lang_label": "🌐 Limba Conținutului",
        "tone_label": "⚡ Tonul Campaniei",
        "toggle_img": "🎨 Generare Imagine (FLUX AI)",
        "btn_gen": "✨ Generează Campania",
        "sidebar_title": "💬 Istoric Postări",
        "new_chat": "➕ Postare Nouă",
        "settings_title": "⚙️ Setări & Preferințe",
        "font_size_label": "🔤 Dimensiune Text Postări",
        "ui_lang_label": "🌐 Limba Interfeței",
        "theme_label": "🌓 Mod Temă (Light / Dark)",
        "save_close": "Salvează & Închide"
    },
    "English": {
        "app_title": "AI Social Media Hub",
        "app_sub": "Enterprise Multi-Platform Campaign Generator",
        "input_label": "🔗 Subject or Article URL:",
        "input_placeholder": "Ex: https://techcrunch.com/... OR Future of AI in medicine",
        "lang_label": "🌐 Content Language",
        "tone_label": "⚡ Campaign Tone",
        "toggle_img": "🎨 Generate Image (FLUX AI)",
        "btn_gen": "✨ Generate Campaign",
        "sidebar_title": "💬 Post History",
        "new_chat": "➕ New Post",
        "settings_title": "⚙️ Settings & Preferences",
        "font_size_label": "🔤 Post Text Font Size",
        "ui_lang_label": "🌐 Interface Language",
        "theme_label": "🌓 Theme Mode (Light / Dark)",
        "save_close": "Save & Close"
    }
}

t = UI_TEXTS[st.session_state.ui_lang]

font_size_map = {"Compact (13px)": "13px", "Normal (15px)": "15px", "Large (18px)": "18px"}
active_font_size = font_size_map.get(st.session_state.font_size, "15px")

theme_css = ""
if st.session_state.theme_mode == "Light (Mod Luminos)":
    theme_css = """
    [data-testid="stAppViewContainer"] { background-color: #ffffff !important; color: #0f172a !important; }
    .mockup-container { background-color: #f8fafc !important; color: #0f172a !important; border: 1px solid #e2e8f0 !important; }
    """
elif st.session_state.theme_mode == "Dark (Mod Întunecat)":
    theme_css = """
    [data-testid="stAppViewContainer"] { background-color: #0e1117 !important; color: #fafafa !important; }
    .mockup-container { background-color: #1e293b !important; color: #fafafa !important; border: 1px solid #334155 !important; }
    """

# ==========================================
# 4. DESIGN CSS CURAT & ÎNCAPSULAT
# ==========================================

st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif !important;
    }}
    
    .stButton button {{
        background: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        padding: 0.75rem !important;
        border: none !important;
        width: 100% !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }}
    .stButton button:hover {{
        opacity: 0.95;
        transform: translateY(-1px);
    }}

    .mockup-container, .mockup-container * {{
        font-size: {active_font_size} !important;
    }}
    .mockup-container {{
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        line-height: 1.6;
    }}
    .mockup-header {{ display: flex; align-items: center; margin-bottom: 16px; }}
    .mockup-avatar {{ width: 44px; height: 44px; border-radius: 50%; background: #94a3b8; margin-right: 12px; }}
    .mockup-name {{ font-weight: 700; font-size: 16px !important; margin: 0; }}
    .mockup-meta {{ font-size: 13px !important; opacity: 0.7; margin: 0; }}
    .brand-linkedin {{ border-top: 4px solid #0a66c2; }}
    .brand-twitter {{ border-top: 4px solid #38bdf8; }}
    .brand-instagram {{ border-top: 4px solid #e1306c; }}
    .mockup-content {{ white-space: pre-wrap; }}

    {theme_css}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 5. MODALUL DE SETĂRI NATIV (ST.DIALOG)
# ==========================================

@st.dialog(t['settings_title'])
def settings_modal():
    st.markdown("Configurează preferințele de sistem și afișare:")
    
    st.session_state.ui_lang = st.selectbox(
        t['ui_lang_label'], 
        ["Română", "English"], 
        index=0 if st.session_state.ui_lang == "Română" else 1
    )
    
    st.session_state.font_size = st.selectbox(
        t['font_size_label'], 
        ["Compact (13px)", "Normal (15px)", "Large (18px)"],
        index=1 if st.session_state.font_size == "Normal (15px)" else (0 if "Compact" in st.session_state.font_size else 2)
    )

    st.session_state.theme_mode = st.selectbox(
        t['theme_label'],
        ["Sincronizat cu sistemul (Auto)", "Light (Mod Luminos)", "Dark (Mod Întunecat)"],
        index=0 if st.session_state.theme_mode == "Sincronizat cu sistemul (Auto)" else (1 if "Light" in st.session_state.theme_mode else 2)
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(t['save_close'], use_container_width=True):
        st.rerun()

# ==========================================
# 6. BARA LATERALĂ (ISTORIC POSTĂRI)
# ==========================================

with st.sidebar:
    st.markdown(f"### {t['sidebar_title']}")
    
    if st.button(t['new_chat'], use_container_width=True):
        st.session_state.current_posts = None
        st.session_state.current_image = None
        st.session_state.current_topic = ""
        st.rerun()
        
    st.markdown("---")
    
    if not st.session_state.history:
        st.caption("Nicio postare salvată în istoric.")
    else:
        for idx, item in enumerate(st.session_state.history):
            title_label = item['topic'][:30] + "..." if len(item['topic']) > 30 else item['topic']
            if st.button(f"💬 {title_label}", key=f"hist_{idx}", use_container_width=True):
                st.session_state.current_posts = item['posts']
                st.session_state.current_image = item['image']
                st.session_state.current_topic = item['topic']
                st.rerun()

# ==========================================
# 7. HEADER PRINCIPAL CU ICONIȚĂ ROTIȚĂ ⚙️
# ==========================================

head_col1, head_col2 = st.columns([11, 1])
with head_col1:
    st.markdown(f"<h2 style='margin:0; font-weight:800;'>{t['app_title']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='opacity:0.7; margin-bottom:1.5rem;'>{t['app_sub']}</p>", unsafe_allow_html=True)
with head_col2:
    if st.button("⚙️", help="Setări"):
        settings_modal()

# ==========================================
# 8. INTERFAȚA DE INPUT & GENERARE
# ==========================================

topic_input = st.text_input(t['input_label'], value=st.session_state.current_topic, placeholder=t['input_placeholder'])

col_opt1, col_opt2 = st.columns(2)
with col_opt1:
    lang = st.selectbox(t['lang_label'], ["Română", "English", "Français", "Deutsch"])
with col_opt2:
    tone = st.selectbox(t['tone_label'], ["Profesional & Analitic", "Casual & Prietenos", "Provocator", "Educațional"])

generate_image_toggle = st.toggle(t['toggle_img'], value=True)
generate_btn = st.button(t['btn_gen'])

if generate_btn:
    if not topic_input.strip():
        st.warning("⚠️️ Te rog să introduci un subiect sau un link valid.")
    elif not GROQ_API_KEY:
        st.error("⚠️ Cheia Groq API lipsește din Streamlit Secrets.")
    else:
        st.session_state.current_topic = topic_input
        st.session_state.current_image = None
        context_data = topic_input
        
        is_url = re.match(r"^https?://", topic_input.strip())
        if is_url:
            with st.spinner("🌍 Se citește articolul web..."):
                try:
                    context_data = scrape_url_content(topic_input.strip())
                except Exception as e:
                    st.error(str(e))
                    st.stop()

        st.markdown("### ✍️ Se generează campania...")
        stream_container = st.empty()
        
        user_prompt = f"SUBJECT/CONTEXT:\n{context_data}\n\nLANGUAGE: {lang}\nTONE: {tone}\n"
        full_response = ""
        
        for chunk in stream_groq_text(user_prompt, GROQ_API_KEY):
            full_response += chunk
            stream_container.markdown(full_response + "▌")
            
        stream_container.empty()

        def extract_section(text, start_tag, end_tag=None):
            pattern = f"{re.escape(start_tag)}(.*?){re.escape(end_tag)}" if end_tag else f"{re.escape(start_tag)}(.*)"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""

        li_post = extract_section(full_response, "[LINKEDIN]", "[TWITTER]")
        tw_post = extract_section(full_response, "[TWITTER]", "[INSTAGRAM]")
        ig_post = extract_section(full_response, "[INSTAGRAM]", "[IMG_PROMPT]")
        img_prompt = extract_section(full_source:=full_response, "[IMG_PROMPT]")

        if not li_post: li_post = full_response
        if not img_prompt: img_prompt = f"Professional corporate illustration of {topic_input}, 8k"

        st.session_state.current_posts = {
            "linkedin": li_post,
            "twitter": tw_post,
            "instagram": ig_post,
            "img_prompt": img_prompt
        }

        if generate_image_toggle and HUGGINGFACE_API_KEY:
            with st.spinner("🎨 Se generează imaginea FLUX..."):
                try:
                    st.session_state.current_image = generate_image_huggingface(img_prompt, HUGGINGFACE_API_KEY)
                except Exception as e:
                    st.warning(f"Imaginea nu a putut fi generată: {str(e)}")

        st.session_state.history.insert(0, {
            "topic": topic_input,
            "posts": st.session_state.current_posts,
            "image": st.session_state.current_image
        })
        st.rerun()

# ==========================================
# 9. AFIȘARE REZULTATE ȘI MOCKUPS
# ==========================================

if st.session_state.current_posts:
    st.markdown("---")
    st.markdown("## 📱 Rezultate Postare")
    
    col_viz, col_posts = st.columns([1.2, 2])
    
    with col_viz:
        st.markdown("#### 🖼️ Vizual Generat")
        if st.session_state.current_image:
            st.image(st.session_state.current_image, use_container_width=True)
            st.download_button("📥 Descarcă Imaginea (.jpg)", st.session_state.current_image, "campanie.jpg", "image/jpeg")
        else:
            st.info("Imagine inactivă sau generare oprită.")
            
        st.markdown("<br><b>Prompt vizual AI:</b>", unsafe_allow_html=True)
        st.caption(st.session_state.current_posts['img_prompt'])

    with col_posts:
        st.markdown(f"""
        <div class="mockup-container brand-linkedin">
            <div class="mockup-header">
                <div class="mockup-avatar"></div>
                <div><p class="mockup-name">Professional Profile</p><p class="mockup-meta">Acum • 🌍</p></div>
            </div>
            <div class="mockup-content">{st.session_state.current_posts['linkedin']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.current_posts['twitter']:
            st.markdown(f"""
            <div class="mockup-container brand-twitter">
                <div class="mockup-header">
                    <div class="mockup-avatar" style="border-radius:10px;"></div>
                    <div><p class="mockup-name">Brand Account <span style="color:#38bdf8;">✔</span></p><p class="mockup-meta">@brand_hub • 1m</p></div>
                </div>
                <div class="mockup-content">{st.session_state.current_posts['twitter']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        if st.session_state.current_posts['instagram']:
            st.markdown(f"""
            <div class="mockup-container brand-instagram">
                <div class="mockup-header">
                    <div class="mockup-avatar"></div>
                    <div><p class="mockup-name">social_hub_official</p></div>
                </div>
                <div class="mockup-content"><b>social_hub_official</b> {st.session_state.current_topic or 'Post'} {st.session_state.current_posts['instagram']}</div>
            </div>
            """, unsafe_allow_html=True)

        full_export = (
            f"=== LINKEDIN ===\n{st.session_state.current_posts['linkedin']}\n\n"
            f"=== TWITTER ===\n{st.session_state.current_posts['twitter']}\n\n"
            f"=== INSTAGRAM ===\n{st.session_state.current_posts['instagram']}"
        )
        st.download_button("📦 Descarcă Toate Postările (.txt)", data=full_export, file_name="campanie.txt", mime="text/plain")
