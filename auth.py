import streamlit as st
from neo4j import GraphDatabase
import hashlib
import random

# --- CONFIGURATION ---
st.set_page_config(page_title="Maroc Travel", layout="wide")

# CSS PERSONNALISÉ AVANCÉ
st.markdown("""
    <style>
    /* Fond dégradé subtil */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Style du Ticket "Boarding Pass" */
    .ticket-body {
        background: white;
        border: 2px solid #006233;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 10px 10px 0px #006233;
        font-family: 'Courier New', Courier, monospace;
        max-width: 500px;
        margin: 20px auto;
        position: relative;
        overflow: hidden;
    }
    .ticket-body::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 8px;
        background: #006233;
    }
    .ticket-header {
        border-bottom: 2px dashed #006233;
        margin-bottom: 15px;
        padding-bottom: 10px;
        text-align: center;
        font-weight: bold;
        color: #006233;
        font-size: 1.2rem;
    }

    /* Cartes de destinations populaires */
    .card-inspiration {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border-top: 5px solid #006233;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        text-align: center;
    }
    .card-inspiration:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.15);
    }

    /* Style des titres */
    h1, h2, h3 {
        color: #004d26;
        font-weight: 800;
    }

    /* Boutons personnalisés */
    .stButton>button {
        border-radius: 20px;
        border: none;
        background-color: #006233;
        color: white;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #004d26;
        transform: scale(1.02);
    }
    </style>
""", unsafe_allow_html=True)


# --- INITIALISATION SESSION ---
if "essais_restants" not in st.session_state:
    st.session_state.essais_restants = 1
if "show_auth" not in st.session_state:
    st.session_state.show_auth = False

class AuthDB:
    def __init__(self):
      
        self.driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "Password"))
    
    def close(self):
        self.driver.close()
    
    def get_villes(self):
        with self.driver.session() as s:
            return [r["nom"] for r in s.run("MATCH (v:Ville) RETURN v.nom as nom ORDER BY v.nom")]
    
    def get_random_top(self):
        with self.driver.session() as s:
            res = s.run("MATCH (a:Activite)-[:SE_TROUVE_A]->(v:Ville) RETURN a.nom as n, v.nom as v, a.prix as p").data()
            if res:
                return random.sample(res, min(len(res), 3))
            return []
            
    def get_preview(self, ville):
        with self.driver.session() as s:
            return s.run("MATCH (a:Activite)-[:SE_TROUVE_A]->(v:Ville {nom:$v}) RETURN a.nom as n, a.prix as p LIMIT 3", v=ville).data()
    
    def check_user(self, u, p):
        hpw = hashlib.sha256(p.encode()).hexdigest() 
        with self.driver.session() as s:
            result = s.run("MATCH (u:User {username:$u, password:$p}) RETURN u.role as r, u.username as un", u=u, p=hpw).single()
            return result

    def register_user(self, username, password, nom, prenom, age, genre, ville):
        hpw = hashlib.sha256(password.encode()).hexdigest() 
        query = "CREATE (u:User {username: $u, password: $p, role: 'user', nom: $nom, prenom: $prenom, age: $age, genre: $genre, ville_natale: $v})"
        with self.driver.session() as s:
            s.run(query, u=username, p=hpw, nom=nom, prenom=prenom, age=age, genre=genre, v=ville)

db = AuthDB()

# --- BARRE D'EN-TÊTE ---
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("MAROC TRAVEL PLANNER") 
with head_col2:
    st.write(" ")
    label = "⬅️ Retour Accueil" if st.session_state.show_auth else "🔑 Connexion / Inscription"
    if st.button(label, use_container_width=True):
        st.session_state.show_auth = not st.session_state.show_auth
        st.rerun()

# --- LOGIQUE D'AFFICHAGE EXCLUSIVE ---
if st.session_state.show_auth:
    # --- FORMULAIRES ---
    st.divider()
    tab1, tab2 = st.tabs(["🔒 Se Connecter", "📝 S'inscrire"]) 
    
    with tab1:
        with st.form("login_f"):
            u = st.text_input("Identifiant")
            p = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("VALIDER", use_container_width=True):
                user = db.check_user(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["un"]
                    st.session_state.role = user["r"]
                    if user["r"] == "admin":
                        st.switch_page("pages/admin.py") 
                    else:
                        st.switch_page("pages/noSql.py") 
                else:
                    st.error("Identifiants incorrects.")

    with tab2:
        with st.form("reg_f"):
            new_u = st.text_input("Nouvel Identifiant")
            new_p = st.text_input("Nouveau Mot de passe", type="password")
            c1, c2 = st.columns(2)
            nom, prenom = c1.text_input("Nom"), c2.text_input("Prénom")
            age = st.number_input("Âge", 1, 100, 25) 
            genre = st.selectbox("Genre", ["Homme", "Femme"]) 
            v_res = st.text_input("Ville de résidence")
            if st.form_submit_button("CRÉER MON COMPTE", use_container_width=True):
                if new_u and new_p:
                    db.register_user(new_u, new_p, nom, prenom, age, genre, v_res)
                    st.success("Compte créé ! Connectez-vous dans l'onglet 'Se Connecter'.")
                else:
                    st.error("Veuillez remplir les champs obligatoires.")

else:
    # --- VISITEUR / FILTRAGE ---
    st.write("### Découvrez le Royaume intelligemment.") 
    st.subheader("✨ Destinations Populaires")
    suggs = db.get_random_top()
    cols = st.columns(3)
    if suggs:
        for i, item in enumerate(suggs):
            cols[i].markdown(f"""
            <div class="card-inspiration">
                <h3 style="margin-bottom:0;">{item['v']}</h3>
                <p style="color:#666; font-style:italic;">{item['n']}</p>
                <div style="font-size:1.2rem; font-weight:bold; color:#006233;">{item['p']} DH</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Chargement des merveilles marocaines...")

    st.divider()

    st.subheader("🎫 Votre Pass Découverte")
    villes = db.get_villes() 
    if villes:
        col_v, col_b = st.columns([2, 1])
        choix_v = col_v.selectbox("Où souhaitez-vous aller ?", villes, label_visibility="collapsed")
        
        if col_b.button("GÉNÉRER MON PASS", use_container_width=True):
            if st.session_state.essais_restants > 0:
                st.session_state.essais_restants -= 1
                previews = db.get_preview(choix_v)
                if previews:
                    st.markdown(f"""
                    <div class="ticket-body">
                        <div class="ticket-header">MAROC TRAVEL - BOARDING PASS</div>
                        <p style="margin-bottom:5px;"><b>NOM :</b> PASSAGER VISITEUR</p>
                        <p><b>DESTINATION :</b> {choix_v.upper()}</p>
                        <div style="font-size: 0.9em; border-top: 2px dashed #eee; padding-top: 10px; margin-top:10px;">
                            <p style="font-weight:bold; text-decoration:underline;">PROGRAMME SUGGÉRÉ :</p>
                            {" ".join([f"• {p['n']} ({p['p']} DH)<br>" for p in previews])}
                        </div>
                        <div style="border-top:1px solid #006233; font-size:0.7em; text-align:right; margin-top:15px; padding-top:5px; color:#555;">
                            NUMÉRO : {random.randint(100000, 999999)} | CAN 2025/2030 EDITION
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Préparez vos valises ! Plus de détails bientôt pour cette ville.")
            else:
                st.error("🔒 Pass unique utilisé. Veuillez vous inscrire pour débloquer tous les itinéraires.")
    else:
        st.warning("Initialisation de la carte touristique en cours...")

db.close()