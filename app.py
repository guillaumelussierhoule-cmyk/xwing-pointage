import streamlit as st
import pandas as pd
import base64
import gspread
from pathlib import Path
from google.oauth2.service_account import Credentials

# -----------------------------------
# App configuration
# -----------------------------------
st.set_page_config(
    page_title="Pointage Escadron",
    page_icon="🚀",
    layout="wide"
)


@st.cache_resource
def connecter_google_sheet():
    """
    Connecte l'app Streamlit à Google Sheets en utilisant les secrets.
    Retourne le fichier Google Sheet ouvert.
    """

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(credentials)

    sheet = client.open(
        st.secrets["google_sheet"]["sheet_name"]
    )

    return sheet


def charger_onglet(sheet, nom_onglet):
    """
    Lit un onglet Google Sheets et le transforme en DataFrame Pandas.
    Si l'onglet est vide, retourne un DataFrame vide.
    """
    worksheet = sheet.worksheet(nom_onglet)
    data = worksheet.get_all_records()

    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data)


def sauvegarder_onglet(sheet, nom_onglet, df):
    """
    Sauvegarde un DataFrame Pandas dans un onglet Google Sheets.
    Efface l'ancien contenu de l'onglet et écrit les nouvelles données.
    """
    worksheet = sheet.worksheet(nom_onglet)

    df = df.fillna("")
    valeurs = [df.columns.tolist()] + df.astype(str).values.tolist()

    worksheet.clear()
    worksheet.update(valeurs)


def charger_donnees_google_sheets(sheet):
    """
    Charge les données depuis Google Sheets vers st.session_state.
    """
    joueurs_df = charger_onglet(sheet, "joueurs")
    vaisseaux_df = charger_onglet(sheet, "vaisseaux")
    touches_df = charger_onglet(sheet, "touches")
    bonus_df = charger_onglet(sheet, "bonus")
    settings_df = charger_onglet(sheet, "settings")

    if not joueurs_df.empty:
        st.session_state.joueurs = joueurs_df

    if not vaisseaux_df.empty:
        st.session_state.vaisseaux = vaisseaux_df

    if not touches_df.empty:
        if "Vaisseau" in touches_df.columns:
            touches_df = touches_df.set_index("Vaisseau")

        for colonne in touches_df.columns:
            touches_df[colonne] = pd.to_numeric(
                touches_df[colonne],
                errors="coerce"
            ).fillna(0).astype(int)

        st.session_state.touches = touches_df

    if not bonus_df.empty:
        st.session_state.bonus_points = dict(
            zip(bonus_df["Joueur"], pd.to_numeric(
                bonus_df["Bonus PV"], errors="coerce").fillna(0).astype(int))
        )

        st.session_state.bonus_credits = dict(
            zip(bonus_df["Joueur"], pd.to_numeric(
                bonus_df["Bonus crédits"], errors="coerce").fillna(0).astype(int))
        )

        st.session_state.bonus_xp = dict(
            zip(bonus_df["Joueur"], pd.to_numeric(
                bonus_df["Bonus XP"], errors="coerce").fillna(0).astype(int))
        )

    if not settings_df.empty:
        try:
            valeur = settings_df.loc[
                settings_df["Paramètre"] == "devoiler_recompenses",
                "Valeur"
            ].iloc[0]

            st.session_state.devoiler_recompenses = str(
                valeur).lower() == "true"

        except Exception:
            pass


def sauvegarder_donnees_google_sheets(sheet):
    """
    Sauvegarde les données actuelles de st.session_state vers Google Sheets.
    """
    sauvegarder_onglet(
        sheet,
        "joueurs",
        st.session_state.joueurs
    )

    sauvegarder_onglet(
        sheet,
        "vaisseaux",
        st.session_state.vaisseaux
    )

    touches_export = st.session_state.touches.copy()
    touches_export.insert(0, "Vaisseau", touches_export.index)

    sauvegarder_onglet(
        sheet,
        "touches",
        touches_export.reset_index(drop=True)
    )

    joueurs = joueurs_actuels()

    bonus_export = pd.DataFrame({
        "Joueur": joueurs,
        "Bonus PV": [
            st.session_state.bonus_points.get(joueur, 0)
            for joueur in joueurs
        ],
        "Bonus crédits": [
            st.session_state.bonus_credits.get(joueur, 0)
            for joueur in joueurs
        ],
        "Bonus XP": [
            st.session_state.bonus_xp.get(joueur, 0)
            for joueur in joueurs
        ],
    })

    sauvegarder_onglet(
        sheet,
        "bonus",
        bonus_export
    )

    settings_export = pd.DataFrame({
        "Paramètre": ["devoiler_recompenses"],
        "Valeur": [str(st.session_state.devoiler_recompenses)]
    })

    sauvegarder_onglet(
        sheet,
        "settings",
        settings_export
    )

