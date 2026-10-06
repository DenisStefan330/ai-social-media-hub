import os
import time
import urllib.parse
import requests
import re
from bs4 import BeautifulSoup
import streamlit as st

# ==========================================
# 1. GESTIONARE SECURE A CHEILOR API (Server-Side)
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
        raise Exception(f"Nu am putut citi link-ul. Asigură-te că este public. ({str(e)})")

def stream_groq_text(prompt: str, api_key: str):
    from groq import Groq
    client = Groq(api_key=api_key)
    
    system_prompt = (
        "You are an elite Social Media Copywriter and Content Strategist. "
        "Create viral, insightful posts based on the user's topic or provided article text. "
        "CRITICAL RULES: "
        "1. You MUST format the output EXACTLY with these markers so the system can parse it:\n"
        "[LINKEDIN]\n...linkedin post here...\n"
        "[TWITTER]\n...twitter post here...\n"
        "[INSTAGRAM]\n...instagram caption here...\n"
        "[IMG_PROMPT]\n...1 highly detailed, professional visual prompt in English for FLUX image generator...\n"
        "2. Do not use generic fluff. Use strong hooks and data-driven insights."
    )

    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2500,
            stream=True
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
    payload = {
        "inputs": image_prompt,
        "options": {"wait_for_model": True}
    }
    
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.content

# ==========================================
# 3. TRADUCERI ȘI CONFIGURARE UI
# ==========================================

