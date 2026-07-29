import streamlit as st
import pandas as pd
import datetime
import os
import json

# =========================================================
# ΡΥΘΜΙΣΕΙΣ & CSS 
# =========================================================
st.set_page_config(page_title="My Finance Hub", page_icon="🌿", layout="centered")

# Ενσωμάτωση του CSS για τα κουμπιά και την εμφάνιση
st.markdown(
    """
    <style>
        .stApp { background: #f5f8f6; color: #20382d; }
        
        /* Στυλ για τα Custom Κουμπιά Επιλογών */
        .stButton > button {
            border-radius: 13px !important;
            font-weight: 700 !important;
            min-height: 48px !important;
            transition: all 0.15s ease !important;
        }
        
        /* Δευτερεύοντα κουμπιά (Μη επιλεγμένα) */
        .stButton > button[kind="secondary"] {
            background: #ffffff !important;
            color: #4F86C6 !important;
            border: 2px solid #79A6D8 !important;
            box-shadow: 0 3px 10px rgba(79, 134, 198, 0.10) !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background: #EAF3FC !important;
            border-color: #4F86C6 !important;
        }
        
        /* Πρωτεύοντα κουμπιά (Επιλεγμένα) */
        .stButton > button[kind="primary"], .stFormSubmitButton > button {
            background: #4F86C6 !important;
            color: #ffffff !important;
            border: 2px solid #4F86C6 !important;
            box-shadow: 0 5px 14px rgba(79, 134, 198, 0.24) !important;
        }
        
        div[data-testid="stForm"] {
            background: #ffffff;
            border-radius: 18px;
            padding: 20px;
            border: 1px solid #c9d7d0;
            box-shadow: 0 8px 28px rgba(31, 53, 44, 0.04);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# ΔΕΔΟΜΕΝΑ & ΡΥΘΜΙΣΕΙΣ ΚΑΤΗΓΟΡΙΩΝ
# =========================================================
DATA_FILE = "my_transactions.csv"
CONFIG_FILE = "my_categories.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # -------------------------------------------------------------
        # Προσαρμοσμένες Κατηγορίες σύμφωνα με το αρχείο ΠΛΗΡΩΜΕΣ.xlsx
        # -------------------------------------------------------------
        default_config = {
            "ΣΠΙΤΙ ΒΟΛΟΣ": {
                "Ενοίκιο Βόλος": "", 
                "Αέριο Zenith Γεωργούλα": "", 
                "Ρεύμα Zenith Γεωργούλα": "", 
                "Νερό Βόλος": "", 
                "Vodafone Βόλος": "", 
                "Κοινόχρηστα Βόλος": "RF80917899000000000001112",
                "Αέριο Βόλος": "",
                "Ρεύμα Βόλος": ""
            },
            "ΣΠΙΤΙ ΡΑΓΚΟΥ": {
                "Ενοίκιο Ράγκου": "",
                "Ρεύμα Ράγκου-Heron": "",
                "Ρεύμα Ράγκου Κοινόχρηστο": "",
                "Νερό (ΔΕΥΑΛ) Ράγκου": "",
                "Vodafone Ράγκου": "",
                "Πετρέλαιο": ""
            },
            "ΟΙΚΟΓΕΝΕΙΑ & ΕΚΠΑΙΔΕΥΣΗ": {
                "Μαρία (Έξοδα/Γυμναστήριο)": "",
                "Αλεξία (Έξοδα/Γυμναστήριο)": "",
                "Θοδωρής": "",
                "Δέσποινα": "",
                "Αλγόριθμος": "",
                "Έκθεση Καραμούζας": "",
                "Ωδείο": "RF49 9011 1300 0000 3121 0162 6",
                "Vodafone Δέσποινα": "",
                "Ασφάλεια Μηχανάκι Δέσποινας": ""
            },
            "ΟΧΗΜΑΤΑ": {
                "Βενζίνη": "", 
                "Ασφάλεια Αυτοκινήτου": "", 
                "Ασφάλεια Μηχανής": ""
            },
            "ΕΠΑΓΓΕΛΜΑΤΙΚΑ & ΦΟΡΟΙ": {
                "ΕΦΚΑ": "", 
                "Εκκαθάριση ΕΦΚΑ": "",
                "ΚΕΑΟ": "", 
                "ΦΠΑ": "", 
                "Εισόδημα / Φόροι": "",
                "Hosting DitsiMedia": "",
                "Λογίστρια": ""
            },
            "ΣΥΝΔΡΟΜΕΣ & ΔΙΑΣΚΕΔΑΣΗ": {
                "Netflix": "", 
                "Spotify": "", 
                "Λέσχη": ""
            },
            "ΑΛΛΑ ΕΞΟΔΑ": {
                "Πιστωτική": "",
                "Vodafone Κινητό": "",
                "Wind / Vodafone": "",
                "Διάφορα": ""
            }
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        return default_config

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=['Ημερομηνία', 'Κατηγορία', 'Υποκατηγορία', 'Ποσό', 'RF_Code', 'Κατάσταση', 'Σημειώσεις'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

config = load_config()
df = load_data()

# =========================================================
# ΜΗΧΑΝΙΣΜΟΣ ΚΟΥΜΠΙΩΝ
# =========================================================
def render_choice_buttons(label, options, state_key, columns=2):
    st.markdown(f"#### {label}")
    if state_key not in st.session_state:
        st.session_state[state_key] = options[0] if options else ""

    selected = st.session_state[state_key]
    safe_columns = max(1, min(int(columns), len(options) or 1))

    for row_start in range(0, len(options), safe_columns):
        row_options = options[row_start:row_start + safe_columns]
        row_columns = st.columns(len(row_options))

        for row_position, option in enumerate(row_options):
            with row_columns[row_position]:
                is_selected = (selected == option)
                button_type = "primary" if is_selected else "secondary"
                if st.button(option, key=f"{state_key}_{option}", use_container_width=True, type=button_type):
                    st.session_state[state_key] = option
                    st.rerun()
    return st.session_state[state_key]

# =========================================================
# ΔΙΕΠΑΦΗ ΧΡΗΣΤΗ (UI)
# =========================================================
st.title("🌿 Personal Finance Hub")
tab1, tab2, tab3 = st.tabs(["➕ Νέα Καταχώρηση", "📋 Εκκρεμότητες & Ιστορικό", "⚙️ Νέες Κατηγορίες"])

with tab1:
    main_categories = list(config.keys())
    
    # 1. Επιλογή Κύριας Κατηγορίας με Κουμπιά (Άλλαξα τις στήλες σε 3 για καλύτερη διάταξη)
    selected_cat = render_choice_buttons("Επίλεξε Κατηγορία", main_categories, "main_cat_choice", columns=3)
    
    with st.form("new_entry_form"):
        # 2. Επιλογή Υποκατηγορίας με Dropdown
        sub_categories = list(config[selected_cat].keys())
        selected_subcat = st.selectbox("Αναλυτικά (Υποκατηγορία)", sub_categories)
        
        # 3. RF Code & Ποσό
        saved_rf = config[selected_cat].get(selected_subcat, "")
        
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Ποσό (€)", min_value=0.0, step=1.0, format="%.2f")
            date_val = st.date_input("Ημερομηνία", datetime.date.today())
        with col2:
            rf_code = st.text_input("Κωδικός RF / Πληρωμής", value=saved_rf)
            notes = st.text_input("Σημειώσεις (Προαιρετικό)")
            
        # 4. Τικ Εκκρεμότητας / Εξόφλησης
        st.markdown("#### Κατάσταση Πληρωμής")
        is_paid = st.checkbox("✅ Εξοφλήθηκε (Ξετίκαρε αν είναι σε εκκρεμότητα)", value=True)
        status_text = "Εξοφλήθηκε" if is_paid else "Σε Εκκρεμότητα"

        submit = st.form_submit_button("💾 Αποθήκευση Συναλλαγής", use_container_width=True)

        if submit:
            if amount <= 0:
                st.error("Το ποσό πρέπει να είναι μεγαλύτερο του μηδενός.")
            else:
                # Ενημέρωση RF αν άλλαξε
                if rf_code != saved_rf:
                    config[selected_cat][selected_subcat] = rf_code
                    save_config(config)
                
                new_row = pd.DataFrame([{
                    'Ημερομηνία': date_val,
                    'Κατηγορία': selected_cat,
                    'Υποκατηγορία': selected_subcat,
                    'Ποσό': amount,
                    'RF_Code': rf_code,
                    'Κατάσταση': status_text,
                    'Σημειώσεις': notes
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success("Η εγγραφή αποθηκεύτηκε με επιτυχία!")
                st.rerun()

with tab2:
    st.header("📋 Δεδομένα Συναλλαγών")
    if not df.empty:
        pending_df = df[df['Κατάσταση'] == "Σε Εκκρεμότητα"]
        if not pending_df.empty:
            st.warning(f"Έχεις {len(pending_df)} απλήρωτες εκκρεμότητες!")
        
        # Πίνακας για επεξεργασία
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        if st.button("Αποθήκευση Αλλαγών Πίνακα", type="primary"):
            save_data(edited_df)
            st.success("Το ιστορικό ενημερώθηκε!")
            st.rerun()
    else:
        st.info("Δεν υπάρχουν καταχωρήσεις ακόμα.")

with tab3:
    st.header("⚙️ Προσθήκη Νέας Κατηγορίας")
    st.write("Εδώ μπορείς να προσθέσεις δικές σου κύριες κατηγορίες ή νέες υποκατηγορίες στις υπάρχουσες.")
    
    with st.form("add_cat_form"):
        new_main = st.text_input("Κύρια Κατηγορία (γράψε υπάρχουσα ή νέα):").upper()
        new_sub = st.text_input("Νέα Υποκατηγορία:")
        
        if st.form_submit_button("Προσθήκη", use_container_width=True):
            if new_main and new_sub:
                if new_main not in config:
                    config[new_main] = {}
                config[new_main][new_sub] = ""
                save_config(config)
                st.success(f"Προστέθηκε επιτυχώς: {new_main} -> {new_sub}")
                st.rerun()
            else:
                st.error("Συμπλήρωσε και τα δύο πεδία.")
