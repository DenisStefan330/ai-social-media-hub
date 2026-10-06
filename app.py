import os
import requests
import re
from bs4 import BeautifulSoup
import streamlit as st
import groq

# ==========================================
# 1. GESTIONARE SECURE A CHEILOR API
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
    if not api_key or not api_key.startswith("gsk_"):
        raise Exception("Cheia Groq API este invalidă sau lipsește. Verifică în setările de pe Streamlit Cloud dacă ai setat corect 'GROQ_API_KEY' (trebuie să înceapă cu 'gsk_').")

    client = groq.Groq(api_key=api_key)
    
    # Listă bulletproof actualizată cu modelele de producție active pe Groq
    candidate_models = [
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "qwen/qwen3-32b",
        "mixtral-8x7b-32768"
    ]
    
    system_prompt = (
        "You are an elite, hard-hitting B2B Social Media Content Strategist and Growth Hacker. "
        "Your task is to write hyper-engaging, highly specific, data-backed, and opinionated social media posts. "
        "CRITICAL RULES TO AVOID GENERIC CONTENT:\n"
        "1. NEVER use cliché fluff phrases like 'In today's fast-paced world', 'In conclusion', 'Revolutionizing the industry', or 'Excited to announce'.\n"
        "2. Start immediately with a controversial hook, a hard metric, a counter-intuitive insight, or a striking observation.\n"
        "3. Provide deep tactical insights, actionable frameworks, or concrete case studies based on the subject provided.\n"
        "4. Format output EXACTLY with these markers:\n"
        "[LINKEDIN]\n...hyper-targeted professional post with bold insights and line breaks...\n"
        "[TWITTER]\n...punchy, high-impact thread hook or single sharp tweet...\n"
        "[INSTAGRAM]\n...engaging visual caption with clear value and relevant hashtags...\n"
        "[IMG_PROMPT]\n...1 highly detailed professional cinematic visual prompt in English for FLUX...\n"
    )
    
    last_exception = None
    for model_name in candidate_models:
        try:
            # Folosim max_completion_tokens pentru modelele noi OpenAI/GPT OSS sau max_tokens pentru celelalte
            kwargs = {
                "model": model_name,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                "temperature": 0.7,
                "stream": True
            }
            if "gpt-oss" in model_name:
                kwargs["max_completion_tokens"] = 2000
            else:
                kwargs["max_tokens"] = 2000

            stream = client.chat.completions.create(**kwargs)
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
            return # Ieșire din funcție la succes
        except Exception as e:
            last_exception = e
            continue
            
    raise Exception(f"Toate modelele Groq încercate au eșuat. Verifică activarea cheii în Groq Console. Detalii: {str(last_exception)}")

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
        "app_sub": "Platformă Enterprise de Generare Conținut Multi-Platformă",
        "input_label": "🔗 Subiect detaliat sau URL Articol:",
        "input_placeholder": "Ex: https://techcrunch.com/... SAU Analiză detaliată despre impactul agentic AI în companii",
        "lang_label": "🌐 Limba Conținutului",
        "tone_label": "⚡ Tonul Campaniei",
        "toggle_img": "🎨 Generare Imagine (FLUX AI)",
        "btn_gen": "✨ Generează Postările",
        "sidebar_title": "💬 Istoric Postări",
        "new_chat": "➕ Postare Nouă",
        "settings_title": "⚙️ Setări & Preferințe",
        "ui_lang_label": "🌐 Limba Interfeței",
        "save_close": "Salvează & Închide"
    },
    "English": {
        "app_title": "AI Social Media Hub",
        "app_sub": "Enterprise Multi-Platform Content Generator",
        "input_label": "🔗 Detailed Subject or Article URL:",
        "input_placeholder": "Ex: https://techcrunch.com/... OR Deep dive into agentic AI enterprise adoption",
        "lang_label": "🌐 Content Language",
        "tone_label": "⚡ Campaign Tone",
        "toggle_img": "🎨 Generate Image (FLUX AI)",
        "btn_gen": "✨ Generate Posts",
        "sidebar_title": "💬 Post History",
        "new_chat": "➕ New Post",
        "settings_title": "⚙️ Settings & Preferences",
        "ui_lang_label": "🌐 Interface Language",
        "save_close": "Save & Close"
    }
}

t = UI_TEXTS[st.session_state.ui_lang]

# ==========================================
# 4. MODALUL DE SETĂRI NATIV (SIMPLIFICAT)
# ==========================================