# -----------------------------------
# Background image
# -----------------------------------


def ajouter_background(image_path: str):
    """Ajoute un background si le fichier existe."""
    if not Path(image_path).exists():
        return

    image = Path(image_path).read_bytes()
    encoded = base64.b64encode(image).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image:
                linear-gradient(rgba(5, 8, 15, 0.65), rgba(5, 8, 15, 0.75)),
                url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        [data-testid="stHeader"] {{
            background: rgba(0, 0, 0, 0);
        }}

        [data-testid="stSidebar"] {{
            background-color: rgba(10, 15, 25, 0.92);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


ajouter_background("images/background.png")


# -----------------------------------
# Images
# -----------------------------------
def afficher_image_si_existe(image_path: str, location="main", **kwargs):
    """Affiche une image seulement si le fichier existe."""
    if Path(image_path).exists():
        if location == "sidebar":
            st.sidebar.image(image_path, **kwargs)
        else:
            st.image(image_path, **kwargs)


st.title("Pointage Escadron")


# -----------------------------------
# Tables de référence
# -----------------------------------
VAISSEAUX = {
    "T-70 X-wing": {"cout": 9, "coque": 4, "boucliers": 3},
    "TIE/fo Fighter": {"cout": 6, "coque": 3, "boucliers": 1},
    "TIE/in Interceptor": {"cout": 8, "coque": 3, "boucliers": 0},
    "UT-60D U-wing": {"cout": 9, "coque": 5, "boucliers": 3},
    "YT-2400 Light Freighter": {"cout": 14, "coque": 6, "boucliers": 4},
    "Autre": {"cout": 0, "coque": 0, "boucliers": 0},
}

EQUIPES = list(range(1, 12))

COLONNE_ENVIRONNEMENT = "☄️ Environnement"

VAISSEAUX_PAR_DEFAUT = pd.DataFrame({
    "Numéro": list("ABCDEFGHIJK"),
    "Joueurs": [
        "Joueur 1",
        "Joueur 2",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ],
    "Vaisseau": [
        "TIE/fo Fighter",
        "TIE/fo Fighter",
        "TIE/fo Fighter",
        "TIE/fo Fighter",
        "TIE/in Interceptor",
        "TIE/in Interceptor",
        "YT-2400 Light Freighter",
        "T-70 X-wing",
        "T-70 X-wing",
        "UT-60D U-wing",
        "Autre",
    ],
    "Coût": [6, 6, 6, 6, 8, 8, 14, 9, 9, 9, 0],
    "Chargement": [0] * 11,
    "Bonus": [0] * 11,
    "Coque": [3, 3, 3, 3, 3, 3, 6, 4, 4, 5, 0],
    "Boucliers": [1, 1, 1, 1, 0, 0, 4, 3, 3, 3, 0],
})


# -----------------------------------
# Helper functions
# -----------------------------------
def calculer_force(cout: float, chargement: float, bonus: float) -> float:
    """Force = coût + chargement/5 + bonus."""
    return cout + (chargement / 5) + bonus


def calculer_valeur_marginale(force: float, coque: float, boucliers: float) -> float:
    """Valeur d'une touche."""
    points_de_vie = coque + boucliers

    if points_de_vie <= 0:
        return 0

    return force / points_de_vie


def nom_normalise(nom: str) -> str:
    """Nettoie un nom pour comparer plus facilement."""
    return str(nom).strip().lower()


def joueurs_actuels() -> list:
    """Retourne la liste des joueurs actifs."""
    return (
        st.session_state.joueurs["Joueur"]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s != ""]
        .tolist()
    )


def appliquer_stats_vaisseau(df: pd.DataFrame) -> pd.DataFrame:
    """Remplit les stats par défaut selon le type de vaisseau."""
    df = df.copy()

    for col in ["Coût", "Coque", "Boucliers", "Chargement", "Bonus"]:
        if col not in df.columns:
            df[col] = 0

    for idx, row in df.iterrows():
        type_vaisseau = row.get("Vaisseau", "")

        if type_vaisseau not in VAISSEAUX:
            continue

        defaults = VAISSEAUX[type_vaisseau]

        df.at[idx, "Coût"] = defaults["cout"]
        df.at[idx, "Coque"] = defaults["coque"]
        df.at[idx, "Boucliers"] = defaults["boucliers"]

    return df


def remplir_equipes_manquantes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remplit les équipes manquantes.
    Les équipes vont de 1 à 11.
    """
    df = df.copy()

    if "Équipe" not in df.columns:
        df["Équipe"] = None

    equipe_suivante = 1

    for idx, row in df.iterrows():
        joueur = row.get("Joueur", "")

        if pd.isna(joueur) or str(joueur).strip() == "":
            continue

        equipe = row.get("Équipe")

        try:
            equipe = int(equipe)
        except (TypeError, ValueError):
            equipe = 0

        if equipe < 1 or equipe > 11:
            equipe = equipe_suivante

        df.at[idx, "Équipe"] = equipe

        equipe_suivante = equipe + 1

        if equipe_suivante > 11:
            equipe_suivante = 11

    df["Équipe"] = pd.to_numeric(
        df["Équipe"], errors="coerce").fillna(1).astype(int)
    df["Équipe"] = df["Équipe"].clip(lower=1, upper=11)

    return df


# -----------------------------------
# Session state
# -----------------------------------
if "joueurs" not in st.session_state:
    st.session_state.joueurs = pd.DataFrame({
        "Joueur": ["Joueur 1", "Joueur 2"],
        "Équipe": [1, 2],
    })

if "vaisseaux" not in st.session_state:
    st.session_state.vaisseaux = VAISSEAUX_PAR_DEFAUT.copy()

if "touches" not in st.session_state:
    st.session_state.touches = pd.DataFrame(
        0,
        index=list("ABCDEFGHIJK"),
        columns=["Joueur 1", "Joueur 2", COLONNE_ENVIRONNEMENT]
    )

if "bonus_points" not in st.session_state:
    st.session_state.bonus_points = {
        "Joueur 1": 0,
        "Joueur 2": 0,
    }

if "bonus_credits" not in st.session_state:
    st.session_state.bonus_credits = {
        "Joueur 1": 0,
        "Joueur 2": 0,
    }

if "bonus_xp" not in st.session_state:
    st.session_state.bonus_xp = {
        "Joueur 1": 0,
        "Joueur 2": 0,
    }

if "devoiler_recompenses" not in st.session_state:
    st.session_state.devoiler_recompenses = False


# -----------------------------------
# Sidebar navigation
# -----------------------------------
afficher_image_si_existe(
    "images/logo.png",
    location="sidebar",
    use_container_width=True
)

mode = st.sidebar.radio(
    "Mode",
    ["Maître de jeu", "Joueur"]
)

if mode == "Maître de jeu":
    pages_disponibles = [
        "1. Préparation de jeu",
        "2. Pointage",
        "3. Tableau de classement",
    ]
else:
    pages_disponibles = ["3. Tableau de classement"]

page = st.sidebar.radio(
    "Menu",
    pages_disponibles
)

if mode == "Joueur":
    st.sidebar.info(
        "Mode lecture seulement : les joueurs peuvent voir le classement et les valeurs marginales."
    )

    st.sidebar.divider()
    st.sidebar.subheader("Google Sheets")

    try:
        sheet = connecter_google_sheet()

        if st.sidebar.button("Rafraîchir les données"):
            charger_donnees_google_sheets(sheet)
            st.sidebar.success("Données rafraîchies.")
            st.rerun()

    except Exception as e:
        st.sidebar.error("Connexion Google Sheets impossible.")
        st.sidebar.caption(
            "Vérifie les secrets Streamlit, le nom du Google Sheet et le partage avec le service account."
        )
        st.sidebar.write(e)

else:
    st.sidebar.warning("Mode maître de jeu : accès protégé par mot de passe.")

    mot_de_passe = st.sidebar.text_input(
        "Mot de passe maître de jeu",
        type="password"
    )

    if mot_de_passe != "2000":
        st.error(
            "Accès maître de jeu refusé. Entre le bon mot de passe dans la barre de gauche.")
        st.info(
            "Astuce : les joueurs peuvent utiliser le mode Joueur pour voir le classement.")
        st.stop()

    st.sidebar.success("Accès maître de jeu autorisé.")

    st.sidebar.divider()
    st.sidebar.subheader("Google Sheets")

    try:
        sheet = connecter_google_sheet()

        if st.sidebar.button("Charger depuis Google Sheets"):
            charger_donnees_google_sheets(sheet)
            st.sidebar.success("Données chargées.")
            st.rerun()

        if st.sidebar.button("Sauvegarder vers Google Sheets"):
            sauvegarder_donnees_google_sheets(sheet)
            st.sidebar.success("Données sauvegardées.")

    except Exception as e:
        st.sidebar.error("Connexion Google Sheets impossible.")
        st.sidebar.caption(
            "Vérifie les secrets Streamlit, le nom du Google Sheet et le partage avec le service account."
        )
        st.sidebar.write(e)

# -----------------------------------
# Page 1: Préparation de jeu
# -----------------------------------
if page == "1. Préparation de jeu":
    st.header("1. Préparation de jeu")

    st.subheader("Joueurs")
    st.write(
        "Entre les joueurs et choisis leur équipe. Les équipes sont numérotées de 1 à 11.")

    joueurs_base = remplir_equipes_manquantes(st.session_state.joueurs)

    with st.form("form_joueurs"):
        joueurs_temp = st.data_editor(
            joueurs_base,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Équipe": st.column_config.NumberColumn(
                    "Équipe",
                    min_value=1,
                    max_value=11,
                    step=1,
                    required=True,
                )
            },
            key="joueurs_editor"
        )

        enregistrer_joueurs = st.form_submit_button("Enregistrer les joueurs")

    if enregistrer_joueurs:
        st.session_state.joueurs = remplir_equipes_manquantes(joueurs_temp)
        st.success("Joueurs enregistrés.")

    st.divider()

    st.subheader("Vaisseaux")
    st.write(
        "Le tableau est fixe de A à K. Choisis le joueur dans la liste, puis ajuste chaque vaisseau au besoin."
    )

    joueurs_options = [""] + joueurs_actuels()

    vaisseaux_base = st.session_state.vaisseaux.copy()
    vaisseaux_base = vaisseaux_base.reindex(range(11))
    vaisseaux_base["Numéro"] = list("ABCDEFGHIJK")

    if "Propriétaire" in vaisseaux_base.columns and "Joueurs" not in vaisseaux_base.columns:
        vaisseaux_base["Joueurs"] = vaisseaux_base["Propriétaire"]

    if "ID" in vaisseaux_base.columns and "Numéro" not in vaisseaux_base.columns:
        vaisseaux_base["Numéro"] = vaisseaux_base["ID"]

    for col in ["Joueurs", "Vaisseau", "Coût", "Chargement", "Bonus", "Coque", "Boucliers"]:
        if col not in vaisseaux_base.columns:
            vaisseaux_base[col] = VAISSEAUX_PAR_DEFAUT[col]

    vaisseaux_base = vaisseaux_base[
        ["Numéro", "Joueurs", "Vaisseau", "Coût",
            "Chargement", "Bonus", "Coque", "Boucliers"]
    ]

    with st.form("form_vaisseaux"):
        vaisseaux_temp = st.data_editor(
            vaisseaux_base,
            num_rows="fixed",
            use_container_width=True,
            height=460,
            hide_index=True,
            column_config={
                "Numéro": st.column_config.TextColumn(
                    "Numéro",
                    disabled=True,
                ),
                "Joueurs": st.column_config.SelectboxColumn(
                    "Joueurs",
                    options=joueurs_options,
                ),
                "Vaisseau": st.column_config.SelectboxColumn(
                    "Vaisseau",
                    options=list(VAISSEAUX.keys())
                ),
                "Coût": st.column_config.NumberColumn(
                    "Coût",
                    min_value=0,
                    step=1,
                ),
                "Chargement": st.column_config.NumberColumn(
                    "Chargement",
                    min_value=0,
                    step=1,
                ),
                "Bonus": st.column_config.NumberColumn(
                    "Bonus",
                    step=1,
                ),
                "Coque": st.column_config.NumberColumn(
                    "Coque",
                    min_value=0,
                    step=1,
                ),
                "Boucliers": st.column_config.NumberColumn(
                    "Boucliers",
                    min_value=0,
                    step=1,
                ),
            },
            key="vaisseaux_editor"
        )

        col1, col2 = st.columns(2)

        with col1:
            enregistrer_vaisseaux = st.form_submit_button(
                "Enregistrer les vaisseaux")

        with col2:
            remplir_stats = st.form_submit_button(
                "Remplir les stats par défaut")

    if enregistrer_vaisseaux:
        st.session_state.vaisseaux = vaisseaux_temp
        st.success("Vaisseaux enregistrés.")

    if remplir_stats:
        st.session_state.vaisseaux = appliquer_stats_vaisseau(vaisseaux_temp)
        st.success("Stats par défaut ajoutées aux vaisseaux.")


# -----------------------------------
# Page 2: Pointage
# -----------------------------------
elif page == "2. Pointage":
    st.header("2. Pointage")

    joueurs = joueurs_actuels()
    joueurs_avec_environnement = joueurs + [COLONNE_ENVIRONNEMENT]

    joueurs_df = st.session_state.joueurs.copy()
    vaisseaux_df = st.session_state.vaisseaux.copy()

    vaisseaux_assignes = vaisseaux_df[
        vaisseaux_df["Joueurs"].notna()
        & (vaisseaux_df["Joueurs"].astype(str).str.strip() != "")
    ].copy()

    ids_vaisseaux = vaisseaux_assignes["Numéro"].astype(str).tolist()

    touches_actuelles = st.session_state.touches.reindex(
        index=ids_vaisseaux,
        columns=joueurs_avec_environnement,
        fill_value=0
    )

    def equipe_du_joueur(nom_joueur: str):
        """Retourne l'équipe d'un joueur."""
        nom_clean = nom_normalise(nom_joueur)

        match = joueurs_df[
            joueurs_df["Joueur"].astype(str).apply(nom_normalise) == nom_clean
        ]

        if match.empty:
            return None

        return match.iloc[0]["Équipe"]

    st.subheader("Touches infligées")
    st.write(
        "Seuls les vaisseaux assignés sont affichés. Les cases X sont bloquées. "
        "La colonne ☄️ Environnement sert pour les astéroïdes, obstacles ou effets neutres."
    )

    touches_temp = touches_actuelles.copy()

    with st.form("form_pointage"):
        if vaisseaux_assignes.empty:
            st.info(
                "Aucun vaisseau assigné. Va dans Préparation de jeu et assigne au moins un vaisseau.")
        else:
            largeur_colonnes = [1.2] + [1 for _ in joueurs_avec_environnement]
            header_cols = st.columns(largeur_colonnes)

            header_cols[0].markdown("**Vaisseau**")

            for col, joueur in zip(header_cols[1:], joueurs_avec_environnement):
                col.markdown(f"**{joueur}**")

            for _, ship_row in vaisseaux_assignes.iterrows():
                ship_id = str(ship_row["Numéro"])
                proprietaire = ship_row["Joueurs"]
                equipe_proprietaire = equipe_du_joueur(proprietaire)

                row_cols = st.columns(largeur_colonnes)

                row_cols[0].markdown(
                    f"<div style='font-size: 1.35rem; font-weight: 800;'>{ship_id}</div>"
                    f"<div style='font-size: 0.75rem; opacity: 0.65;'>{proprietaire}</div>",
                    unsafe_allow_html=True,
                )

                for col, joueur in zip(row_cols[1:], joueurs_avec_environnement):
                    meme_proprietaire = nom_normalise(
                        joueur) == nom_normalise(proprietaire)
                    meme_equipe = equipe_du_joueur(
                        joueur) == equipe_proprietaire

                    if joueur == COLONNE_ENVIRONNEMENT:
                        meme_proprietaire = False
                        meme_equipe = False

                    if meme_proprietaire or meme_equipe:
                        col.markdown("**X**")
                        touches_temp.loc[ship_id, joueur] = 0
                    else:
                        valeur_actuelle = int(
                            touches_actuelles.loc[ship_id, joueur])

                        touches_temp.loc[ship_id, joueur] = col.number_input(
                            label=f"Touches {joueur} contre {ship_id}",
                            min_value=0,
                            step=1,
                            value=valeur_actuelle,
                            label_visibility="collapsed",
                            key=f"touche_{ship_id}_{joueur}"
                        )

        st.subheader("Bonus supplémentaires")
        st.write(
            "Ajoute ici les points de victoire, crédits et XP gagnés par objectif ou effet de mission.")

        bonus_temp = {}
        credits_temp = {}
        xp_temp = {}

        bonus_cols = st.columns(4)
        bonus_cols[0].markdown("**Joueur**")
        bonus_cols[1].markdown("**Points victoire**")
        bonus_cols[2].markdown("**Crédits**")
        bonus_cols[3].markdown("**XP**")

        for joueur in joueurs:
            bonus_cols = st.columns(4)

            bonus_cols[0].markdown(f"**{joueur}**")

            bonus_temp[joueur] = bonus_cols[1].number_input(
                f"Points victoire supplémentaires pour {joueur}",
                value=int(st.session_state.bonus_points.get(joueur, 0)),
                step=1,
                key=f"bonus_points_{joueur}",
                label_visibility="collapsed",
            )

            credits_temp[joueur] = bonus_cols[2].number_input(
                f"Crédits supplémentaires pour {joueur}",
                value=int(st.session_state.bonus_credits.get(joueur, 0)),
                step=1,
                key=f"bonus_credits_{joueur}",
                label_visibility="collapsed",
            )

            xp_temp[joueur] = bonus_cols[3].number_input(
                f"XP supplémentaire pour {joueur}",
                value=int(st.session_state.bonus_xp.get(joueur, 0)),
                step=1,
                key=f"bonus_xp_{joueur}",
                label_visibility="collapsed",
            )

        enregistrer_pointage = st.form_submit_button("Enregistrer le pointage")

    if enregistrer_pointage:
        st.session_state.touches = touches_temp
        st.session_state.bonus_points = bonus_temp
        st.session_state.bonus_credits = credits_temp
        st.session_state.bonus_xp = xp_temp
        st.success("Pointage enregistré.")


# -----------------------------------
# Page 3: Tableau de classement
# -----------------------------------
elif page == "3. Tableau de classement":
    st.header("3. Tableau de classement")

    joueurs_df = st.session_state.joueurs.copy()
    vaisseaux_df = st.session_state.vaisseaux.copy()
    touches_df = st.session_state.touches.copy()

    resultats = []

    for _, joueur_row in joueurs_df.iterrows():
        joueur = joueur_row["Joueur"]
        equipe = joueur_row["Équipe"]

        if pd.isna(joueur) or str(joueur).strip() == "":
            continue

        joueur_clean = nom_normalise(joueur)
        force_totale = 0
        points_attaque = 0
        dommages_recus = 0

        for _, ship_row in vaisseaux_df.iterrows():
            ship_id = ship_row.get("Numéro", "")
            proprietaire = ship_row.get("Joueurs", "")

            chargement = float(ship_row.get("Chargement", 0) or 0)
            bonus = float(ship_row.get("Bonus", 0) or 0)
            cout = float(ship_row.get("Coût", 0) or 0)
            coque = float(ship_row.get("Coque", 0) or 0)
            boucliers = float(ship_row.get("Boucliers", 0) or 0)

            force = calculer_force(cout, chargement, bonus)
            valeur_marginale = calculer_valeur_marginale(
                force, coque, boucliers)

            if nom_normalise(proprietaire) == joueur_clean:
                force_totale += force

                if ship_id in touches_df.index:
                    touches_contre_ce_vaisseau = touches_df.loc[ship_id].sum()
                    dommages_recus += touches_contre_ce_vaisseau * valeur_marginale

            if ship_id in touches_df.index and joueur in touches_df.columns:
                touches_causees = touches_df.loc[ship_id, joueur]
                points_attaque += touches_causees * valeur_marginale

        bonus_points = st.session_state.bonus_points.get(joueur, 0)
        bonus_credits = st.session_state.bonus_credits.get(joueur, 0)
        bonus_xp = st.session_state.bonus_xp.get(joueur, 0)

        points_victoire_individuels = points_attaque - dommages_recus + bonus_points

        resultats.append({
            "Joueur": joueur,
            "Équipe": equipe,
            "Force totale": round(force_totale, 2),
            "Points d'attaque": round(points_attaque, 2),
            "Dommages reçus": round(dommages_recus, 2),
            "Bonus PV": bonus_points,
            "Bonus crédits": bonus_credits,
            "Bonus XP": bonus_xp,
            "Points de victoire individuels": round(points_victoire_individuels, 2),
        })

    resultats_df = pd.DataFrame(resultats)

    if not resultats_df.empty:
        resultats_df["Points de victoire d'équipe"] = resultats_df.groupby(
            "Équipe"
        )["Points de victoire individuels"].transform("sum")

        resultats_df = resultats_df.sort_values(
            "Points de victoire d'équipe",
            ascending=False
        )

        resultats_df["Rang"] = resultats_df["Points de victoire d'équipe"].rank(
            method="min",
            ascending=False
        ).astype(int)

        credits_par_rang = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4}

        resultats_df["Crédits"] = resultats_df["Rang"].apply(
            lambda r: credits_par_rang.get(r, 3)
        ) + resultats_df["Bonus crédits"]

        resultats_df["XP"] = (
            resultats_df["Points d'attaque"].round(0).astype(int)
            + resultats_df["Bonus XP"]
        )

        affichage_df = resultats_df[[
            "Joueur",
            "Points d'attaque",
            "Dommages reçus",
            "Points de victoire d'équipe",
            "Rang",
            "Crédits",
            "XP",
        ]].copy()

        if not st.session_state.devoiler_recompenses:
            affichage_df["Crédits"] = "?"
            affichage_df["XP"] = "?"

        st.subheader("Classement final")

        styled_classement = (
            affichage_df.style
            .format({
                "Points d'attaque": "{:.2f}",
                "Dommages reçus": "{:.2f}",
                "Points de victoire d'équipe": "{:.2f}",
            })
            .set_properties(
                subset=["Joueur", "Rang"],
                **{"font-weight": "900", "font-size": "1.15rem"}
            )
        )

        st.dataframe(
            styled_classement,
            use_container_width=True,
            hide_index=True,
            height=min(260, 38 + (len(affichage_df) + 1) * 36),
            column_config={
                "Joueur": st.column_config.TextColumn("Joueur", width="small"),
                "Points d'attaque": st.column_config.NumberColumn("Attaques infligées", width="small"),
                "Dommages reçus": st.column_config.NumberColumn("Dommages reçus", width="small"),
                "Points de victoire d'équipe": st.column_config.NumberColumn("Pts équipe", width="small"),
                "Rang": st.column_config.NumberColumn("Rang", width="small"),
                "Crédits": st.column_config.TextColumn("Crédits", width="small"),
                "XP": st.column_config.TextColumn("XP", width="small"),
            },
        )

        if mode == "Maître de jeu":
            if st.button("Dévoiler / cacher les crédits et XP"):
                st.session_state.devoiler_recompenses = not st.session_state.devoiler_recompenses
                st.rerun()

        st.subheader("Valeur marginale des vaisseaux assignés")

        valeurs_marginales = []

        for _, ship_row in vaisseaux_df.iterrows():
            proprietaire = ship_row.get("Joueurs", "")

            if pd.isna(proprietaire) or str(proprietaire).strip() == "":
                continue

            ship_id = ship_row.get("Numéro", "")

            cout = float(ship_row.get("Coût", 0) or 0)
            chargement = float(ship_row.get("Chargement", 0) or 0)
            bonus = float(ship_row.get("Bonus", 0) or 0)
            coque = float(ship_row.get("Coque", 0) or 0)
            boucliers = float(ship_row.get("Boucliers", 0) or 0)

            force = calculer_force(cout, chargement, bonus)
            valeur_marginale = calculer_valeur_marginale(
                force, coque, boucliers)

            points_de_vie_total = coque + boucliers

            if ship_id in touches_df.index:
                touches_recues = touches_df.loc[ship_id].sum()
            else:
                touches_recues = 0

            if points_de_vie_total > 0:
                morts = int(touches_recues // points_de_vie_total)
                vie_actuelle = points_de_vie_total - \
                    (touches_recues % points_de_vie_total)
            else:
                morts = 0
                vie_actuelle = 0

            valeurs_marginales.append({
                "Vaisseau": ship_id,
                "Joueur": proprietaire,
                "Type": ship_row.get("Vaisseau", ""),
                "Morts": morts,
                "Vie actuelle": int(vie_actuelle),
                "Valeur par touche": round(valeur_marginale, 2),
            })

        if valeurs_marginales:
            st.dataframe(
                pd.DataFrame(valeurs_marginales),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Aucun vaisseau assigné à afficher.")

    else:
        st.info("Aucun joueur à afficher.")