st.set_page_config(page_title="AI Social Media Hub v3.1", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

UI_TEXTS = {
    "Română": {
        "app_title": "AI Social Media Hub v3.1",
        "app_sub": "Platformă Enterprise de Generare Campanii Multi-Platformă",
        "tab_generator": "🚀 Generator Campanii",
        "tab_settings": "⚙️ Panou de Setări & Preferințe",
        "tab_history": "📜 Istoric Campanii",
        "input_label": "🔗 Subiect sau URL Articol:",
        "input_placeholder": "Ex: https://techcrunch.com/... SAU Viitorul AI-ului în medicină",
        "lang_label": "🌐 Limba Conținutului",
        "tone_label": "⚡ Tonul Campaniei",
        "toggle_img": "🎨 Generare Imagine (FLUX AI)",
        "btn_gen": "✨ Generează Campania (Live Streaming)",
        "spinner_scrape": "🌍 Extragem conținutul de pe web...",
        "spinner_text": "✍️ Se generează strategia de conținut...",
        "spinner_img": "🎨 Generăm vizualul cu modelul FLUX.1-schnell...",
        "success_scrape": "✅ Articol citit cu succes!",
        "results": "📱 Rezultate Campanie",
        "settings_header": "Parametri Vizuali și de Sistem",
        "font_size_label": "🔤 Dimensiune Text în Postări",
        "ui_lang_label": "🌐 Limba Interfeței (UI)",
        "history_empty": "Nu există campanii salvate în istoricul sesiunii."
    },
    "English": {
        "app_title": "AI Social Media Hub v3.1",
        "app_sub": "Enterprise Multi-Platform Campaign Generator",
        "tab_generator": "🚀 Campaign Generator",
        "tab_settings": "⚙️ Settings & Preferences",
        "tab_history": "📜 Campaign History",
        "input_label": "🔗 Subject or Article URL:",
        "input_placeholder": "Ex: https://techcrunch.com/... OR Future of AI in medicine",
        "lang_label": "🌐 Content Language",
        "tone_label": "⚡ Campaign Tone",
        "toggle_img": "🎨 Generate Image (FLUX AI)",
        "btn_gen": "✨ Generate Campaign (Live Streaming)",
        "spinner_scrape": "🌍 Extracting web content...",
        "spinner_text": "✍ Generating content strategy...",
        "spinner_img": "🎨 Rendering visual with FLUX.1-schnell...",
        "success_scrape": "✅ Article parsed successfully!",
        "results": "📱 Campaign Results",
        "settings_header": "Visual and System Parameters",
        "font_size_label": "🔤 Post Text Font Size",
        "ui_lang_label": "🌐 Interface Language (UI)",
        "history_empty": "No campaigns saved in the session history."
    }
}

# ==========================================
# 4. GESTIONARE STATE & PREFERINȚE
# ==========================================

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "Română"
if "font_size" not in st.session_state:
    st.session_state.font_size = "Normal (15px)"
if "generated" not in st.session_state:
    st.session_state.generated = False
if "current_posts" not in st.session_state:
    st.session_state.current_posts = {"linkedin": "", "twitter": "", "instagram": "", "img_prompt": ""}
if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = None
if "history" not in st.session_state:
    st.session_state.history = []

t = UI_TEXTS[st.session_state.ui_lang]

font_size_map = {
    "Compact (13px)": "13px",
    "Normal (15px)": "15px",
    "Large (18px)": "18px"
}
active_font_size = font_size_map.get(st.session_state.font_size, "15px")

st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}
    .stTextInput input, .stSelectbox select {{
        background-color: #f8fafc !important; border: 2px solid #e2e8f0 !important;
        border-radius: 12px !important; padding: 0.8rem !important; transition: 0.3s;
    }}
    .stTextInput input:focus {{ border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.2) !important; }}
    .stButton button {{
        background: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%);
        color: white; font-weight: bold; border-radius: 12px; padding: 0.8rem; border: none; width: 100%;
    }}
    .mockup-container {{
        background: white; border-radius: 16px; padding: 24px; margin-bottom: 24px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #f1f5f9;
        color: #0f172a; font-size: {active_font_size} !important; line-height: 1.6;
    }}
    .mockup-header {{ display: flex; align-items: center; margin-bottom: 16px; }}
    .mockup-avatar {{ width: 48px; height: 48px; border-radius: 50%; background: #e2e8f0; margin-right: 12px; }}
    .mockup-name {{ font-weight: 700; font-size: 16px; margin: 0; padding: 0; }}
    .mockup-meta {{ font-size: 13px; color: #64748b; margin: 0; }}
    .brand-linkedin {{ border-top: 4px solid #0a66c2; }}
    .brand-twitter {{ border-top: 4px solid #000000; }}
    .brand-instagram {{ border-top: 4px solid #e1306c; }}
    .mockup-content {{ white-space: pre-wrap; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 5. NAVIGARE PRINCIPALĂ PE TAB-URI
# ==========================================

tab_gen, tab_settings, tab_history = st.tabs([t["tab_generator"], t["tab_settings"], t["tab_history"]])

# --- TAB 1: GENERATOR ---
with tab_gen:
    st.markdown(f"<h1 style='text-align:center; font-weight:800; color:#0f172a;'>{t['app_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#64748b; margin-bottom:2.5rem;'>{t['app_sub']}</p>", unsafe_allow_html=True)

    input_col, controls_col = st.columns([2, 1])
    with input_col:
        topic_input = st.text_input(t['input_label'], placeholder=t['input_placeholder'])

    with controls_col:
        lang = st.selectbox(t['lang_label'], ["Română", "English", "Français", "Deutsch"])
        tone = st.selectbox(t['tone_label'], ["Profesional & Analitic", "Casual & Prietenos", "Provocator", "Educațional"])
        generate_image_toggle = st.toggle(t['toggle_img'], value=True)

    generate_btn = st.button(t['btn_gen'])

    if generate_btn:
        if not topic_input.strip():
            st.warning("⚠️ Te rog să introduci un subiect valid sau un link.")
        elif not GROQ_API_KEY:
            st.error("⚠️ Lipsă cheie API Groq în setările serverului (Streamlit Secrets).")
        else:
            st.session_state.generated = False
            st.session_state.image_bytes = None
            context_data = topic_input
            
            is_url = re.match(r"^https?://", topic_input.strip())
            if is_url:
                with st.spinner(t['spinner_scrape']):
                    try:
                        context_data = scrape_url_content(topic_input.strip())
                        st.success(t['success_scrape'])
                    except Exception as e:
                        st.error(str(e))
                        st.stop()

            st.markdown(f"### {t['spinner_text']}")
            stream_container = st.empty()
            
            user_prompt = f"SUBJECT OR CONTEXT:\n{context_data}\n\nLANGUAGE: {lang}\nTONE: {tone}\n"
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
            img_prompt = extract_section(full_response, "[IMG_PROMPT]")

            if not li_post: li_post = full_response
            if not img_prompt: img_prompt = f"Professional corporate illustration of {topic_input}, 8k, modern aesthetic"

            st.session_state.current_posts = {"linkedin": li_post, "twitter": tw_post, "instagram": ig_post, "img_prompt": img_prompt}

            if generate_image_toggle:
                if not HUGGINGFACE_API_KEY:
                    st.warning("⚠️ Toggle-ul de imagine este activ, dar lipsește 'HUGGINGFACE_API_KEY' în Secrets.")
                else:
                    with st.spinner(t['spinner_img']):
                        try:
                            st.session_state.image_bytes = generate_image_huggingface(img_prompt, HUGGINGFACE_API_KEY)
                        except Exception as e:
                            st.error(f"Eroare la generarea imaginii: {str(e)}")
                            
            st.session_state.generated = True
            
            # Adăugăm în istoricul sesiunii
            st.session_state.history.insert(0, {
                "topic": topic_input,
                "posts": st.session_state.current_posts,
                "image": st.session_state.image_bytes
            })
            st.rerun()

    # Afișare rezultate curente
    if st.session_state.generated:
        st.markdown("---")
        st.markdown(f"## {t['results']}")
        
        col_viz, col_posts = st.columns([1.2, 2])
        
        with col_viz:
            st.markdown("#### 🖼️ Vizual Generat")
            if st.session_state.image_bytes:
                st.image(st.session_state.image_bytes, use_container_width=True)
                st.download_button("📥 Descarcă Imaginea (.jpg)", st.session_state.image_bytes, "campanie_vizual.jpg", "image/jpeg")
            else:
                st.info("Generarea de imagini a fost oprită sau indisponibilă.")
                
            st.markdown("<br><b>Promptul vizual creat de AI:</b>", unsafe_allow_html=True)
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
                        <div><p class="mockup-name">Brand Account <span style="color:#1d9bf0;">✔</span></p><p class="mockup-meta">@brand_hub • 1m</p></div>
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
                    <div class="mockup-content"><b>social_hub_official</b> {st.session_state.current_posts['instagram']}</div>
                </div>
                """, unsafe_allow_html=True)

            full_export_text = (
                f"=== LINKEDIN ===\n{st.session_state.current_posts['linkedin']}\n\n"
                f"=== TWITTER ===\n{st.session_state.current_posts['twitter']}\n\n"
                f"=== INSTAGRAM ===\n{st.session_state.current_posts['instagram']}\n\n"
                f"=== IMG PROMPT ===\n{st.session_state.current_posts['img_prompt']}"
            )
            st.download_button("📦 Descarcă Toate Postările (.txt)", data=full_export_text, file_name="pachet_campanie_complet.txt", mime="text/plain")


# --- TAB 2: SETĂRI ȘI PREFERINȚE ---
with tab_settings:
    st.markdown(f"<h2>{t['tab_settings']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p>{t['settings_header']}</p><br>", unsafe_allow_html=True)
    
    st.session_state.ui_lang = st.selectbox(
        t['ui_lang_label'], 
        ["Română", "English"], 
        index=0 if st.session_state.ui_lang == "Română" else 1
    )
    
    st.session_state.font_size = st.selectbox(
        t['font_size_label'], 
        ["Compact (13px)", "Normal (15px)", "Large (18px)"],
        index=1
    )
    
    st.success("✨ Setările sunt aplicate instantaneu în toată aplicația.")


# --- TAB 3: ISTORIC CAMPANII ---
with tab_history:
    st.markdown(f"<h2>{t['tab_history']}</h2><br>", unsafe_allow_html=True)
    
    if not st.session_state.history:
        st.info(t['history_empty'])
    else:
        for idx, item in enumerate(st.session_state.history):
            with st.expander(f"📁 Campania #{len(st.session_state.history) - idx}: {item['topic']}"):
                st.markdown(f"**Subiect / Link:** {item['topic']}")
                st.markdown("---")
                st.markdown(item['posts']['linkedin'])
                if item['image']:
                    st.image(item['image'], width=400)