@st.dialog(t['settings_title'])
def settings_modal():
    st.markdown("Configurează limba interfeței:")
    
    st.session_state.ui_lang = st.selectbox(
        t['ui_lang_label'], 
        ["Română", "English"], 
        index=0 if st.session_state.ui_lang == "Română" else 1
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(t['save_close'], use_container_width=True):
        st.rerun()

# ==========================================
# 5. BARA LATERALĂ (ISTORIC POSTĂRI)
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
# 6. HEADER PRINCIPAL ȘI INTERFAȚĂ
# ==========================================

head_col1, head_col2 = st.columns([11, 1])
with head_col1:
    st.markdown(f"<h1 style='margin:0; font-size: 2.2rem; color: #2563eb;'>{t['app_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='opacity:0.7; margin-top:0.3rem; margin-bottom:1.8rem;'>{t['app_sub']}</p>", unsafe_allow_html=True)
with head_col2:
    if st.button("⚙️", help="Setări"):
        settings_modal()

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
        st.warning("⚠️ Te rog să introduci un subiect sau un link valid.")
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
        else:
            context_data = f"SUBIECT: {topic_input}. Te rog să incluzi date concrete din industrie, metrici estimative de impact, exemple practice și unghiuri de analiză profunde, evitând orice clișeu sau introducere generală."

        st.markdown("### ✍️ Se generează conținutul avansat...")
        stream_container = st.empty()
        
        user_prompt = f"TARGET CONTENT / CONTEXT:\n{context_data}\n\nLANGUAGE: {lang}\nTONE: {tone}\n"
        full_response = ""
        
        try:
            for chunk in stream_groq_text(user_prompt, GROQ_API_KEY):
                full_response += chunk
                stream_container.markdown(full_response + "▌")
        except Exception as api_err:
            st.error(str(api_err))
            st.stop()
            
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
        if not img_prompt: img_prompt = f"Professional corporate illustration of {topic_input}, 8k"

        st.session_state.current_posts = {
            "linkedin": li_post,
            "twitter": tw_post,
            "instagram": ig_post,
            "img_prompt": img_prompt
        }

        if generate_image_toggle and HUGGINGFACE_API_KEY:
            with st.spinner("🎨 Se generează imaginea prin Hugging Face FLUX..."):
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
# 7. AFIȘARE REZULTATE CU COMPONENTE NATIVE
# ==========================================

if st.session_state.current_posts:
    st.markdown("---")
    st.markdown("## 📱 Rezultate Campanie")
    
    col_viz, col_posts = st.columns([1.2, 2])
    
    with col_viz:
        st.markdown("#### 🖼️ Vizual Generat (FLUX)")
        if st.session_state.current_image:
            st.image(st.session_state.current_image, use_container_width=True)
            st.download_button("📥 Descarcă Imaginea (.jpg)", st.session_state.current_image, "campanie.jpg", "image/jpeg")
        else:
            st.info("Imagine inactivă sau generare oprită.")
            
        st.markdown("<br><b>Prompt vizual AI:</b>", unsafe_allow_html=True)
        st.caption(st.session_state.current_posts['img_prompt'])

    with col_posts:
        st.markdown("#### 💼 LinkedIn Post")
        st.text_area("LinkedIn", value=st.session_state.current_posts['linkedin'], height=180, key="ta_li", label_visibility="collapsed")
        
        if st.session_state.current_posts['twitter']:
            st.markdown("#### 🐦 Twitter / X Post")
            st.text_area("Twitter", value=st.session_state.current_posts['twitter'], height=120, key="ta_tw", label_visibility="collapsed")
            
        if st.session_state.current_posts['instagram']:
            st.markdown("#### 📸 Instagram Caption")
            ig_full_text = f"social_hub_official {st.session_state.current_topic or ''} {st.session_state.current_posts['instagram']}"
            st.text_area("Instagram", value=ig_full_text, height=140, key="ta_ig", label_visibility="collapsed")

        full_export = (
            f"=== LINKEDIN ===\n{st.session_state.current_posts['linkedin']}\n\n"
            f"=== TWITTER ===\n{st.session_state.current_posts['twitter']}\n\n"
            f"=== INSTAGRAM ===\n{st.session_state.current_posts['instagram']}"
        )
        st.download_button("📦 Descarcă Toate Postările (.txt)", data=full_export, file_name="campanie.txt", mime="text/plain")
