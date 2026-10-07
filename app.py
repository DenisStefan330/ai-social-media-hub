import os
import re
import json
import requests
import streamlit as st
import groq
from streamlit_local_storage import LocalStorage
from duckduckgo_search import DDGS

# ==============================================================================
# 1. PAGE CONFIGURATION & INITIALIZATION
# ==============================================================================
st.set_page_config(
    page_title="Nexus Social AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Local Storage manager
localS = LocalStorage()

# Initialize Session State variables
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
if "daily_quota" not in st.session_state:
    st.session_state.daily_quota = 0
if "user_api_key" not in st.session_state:
    st.session_state.user_api_key = ""

# ==============================================================================
# 2. COMPLETE i18n DICTIONARY (ZERO HARDCODED TEXT)
# ==============================================================================
UI_TEXTS = {
    "Română": {
        "app_title": "Nexus Social AI",
        "app_sub": "Platformă Enterprise de Generare Conținut Multi-Platformă V2.0",
        "sidebar_title": "💬 Meniul Tău",
        "new_chat": "➕ Postare Nouă",
        "settings_btn": "⚙️ Setări",
        "settings_title": "⚙️ Setări & Preferințe",
        "ui_lang_label": "🌐 Limba Interfeței",
        "api_key_label": "Groq API Key Personal (Mod Nelimitat):",
        "save_close": "Salvează & Închide",
        "energy_label": "⚡ Energie Zilnică",
        "energy_delta": "consumată",
        "unlimited_badge": "🌟 Mod Nelimitat Activat",
        "config_header": "🎯 Configurare Campanie",
        "input_label": "🔗 Subiect detaliat, Întrebare sau URL Articol:",
        "input_placeholder": "Ex: https://techcrunch.com/... SAU Viitorul agentic AI în corporații",
        "lang_label": "🌐 Limba Conținutului",
        "tone_label": "⚡ Tonul Campaniei",
        "persona_label": "🎭 Brand Persona / Nișă (Opțional)",
        "persona_placeholder": "Ex: Nișa B2B SaaS, folosește tonul unui fondator tech...",
        "toggle_img": "🎨 Generare Imagine (FLUX AI)",
        "btn_gen": "✨ Generează Postările",
        "results_header": "📱 Vizualizare și Export",
        "tab_li": "💼 LinkedIn",
        "tab_tw": "🐦 Twitter (Thread)",
        "tab_ig": "📸 Instagram",
        "tab_img": "🖼️ Vizual Generat",
        "img_prompt_label": "**Prompt vizual AI (FLUX):**",
        "download_img": "📥 Descarcă JPG",
        "download_all": "📦 Descarcă Toate Postările (.txt)",
        "empty_history": "Nicio postare salvată în istoric.",
        "quota_exceeded": "❌ Ai atins limita de 3 generări zilnice. Introdu propria cheie Groq în Setări!",
        "warning_empty": "⚠️ Te rog să introduci un subiect sau un link valid.",
        "spinner_jina": "🌍 Extragem datele prin Jina AI Reader...",
        "spinner_ddg": "🔍 Căutăm știri relevante pe DuckDuckGo...",
        "spinner_gen": "🧠 Nexus AI generează campania strategică...",
        "spinner_flux": "🎨 Se sintetizează imaginea prin FLUX...",
        "toast_success": "🚀 Campania a fost generată cu succes!",
        "error_json": "Eroare: Răspunsul AI nu a putut fi decodat în JSON valid.",
        "no_models": "Nu s-a găsit niciun model Groq compatibil disponibil pe această cheie."
    },
    "English": {
        "app_title": "Nexus Social AI",
        "app_sub": "Enterprise Multi-Platform Content Generator V2.0",
        "sidebar_title": "💬 Your Menu",
        "new_chat": "➕ New Post",
        "settings_btn": "⚙️ Settings",
        "settings_title": "⚙️ Settings & Preferences",
        "ui_lang_label": "🌐 Interface Language",
        "api_key_label": "Custom Groq API Key (Unlimited Mode):",
        "save_close": "Save & Close",
        "energy_label": "⚡ Daily Energy",
        "energy_delta": "consumed",
        "unlimited_badge": "🌟 Unlimited Mode Active",
        "config_header": "🎯 Campaign Configuration",
        "input_label": "🔗 Detailed Subject, Query, or Article URL:",
        "input_placeholder": "Ex: https://techcrunch.com/... OR The future of agentic AI in enterprise",
        "lang_label": "🌐 Content Language",
        "tone_label": "⚡ Campaign Tone",
        "persona_label": "🎭 Brand Persona / Niche (Optional)",
        "persona_placeholder": "Ex: B2B SaaS niche, speak like a tech founder...",
        "toggle_img": "🎨 Generate Image (FLUX AI)",
        "btn_gen": "✨ Generate Posts",
        "results_header": "📱 View & Export",
        "tab_li": "💼 LinkedIn",
        "tab_tw": "🐦 Twitter (Thread)",
        "tab_ig": "📸 Instagram",
        "tab_img": "🖼️ Generated Visual",
        "img_prompt_label": "**AI Visual Prompt (FLUX):**",
        "download_img": "📥 Download JPG",
        "download_all": "📦 Download All Posts (.txt)",
        "empty_history": "No saved posts in history.",
        "quota_exceeded": "❌ You reached the daily limit of 3 free generations. Add your custom Groq API key in Settings!",
        "warning_empty": "⚠️ Please enter a valid subject or link.",
        "spinner_jina": "🌍 Extracting data via Jina AI Reader...",
        "spinner_ddg": "🔍 Searching recent news via DuckDuckGo...",
        "spinner_gen": "🧠 Nexus AI is crafting your strategic campaign...",
        "spinner_flux": "🎨 Synthesizing visual via FLUX...",
        "toast_success": "🚀 Campaign generated successfully!",
        "error_json": "Error: AI response could not be parsed into valid JSON.",
        "no_models": "No compatible Groq models available for this API key."
    }
}

t = UI_TEXTS[st.session_state.ui_lang]

# ==============================================================================
# 3. SECURE SECRETS & API HANDLERS
# ==============================================================================
def get_secret(key_name: str) -> str:
    try:
        return st.secrets[key_name]
    except Exception:
        return os.environ.get(key_name, "")

is_unlimited = bool(st.session_state.user_api_key.strip())
ACTIVE_GROQ_KEY = st.session_state.user_api_key if is_unlimited else get_secret("GROQ_API_KEY")
HUGGINGFACE_API_KEY = get_secret("HUGGINGFACE_API_KEY")

# ==============================================================================
# 4. BACKEND: JINA AI READER, DUCKDUCKGO & AUTO-HEALING GROQ
# ==============================================================================
def fetch_context_data(topic_input: str) -> str:
    is_url = topic_input.strip().startswith("http")
    if is_url:
        try:
            jina_url = f"https://r.jina.ai/{topic_input.strip()}"
            response = requests.get(jina_url, timeout=12)
            response.raise_for_status()
            return f"ARTICOL EXTRACTS:\n{response.text[:5000]}"
        except Exception as e:
            raise Exception(f"Eroare Jina AI: {str(e)}")
    else:
        try:
            with DDGS() as ddgs:
                results = [r.get('body', '') for r in ddgs.text(topic_input, max_results=3)]
                search_context = "\n".join(results) if results else "Niciun rezultat extern."
            return f"SUBIECT: {topic_input}\nCONTEXT WEB ACTUAL (TRENDS & NEWS):\n{search_context}"
        except Exception:
            return f"SUBIECT: {topic_input}"

def select_best_groq_model(client: groq.Groq) -> str:
    try:
        models_response = client.models.list()
        # Filtrare strictă: excludem modelele audio/whisper/embeddings
        valid_models = [
            m.id for m in models_response.data 
            if not any(x in m.id.lower() for x in ["whisper", "audio", "embed", "tts", "stt", "vision"])
        ]
        
        for pattern in ["llama-3.3", "llama-3.1", "mixtral", "llama3"]:
            matches = [mid for mid in valid_models if pattern in mid.lower()]
            if matches:
                return matches[0]
                
        if valid_models:
            return valid_models[0]
        return "llama-3.3-70b-versatile"
    except Exception:
        return "llama-3.3-70b-versatile"

def sanitize_json_output(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_substring = cleaned[first_brace:last_brace+1]
        return json.loads(json_substring)
    
    return json.loads(cleaned)

def generate_groq_campaign(prompt: str, api_key: str):
    if not api_key or not api_key.startswith("gsk_"):
        raise Exception("Cheia Groq API este invalidă sau lipsește.")

    client = groq.Groq(api_key=api_key)
    chosen_model = select_best_groq_model(client)
    
    # 🌟 NOUL PROMPT STRATEGIC DE ELITĂ (DEMAND GENERATION & CONTRARIAN TAKES)
    system_prompt = (
        "Ești un Strateg de Conținut B2B de elită și Growth Hacker specializat în generarea de cereri (demand generation) "
        "și poziționare de brand pe canale multiple. Sarcina ta este să creezi campanii de social media hiper-engaginge, "
        "extrem de specifice, bazate pe date și tendințe actuale.\n\n"
        "Campania trebuie să evite clișeele și limbajul de lemn corporatist, punând accent pe valoare practică, "
        "perspective nepopulare dar argumentate (contrarian takes) și studii de caz reale.\n\n"
        "CRITICAL: TREBUIE SĂ RĂSPUNZI EXCLUSIV ÎN FORMAT JSON VALID. Fără text conversațional în afara obiectului JSON.\n\n"
        "Chei obligatorii în structura JSON:\n"
        "1. 'linkedin': Un text lung, structurat tip fir logic (hook puternic, corp cu puncte clare bazate pe date/experiență, call-to-action de conversie), optimizat pentru algoritmii actuali de engagement profesional.\n"
        "2. 'twitter': O serie conectată (thread) de 3 până la 5 tweet-uri cu o idee densă, concisă și cu impact vizual ridicat pe linie de growth.\n"
        "3. 'instagram': O descriere (caption) dinamică, orientată vizual și narativ, incluzând sugestii clare pentru textul afișat pe ecran (on-screen text).\n"
        "4. 'img_prompt': Un prompt detaliat în limba engleză, optimizat pentru generatoare avansate de imagini (FLUX), descriind o vizualizare curată, modernă, non-stock, relevantă pentru tema postării."
    )
    
    completion = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.75,
        max_tokens=2500,
        response_format={"type": "json_object"}
    )
    
    raw_content = completion.choices[0].message.content
    return sanitize_json_output(raw_content)

def generate_image_huggingface(image_prompt: str, api_key: str) -> bytes:
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"inputs": image_prompt, "options": {"wait_for_model": True}}
    response = requests.post(API_URL, headers=headers, json=payload, timeout=35)
    response.raise_for_status()
    return response.content

