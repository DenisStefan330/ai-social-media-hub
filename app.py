import os
import time
import streamlit as st
from google import genai

# 1. Configurare pagină (Layout centrat, sidebar ascuns și glisabil implicit)
st.set_page_config(
    page_title="AI Social Media Hub",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Design minimalist, curat și profesional
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    .stTextInput input, .stSelectbox select {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        padding: 0.6rem !important;
    }
    .stTextInput input:focus, .stSelectbox select:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 1px #6366f1 !important;
    }
    .stButton button {
        width: 100%;
        background: linear-gradient(135deg, #6366f1 0%, #06b6d4 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 10px;
        padding: 0.75rem;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
    }
    .stButton button:hover {
        opacity: 0.95;
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(99, 102, 241, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# --- DICTIONAR DE TRADUCERI UI PENTRU TOATE CELE 5 LIMBI ---
UI_TEXTS = {
    "English": {
        "sidebar_title": "⚙️ Settings & Auth",
        "sidebar_api_label": "Gemini API Key",
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
        "generate_btn": "✨ Generate Content Package",
        "spinner": "Processing campaign strategy...",
        "success": "🎉 Campaign generated successfully!",
        "results_header": "📱 Campaign Results",
        "download_btn": "📥 Download Campaign (.txt file)",
        "err_topic": "⚠️ Please enter a valid subject before generating.",
        "err_auth": "⚠️ Please open the sidebar and enter your Gemini API key (or check 'Activate Test Mode').",
        "err_503": "⚠️ Google servers are temporarily busy (Error 503). You can check 'Activate Test Mode' from the sidebar!"
    },
    "Română": {
        "sidebar_title": "⚙️ Setări & Autentificare",
        "sidebar_api_label": "Gemini API Key",
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
        "generate_btn": "✨ Generează Pachetul de Conținut",
        "spinner": "Se procesează strategia campaniei...",
        "success": "🎉 Campania a fost generată cu succes!",
        "results_header": "📱 Rezultate Campanie",
        "download_btn": "📥 Descarcă Campania (fișier .txt)",
        "err_topic": "⚠️ Te rog să introduci un subiect valid înainte de generare.",
        "err_auth": "⚠️ Te rog să deschizi meniul din stânga și să introduci cheia ta Gemini API (sau bifează 'Activează Test Mode').",
        "err_503": "⚠️ Serverul Google este temporar aglomerat (Eroare 503). Poți bifa 'Activează Test Mode' din meniul lateral!"
    },
    "Français": {
        "sidebar_title": "⚙️ Paramètres & Authentification",
        "sidebar_api_label": "Clé API Gemini",
        "sidebar_test_header": "🧪 Mode Test (Hors ligne)",
        "sidebar_test_checkbox": "Activer le mode test (Sans API)",
        "sidebar_test_desc": "Simule une campagne riche sans consommer d'appels API.",
        "sidebar_lang_header": "🌐 Langue de l'interface (UI)",
        "title": "AI Social Media Hub",
        "subtitle": "Transformez n'importe quel sujet brut en une campagne multi-plateforme à fort impact.",
        "topic_label": "🎯 Sujet de la campagne / Idée principale :",
        "topic_placeholder": "Ex: Automatisation des flux de travail IA",
        "lang_label": "🌐 Langue du contenu de sortie",
        "tone_label": "⚡ Ton de la campagne",
        "generate_btn": "✨ Générer le package de contenu",
        "spinner": "Traitement de la stratégie de campagne...",
        "success": "🎉 Campagne générée avec succès !",
        "results_header": "📱 Résultats de la campagne",
        "download_btn": "📥 Télécharger la campagne (.txt)",
        "err_topic": "⚠️ Veuillez entrer un sujet valide avant de générer.",
        "err_auth": "⚠️ Veuillez ouvrir la barre latérale et entrer votre clé API Gemini (ou activer le mode test).",
        "err_503": "⚠️ Les serveurs Google sont temporairement occupés (Erreur 503). Activez le mode test !"
    },
    "Deutsch": {
        "sidebar_title": "⚙️ Einstellungen & Auth",
        "sidebar_api_label": "Gemini API-Schlüssel",
        "sidebar_test_header": "🧪 Testmodus (Offline)",
        "sidebar_test_checkbox": "Testmodus aktivieren (Keine API)",
        "sidebar_test_desc": "Simuliert eine reichhaltige Kampagne ohne API-Aufrufe.",
        "sidebar_lang_header": "🌐 App-Sprache (UI)",
        "title": "AI Social Media Hub",
        "subtitle": "Verwandeln Sie jedes Thema in eine wirkungsvolle Multi-Plattform-Kampagne.",
        "topic_label": "🎯 Kampagnenthema / Hauptidee:",
        "topic_placeholder": "Bsp.: KI-Workflow-Automatisierung in Remote-Teams",
        "lang_label": "🌐 Zielsprache für Inhalte",
        "tone_label": "⚡ Kampagnenton",
        "generate_btn": "✨ Inhaltspaket generieren",
        "spinner": "Kampagnenstrategie wird verarbeitet...",
        "success": "🎉 Kampagne erfolgreich generiert!",
        "results_header": "📱 Kampagnenergebnisse",
        "download_btn": "📥 Kampagne herunterladen (.txt)",
        "err_topic": "⚠️ Bitte geben Sie vor dem Generieren ein gültiges Thema ein.",
        "err_auth": "⚠️ Bitte öffnen Sie die Seitenleiste und geben Sie Ihren Gemini-Schlüssel ein (oder Testmodus aktivieren).",
        "err_503": "⚠️ Google-Server sind vorübergehend ausgelastet (Fehler 503). Aktivieren Sie den Testmodus!"
    },
    "Español": {
        "sidebar_title": "⚙️ Configuración y Autenticación",
        "sidebar_api_label": "Clave API de Gemini",
        "sidebar_test_header": "🧪 Modo de Prueba (Sin conexión)",
        "sidebar_test_checkbox": "Activar modo de prueba (Sin API)",
        "sidebar_test_desc": "Simula una campaña completa sin consumir llamadas API.",
        "sidebar_lang_header": "🌐 Idioma de la interfaz (UI)",
        "title": "AI Social Media Hub",
        "subtitle": "Transforma cualquier tema bruto en una campaña multiplataforma de alto impacto.",
        "topic_label": "🎯 Tema de la campaña / Idea principal:",
        "topic_placeholder": "Ej: Automatización de flujos de trabajo de IA",
        "lang_label": "🌐 Idioma de contenido de salida",
        "tone_label": "⚡ Tono de la campaña",
        "generate_btn": "✨ Generar paquete de contenido",
        "spinner": "Procesando estrategia de campaña...",
        "success": "🎉 ¡Campaña generada con éxito!",
        "results_header": "📱 Resultados de la campaña",
        "download_btn": "📥 Descargar campaña (archivo .txt)",
        "err_topic": "⚠️ Por favor, introduce un tema válido antes de generar.",
        "err_auth": "⚠️ Por favor, abre la barra lateral e introduce tu clave API (o activa el Modo de Prueba).",
        "err_503": "⚠️ Los servidores de Google están ocupados temporalmente (Error 503). ¡Activa el Modo de Prueba!"
    }
}

# 3. Meniul lateral glisabil
st.sidebar.header("⚙ Settings")
api_key_input = st.sidebar.text_input("Gemini API Key", type="password")
api_key = api_key_input if api_key_input else os.environ.get("GEMINI_API_KEY")

st.sidebar.markdown("---")
st.sidebar.header("🧪 Test Mode")
test_mode = st.sidebar.checkbox("Activate Test Mode (No API)", value=False)
st.sidebar.markdown("Simulates tone-adaptive rich output instantly.")

st.sidebar.markdown("---")
ui_language = st.sidebar.selectbox(
    "🌐 App Language (UI)",
    ["English", "Română", "Français", "Deutsch", "Español"],
    index=0
)

t = UI_TEXTS[ui_language]

# 4. Antet minimalist
st.markdown("<div style='text-align: center; margin-top: 1rem;'>", unsafe_allow_html=True)
st.markdown(f"<h1 style='font-size: 2.25rem; font-weight: 700; margin-bottom: 0.5rem; background: linear-gradient(135deg, #818cf8 0%, #22d3ee 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>{t['title']}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #94a3b8; font-size: 1rem; margin-bottom: 2rem;'>{t['subtitle']}</p>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 5. Interfața principală
topic_input = st.text_input(
    t['topic_label'], 
    placeholder=t['topic_placeholder']
)

col1, col2 = st.columns(2)

with col1:
    language_choice = st.selectbox(
        t['lang_label'],
        ["English", "Română", "Français", "Deutsch", "Español"]
    )

with col2:
    tone_choice = st.selectbox(
        t['tone_label'],
        [
            "Professional & Analytical", 
            "Casual & Engaging", 
            "Bold & Provocative", 
            "Educational & Structured"
        ]
    )

st.markdown("<br>", unsafe_allow_html=True)
generate_btn = st.button(t['generate_btn'])

# 6. Logica de generare cu adaptare reală în funcție de ton
if generate_btn:
    if not topic_input.strip():
        st.warning(t['err_topic'])
    elif not test_mode and not api_key:
        st.error(t['err_auth'])
    else:
        with st.spinner(t['spinner']):
            try:
                if test_mode:
                    time.sleep(0.4)
                    tag = topic_input.replace(' ', '')
                    
                    # Generare offline sigură folosind .format() pentru a preveni erorile de f-string
                    if tone_choice == "Professional & Analytical":
                        if language_choice == "Română":
                            response_text = "### 📊 LINKEDIN (Analitic & Corporatist)\n" \
                                f"Analiza pieței relevă un impact direct generat de **{topic_input}**. Conform datelor recente, organizațiile care adoptă această direcție înregistrează o creștere a eficienței operaționale.\n\n" \
                                "Puncte cheie de analiză:\n" \
                                "1. Optimizarea resurselor prin indicatori de performanță (KPI).\n" \
                                "2. Reducerea costurilor structurale pe termen mediu.\n" \
                                "3. Alinierea la standardele corporatiste de guvernanță.\n\n" \
                                f"#CorporateStrategy #BusinessIntelligence #{tag}\n\n" \
                                "### 🧵 X (TWITTER) - THREAD ANALITIC\n" \
                                f"1/3 📊 Tendințele macroeconomice indică o schimbare de paradigmă privind {topic_input}. Să examinăm cifrele cheie. 🧵\n\n" \
                                "2/3 Datele arată o corelație directă între scalabilitatea sistemelor și profitabilitatea operațională.\n\n" \
                                "### 📸 INSTAGRAM\n" \
                                f"📈 Indicatorii cheie pentru {topic_input} demonstrează o maturizare a pieței. Abonați-vă la newsletterul nostru pentru raportul complet trimestrial. #DataDriven #BusinessAnalysis"
                        else:
                            response_text = "### 📊 LINKEDIN (Professional & Analytical)\n" \
                                f"Market analysis indicates a direct strategic impact driven by **{topic_input}**. Organizations implementing this framework show measurable operational gains.\n\n" \
                                "Key metrics to evaluate:\n" \
                                "1. Resource optimization via quantitative KPIs.\n" \
                                "2. Structural cost reduction over mid-term cycles.\n" \
                                "3. Alignment with enterprise governance standards.\n\n" \
                                f"#CorporateStrategy #BusinessIntelligence #{tag}\n\n" \
                                "### 🧵 X (TWITTER) - ANALYTICAL THREAD\n" \
                                f"1/3 📊 Macro trends point to a structural shift in {topic_input}. Let's examine the data points. 🧵\n\n" \
                                "2/3 Quantitative evidence highlights a direct correlation between system scalability and net efficiency.\n\n" \
                                "### 📸 INSTAGRAM\n" \
                                f"📈 Key performance indicators for {topic_input} signal a maturing market. Check our bio for the full quarterly report. #DataDriven #BusinessAnalysis"

                    elif tone_choice == "Casual & Engaging":
                        if language_choice == "Română":
                            response_text = "### 🚀 LINKEDIN (Relaxat & Prietenos)\n" \
                                f"Hei, voi cum vă descurcați cu **{topic_input}**? ☕\n\n" \
                                "Să fim serioși, nimeni nu s-a născut învățat, dar cel mai mult am învățat făcând greșeli. Iată 3 lucruri relaxate care pe mine m-au ajutat enorm:\n" \
                                "1. Fără stres, lucrează pas cu pas.\n" \
                                "2. Întreabă echipa când te blochezi.\n" \
                                "3. Sărbătorește fiecare mică victorie!\n\n" \
                                f"Voi ce păreri aveți? Hai să discutăm în comentarii! 👇\n\n" \
                                f"#WorkCulture #TeamWork #{tag}\n\n" \
                                "### 🧵 X (TWITTER)\n" \
                                f"1/3 ☕ Să vorbim deschis despre {topic_input}. Fără corporateisme plictisitoare, doar ce funcționează pe bune în viața reală. 🧵\n\n" \
                                "2/3 Cel mai bun sfat? Nu complica lucrurile mai mult decât e cazul.\n\n" \
                                "### 📸 INSTAGRAM\n" \
                                f"✨ O cafea, o idee bună și un plan simplu pentru {topic_input}. Salvează postarea dacă ți se pare utilă! 🚀 #GoodVibes #Productivity"
                        else:
                            response_text = "### 🚀 LINKEDIN (Casual & Engaging)\n" \
                                f"Hey everyone, how are you handling **{topic_input}** lately? ☕\n\n" \
                                "Let's be real—nobody has it all figured out on day one. Here are 3 friendly reminders that saved me a ton of headaches:\n" \
                                "1. Take it one step at a time, no rush.\n" \
                                "2. Lean on your team when things get tricky.\n" \
                                "3. Celebrate small wins along the way!\n\n" \
                                f"What's your take on this? Drop a comment below! 👇\n\n" \
                                f"#WorkCulture #TeamWork #{tag}\n\n" \
                                "### 🧵 X (TWITTER)\n" \
                                f"1/3 ☕ Let's talk honestly about {topic_input}. No boring corporate jargon, just what actually works in the real world. 🧵\n\n" \
                                "2/3 Best advice? Keep things simple and don't overcomplicate.\n\n" \
                                "### 📸 INSTAGRAM\n" \
                                f"✨ Coffee, a great idea, and a simple approach to {topic_input}. Save this post if you vibe with it! 🚀 #GoodVibes #Productivity"

                    elif tone_choice == "Bold & Provocative":
                        if language_choice == "Română":
                            response_text = "### 🔥 LINKEDIN (Îndrăzneț & Provocator)\n" \
                                f"Majoritatea companiilor eșuează lamentabil când vine vorba de **{topic_input}**. De ce? Pentru că le este frică de schimbare și se agață de practici învechite! 🛑\n\n" \
                                "Adevărul dur:\n" \
                                "1. Dacă faci ce făceai acum 2 ani, ești deja irelevant.\n" \
                                "2. Scuzele nu generează profit.\n" \
                                "3. Liderii adevărați sparg tiparele, ceilalți doar urmează turma.\n\n" \
                                f"Te deranjează adevărul ăsta? Vino în comentarii și contrazice-mă! 👇\n\n" \
                                f"#Disruptive #Leadership #Innovation #{tag}\n\n" \
                                "### 🧵 X (TWITTER)\n" \
                                f"1/3 🔥 Să dăm cărțile pe față despre {topic_input}. Cei care spun că 'nu se poate' sunt doar cei care nu vor să riște. 🧵\n\n" \
                                "2/3 Conformismul este cel mai rapid mod de faliment în piața actuală.\n\n" \
                                "### 📸 INSTAGRAM\n" \
                                f"⚡ Oprește mediocritatea! Dacă nu te adaptezi la {topic_input}, piața te va scoate din joc. E simplu. 💥 #DisruptTech #GameChanger"
                        else:
                            response_text = "### 🔥 LINKEDIN (Bold & Provocative)\n" \
                                f"Most companies are failing completely at **{topic_input}**. Why? Because they are terrified of disruption and clinging to obsolete habits! 🛑\n\n" \
                                "The harsh truth:\n" \
                                "1. If you're doing what you did 2 years ago, you're already behind.\n" \
                                "2. Excuses don't pay the bills.\n" \
                                "3. True leaders break the mold; everyone else follows the crowd.\n\n" \
                                f"Uncomfortable with this take? Prove me wrong in the comments! 👇\n\n" \
                                f"#Disruptive #Leadership #Innovation #{tag}\n\n" \
                                "### 🧵 X (TWITTER)\n" \
                                f"1/3 🔥 Let's stop sugarcoating {topic_input}. People saying 'it can't be done' are usually just afraid to take a risk. 🧵\n\n" \
                                "2/3 Status quo is the fastest route to irrelevance.\n\n" \
                                "### 📸 INSTAGRAM\n" \
                                f"⚡ Stop settling for average! If you don't master {topic_input}, the market will leave you behind. Period. 💥 #DisruptTech #GameChanger"

                    else: # Educational & Structured
                        if language_choice == "Română":
                            response_text = "### 📚 LINKEDIN (Educațional & Structurat)\n" \
                                f"Vrei să stăpânești **{topic_input}** pas cu pas? Iată un cadru de lucru structurat, gata de aplicat în compania ta:\n\n" \
                                "📌 **Etapa 1: Auditul Inițial**\n" \
                                "- Identifică blocajele actuale.\n" \
                                "- Setează obiective clare pe 30 de zile.\n\n" \
                                "📌 **Etapa 2: Implementarea Tactică**\n" \
                                "- Distribuie sarcinile pe departamente.\n" \
                                "- Monitorizează progresul săptămânal.\n\n" \
                                "📌 **Etapa 3: Scalarea**\n" \
                                "- Automatizează procesele repetitive.\n\n" \
                                "Salvează această postare pentru a o avea la îndemână! 📖\n\n" \
                                f"#Education #Framework #BusinessGrowth #{tag}\n\n" \
                                "### 🧵 X (TWITTER) - GHID RAPID\n" \
                                f"1/4 📚 Ghid pas cu pas pentru {topic_input}: Un cadru simplu pe care îl poți aplica chiar de azi. Să începem! 🧵\n\n" \
                                "2/4 Pasul 1: Analiza stării actuale.\n" \
                                "3/4 Pasul 2: Execuția controlată.\n\n" \
                                "### 📸 INSTAGRAM\n" \
                                f"💡 Masterclass rapid despre {topic_input}: Salvează infograficul de mai jos și urmează pașii recomandați! 📊 #Learning #SkillUp"
                        else:
                            response_text = "### 📚 LINKEDIN (Educational & Structured)\n" \
                                f"Want to master **{topic_input}** step-by-step? Here is a structured execution framework ready for your team:\n\n" \
                                "📌 **Phase 1: Initial Assessment**\n" \
                                "- Identify current workflow bottlenecks.\n" \
                                "- Define clear 30-day milestones.\n\n" \
                                "📌 **Phase 2: Tactical Execution**\n" \
                                "- Assign clear responsibilities across departments.\n" \
                                "- Review weekly metrics.\n\n" \
                                "📌 **Phase 3: Scaling**\n" \
                                "- Automate repetitive sub-tasks.\n\n" \
                                "Save this guide for your next team strategy meeting! 📖\n\n" \
                                f"#Education #Framework #BusinessGrowth #{tag}\n\n" \
                                "### 🧵 X (TWITTER) - QUICK GUIDE\n" \
                                f"1/4 📚 Step-by-step guide to {topic_input}: A clean framework you can implement starting today. Let's dive in! 🧵\n\n" \
                                "2/4 Step 1: Baseline audit.\n" \
                                "3/4 Step 2: Controlled execution.\n\n" \
                                "### 📸 INSTAGRAM\n" \
                                f"💡 Quick Masterclass on {topic_input}: Save this post and follow the structured blueprint! 📊 #Learning #SkillUp"
                
                else:
                    client = genai.Client(api_key=api_key)
                    prompt = (
                        "You are an elite AI Social Media R&D Strategist for high-performing digital teams.\n"
                        f'Create a comprehensive, professional, and engaging multi-platform content package for the following topic: "{topic_input}".\n\n'
                        "CRITICAL INSTRUCTION:\n"
                        f"- You MUST write the entire content package strictly in the following language: {language_choice}. Do not mix languages.\n"
                        f"- Content Tone & Style: {tone_choice} (Make sure the vocabulary, hook, and framing strictly reflect this specific tone).\n\n"
                        "Strictly structure the response into 3 distinct sections using clear headings:\n"
                        "1. LINKEDIN: Tailored to the requested tone and language, structured with an engagement hook, core insights, and relevant professional hashtags.\n"
                        "2. X (TWITTER): Punchy, concise hook, designed to start an educational thread.\n"
                        "3. INSTAGRAM: Visual-oriented, high energy, engaging caption with a tailored hashtag cluster.\n\n"
                        "Ensure the content sounds completely human, creative, and free of generic marketing fluff."
                    )

                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=prompt,
                    )
                    response_text = response.text
                
                st.success(t['success'])
                st.markdown(f"### {t['results_header']}")
                st.markdown(response_text)
                
                st.markdown("---")
                st.download_button(
                    label=t['download_btn'],
                    data=response_text,
                    file_name=f"social_campaign_{language_choice.lower()}_{topic_input.lower().replace(' ', '_')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
            except Exception as e:
                error_str = str(e)
                if "503" in error_str or "UNAVAILABLE" in error_str:
                    st.error(t['err_503'])
                else:
                    st.error(f"❌ Generarea a eșuat. Detalii: {error_str}")

# Footer discret
st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748b; font-size: 12px;'>Dezvoltat pentru R&D Portfolio • Asigurat de Google Gemini API</p>", unsafe_allow_html=True)