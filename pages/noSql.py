import streamlit as st
from neo4j import GraphDatabase
from datetime import datetime

# --- SÉCURITÉ ---
if "logged_in" not in st.session_state or st.session_state.role != "user":
    st.error("🔒 Veuillez vous connecter sur la page d'accueil pour accéder à cet espace.")
    st.stop()

st.set_page_config(page_title="Maroc Travel - Mon Espace", layout="wide")

# --- STYLE CSS AVANCÉ ---
st.markdown("""
    <style>
    /* Fond de la page */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* En-tête personnalisé */
    .user-header {
        background: linear-gradient(90deg, #006233 0%, #009245 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Métriques de profil */
    [data-testid="stMetric"] {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border-bottom: 4px solid #006233;
    }
    
    /* Cartes d'activités */
    .activity-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        border-left: 8px solid #006233;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    .activity-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }
    
    /* Badges de ville */
    .planning-badge {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 6px 15px;
        border-radius: 50px;
        font-weight: bold;
        font-size: 0.85em;
        border: 1px solid #c8e6c9;
    }
    
    /* Informations archives */
    .archive-info {
        background-color: #f1f8e9;
        padding: 10px;
        border-radius: 8px;
        color: #33691e;
        font-size: 0.95em;
        margin-bottom: 10px;
        display: inline-block;
    }
    
    /* Boutons personnalisés */
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

class UserDB:
    def __init__(self):
        self.driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "Password"))
    
    def close(self):
        self.driver.close()

    def get_profile(self, u):
        query = "MATCH (u:User {username: $u}) RETURN u"
        with self.driver.session() as session:
            res = session.run(query, u=u).single()
            return res["u"] if res else None

    def get_all_villes(self):
        query = "MATCH (v:Ville) RETURN v.nom as nom ORDER BY v.nom"
        with self.driver.session() as session:
            result = session.run(query)
            return [record["nom"] for record in result]

    def get_suggestions(self, age, genre):
        query = """
        MATCH (a:Activite)-[:SE_TROUVE_A]->(v:Ville)
        WHERE a.age_min <= $age AND (a.genre = 'Mixte' OR a.genre = $genre)
        RETURN a.nom as nom, a.prix as prix, a.duree as duree, v.nom as ville, a.score as score
        ORDER BY a.score DESC LIMIT 5
        """
        with self.driver.session() as session:
            return session.run(query, age=age, genre=genre).data()

    def find_filtered_activities(self, ville, budget, age, genre):
        query = """
        MATCH (a:Activite)-[:SE_TROUVE_A]->(v:Ville {nom: $ville})
        WHERE a.prix <= $budget AND a.age_min <= $age AND (a.genre = 'Mixte' OR a.genre = $genre)
        RETURN a.nom as nom, a.prix as prix, a.duree as duree, a.score as score
        ORDER BY a.score DESC
        """
        with self.driver.session() as session:
            return session.run(query, ville=ville, budget=budget, age=age, genre=genre).data()

    def save_plan(self, u, name, acts):
        query = """
        MATCH (u:User {username: $u})
        CREATE (p:Planning {nom: $nom, date: $date})
        MERGE (u)-[:A_ENREGISTRE]->(p)
        WITH p UNWIND $acts as aname
        MATCH (a:Activite {nom: aname})
        CREATE (p)-[:CONTIENT]->(a)
        """
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        with self.driver.session() as session:
            session.run(query, u=u, nom=name, date=now, acts=acts)

    def get_history(self, u):
        query = """
        MATCH (u:User {username: $u})-[:A_ENREGISTRE]->(p:Planning)-[:CONTIENT]->(a:Activite)
        RETURN p.nom as nom, p.date as date, 
               collect(a.nom) as acts, 
               sum(a.prix) as prix_total, 
               sum(a.duree) as duree_totale
        ORDER BY p.date DESC
        """
        with self.driver.session() as session:
            return session.run(query, u=u).data()
        
    def delete_planning(self, username, voyage_nom, date):
        query = """
        MATCH (u:User {username: $u})-[:A_ENREGISTRE]->(p:Planning {nom: $v_nom, date: $d})
        DETACH DELETE p
        """
        with self.driver.session() as s:
            s.run(query, u=username, v_nom=voyage_nom, d=date)

# --- LOGIQUE D'AFFICHAGE ---
db = UserDB()
profile = db.get_profile(st.session_state.username)

if profile:
    st.markdown(f"""
        <div class="user-header">
            <h1>🇲🇦 Bonjour, {profile['prenom']} {profile['nom']} !</h1>
            <p>Bienvenue dans votre assistant de voyage personnel. Planifiez votre séjour pour la CAN ou explorez le Royaume.</p>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🎂 Votre Âge", f"{profile['age']} ans")
    c2.metric("👤 Genre", profile['genre'])
    c3.metric("🏠 Résidence", profile['ville_natale'])

    st.write("") 

    t1, t2, t3 = st.tabs(["✨ Suggestions Idéales", "🗓️ Créateur de Planning", "📂 Mes Archives"])

    with t1:
        st.markdown("### 💡 Recommandations Personnalisées")
        suggs = db.get_suggestions(profile['age'], profile['genre'])
        if suggs:
            for s in suggs:
                st.markdown(f"""
                <div class="activity-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:1.3em; font-weight:bold; color:#006233;">🏺 {s['nom']}</span>
                        <span class="planning-badge">📍 {s['ville']}</span>
                    </div>
                    <p style="margin:10px 0; color:#555; font-size:1.1em;">
                        💵 <b>{s['prix']} DH</b> | ⏱️ <b>{s['duree']}h</b> de découverte
                    </p>
                    <div style="color:#f1c40f;">{'⭐' * int(s.get('score', 5)/2)} <span style="color:gray; font-size:0.8em;">({s.get('score', 0)}/10)</span></div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nous n'avons pas encore de suggestions spécifiques pour votre profil.")

    with t2:
        st.markdown("### 🗺️ Construire votre itinéraire")
        with st.container(border=True):
            villes_neo4j = db.get_all_villes()
            col1, col2 = st.columns([2, 2])
            v_choix = col1.selectbox("📍 Choisissez votre destination :", villes_neo4j if villes_neo4j else ["Aucune ville"])
            budget_max = col2.slider("💰 Quel est votre budget max ? (DH)", 50, 5000, 1000)
            btn_gen = st.button("🚀 GÉNÉRER MON PROGRAMME", use_container_width=True)

        if btn_gen:
            results = db.find_filtered_activities(v_choix, budget_max, profile['age'], profile['genre'])
            if results:
                st.session_state.filtered_acts = []
                total_prix = 0
                total_duree = 0
                limite_temps = 8 
                
                st.success(f"✅ Nous avons trouvé un programme optimal pour **{v_choix}** !")
                
                for act in results:
                    if (total_prix + act['prix'] <= budget_max) and (total_duree + act['duree'] <= limite_temps):
                        st.session_state.filtered_acts.append(act['nom'])
                        total_prix += act['prix']
                        total_duree += act['duree']
                        st.markdown(f"""
                            <div style="background:white; padding:10px; border-radius:8px; border-left:4px solid #009245; margin-bottom:5px;">
                                <b>{act['nom']}</b> — {act['prix']} DH | {act['duree']}h
                            </div>
                        """, unsafe_allow_html=True)
                
                st.metric("Total à prévoir", f"{total_prix} DH", delta=f"{budget_max - total_prix} DH restants")
                st.info(f"⏱️ Temps de parcours estimé : **{total_duree}h** sur une limite de {limite_temps}h.")
            else:
                st.warning("⚠️ Aucune activité ne correspond à vos critères dans cette ville.")

        if "filtered_acts" in st.session_state and st.session_state.filtered_acts:
            st.divider()
            p_name = st.text_input("📝 Donnez un nom à ce planning :")
            if st.button("💾 SAUVEGARDER DANS MES ARCHIVES", use_container_width=True):
                if p_name:
                    db.save_plan(st.session_state.username, p_name, st.session_state.filtered_acts)
                    st.success("🎉 Planning enregistré !")
                    st.session_state.filtered_acts = []
                    st.rerun()
                else:
                    st.error("Veuillez entrer un nom.")

    with t3:
        st.markdown("### 📂 Historique de vos Voyages")
        hist = db.get_history(st.session_state.username)
        if hist:
            for h in hist:
                key = f"{h['nom']}_{h['date']}".replace(" ", "").replace("/", "").replace(":", "")
                with st.expander(f"📅 {h['nom']} — {h['date']}"):
                    st.markdown(f"<div class='archive-info'>💰 Budget : {h['prix_total']} DH | ⏱️ Temps : {h['duree_totale']}h</div>", unsafe_allow_html=True)
                    for a in h['acts']:
                        st.write(f"📍 {a}")
                    st.divider()
                    if st.button("🗑️ Supprimer ce planning", key=f"del_{key}"):
                        db.delete_planning(st.session_state.username, h['nom'], h['date'])
                        st.rerun()
        else:
            st.info("Vous n'avez pas encore de planning enregistré.")

with st.sidebar:
    st.title("Mon Compte")
    st.write(f"Connecté en tant que : **{st.session_state.username}**")
    st.divider()
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.clear()
        st.switch_page("auth.py")

db.close()