# ==============================================================================
# 5. NATIVE SETTINGS DIALOG
# ==============================================================================
@st.dialog(t['settings_title'])
def settings_modal():
    st.session_state.ui_lang = st.selectbox(
        t['ui_lang_label'], 
        ["Română", "English"], 
        index=0 if st.session_state.ui_lang == "Română" else 1
    )
    st.markdown("---")
    st.session_state.user_api_key = st.text_input(
        t['api_key_label'], 
        value=st.session_state.user_api_key, 
        type="password",
        placeholder="gsk_..."
    )
    
    if st.button(t['save_close'], use_container_width=True):
        st.rerun()

# ==============================================================================
# 6. SIDEBAR & VISUAL ENERGY BAR
# ==============================================================================
with st.sidebar:
    st.markdown(f"### {t['sidebar_title']}")
    
    if st.button(t['new_chat'], use_container_width=True):
        st.session_state.current_posts = None
        st.session_state.current_image = None
        st.session_state.current_topic = ""
        st.rerun()
        
    st.markdown("---")
    
    if is_unlimited:
        st.success(t['unlimited_badge'])
    else:
        current_q = st.session_state.daily_quota
        remaining = max(0, 3 - current_q)
        delta_str = f"-1 {t['energy_delta']}" if current_q > 0 else None
        
        st.metric(label=t['energy_label'], value=f"{remaining} rămase", delta=delta_str)
        st.progress(max(0.0, float(remaining) / 3.0))
        
    st.markdown("---")
    st.caption("Nexus Social AI V2.0 • Powered by Groq & FLUX")

