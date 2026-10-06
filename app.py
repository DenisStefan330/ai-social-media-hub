import os
import time
import urllib.parse
import requests
import io
import streamlit as st

# ==========================================
# FUNCȚII HELPER (Business Logic & API Calls)
# ==========================================


def generate_text_groq(prompt: str, api_key: str) -> str:
    from groq import Groq
    client = Groq(api_key=api_key)
    
    # Lista de modele, ordonata de la cel mai performant la fallback-uri stabile (Free Tier)
    models_to_try = [
        "llama-3.1-70b-versatile", # Modelul principal stabil
        "llama-3.1-8b-instant",    # Extrem de rapid, fallback excelent
        "mixtral-8x7b-32768"       # Model arhitectural diferit, foarte fiabil pe Groq
    ]
    
    last_error = None
    
    # Incercam modelele secvential. Daca unul pica (ex: 404 sau Rate Limit), trecem la urmatorul.
    for model_name in models_to_try:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an elite AI Social Media R&D Strategist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2048,
            )
            # Daca a reusit, returnam textul si oprim bucla
            return completion.choices[0].message.content
            
        except Exception as e:
            # Salvam eroarea si continuam bucla catre urmatorul model
            last_error = str(e)
            continue
            
    # Daca TOATE modelele au picat, abia atunci ridicam eroarea catre interfata Streamlit
    raise Exception(f"Toate modelele au eșuat. Ultima eroare: {last_error}")

