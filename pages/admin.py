import streamlit as st
from neo4j import GraphDatabase
import hashlib
import pandas as pd

# --- SÉCURITÉ ADMIN ---
if "logged_in" not in st.session_state or st.session_state.role != "admin":
    st.error("Accès Admin requis.")
    st.stop()

st.set_page_config(page_title="Admin Panel", layout="wide")

# --- CSS ADMIN ---
st.markdown("""
    <style>
   .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    .main-header { background: #006233; color: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem; }
    .card-ville { background: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- CLASSE ADMIN ---
class AdminDB:
    def __init__(self):
        self.driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "Password"))
    def close(self): 
        self.driver.close()
    def execute(self, q, p=None):
        with self.driver.session() as s: 
            return s.run(q, p or {}).data()

db = AdminDB()

st.markdown('<div class="main-header"><h1>⚙️ Administration du Graphe NoSQL</h1></div>', unsafe_allow_html=True)

menu = st.sidebar.selectbox("🎯 Menu Gestion", ["👥 Utilisateurs", "🏙 Villes & Destinations", "🎡 Activités & Voyages"])

# --- SECTION 1 : UTILISATEURS ---
if menu == "👥 Utilisateurs":
    st.header("Gestion des Membres")
    
    with st.expander("➕ Créer / Modifier un compte"):
        u_name = st.text_input("Nom d'utilisateur")
        u_pass = st.text_input("Mot de passe (si nouveau)", type="password")
        u_role = st.selectbox("Rôle", ["user", "admin"])
        if st.button("Enregistrer", key="save_user"):
            if u_name and u_pass:
                hpw = hashlib.sha256(u_pass.encode()).hexdigest()
                db.execute("MERGE (u:User {username: $u}) SET u.password=$p, u.role=$r", {"u": u_name, "p": hpw, "r": u_role})
                st.experimental_rerun()
            else:
                st.warning("Veuillez remplir le nom d'utilisateur et le mot de passe.")

    users = db.execute("MATCH (u:User) RETURN u.username as User, u.role as Role ORDER BY u.username")
    if users:
        st.table(pd.DataFrame(users))
        u_to_del = st.selectbox("Action : Supprimer un compte", [u['User'] for u in users if u['User'] != 'admin'], key="del_user")
        if st.button("🗑 Supprimer l'utilisateur sélectionné"):
            db.execute("MATCH (u:User {username: $u}) DELETE u", {"u": u_to_del})
            st.experimental_rerun()

# --- SECTION 2 : VILLES ---
elif menu == "🏙 Villes & Destinations":
    st.header("Gestion des Destinations")
    col_in, col_list = st.columns([1, 2])
    
    with col_in:
        st.subheader("Ajouter / Renommer")
        v_actuel = st.text_input("Nom de la ville")
        v_nouveau = st.text_input("Nouveau nom (pour modification)")
        if st.button("✅ Valider l'opération", key="save_ville"):
            if v_actuel:
                if v_nouveau:
                    db.execute("MATCH (v:Ville {nom:$o}) SET v.nom=$n", {"o": v_actuel, "n": v_nouveau})
                else:
                    db.execute("MERGE (v:Ville {nom:$n})", {"n": v_actuel})
                st.experimental_rerun()
            else:
                st.warning("Entrez le nom de la ville.")

    with col_list:
        st.subheader("Liste des Destinations")
        villes = db.execute("MATCH (v:Ville) RETURN v.nom as nom ORDER BY v.nom")
        for v in villes:
            st.markdown(f"<div class='card-ville'>📍 <b>{v['nom']}</b></div>", unsafe_allow_html=True)
            if st.button(f"Supprimer {v['nom']}", key=f"del_{v['nom']}"):
                db.execute("MATCH (v:Ville {nom:$n}) DETACH DELETE v", {"n": v['nom']})
                st.experimental_rerun()

# --- SECTION 3 : ACTIVITÉS ---
elif menu == "🎡 Activités & Voyages":
    st.header("Gestion du Catalogue")
    v_dispo = [v['nom'] for v in db.execute("MATCH (v:Ville) RETURN v.nom as nom ORDER BY v.nom")]
    
    with st.expander("📝 Formulaire d'Activité"):
        nom_a = st.text_input("Nom de l'activité")
        c1, c2, c3 = st.columns(3)
        prix = c1.number_input("Prix (DH)", min_value=0, step=10)
        duree = c2.number_input("Durée (h)", min_value=1, step=1)
        age_min = c3.number_input("Âge Minimum requis", min_value=0, step=1, value=12)
        
        genre_a = st.selectbox("Genre autorisé", ["Mixte", "Homme", "Femme"])
        ville_a = st.selectbox("Ville liée", v_dispo)
        
        if st.button("🚀 Publier / Mettre à jour", key="save_activite"):
            if nom_a and ville_a:
                db.execute("""
                    MATCH (v:Ville {nom:$v}) 
                    MERGE (a:Activite {nom:$n}) 
                    SET a.prix=$p, a.duree=$d, a.age_min=$age, a.genre=$g
                    MERGE (a)-[:SE_TROUVE_A]->(v)
                """, {"n": nom_a, "p": prix, "d": duree, "age": age_min, "g": genre_a, "v": ville_a})
                st.experimental_rerun()
            else:
                st.warning("Remplissez le nom et la ville.")

    st.subheader("📋 Inventaire Complet")
    acts = db.execute("""
        MATCH (a:Activite)-[:SE_TROUVE_A]->(v:Ville) 
        RETURN a.nom as Nom, 
               a.type as Categorie, 
               a.prix as Prix, 
               a.duree as Durée, 
               a.genre as Genre, 
               v.nom as Ville
        ORDER BY a.nom
    """)
    if acts:
        df = pd.DataFrame(acts)
        st.dataframe(df, use_container_width=True)

        a_del = st.selectbox("Supprimer une activité", [a['Nom'] for a in acts], key="del_activite")
        if st.button("🗑 Supprimer l'activité", key="del_button"):
            db.execute("MATCH (a:Activite {nom:$n}) DETACH DELETE a", {"n": a_del})
            st.experimental_rerun()
    else:
        st.info("Aucune activité enregistrée pour le moment.")

# --- Déconnexion ---
if st.sidebar.button("🚪 Déconnexion"):
    st.session_state.clear()
    st.switch_page("auth.py")

db.close()