# ==============================================================================
# 7. HEADER & MAIN CONTAINER LAYOUT
# ==============================================================================
col_title, col_settings = st.columns([11, 1])
with col_title:
    st.markdown(f"<h1 style='margin:0; font-size: 2.3rem; color: #2563eb;'>{t['app_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='opacity:0.7; margin-top:0.3rem; margin-bottom:1.5rem;'>{t['app_sub']}</p>", unsafe_allow_html=True)
with col_settings:
    if st.button(t['settings_btn'], help="Settings"):
        settings_modal()

with st.container(border=True):
    st.markdown(f"#### {t['config_header']}")
    
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
        
    with st.expander(t['persona_label']):
        brand_persona = st.text_area("Persona details", placeholder=t['persona_placeholder'], height=75, label_visibility="collapsed")
        
    generate_image_toggle = st.toggle(t['toggle_img'], value=True)
    generate_btn = st.button(t['btn_gen'], type="primary")

# ==============================================================================
# 8. EXECUTION & GENERATION LOGIC
# ==============================================================================
if generate_btn:
    if not is_unlimited and st.session_state.daily_quota >= 3:
        st.error(t['quota_exceeded'])
        st.stop()
        
    if not topic_input.strip():
        st.warning(t['warning_empty'])
        st.stop()
        
    st.session_state.current_topic = topic_input
    
    is_url = topic_input.strip().startswith("http")
    spinner_text = t['spinner_jina'] if is_url else t['spinner_ddg']
    
    with st.spinner(spinner_text):
        try:
            context_data = fetch_context_data(topic_input.strip())
        except Exception as e:
            st.error(str(e))
            st.stop()
            
    prompt = (
        f"TARGET SUBJECT / CONTEXT / NEWS:\n{context_data}\n\n"
        f"LANGUAGE FOR CONTENT: {lang}\n"
        f"TONE: {tone}\n"
        f"NICHE / BRAND PERSONA DETAILS: {brand_persona}\n"
    )
    
    try:
        with st.spinner(t['spinner_gen']):
            parsed_json = generate_groq_campaign(prompt, ACTIVE_GROQ_KEY)
            
        st.session_state.current_posts = {
            "linkedin": parsed_json.get("linkedin", ""),
            "twitter": parsed_json.get("twitter", ""),
            "instagram": parsed_json.get("instagram", ""),
            "img_prompt": parsed_json.get("img_prompt", f"Professional modern visual representation of {topic_input}, 8k")
        }
    except json.JSONDecodeError:
        st.error(t['error_json'])
        st.stop()
    except Exception as api_err:
        st.error(f"Eroare API: {str(api_err)}")
        st.stop()
        
    st.session_state.current_image = None
    if generate_image_toggle and HUGGINGFACE_API_KEY:
        with st.spinner(t['spinner_flux']):
            try:
                st.session_state.current_image = generate_image_huggingface(
                    st.session_state.current_posts['img_prompt'], 
                    HUGGINGFACE_API_KEY
                )
            except Exception as img_err:
                st.warning(f"Imaginea nu a putut fi generată: {str(img_err)}")
                
    if not is_unlimited:
        st.session_state.daily_quota += 1
        
    st.toast(t['toast_success'], icon='✅')
    st.rerun()