def generate_image_pollinations(prompt: str, width: int = 1280, height: int = 720) -> bytes:
    # Optimizare: Adaugam 'high quality, professional' in engleza pentru a forta modelul vizual
    enhanced_prompt = f"Professional conceptual digital art depicting: {prompt}, high resolution, corporate aesthetic, clean UI"
    encoded_prompt = urllib.parse.quote(enhanced_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"
    
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.content

# ==========================================
# CONFIGURARE UI ȘI TRADUCERI (Presentation)
# ==========================================

st.set_page_config(
    page_title="AI Social Media Hub",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    .stTextInput input, .stSelectbox select {
        background-color: #1e293b !important; color: #f8fafc !important;
        border: 1px solid #334155 !important; border-radius: 10px !important; padding: 0.6rem !important;
    }
    .stTextInput input:focus, .stSelectbox select:focus {
        border-color: #6366f1 !important; box-shadow: 0 0 0 1px #6366f1 !important;
    }
    .stButton button {
        width: 100%; background: linear-gradient(135deg, #6366f1 0%, #06b6d4 100%);
        color: white; font-weight: 600; border: none; border-radius: 10px; padding: 0.75rem;
        transition: all 0.2s ease; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
    }
    .stButton button:hover { opacity: 0.95; transform: translateY(-1px); }
    </style>
""", unsafe_allow_html=True)

UI_TEXTS = {
    "English": {
        "sidebar_title": "⚙️ Settings & Auth",
        "sidebar_api_label": "Groq API Key (Free)",
        "sidebar_test_header": "🧪 Test Mode (Offline)",
        "sidebar_test_checkbox": "Activate Test Mode (No API)",
        "sidebar_test_desc": "Simulates a rich campaign without consuming API calls.",
        "sidebar_lang_header": "🌐 App Language (UI)",
        "title": "AI Social Media Hub",
        "subtitle": "Transform any raw subject into a high-impact multi-platform campaign.",
        "topic_label": "🎯 Campaign Subject / Main Idea:",
        "topic_placeholder": "Ex: AI Workflow Automation in Remote Teams",
        "lang_label": "🌐 Output Content Language",
        "tone_label": "⚡ Campaign Tone",
        "image_checkbox": "🎨 Generate Campaign Image (Free)",
        "generate_btn": "✨ Generate Content Package",
        "spinner_text": "Processing campaign strategy (via Groq)...",
        "spinner_image": "Generating stunning visuals (via Pollinations)...",
        "success": "🎉 Campaign generated successfully!",
        "results_header": "📱 Campaign Results",
        "download_btn": "📥 Download Campaign (.txt)",
        "download_img_btn": "🖼️ Download Image (.jpg)",
        "err_topic": "⚠️ Please enter a valid subject before generating.",
        "err_auth": "⚠️ Please open the sidebar and enter your Groq API key.",
        "err_gen": "⚠️ Error generating content:"
    },
    "Română": {
        "sidebar_title": "⚙️ Setări & Autentificare",
        "sidebar_api_label": "Cheie API Groq (Gratuit)",
        "sidebar_test_header": "🧪 Mod de Test (Offline)",
        "sidebar_test_checkbox": "Activează Test Mode (Fără API)",
        "sidebar_test_desc": "Simulează o campanie bogată fără a consuma cereri API.",
        "sidebar_lang_header": "🌐 Limba Interfeței (UI)",
        "title": "AI Social Media Hub",
        "subtitle": "Transformă orice subiect brut într-o campanie multi-platformă de impact.",
        "topic_label": "🎯 Subiectul campaniei / Ideea principală:",
        "topic_placeholder": "Ex: AI Workflow Automation in Remote Teams",
        "lang_label": "🌐 Limba de ieșire (Conținut)",
        "tone_label": "⚡ Tonul Campaniei",
        "image_checkbox": "🎨 Generează Imagine (Gratuit)",
        "generate_btn": "✨ Generează Pachetul de Conținut",
        "spinner_text": "Se procesează strategia campaniei (via Groq)...",
        "spinner_image": "Se generează elementele vizuale (via Pollinations)...",
        "success": "🎉 Campania a fost generată cu succes!",
        "results_header": "📱 Rezultate Campanie",
        "download_btn": "📥 Descarcă Campania (.txt)",
        "download_img_btn": "🖼️ Descarcă Imaginea (.jpg)",
        "err_topic": "⚠️ Te rog să introduci un subiect valid înainte de generare.",
        "err_auth": "⚠️ Deschide meniul lateral și introdu cheia API Groq.",
        "err_gen": "⚠️️ Eroare la generarea conținutului:"
    },
    "Français": {
        "sidebar_title": "⚙️ Paramètres & Auth",
        "sidebar_api_label": "Clé API Groq (Gratuit)",
        "sidebar_test_header": "🧪 Mode Test (Hors ligne)",
        "sidebar_test_checkbox": "Activer le mode test (Sans API)",
        "sidebar_test_desc": "Simule une campagne sans appels API.",
        "sidebar_lang_header": "🌐 Langue de l'interface (UI)",
        "title": "AI Social Media Hub",
        "subtitle": "Transformez n'importe quel sujet brut en une campagne à fort impact.",
        "topic_label": "🎯 Sujet de la campagne :",
        "topic_placeholder": "Ex: Automatisation des flux IA",
        "lang_label": "🌐 Langue du contenu de sortie",
        "tone_label": "⚡ Ton de la campagne",
        "image_checkbox": "🎨 Générer une image (Gratuit)",
        "generate_btn": "✨ Générer le package",
        "spinner_text": "Traitement de la stratégie...",
        "spinner_image": "Génération de visuels...",
        "success": "🎉 Campagne générée avec succès !",
        "results_header": "📱 Résultats",
        "download_btn": "📥 Télécharger la campagne (.txt)",
        "download_img_btn": "🖼️ Télécharger l'image (.jpg)",
        "err_topic": "⚠️ Veuillez entrer un sujet valide.",
        "err_auth": "⚠️ Veuillez entrer votre clé API Groq.",
        "err_gen": "⚠️ Erreur :"
    },
    "Deutsch": {
        "sidebar_title": "⚙️ Einstellungen",
        "sidebar_api_label": "Groq API-Schlüssel",
        "sidebar_test_header": "🧪 Testmodus",
        "sidebar_test_checkbox": "Testmodus aktivieren",
        "sidebar_test_desc": "Simuliert eine Kampagne ohne API.",
        "sidebar_lang_header": "🌐 App-Sprache (UI)",
        "title": "AI Social Media Hub",
        "subtitle": "Verwandeln Sie jedes Thema in eine wirkungsvolle Kampagne.",
        "topic_label": "🎯 Kampagnenthema:",
        "topic_placeholder": "Bsp.: KI-Automatisierung",
        "lang_label": "🌐 Zielsprache für Inhalte",
        "tone_label": "⚡ Kampagnenton",
        "image_checkbox": "🎨 Kampagnenbild generieren",
        "generate_btn": "✨ Inhaltspaket generieren",
        "spinner_text": "Kampagnenstrategie wird verarbeitet...",
        "spinner_image": "Visuals werden erstellt...",
        "success": "🎉 Kampagne erfolgreich generiert!",
        "results_header": "📱 Ergebnisse",
        "download_btn": "📥 Text herunterladen (.txt)",
        "download_img_btn": "🖼️ Bild herunterladen (.jpg)",
        "err_topic": "⚠️ Bitte ein Thema eingeben.",
        "err_auth": "⚠️ Bitte Groq API-Schlüssel eingeben.",
        "err_gen": "⚠️ Fehler:"
    },
    "Español": {
        "sidebar_title": "⚙️ Configuración",
        "sidebar_api_label": "Clave API Groq",
        "sidebar_test_header": "🧪 Modo de Prueba",
        "sidebar_test_checkbox": "Activar modo de prueba",
        "sidebar_test_desc": "Simula una campaña sin consumir API.",
        "sidebar_lang_header": "🌐 Idioma de la interfaz",
        "title": "AI Social Media Hub",
        "subtitle": "Transforma cualquier tema en una campaña de alto impacto.",
        "topic_label": "🎯 Tema de la campaña:",
        "topic_placeholder": "Ej: Automatización de IA",
        "lang_label": "🌐 Idioma de contenido",
        "tone_label": "⚡ Tono de la campaña",
        "image_checkbox": "🎨 Generar imagen (Gratis)",
        "generate_btn": "✨ Generar paquete",
        "spinner_text": "Procesando estrategia...",
        "spinner_image": "Generando imagen...",
        "success": "🎉 ¡Campaña generada!",
        "results_header": "📱 Resultados",
        "download_btn": "📥 Descargar texto (.txt)",
        "download_img_btn": "🖼️ Descargar Imagen (.jpg)",
        "err_topic": "⚠️️ Introduce un tema válido.",
        "err_auth": "⚠️ Introduce tu clave API Groq.",
        "err_gen": "⚠️ Error:"
    }
}

# ==========================================
# MENIU LATERAL & STARE (Sidebar)
# ==========================================

st.sidebar.header(UI_TEXTS["English"]["sidebar_title"]) # Header fix pentru a rula corect inainte de selectia limbii
ui_language = st.sidebar.selectbox(
    "🌐 App Language (UI)",
    ["English", "Română", "Français", "Deutsch", "Español"],
    index=0
)
t = UI_TEXTS[ui_language] # Incarcam traducerile alese

api_key_input = st.sidebar.text_input(t["sidebar_api_label"], type="password")
api_key = api_key_input if api_key_input else os.environ.get("GROQ_API_KEY")

st.sidebar.markdown("---")
st.sidebar.header(t["sidebar_test_header"])
test_mode = st.sidebar.checkbox(t["sidebar_test_checkbox"], value=False)
st.sidebar.markdown(t["sidebar_test_desc"])

# ==========================================
# INTERFAȚA PRINCIPALĂ (Main Body)
# ==========================================

st.markdown("<div style='text-align: center; margin-top: 1rem;'>", unsafe_allow_html=True)
st.markdown(f"<h1 style='font-size: 2.25rem; font-weight: 700; margin-bottom: 0.5rem; background: linear-gradient(135deg, #818cf8 0%, #22d3ee 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>{t['title']}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #94a3b8; font-size: 1rem; margin-bottom: 2rem;'>{t['subtitle']}</p>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

topic_input = st.text_input(t['topic_label'], placeholder=t['topic_placeholder'])

col1, col2 = st.columns(2)
with col1:
    language_choice = st.selectbox(
        t['lang_label'],
        ["English", "Română", "Français", "Deutsch", "Español"]
    )
with col2:
    tone_choice = st.selectbox(
        t['tone_label'],
        ["Professional & Analytical", "Casual & Engaging", "Bold & Provocative", "Educational & Structured"]
    )

generate_image_cb = st.checkbox(t['image_checkbox'], value=True)
st.markdown("<br>", unsafe_allow_html=True)
generate_btn = st.button(t['generate_btn'])

# ==========================================
# EXECUȚIE ȘI REZULTATE
# ==========================================

if generate_btn:
    if not topic_input.strip():
        st.warning(t['err_topic'])
    elif not test_mode and not api_key:
        st.error(t['err_auth'])
    else:
        response_text = ""
        image_bytes = None
        
        # 1. GENERARE TEXT
        with st.spinner(t['spinner_text']):
            try:
                if test_mode:
                    time.sleep(0.5)
                    response_text = f"### 📊 LINKEDIN\n[Test Mode] Campanie despre {topic_input} in limba {language_choice} cu ton {tone_choice}.\n\n### 🧵 X (TWITTER)\n[Test Mode] Thread de test."
                else:
                    prompt = (
                        f'Create a comprehensive multi-platform content package for the following topic: "{topic_input}".\n\n'
                        "CRITICAL INSTRUCTIONS:\n"
                        f"- Output Language: STRICTLY {language_choice}. Do not mix languages.\n"
                        f"- Tone & Style: {tone_choice}.\n\n"
                        "Structure into 3 sections using markdown headings: 1. LINKEDIN 2. X (TWITTER) 3. INSTAGRAM."
                    )
                    response_text = generate_text_groq(prompt, api_key)
            except Exception as e:
                st.error(f"{t['err_gen']} {str(e)}")

        # 2. GENERARE IMAGINE (Daca e bifat si avem text valid)
        if generate_image_cb and response_text:
            with st.spinner(t['spinner_image']):
                try:
                    if test_mode:
                        req = requests.get("https://picsum.photos/1280/720")
                        image_bytes = req.content
                    else:
                        image_bytes = generate_image_pollinations(f"{topic_input} - {tone_choice} style")
                except Exception as e:
                    st.warning(f"Imaginea nu a putut fi generată, dar textul este gata. Detalii: {str(e)}")

        # 3. AFIȘARE REZULTATE
        if response_text:
            st.success(t['success'])
            st.markdown(f"### {t['results_header']}")
            st.markdown(response_text)
            
            if image_bytes:
                st.markdown("---")
                st.image(image_bytes, caption=f"Generated for: {topic_input}", use_container_width=True)
            
            st.markdown("---")
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.download_button(
                    label=t['download_btn'],
                    data=response_text,
                    file_name=f"social_campaign_{language_choice.lower()}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with dl_col2:
                if image_bytes:
                    st.download_button(
                        label=t['download_img_btn'],
                        data=image_bytes,
                        file_name="campaign_img.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748b; font-size: 12px;'>Fast Engine R&D • Powered by Groq & Pollinations.ai</p>", unsafe_allow_html=True)