# ==============================================================================
# 9. RESULTS CARD & TABS CONTAINER
# ==============================================================================
if st.session_state.current_posts:
    with st.container(border=True):
        st.markdown(f"#### {t['results_header']}")
        
        tab_li, tab_tw, tab_ig, tab_img = st.tabs([
            t['tab_li'], 
            t['tab_tw'], 
            t['tab_ig'], 
            t['tab_img']
        ])
        
        with tab_li:
            st.text_area("LinkedIn Content", value=st.session_state.current_posts['linkedin'], height=250, key="ta_li", label_visibility="collapsed")
            
        with tab_tw:
            st.text_area("Twitter Thread", value=st.session_state.current_posts['twitter'], height=200, key="ta_tw", label_visibility="collapsed")
            
        with tab_ig:
            ig_full = f"nexus_social_official {st.session_state.current_topic}\n\n{st.session_state.current_posts['instagram']}"
            st.text_area("Instagram Caption", value=ig_full, height=200, key="ta_ig", label_visibility="collapsed")
            
        with tab_img:
            if st.session_state.current_image:
                col_img_view, col_img_info = st.columns([2, 1])
                with col_img_view:
                    st.image(st.session_state.current_image, use_container_width=True)
                with col_img_info:
                    st.markdown(t['img_prompt_label'])
                    st.caption(st.session_state.current_posts['img_prompt'])
                    st.download_button(t['download_img'], st.session_state.current_image, "nexus_campaign.jpg", "image/jpeg", use_container_width=True)
            else:
                st.info("Generarea vizuală este inactivă sau cheia Hugging Face lipsește.")
                
        st.markdown("---")
        full_export = (
            f"=== LINKEDIN ===\n{st.session_state.current_posts['linkedin']}\n\n"
            f"=== TWITTER THREAD ===\n{st.session_state.current_posts['twitter']}\n\n"
            f"=== INSTAGRAM ===\n{st.session_state.current_posts['instagram']}"
        )
        st.download_button(t['download_all'], data=full_export, file_name="nexus_campaign.txt", mime="text/plain")
