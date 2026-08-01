import io
import time as time_module
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta

import altair as alt
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# =========================================================
# ΡΥΘΜΙΣΕΙΣ ΕΦΑΡΜΟΓΗΣ
# =========================================================

st.set_page_config(
    page_title="My Personal Hub",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

TIMEZONE = "Europe/Athens"

SPREADSHEET_ID = st.secrets["app"]["spreadsheet_id"]
DRIVE_FOLDER_ID = st.secrets["app"]["drive_folder_id"]
CALENDAR_ID = st.secrets["app"].get("calendar_id", "primary")

TRANSACTIONS_SHEET = "PH v50 - Κινήσεις"
REMINDERS_SHEET = "PH v50 - Υπενθυμίσεις"
TASKS_SHEET = "PH v50 - Εκκρεμότητες"
DEBTS_SHEET = "PH v50 - Οφειλές"
DEBT_MOVEMENTS_SHEET = "PH v50 - Κινήσεις Οφειλών"
MONTHLY_BUDGET_SHEET = "PH v50 - Μηνιαίος Προϋπολογισμός"
BUDGET_ITEMS_SHEET = "PH v50 - Γραμμές Προϋπολογισμού"
BUDGET_STATUS_SHEET = "PH v50 - Κατάσταση Προϋπολογισμού"
RECURRING_SHEET = "PH v50 - Πάγια και Συνδρομές"
DOCUMENTS_SHEET = "PH v50 - Έγγραφα και Εγγυήσεις"
SAVINGS_SHEET = "PH v50 - Αποταμίευση"
CUSTOM_OPTIONS_SHEET = "PH v50 - Προσαρμοσμένες Επιλογές"
FINANCIAL_CLOSES_SHEET = "PH v50 - Κλεισίματα Περιόδων"
ANALYTICS_TARGETS_SHEET = "PH v50 - Στόχοι Ανάλυσης"

APP_VERSION = "v64"

CUSTOM_OPTION = "➕ Προσθήκη δικής μου επιλογής"



# =========================================================
# ΕΤΟΙΜΕΣ ΕΠΙΛΟΓΕΣ
# =========================================================

EXPENSE_CATEGORIES = {
    "Σπίτι": [
        "Ενοίκιο",
        "Ρεύμα",
        "Νερό",
        "Αέριο",
        "Κοινόχρηστα",
    ],
    "Αυτοκίνητο": [
        "Καύσιμα",
        "Ασφάλεια",
        "Service",
        "Τέλη κυκλοφορίας",
    ],
    "Προσωπικά": [
        "Ρούχα",
        "Προσωπική φροντίδα",
        "Δώρο",
    ],
    "Συνδρομές": [
        "Συνδρομή",
    ],
    "Σούπερ μάρκετ": [
        "Σούπερ μάρκετ",
    ],
    "Υγεία": [
        "Γιατρός",
        "Φαρμακείο",
        "Εξετάσεις",
    ],
    "Έξοδος": [
        "Καφές",
        "Φαγητό",
        "Ποτό",
        "Delivery",
        "Ταξίδι",
        "Εκδρομή",
    ],
    "Δάνεια / Κάρτες": [
        "Δόση δανείου",
        "Πληρωμή κάρτας",
    ],
}

INCOME_CATEGORIES = {
    "Μισθός": [
        "Μισθός",
    ],
    "Επιπλέον έσοδο": [
        "Πρόσθετη αμοιβή",
        "Επιστροφή χρημάτων",
        "Πώληση αντικειμένου",
    ],
    "Μεταφορά χρημάτων": [
        "Κατάθεση",
        "Επιστροφή από άλλο άτομο",
    ],
}


PAYMENT_METHODS = [
    "Κάρτα",
    "Μετρητά",
    "Τραπεζική μεταφορά",
]

REMINDER_CATEGORIES = [
    CUSTOM_OPTION,
    "Λογαριασμός",
    "Αυτοκίνητο",
    "Υγεία",
    "Ραντεβού",
    "Συνδρομή",
    "Έγγραφο",
    "Προσωπικό",
    "Άλλο",
]

REMINDER_TITLES = {
    "Λογαριασμός": [
        "Πληρωμή ρεύματος",
        "Πληρωμή νερού",
        "Πληρωμή κοινοχρήστων",
        "Πληρωμή Internet",
        "Πληρωμή τηλεφώνου",
    ],
    "Αυτοκίνητο": [
        "Λήξη ασφάλειας αυτοκινήτου",
        "ΚΤΕΟ",
        "Service αυτοκινήτου",
        "Τέλη κυκλοφορίας",
    ],
    "Υγεία": [
        "Ιατρική εξέταση",
        "Επανέλεγχος",
        "Ανανέωση συνταγής",
        "Ραντεβού με γιατρό",
    ],
    "Ραντεβού": [
        "Προσωπικό ραντεβού",
        "Επαγγελματικό ραντεβού",
        "Ραντεβού με γιατρό",
    ],
    "Συνδρομή": [
        "Λήξη συνδρομής",
        "Ανανέωση συνδρομής",
    ],
    "Έγγραφο": [
        "Λήξη εγγράφου",
        "Ανανέωση εγγράφου",
    ],
    "Προσωπικό": [
        "Προσωπική υπενθύμιση",
    ],
    "Άλλο": [
        "Άλλη υπενθύμιση",
    ],
}

TASK_CATEGORIES = [
    CUSTOM_OPTION,
    "Εργασία",
    "Σπίτι",
    "Υγεία",
    "Οικονομικά",
    "Προσωπικό",
    "Αγορά",
    "Τηλέφωνο / Email",
    "Αυτοκίνητο",
    "Άλλο",
]

PRIORITIES = [
    CUSTOM_OPTION,
    "Χαμηλή",
    "Κανονική",
    "Υψηλή",
]


DEBT_NAMES = [
    "Δάνειο / Κάρτα",
            ]


# =========================================================
# ΕΜΦΑΝΙΣΗ
# =========================================================

st.markdown(
    """
    <style>
        .stApp {
            background:
                radial-gradient(
                    circle at 10% 5%,
                    rgba(229, 240, 235, 0.85),
                    transparent 25%
                ),
                radial-gradient(
                    circle at 95% 10%,
                    rgba(244, 235, 224, 0.75),
                    transparent 24%
                ),
                #f8faf9;
        }

        [data-testid="stSidebar"] {
            background: rgba(247, 249, 248, 0.97);
            border-right: 1px solid rgba(35, 63, 51, 0.08);
        }

        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(35, 63, 51, 0.08);
            padding: 16px;
            border-radius: 18px;
            box-shadow: 0 8px 28px rgba(31, 53, 44, 0.05);
        }

        div[data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(35, 63, 51, 0.08);
            padding: 22px;
            border-radius: 20px;
            box-shadow: 0 8px 28px rgba(31, 53, 44, 0.04);
        }

        .hero {
            padding: 22px 26px;
            margin-bottom: 18px;
            border-radius: 24px;
            background:
                linear-gradient(
                    120deg,
                    rgba(38, 74, 58, 0.96),
                    rgba(76, 111, 92, 0.92)
                );
            color: white;
            box-shadow: 0 12px 38px rgba(38, 74, 58, 0.16);
        }

        .hero h1 {
            margin: 0;
            font-size: 2rem;
            font-weight: 650;
        }

        .hero p {
            margin: 8px 0 0 0;
            opacity: 0.88;
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 650;
            margin-top: 8px;
            margin-bottom: 8px;
        }

        .soft-card {
            padding: 16px 18px;
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid rgba(35, 63, 51, 0.08);
            border-radius: 18px;
            margin-bottom: 10px;
        }

        .warning-card {
            padding: 14px 16px;
            background: rgba(255, 247, 230, 0.92);
            border: 1px solid rgba(190, 135, 48, 0.18);
            border-radius: 16px;
            margin-bottom: 8px;
        }

        .success-card {
            padding: 14px 16px;
            background: rgba(234, 246, 239, 0.94);
            border: 1px solid rgba(61, 133, 94, 0.16);
            border-radius: 16px;
            margin-bottom: 8px;
        }

        .small-label {
            color: #68756f;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .big-number {
            color: #263e33;
            font-size: 1.35rem;
            font-weight: 650;
        }

        .stButton > button,
        .stFormSubmitButton > button {
            border-radius: 12px;
            min-height: 42px;
        }

        div[data-baseweb="select"] > div {
            border-radius: 12px;
        }

        /* Σταθερά ευανάγνωστα χρώματα, ανεξάρτητα από dark mode browser */
        .stApp,
        .stApp p,
        .stApp span,
        .stApp label,
        .stApp div {
            color: #263e33;
        }

        .hero,
        .hero h1,
        .hero p,
        .hero div,
        .hero span {
            color: #ffffff !important;
        }

        [data-testid="stMetric"] {
            background: #ffffff !important;
        }

        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] p,
        [data-testid="stMetricLabel"] div {
            color: #5f6f67 !important;
            opacity: 1 !important;
        }

        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] div {
            color: #20382d !important;
            opacity: 1 !important;
            font-weight: 700 !important;
        }

        [data-testid="stMetricDelta"],
        [data-testid="stMetricDelta"] div {
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] * {
            color: #263e33;
        }

        div[data-testid="stForm"],
        .soft-card,
        .warning-card,
        .success-card {
            color: #263e33 !important;
        }

        input,
        textarea,
        [data-baseweb="select"] input,
        [data-baseweb="select"] div {
            color: #263e33 !important;
        }

        @media (prefers-color-scheme: dark) {
            .stApp {
                color-scheme: light;
                background:
                    radial-gradient(
                        circle at 10% 5%,
                        rgba(229, 240, 235, 0.95),
                        transparent 25%
                    ),
                    radial-gradient(
                        circle at 95% 10%,
                        rgba(244, 235, 224, 0.90),
                        transparent 24%
                    ),
                    #f8faf9 !important;
            }

            [data-testid="stMetric"],
            div[data-testid="stForm"],
            .soft-card {
                background: #ffffff !important;
            }
        }

        /* Επιλογές τύπου radio σαν κανονικά κουμπιά */
        div[role="radiogroup"] {
            gap: 0.55rem !important;
        }

        div[role="radiogroup"] label {
            background: #ffffff !important;
            border: 2px solid #c7d4cd !important;
            border-radius: 14px !important;
            padding: 0.68rem 0.9rem !important;
            margin: 0.18rem 0 !important;
            min-height: 46px !important;
            cursor: pointer !important;
            box-shadow: 0 3px 10px rgba(31, 53, 44, 0.06);
        }

        div[role="radiogroup"] label:has(input:checked) {
            background: #315c49 !important;
            border-color: #315c49 !important;
            box-shadow: 0 5px 14px rgba(49, 92, 73, 0.20);
        }

        div[role="radiogroup"] label:has(input:checked) p,
        div[role="radiogroup"] label:has(input:checked) span,
        div[role="radiogroup"] label:has(input:checked) div {
            color: #ffffff !important;
        }

        div[role="radiogroup"] label p,
        div[role="radiogroup"] label span,
        div[role="radiogroup"] label div {
            color: #263e33 !important;
            font-weight: 600 !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label {
            width: 100% !important;
            padding: 0.75rem 0.9rem !important;
        }

        /* Φωτεινά πεδία αντί για σκούρα μαύρα κουτιά στο κινητό */
        div[data-baseweb="select"] > div,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            background: #ffffff !important;
            border: 1.5px solid #b9c9c1 !important;
            color: #20382d !important;
            -webkit-text-fill-color: #20382d !important;
            opacity: 1 !important;
        }

        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div {
            color: #20382d !important;
            opacity: 1 !important;
        }

        [data-testid="stNumberInput"] button {
            background: #edf3f0 !important;
            color: #20382d !important;
            border-color: #b9c9c1 !important;
        }

        .stButton > button,
        .stFormSubmitButton > button,
        [data-testid="stDownloadButton"] > button {
            background: #315c49 !important;
            color: #ffffff !important;
            border: 1px solid #315c49 !important;
            font-weight: 700 !important;
            min-height: 50px !important;
            box-shadow: 0 5px 14px rgba(49, 92, 73, 0.18);
        }

        .stButton > button *,
        .stFormSubmitButton > button *,
        [data-testid="stDownloadButton"] > button * {
            color: #ffffff !important;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            background: #264b3b !important;
            border-color: #264b3b !important;
        }

        /* Ισχυρή διόρθωση εμφάνισης selectbox στο κινητό */
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="select"] > div > div {
            background-color: #ffffff !important;
            color: #20382d !important;
            -webkit-text-fill-color: #20382d !important;
            border-color: #8fa79b !important;
            opacity: 1 !important;
        }

        [data-testid="stSelectbox"] input,
        [data-testid="stSelectbox"] span,
        [data-testid="stSelectbox"] p,
        [data-testid="stSelectbox"] div,
        div[data-baseweb="select"] input,
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] p {
            color: #20382d !important;
            -webkit-text-fill-color: #20382d !important;
            opacity: 1 !important;
        }

        [data-testid="stSelectbox"] svg,
        div[data-baseweb="select"] svg {
            fill: #20382d !important;
            color: #20382d !important;
        }

        /* Επιλογές μέσα στην ανοιχτή λίστα */
        ul[role="listbox"],
        ul[role="listbox"] li,
        div[role="listbox"],
        div[role="option"] {
            background: #ffffff !important;
            color: #20382d !important;
            -webkit-text-fill-color: #20382d !important;
            opacity: 1 !important;
        }

        div[role="option"]:hover,
        div[role="option"][aria-selected="true"],
        li[role="option"]:hover,
        li[role="option"][aria-selected="true"] {
            background: #dfeae4 !important;
            color: #20382d !important;
        }

        /* Το placeholder και η επιλεγμένη τιμή να είναι πάντα ορατά */
        [data-testid="stSelectbox"] [aria-selected="true"],
        [data-testid="stSelectbox"] [data-baseweb="select"] * {
            color: #20382d !important;
            -webkit-text-fill-color: #20382d !important;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-top: 1rem !important;
                padding-left: 0.85rem !important;
                padding-right: 0.85rem !important;
                padding-bottom: 4rem !important;
            }

            .hero {
                padding: 18px 18px;
                border-radius: 18px;
                margin-bottom: 14px;
            }

            .hero h1 {
                font-size: 1.55rem;
            }

            .hero p {
                font-size: 0.9rem;
            }

            [data-testid="stMetric"] {
                padding: 15px !important;
                border-radius: 16px !important;
                min-height: 128px;
                box-shadow: 0 5px 18px rgba(31, 53, 44, 0.08);
            }

            [data-testid="stMetricLabel"] p {
                font-size: 0.9rem !important;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.65rem !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.65rem;
            }

            [data-testid="stVerticalBlock"] {
                gap: 0.65rem !important;
            }

            h1, h2, h3 {
                line-height: 1.2 !important;
            }

            .stButton > button,
            .stFormSubmitButton > button {
                width: 100% !important;
                border-radius: 14px !important;
                font-size: 1rem !important;
            }

            div[data-testid="stForm"] {
                padding: 16px !important;
                border-radius: 18px !important;
            }

            .soft-card,
            .warning-card,
            .success-card {
                border-radius: 15px;
            }
        }

        /* =====================================================
           ΥΠΟΧΡΕΩΤΙΚΟ LIGHT MODE
           ===================================================== */

        :root,
        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"] {
            color-scheme: light !important;
        }

        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: #f5f8f6 !important;
            color: #20382d !important;
        }

        [data-testid="stHeader"] {
            background: rgba(245, 248, 246, 0.96) !important;
        }

        [data-testid="stToolbar"] {
            color: #20382d !important;
        }

        [data-testid="stSidebar"] {
            background: #f7faf8 !important;
            color: #20382d !important;
            border-right: 1px solid #d3dfd8 !important;
        }

        [data-testid="stSidebar"] *,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] div {
            color: #20382d !important;
            -webkit-text-fill-color: #20382d !important;
            opacity: 1 !important;
        }

        h1, h2, h3, h4, h5, h6,
        p, span, label, small,
        .stMarkdown,
        .stCaption,
        [data-testid="stCaptionContainer"] {
            color: #20382d !important;
            opacity: 1 !important;
        }

        .hero,
        .hero *,
        .hero h1,
        .hero p {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        [data-testid="stMetric"],
        div[data-testid="stForm"],
        .soft-card,
        .warning-card,
        .success-card,
        [data-testid="stExpander"],
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            background: #ffffff !important;
            color: #20382d !important;
            border-color: #c9d7d0 !important;
        }

        [data-testid="stMetricLabel"] *,
        [data-testid="stMetricValue"] *,
        [data-testid="stMetricDelta"] * {
            opacity: 1 !important;
        }

        [data-testid="stMetricLabel"] *,
        [data-testid="stMetricLabel"] {
            color: #5a6c63 !important;
            -webkit-text-fill-color: #5a6c63 !important;
        }

        [data-testid="stMetricValue"] *,
        [data-testid="stMetricValue"] {
            color: #183428 !important;
            -webkit-text-fill-color: #183428 !important;
        }

        /* Selectbox κλειστό */
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="select"] > div > div {
            background: #ffffff !important;
            color: #183428 !important;
            -webkit-text-fill-color: #183428 !important;
            border: 1.5px solid #8fa79b !important;
            box-shadow: none !important;
            opacity: 1 !important;
        }

        [data-testid="stSelectbox"] *,
        div[data-baseweb="select"] * {
            color: #183428 !important;
            -webkit-text-fill-color: #183428 !important;
            opacity: 1 !important;
        }

        [data-testid="stSelectbox"] svg,
        div[data-baseweb="select"] svg {
            color: #183428 !important;
            fill: #183428 !important;
        }

        /* Dropdown ανοιχτό */
        [data-baseweb="popover"],
        [data-baseweb="menu"],
        ul[role="listbox"],
        div[role="listbox"],
        li[role="option"],
        div[role="option"] {
            background: #ffffff !important;
            color: #183428 !important;
            -webkit-text-fill-color: #183428 !important;
            opacity: 1 !important;
        }

        li[role="option"] *,
        div[role="option"] * {
            color: #183428 !important;
            -webkit-text-fill-color: #183428 !important;
        }

        li[role="option"]:hover,
        li[role="option"][aria-selected="true"],
        div[role="option"]:hover,
        div[role="option"][aria-selected="true"] {
            background: #dce9e2 !important;
            color: #183428 !important;
        }

        /* Όλα τα πεδία εισαγωγής */
        input,
        textarea,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input {
            background: #ffffff !important;
            color: #183428 !important;
            -webkit-text-fill-color: #183428 !important;
            caret-color: #183428 !important;
            border-color: #8fa79b !important;
            opacity: 1 !important;
        }

        input::placeholder,
        textarea::placeholder {
            color: #73837b !important;
            -webkit-text-fill-color: #73837b !important;
            opacity: 1 !important;
        }

        input:disabled,
        textarea:disabled {
            background: #eef3f0 !important;
            color: #52635b !important;
            -webkit-text-fill-color: #52635b !important;
            opacity: 1 !important;
        }

        [data-testid="stNumberInput"] button {
            background: #edf3f0 !important;
            color: #183428 !important;
            border-color: #8fa79b !important;
        }

        [data-testid="stNumberInput"] button * {
            color: #183428 !important;
            fill: #183428 !important;
        }

        /* Checkbox */
        [data-testid="stCheckbox"] label,
        [data-testid="stCheckbox"] label * {
            color: #20382d !important;
            -webkit-text-fill-color: #20382d !important;
            opacity: 1 !important;
        }

        /* Radio σαν κουμπιά */
        div[role="radiogroup"] label {
            background: #ffffff !important;
            color: #20382d !important;
            border: 2px solid #9db2a7 !important;
        }

        div[role="radiogroup"] label *,
        div[role="radiogroup"] label p,
        div[role="radiogroup"] label span {
            color: #20382d !important;
            -webkit-text-fill-color: #20382d !important;
        }

        div[role="radiogroup"] label:has(input:checked) {
            background: #A66F00 !important;
            border-color: #A66F00 !important;
        }

        div[role="radiogroup"] label:has(input:checked) *,
        div[role="radiogroup"] label:has(input:checked) p,
        div[role="radiogroup"] label:has(input:checked) span {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        /* Κουμπιά */
        .stButton > button,
        .stFormSubmitButton > button,
        [data-testid="stDownloadButton"] > button {
            background: #A66F00 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: 1px solid #A66F00 !important;
            opacity: 1 !important;
        }

        .stButton > button *,
        .stFormSubmitButton > button *,
        [data-testid="stDownloadButton"] > button * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover,
        [data-testid="stDownloadButton"] > button:hover {
            background: #7F5600 !important;
            border-color: #7F5600 !important;
        }

        /* Expander */
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary * {
            color: #20382d !important;
            -webkit-text-fill-color: #20382d !important;
        }

        /* Tabs */
        [data-baseweb="tab-list"] {
            background: #edf3f0 !important;
            border-radius: 12px !important;
        }

        [data-baseweb="tab"] {
            color: #20382d !important;
            -webkit-text-fill-color: #20382d !important;
        }

        [data-baseweb="tab"][aria-selected="true"] {
            background: #ffffff !important;
            color: #183428 !important;
        }

        /* Πίνακες */
        [data-testid="stDataFrame"] *,
        [data-testid="stTable"] * {
            color: #20382d !important;
        }

        /* Mobile */
        @media (max-width: 768px) {
            [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
            [data-testid="stNumberInput"] input,
            [data-testid="stDateInput"] input,
            [data-testid="stTextInput"] input,
            [data-testid="stTextArea"] textarea {
                min-height: 52px !important;
                font-size: 1rem !important;
                border-radius: 12px !important;
            }

            [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                padding-left: 0.2rem !important;
            }

            .stButton > button,
            .stFormSubmitButton > button {
                min-height: 54px !important;
                font-size: 1rem !important;
            }
        }


        /* =====================================================
           ΚΟΥΜΠΙΑ ΕΠΙΛΟΓΩΝ
           Λευκά με πράσινο περίγραμμα, πράσινα όταν επιλεγούν
           ===================================================== */

        .stButton > button[kind="secondary"],
        button[data-testid="baseButton-secondary"] {
            background: #ffffff !important;
            color: #A66F00 !important;
            -webkit-text-fill-color: #A66F00 !important;
            border: 2px solid #D3A62A !important;
            box-shadow: 0 3px 10px rgba(166, 111, 0, 0.10) !important;
            font-weight: 700 !important;
        }

        .stButton > button[kind="secondary"] *,
        button[data-testid="baseButton-secondary"] * {
            color: #A66F00 !important;
            -webkit-text-fill-color: #A66F00 !important;
        }

        .stButton > button[kind="secondary"]:hover,
        button[data-testid="baseButton-secondary"]:hover {
            background: #FFF7D6 !important;
            color: #7F5600 !important;
            border-color: #A66F00 !important;
        }

        .stButton > button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            background: #A66F00 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: 2px solid #A66F00 !important;
            box-shadow: 0 5px 14px rgba(166, 111, 0, 0.22) !important;
            font-weight: 700 !important;
        }

        .stButton > button[kind="primary"] *,
        button[data-testid="baseButton-primary"] * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        .stButton > button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {
            background: #7F5600 !important;
            border-color: #7F5600 !important;
        }

        @media (max-width: 768px) {
            .stButton > button[kind="secondary"],
            .stButton > button[kind="primary"],
            button[data-testid="baseButton-secondary"],
            button[data-testid="baseButton-primary"] {
                min-height: 52px !important;
                border-radius: 14px !important;
                font-size: 0.98rem !important;
                padding: 0.65rem 0.75rem !important;
            }
        }


        [data-baseweb="tab-list"] {
            gap: 0.5rem !important;
            background: transparent !important;
            flex-wrap: wrap !important;
        }

        [data-baseweb="tab"] {
            background: #ffffff !important;
            border: 2px solid #D3A62A !important;
            border-radius: 13px !important;
            padding: 0.65rem 0.9rem !important;
            color: #A66F00 !important;
            font-weight: 700 !important;
        }

        [data-baseweb="tab"][aria-selected="true"] {
            background: #A66F00 !important;
            border-color: #A66F00 !important;
            color: #ffffff !important;
        }

        [data-baseweb="tab"][aria-selected="true"] * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }


        /* =====================================================
           ΖΕΣΤΗ ΠΑΛΕΤΑ ΜΟΥΣΤΑΡΔΙ / ΩΧΡΑ
           ===================================================== */

        :root {
            --mustard-main: #C89211;
            --mustard-deep: #9B6800;
            --mustard-border: #D6AA36;
            --mustard-soft: #FFF5CC;
            --mustard-text: #6F4B00;
        }

        .stButton > button[kind="secondary"],
        button[data-testid="baseButton-secondary"] {
            background: #ffffff !important;
            color: var(--mustard-text) !important;
            -webkit-text-fill-color: var(--mustard-text) !important;
            border: 2px solid var(--mustard-border) !important;
            box-shadow: 0 3px 10px rgba(200, 146, 17, 0.10) !important;
        }

        .stButton > button[kind="secondary"] *,
        button[data-testid="baseButton-secondary"] * {
            color: var(--mustard-text) !important;
            -webkit-text-fill-color: var(--mustard-text) !important;
        }

        .stButton > button[kind="secondary"]:hover,
        button[data-testid="baseButton-secondary"]:hover {
            background: var(--mustard-soft) !important;
            color: var(--mustard-deep) !important;
            border-color: var(--mustard-main) !important;
        }

        .stButton > button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            background: var(--mustard-main) !important;
            color: #2F2408 !important;
            -webkit-text-fill-color: #2F2408 !important;
            border: 2px solid var(--mustard-main) !important;
            box-shadow: 0 5px 14px rgba(200, 146, 17, 0.24) !important;
        }

        .stButton > button[kind="primary"] *,
        button[data-testid="baseButton-primary"] * {
            color: #2F2408 !important;
            -webkit-text-fill-color: #2F2408 !important;
        }

        .stButton > button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {
            background: #B9820C !important;
            border-color: #B9820C !important;
        }

        [data-baseweb="tab"] {
            background: #ffffff !important;
            border: 2px solid var(--mustard-border) !important;
            color: var(--mustard-text) !important;
        }

        [data-baseweb="tab"][aria-selected="true"] {
            background: var(--mustard-main) !important;
            border-color: var(--mustard-main) !important;
            color: #2F2408 !important;
        }

        [data-baseweb="tab"][aria-selected="true"] * {
            color: #2F2408 !important;
            -webkit-text-fill-color: #2F2408 !important;
        }

        div[data-testid="stMetric"] {
            border-color: rgba(200, 146, 17, 0.28) !important;
        }

        div[data-testid="stAlert"] {
            border-left-color: var(--mustard-main) !important;
        }

        input:focus,
        textarea:focus,
        [data-baseweb="select"] > div:focus-within {
            border-color: var(--mustard-main) !important;
            box-shadow: 0 0 0 1px var(--mustard-main) !important;
        }

    </style>
    """,
    unsafe_allow_html=True,
)



THEMES = {
    "Μπλε": {
        "main": "#0F6B6D",
        "deep": "#0A4F51",
        "border": "#86BFC0",
        "soft": "#D7EEEE",
        "soft_2": "#EDF8F8",
        "text": "#173F40",
        "button_text": "#FFFFFF",
        "shadow": "15, 107, 109",
    },
    "Φούξια": {
        "main": "#0F6B6D",
        "deep": "#0A4F51",
        "border": "#86BFC0",
        "soft": "#D7EEEE",
        "soft_2": "#EDF8F8",
        "text": "#173F40",
        "button_text": "#FFFFFF",
        "shadow": "15, 107, 109",
    },
    "Πράσινο": {
        "main": "#0F6B6D",
        "deep": "#0A4F51",
        "border": "#86BFC0",
        "soft": "#D7EEEE",
        "soft_2": "#EDF8F8",
        "text": "#173F40",
        "button_text": "#FFFFFF",
        "shadow": "15, 107, 109",
    },
    "Ροζ": {
        "main": "#0F6B6D",
        "deep": "#0A4F51",
        "border": "#86BFC0",
        "soft": "#D7EEEE",
        "soft_2": "#EDF8F8",
        "text": "#173F40",
        "button_text": "#FFFFFF",
        "shadow": "15, 107, 109",
    },
    "Πετρόλ": {
        "main": "#0F6B6D",
        "deep": "#0A4F51",
        "border": "#86BFC0",
        "soft": "#D7EEEE",
        "soft_2": "#EDF8F8",
        "text": "#173F40",
        "button_text": "#FFFFFF",
        "shadow": "15, 107, 109",
    },
}


def apply_selected_theme():
    selected_theme = st.session_state.get("selected_app_theme", "Πετρόλ")
    if selected_theme not in THEMES:
        selected_theme = "Πετρόλ"
        st.session_state["selected_app_theme"] = selected_theme

    palette = THEMES.get(selected_theme, THEMES["Πετρόλ"]).copy()
    palette_defaults = {
        "main": "#0F6B6D",
        "deep": "#0A4F51",
        "border": "#86BFC0",
        "soft": "#D7EEEE",
        "soft_2": "#EDF8F8",
        "text": "#173F40",
        "button_text": "#FFFFFF",
        "shadow": "15, 107, 109",
    }
    for palette_key, default_value in palette_defaults.items():
        palette.setdefault(palette_key, default_value)

    st.markdown(
        f"""
        <style>
            :root {{
                --app-main: {palette["main"]};
                --app-deep: {palette["deep"]};
                --app-border: {palette["border"]};
                --app-soft: {palette["soft"]};
                --app-soft-2: {palette["soft_2"]};
                --app-text: {palette["text"]};
                --app-button-text: {palette["button_text"]};
                --app-shadow-rgb: {palette["shadow"]};
            }}

            .stButton > button[kind="secondary"],
            button[data-testid="baseButton-secondary"] {{
                background: #ffffff !important;
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
                border: 2px solid var(--app-border) !important;
                box-shadow:
                    0 3px 10px rgba(var(--app-shadow-rgb), 0.10)
                    !important;
            }}

            .stButton > button[kind="secondary"] *,
            button[data-testid="baseButton-secondary"] * {{
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }}

            .stButton > button[kind="secondary"]:hover,
            button[data-testid="baseButton-secondary"]:hover {{
                background: var(--app-soft) !important;
                color: var(--app-deep) !important;
                border-color: var(--app-main) !important;
            }}

            .stButton > button[kind="primary"],
            button[data-testid="baseButton-primary"] {{
                background: var(--app-main) !important;
                color: var(--app-button-text) !important;
                -webkit-text-fill-color:
                    var(--app-button-text) !important;
                border: 2px solid var(--app-main) !important;
                box-shadow:
                    0 5px 14px rgba(var(--app-shadow-rgb), 0.24)
                    !important;
            }}

            .stButton > button[kind="primary"] *,
            button[data-testid="baseButton-primary"] * {{
                color: var(--app-button-text) !important;
                -webkit-text-fill-color:
                    var(--app-button-text) !important;
            }}

            .stButton > button[kind="primary"]:hover,
            button[data-testid="baseButton-primary"]:hover {{
                background: var(--app-deep) !important;
                border-color: var(--app-deep) !important;
            }}

            [data-baseweb="tab"] {{
                background: #ffffff !important;
                border: 2px solid var(--app-border) !important;
                color: var(--app-text) !important;
            }}

            [data-baseweb="tab"][aria-selected="true"] {{
                background: var(--app-main) !important;
                border-color: var(--app-main) !important;
                color: var(--app-button-text) !important;
            }}

            [data-baseweb="tab"][aria-selected="true"] * {{
                color: var(--app-button-text) !important;
                -webkit-text-fill-color:
                    var(--app-button-text) !important;
            }}

            div[data-testid="stMetric"] {{
                border-color:
                    rgba(var(--app-shadow-rgb), 0.30) !important;
                background:
                    linear-gradient(
                        145deg,
                        #ffffff 0%,
                        var(--app-soft-2) 100%
                    ) !important;
            }}

            div[data-testid="stAlert"] {{
                border-left-color: var(--app-main) !important;
            }}

            input:focus,
            textarea:focus,
            [data-baseweb="select"] > div:focus-within {{
                border-color: var(--app-main) !important;
                box-shadow:
                    0 0 0 1px var(--app-main) !important;
            }}

            [data-testid="stSidebar"] {{
                background:
                    linear-gradient(
                        180deg,
                        var(--app-soft-2) 0%,
                        var(--app-soft) 100%
                    ) !important;
                color: var(--app-text) !important;
                border-right:
                    1px solid rgba(var(--app-shadow-rgb), 0.28)
                    !important;
            }}

            [data-testid="stSidebar"] > div {{
                background: transparent !important;
            }}

            [data-testid="stSidebar"] *,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] span,
            [data-testid="stSidebar"] label {{
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }}

            [data-testid="stSidebar"] div[role="radiogroup"] label {{
                background: rgba(255, 255, 255, 0.62) !important;
                border: 1px solid rgba(var(--app-shadow-rgb), 0.18)
                    !important;
                border-radius: 13px !important;
                margin-bottom: 5px !important;
                padding: 7px 9px !important;
            }}

            [data-testid="stSidebar"]
            div[role="radiogroup"]
            label:has(input:checked) {{
                background: var(--app-main) !important;
                border-color: var(--app-main) !important;
                box-shadow:
                    0 4px 12px rgba(var(--app-shadow-rgb), 0.22)
                    !important;
            }}

            [data-testid="stSidebar"]
            div[role="radiogroup"]
            label:has(input:checked) * {{
                color: var(--app-button-text) !important;
                -webkit-text-fill-color:
                    var(--app-button-text) !important;
            }}

            [data-testid="stSidebar"] hr,
            hr {{
                border-color:
                    rgba(var(--app-shadow-rgb), 0.18) !important;
            }}

            .theme-preview {{
                background:
                    linear-gradient(
                        135deg,
                        var(--app-soft-2),
                        var(--app-soft)
                    );
                border: 2px solid var(--app-border);
                border-radius: 18px;
                padding: 18px;
                margin: 10px 0 18px;
            }}

            .theme-preview-title {{
                color: var(--app-deep);
                font-weight: 800;
                font-size: 1.08rem;
                margin-bottom: 6px;
            }}

            .theme-preview-dots {{
                display: flex;
                gap: 8px;
                margin-top: 12px;
            }}

            .theme-preview-dot {{
                width: 28px;
                height: 28px;
                border-radius: 999px;
                border: 2px solid rgba(255, 255, 255, 0.9);
                box-shadow: 0 2px 7px rgba(0, 0, 0, 0.12);
            }}

            /* Επάνω πλαίσιο My Personal Hub */
            .hero {{
                background:
                    linear-gradient(
                        125deg,
                        var(--app-deep) 0%,
                        var(--app-main) 62%,
                        var(--app-border) 100%
                    ) !important;
                box-shadow:
                    0 12px 34px
                    rgba(var(--app-shadow-rgb), 0.28) !important;
                border:
                    1px solid
                    rgba(var(--app-shadow-rgb), 0.22) !important;
            }}

            .hero,
            .hero h1,
            .hero p,
            .hero div,
            .hero span {{
                color: var(--app-button-text) !important;
                -webkit-text-fill-color:
                    var(--app-button-text) !important;
            }}

            /* Όλα τα κανονικά και form buttons */
            .stButton > button,
            .stFormSubmitButton > button,
            .stDownloadButton > button,
            [data-testid="stBaseButton-primary"],
            [data-testid="stBaseButton-secondary"],
            button[data-testid="baseButton-primary"],
            button[data-testid="baseButton-secondary"] {{
                border-radius: 13px !important;
                font-weight: 700 !important;
                transition:
                    background 0.15s ease,
                    border-color 0.15s ease,
                    transform 0.15s ease !important;
            }}

            .stFormSubmitButton > button,
            .stDownloadButton > button,
            [data-testid="stBaseButton-primary"],
            button[data-testid="baseButton-primary"] {{
                background: var(--app-main) !important;
                border: 2px solid var(--app-main) !important;
                color: var(--app-button-text) !important;
                -webkit-text-fill-color:
                    var(--app-button-text) !important;
                box-shadow:
                    0 5px 14px
                    rgba(var(--app-shadow-rgb), 0.22) !important;
            }}

            .stFormSubmitButton > button *,
            .stDownloadButton > button *,
            [data-testid="stBaseButton-primary"] *,
            button[data-testid="baseButton-primary"] * {{
                color: var(--app-button-text) !important;
                -webkit-text-fill-color:
                    var(--app-button-text) !important;
            }}

            .stFormSubmitButton > button:hover,
            .stDownloadButton > button:hover,
            [data-testid="stBaseButton-primary"]:hover,
            button[data-testid="baseButton-primary"]:hover {{
                background: var(--app-deep) !important;
                border-color: var(--app-deep) !important;
            }}

            /* Μπάρες προόδου στην αρχική, στον προϋπολογισμό και στα δάνεια */
            [data-testid="stProgress"] div[role="progressbar"] > div,
            [data-testid="stProgress"] div[role="progressbar"] span,
            div[role="progressbar"] > div {{
                background-color: var(--app-main) !important;
            }}

            [data-testid="stProgress"] div[role="progressbar"] {{
                background-color: var(--app-soft) !important;
                border:
                    1px solid
                    rgba(var(--app-shadow-rgb), 0.20) !important;
            }}

            [data-testid="stProgress"] p,
            [data-testid="stProgress"] span {{
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }}

            /* Κάρτες, πλαίσια και expander */
            .soft-card,
            .success-card,
            .warning-card {{
                background:
                    linear-gradient(
                        145deg,
                        #ffffff 0%,
                        var(--app-soft-2) 100%
                    ) !important;
                border:
                    1.5px solid
                    rgba(var(--app-shadow-rgb), 0.24) !important;
                color: var(--app-text) !important;
                box-shadow:
                    0 5px 16px
                    rgba(var(--app-shadow-rgb), 0.07) !important;
            }}

            [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stExpander"],
            details[data-testid="stExpander"] {{
                border-color:
                    rgba(var(--app-shadow-rgb), 0.28) !important;
                background:
                    linear-gradient(
                        145deg,
                        #ffffff 0%,
                        var(--app-soft-2) 100%
                    ) !important;
            }}

            [data-testid="stExpander"] summary,
            details[data-testid="stExpander"] summary {{
                color: var(--app-text) !important;
            }}

            /* Metrics της αρχικής σελίδας */
            [data-testid="stMetric"] {{
                background:
                    linear-gradient(
                        145deg,
                        #ffffff 0%,
                        var(--app-soft-2) 100%
                    ) !important;
                border:
                    1.5px solid
                    rgba(var(--app-shadow-rgb), 0.26) !important;
                box-shadow:
                    0 5px 16px
                    rgba(var(--app-shadow-rgb), 0.07) !important;
            }}

            [data-testid="stMetricLabel"],
            [data-testid="stMetricLabel"] *,
            [data-testid="stMetricValue"],
            [data-testid="stMetricValue"] *,
            [data-testid="stMetricDelta"],
            [data-testid="stMetricDelta"] * {{
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }}

            /* Radio, checkbox και toggles */
            [data-testid="stCheckbox"] svg,
            [data-testid="stRadio"] svg {{
                color: var(--app-main) !important;
                fill: var(--app-main) !important;
            }}

            /* Ενεργά links και μικρές διακοσμητικές λεπτομέρειες */
            a {{
                color: var(--app-deep) !important;
            }}

            blockquote {{
                border-left-color: var(--app-main) !important;
                background: var(--app-soft-2) !important;
            }}

            /* Θεματικά ενημερωτικά πλαίσια */
            .theme-message {{
                background:
                    linear-gradient(
                        135deg,
                        var(--app-soft-2) 0%,
                        var(--app-soft) 100%
                    ) !important;
                border:
                    1.5px solid
                    rgba(var(--app-shadow-rgb), 0.30) !important;
                border-left:
                    6px solid var(--app-main) !important;
                border-radius: 13px !important;
                color: var(--app-text) !important;
                padding: 14px 16px !important;
                margin: 8px 0 16px !important;
                box-shadow:
                    0 4px 14px
                    rgba(var(--app-shadow-rgb), 0.08) !important;
            }}

            .theme-message,
            .theme-message * {{
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }}

            .theme-status-card {{
                background:
                    linear-gradient(
                        135deg,
                        var(--app-soft-2) 0%,
                        var(--app-soft) 100%
                    ) !important;
                border:
                    1.5px solid
                    rgba(var(--app-shadow-rgb), 0.30) !important;
                border-radius: 14px !important;
                padding: 14px 16px !important;
                min-height: 62px !important;
                color: var(--app-text) !important;
                box-shadow:
                    0 4px 14px
                    rgba(var(--app-shadow-rgb), 0.08) !important;
            }}

            .theme-status-card,
            .theme-status-card * {{
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }}

            .theme-info-box {{
                background:
                    linear-gradient(
                        135deg,
                        var(--app-soft-2) 0%,
                        var(--app-soft) 100%
                    ) !important;
                border:
                    1.5px solid
                    rgba(var(--app-shadow-rgb), 0.28) !important;
                border-left:
                    6px solid var(--app-main) !important;
                border-radius: 13px !important;
                padding: 14px 16px !important;
                color: var(--app-text) !important;
                margin-top: 14px !important;
            }}

            .theme-info-box,
            .theme-info-box * {{
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }}

            input[type="number"]::-webkit-inner-spin-button,
            input[type="number"]::-webkit-outer-spin-button {{
                -webkit-appearance: none !important;
                margin: 0 !important;
            }}

            input[type="number"] {{
                -moz-appearance: textfield !important;
            }}

            [data-testid="stPopover"] button,
            [data-baseweb="select"] > div,
            [data-baseweb="input"] > div,
            [data-baseweb="textarea"] > div {{
                border-color: var(--app-border) !important;
            }}

            [data-testid="stPopover"] button:hover,
            [data-baseweb="select"] > div:hover,
            [data-baseweb="input"] > div:focus-within,
            [data-baseweb="textarea"] > div:focus-within {{
                border-color: var(--app-primary) !important;
                box-shadow: 0 0 0 1px var(--app-primary-soft) !important;
            }}

            @media (max-width: 768px) {{
                [data-testid="stHorizontalBlock"] {{
                    gap: 0.45rem !important;
                }}

                [data-testid="column"] {{
                    min-width: 0 !important;
                }}

                input[type="number"]::-webkit-inner-spin-button,
                input[type="number"]::-webkit-outer-spin-button {{
                    -webkit-appearance: none !important;
                    margin: 0 !important;
                }}

                input[type="number"] {{
                    -moz-appearance: textfield !important;
                }}

                .stButton > button,
                .stDownloadButton > button,
                .stFormSubmitButton > button {{
                    min-height: 50px !important;
                    white-space: normal !important;
                    line-height: 1.15 !important;
                    padding: 0.58rem 0.55rem !important;
                }}

                [data-testid="stMetric"] {{
                    min-height: 118px !important;
                }}

                .hero {{
                    padding: 20px 18px !important;
                    border-radius: 0 0 24px 24px !important;
                }}

                .hero h1 {{
                    font-size: 1.7rem !important;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_selected_theme()


# =========================================================
# GOOGLE SERVICES
# =========================================================

@st.cache_resource
def init_services():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/calendar",
    ]

    credentials_info = dict(st.secrets["gcp_service_account"])

    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=scopes,
    )

    sheet_client = gspread.authorize(credentials)

    drive_service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    calendar_service = build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    spreadsheet_id = str(SPREADSHEET_ID).strip()

    if "docs.google.com" in spreadsheet_id:
        raise ValueError(
            "Στο spreadsheet_id έχει τοποθετηθεί ολόκληρος σύνδεσμος. "
            "Χρειάζεται μόνο το ID ανάμεσα στο /d/ και στο /edit."
        )

    if not spreadsheet_id:
        raise ValueError(
            "Δεν έχει συμπληρωθεί το spreadsheet_id στα Streamlit Secrets."
        )

    try:
        spreadsheet = sheet_client.open_by_key(spreadsheet_id)
    except gspread.exceptions.SpreadsheetNotFound as exc:
        raise RuntimeError(
            "Το Google Sheet δεν βρέθηκε ή δεν έχει κοινοποιηθεί "
            "στο email του service account."
        ) from exc
    except gspread.exceptions.APIError as exc:
        raise RuntimeError(
            "Η Google δεν μπόρεσε να ανοίξει το spreadsheet. "
            "Έλεγξε ότι το spreadsheet_id είναι το ID ενός Google Sheet."
        ) from exc

    return spreadsheet, drive_service, calendar_service


try:
    spreadsheet, drive_service, calendar_service = init_services()
except Exception as exc:
    st.error("Δεν ήταν δυνατή η σύνδεση με το Google Sheet.")
    st.warning(
        "Έλεγξε ότι το spreadsheet_id είναι σωστό και ότι το αρχείο "
        "έχει κοινοποιηθεί στο service account ως Επεξεργαστής."
    )
    st.code(str(exc), language=None)
    st.stop()


# =========================================================
# GOOGLE SHEETS
# =========================================================

SHEET_SCHEMAS = {
    TRANSACTIONS_SHEET: [
        "id",
        "ημερομηνία",
        "έτος_αναφοράς",
        "μήνας_αναφοράς",
        "τύπος",
        "κατηγορία",
        "περιγραφή",
        "ποσό",
        "τρόπος_πληρωμής",
        "πάγιο",
        "πηγή_χρημάτων",
        "σχετική_αποταμίευση",
        "αρχείο",
        "σημειώσεις",
        "καταχωρήθηκε",
        "δραστηριότητα",
    ],
    REMINDERS_SHEET: [
        "id",
        "τίτλος",
        "κατηγορία",
        "ημερομηνία",
        "ώρα",
        "ποσό",
        "επανάληψη",
        "κατάσταση",
        "calendar_link",
        "αρχείο",
        "σημειώσεις",
        "καταχωρήθηκε",
    ],
    TASKS_SHEET: [
        "id",
        "τύπος",
        "τίτλος",
        "κατηγορία",
        "προθεσμία",
        "αρχική_προθεσμία",
        "ποσό",
        "πληρωμένο_ποσό",
        "υπόλοιπο",
        "κατάσταση_πληρωμής",
        "rf",
        "επανάληψη",
        "προτεραιότητα",
        "κατάσταση",
        "σημειώσεις",
        "καταχωρήθηκε",
        "ενημερώθηκε",
    ],
    DEBTS_SHEET: [
        "id",
        "όνομα",
        "είδος",
        "πιστωτής",
        "αρχικό_ποσό",
        "προεπιλεγμένη_δόση",
        "ετήσιο_επιτόκιο",
        "συνολικές_δόσεις",
        "ημερομηνία_πρώτης_δόσης",
        "τύπος_επιτοκίου",
        "ενεργό",
        "σημειώσεις",
        "ενημερώθηκε",
    ],
    DEBT_MOVEMENTS_SHEET: [
        "id",
        "debt_id",
        "όνομα",
        "ημερομηνία",
        "τύπος",
        "ποσό",
        "σχετική_κίνηση",
        "πηγή_χρημάτων",
        "σημειώσεις",
        "καταχωρήθηκε",
    ],
    MONTHLY_BUDGET_SHEET: [
        "id",
        "έτος",
        "μήνας",
        "μισθός",
        "άλλο_σταθερό_έσοδο",
        "έκτακτο_έσοδο",
        "ενοίκιο",
        "κοινόχρηστα",
        "ρεύμα",
        "αέριο",
        "νερό",
        "κινητό_τηλέφωνο",
        "σταθερό_τηλέφωνο",
        "δάνειο_πειραιώς",
        "δάνειο_γεωργία",
        "δάνειο_θεία",
        "εφορία",
        "εφκα",
        "πιστωτική",
        "δάνεια_κάρτες",
        "συνδρομές",
        "φαρμακείο",
        "γιατρός",
        "έξοδα_αυτοκινήτου",
        "ασφάλεια_αυτοκινήτου",
        "τέλη_κυκλοφορίας",
        "άλλο_περιγραφή",
        "άλλο_ποσό",
        "μαξιλάρι_ασφαλείας",
        "σημειώσεις",
        "ενημερώθηκε",
    ],
    BUDGET_ITEMS_SHEET: [
        "id",
        "έτος",
        "μήνας",
        "περιγραφή",
        "κατηγορία",
        "τύπος",
        "ποσό",
        "πάγιο",
        "συχνότητα",
        "ολοκληρώθηκε",
        "πηγή_χρημάτων",
        "σχετική_κίνηση",
        "πηγή",
        "σημειώσεις",
        "ενημερώθηκε",
    ],
    BUDGET_STATUS_SHEET: [
        "id",
        "έτος",
        "μήνας",
        "κωδικός_πεδίου",
        "περιγραφή",
        "τύπος",
        "πάγιο",
        "συχνότητα",
        "ολοκληρώθηκε",
        "πηγή_χρημάτων",
        "σχετική_κίνηση",
        "σχετικό_πάγιο",
        "ενημερώθηκε",
    ],    RECURRING_SHEET: [
        "id",
        "όνομα",
        "κατηγορία",
        "τύπος",
        "ποσό",
        "συχνότητα",
        "τελευταία_πληρωμή",
        "επόμενη_χρέωση",
        "rf",
        "τρόπος_πληρωμής",
        "ενεργό",
        "υπενθύμιση_ημέρες",
        "σημειώσεις",
        "ενημερώθηκε",
    ],
    DOCUMENTS_SHEET: [
        "id",
        "τίτλος",
        "τύπος",
        "κατηγορία",
        "ημερομηνία_αγοράς",
        "ημερομηνία_λήξης",
        "ποσό",
        "φορέας",
        "αρχείο",
        "κατάσταση",
        "σημειώσεις",
        "ενημερώθηκε",
    ],
    SAVINGS_SHEET: [
        "id",
        "ημερομηνία",
        "έτος",
        "μήνας",
        "τύπος",
        "ποσό",
        "σχετική_κίνηση",
        "σημειώσεις",
        "καταχωρήθηκε",
    ],
    CUSTOM_OPTIONS_SHEET: [
        "id",
        "πλαίσιο",
        "τιμή",
        "καταχωρήθηκε",
    ],
    FINANCIAL_CLOSES_SHEET: [
        "id",
        "τύπος_περιόδου",
        "έτος",
        "μήνας",
        "κατηγορία",
        "περιγραφή",
        "έσοδα",
        "έξοδα",
        "υπόλοιπο",
        "αποταμίευση",
        "σημειώσεις",
        "κλείστηκε",
    ],
    ANALYTICS_TARGETS_SHEET: [
        "id",
        "έτος",
        "κατηγορία",
        "περιγραφή",
        "τύπος",
        "ποσό_στόχου",
        "σημειώσεις",
        "ενημερώθηκε",
    ],

}


def get_all_values_with_retry(worksheet, attempts=5):
    """
    Διαβάζει ένα φύλλο με επαναλήψεις, ώστε ένα προσωρινό
    σφάλμα ή όριο κλήσεων της Google να μην κλείνει την εφαρμογή.
    """
    last_error = None

    for attempt in range(attempts):
        try:
            return worksheet.get_all_values()
        except gspread.exceptions.APIError as exc:
            last_error = exc

            if attempt < attempts - 1:
                time_module.sleep(min(2 ** attempt, 12))

    raise last_error


def get_spreadsheet_worksheets_with_retry(attempts=5):
    """
    Φορτώνει μία φορά όλα τα φύλλα του spreadsheet.
    Έτσι αποφεύγουμε ξεχωριστό metadata request για κάθε worksheet.
    """
    last_error = None

    for attempt in range(attempts):
        try:
            return spreadsheet.worksheets()
        except gspread.exceptions.APIError as exc:
            last_error = exc

            if attempt < attempts - 1:
                time_module.sleep(min(2 ** attempt, 12))

    raise last_error


@st.cache_resource
def initialize_worksheets(schema_version):
    """
    Δημιουργεί ή διορθώνει όλα τα απαιτούμενα φύλλα με μία αρχική
    ανάγνωση metadata και επιστρέφει λεξικό worksheet objects.
    """
    existing_worksheets = get_spreadsheet_worksheets_with_retry()
    worksheet_map = {
        worksheet.title: worksheet
        for worksheet in existing_worksheets
    }

    for title, headers in SHEET_SCHEMAS.items():
        worksheet = worksheet_map.get(title)

        if worksheet is None:
            worksheet = spreadsheet.add_worksheet(
                title=title,
                rows=1000,
                cols=max(len(headers), 15),
            )
            worksheet.update(
                values=[headers],
                range_name="A1",
            )
            worksheet_map[title] = worksheet
            continue

        existing_values = get_all_values_with_retry(
            worksheet,
            attempts=4,
        )

        if not existing_values:
            worksheet.update(
                values=[headers],
                range_name="A1",
            )
            continue

        existing_headers = [
            str(value).strip()
            for value in existing_values[0]
        ]

        if existing_headers != headers:
            migrated_rows = []

            for old_row in existing_values[1:]:
                old_record = {
                    header: old_row[index] if index < len(old_row) else ""
                    for index, header in enumerate(existing_headers)
                    if header
                }

                migrated_rows.append([
                    old_record.get(header, "")
                    for header in headers
                ])

            worksheet.clear()
            worksheet.update(
                values=[headers] + migrated_rows,
                range_name="A1",
            )

    return worksheet_map


try:
    WORKSHEETS = initialize_worksheets(APP_VERSION)
except gspread.exceptions.APIError as exc:
    st.error(
        "Η Google Sheets API δεν απάντησε κατά την αρχική φόρτωση."
    )
    st.info(
        "Περίμενε περίπου ένα λεπτό και κάνε Reboot την εφαρμογή. "
        "Ο κώδικας πλέον κάνει μία μόνο ανάγνωση των φύλλων αντί για "
        "ξεχωριστή κλήση για κάθε φύλλο."
    )
    st.code(str(exc), language=None)
    st.stop()


def ensure_worksheet_available(sheet_name):
    """
    Επιστρέφει το worksheet από το αρχικό map.
    Αν λείπει λόγω παλιού Streamlit cache, το δημιουργεί άμεσα.
    """
    worksheet = WORKSHEETS.get(sheet_name)

    if worksheet is not None:
        return worksheet

    headers = SHEET_SCHEMAS[sheet_name]

    try:
        current_worksheets = get_spreadsheet_worksheets_with_retry()
        current_map = {
            item.title: item
            for item in current_worksheets
        }
        worksheet = current_map.get(sheet_name)

        if worksheet is None:
            worksheet = spreadsheet.add_worksheet(
                title=sheet_name,
                rows=1000,
                cols=max(len(headers), 15),
            )
            worksheet.update(
                values=[headers],
                range_name="A1",
            )

        WORKSHEETS[sheet_name] = worksheet
        return worksheet

    except gspread.exceptions.APIError as exc:
        st.error(
            f"Δεν ήταν δυνατή η δημιουργία ή φόρτωση του φύλλου "
            f"«{sheet_name}»."
        )
        st.code(str(exc), language=None)
        st.stop()


transactions_ws = ensure_worksheet_available(TRANSACTIONS_SHEET)
reminders_ws = ensure_worksheet_available(REMINDERS_SHEET)
tasks_ws = ensure_worksheet_available(TASKS_SHEET)
debts_ws = ensure_worksheet_available(DEBTS_SHEET)
debt_movements_ws = ensure_worksheet_available(DEBT_MOVEMENTS_SHEET)
monthly_budget_ws = ensure_worksheet_available(MONTHLY_BUDGET_SHEET)
budget_items_ws = ensure_worksheet_available(BUDGET_ITEMS_SHEET)
budget_status_ws = ensure_worksheet_available(BUDGET_STATUS_SHEET)
recurring_ws = ensure_worksheet_available(RECURRING_SHEET)
documents_ws = ensure_worksheet_available(DOCUMENTS_SHEET)
savings_ws = ensure_worksheet_available(SAVINGS_SHEET)
custom_options_ws = ensure_worksheet_available(CUSTOM_OPTIONS_SHEET)
financial_closes_ws = ensure_worksheet_available(FINANCIAL_CLOSES_SHEET)
analytics_targets_ws = ensure_worksheet_available(ANALYTICS_TARGETS_SHEET)


# =========================================================
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ
# =========================================================

def create_id(prefix):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{timestamp}"


def format_currency(value):
    try:
        amount = float(value)
        formatted = f"{amount:,.2f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} €"
    except (TypeError, ValueError):
        return "0,00 €"


def parse_number(value):
    try:
        if isinstance(value, str):
            value = value.replace(".", "").replace(",", ".")
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def upload_to_drive(uploaded_file):
    if uploaded_file is None:
        return ""

    file_metadata = {
        "name": uploaded_file.name,
        "parents": [DRIVE_FOLDER_ID],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(uploaded_file.getvalue()),
        mimetype=uploaded_file.type or "application/octet-stream",
        resumable=False,
    )

    result = (
        drive_service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
        )
        .execute()
    )

    return result.get("webViewLink", "")


def create_calendar_event(summary, event_date, event_time, description=""):
    start_datetime = datetime.combine(event_date, event_time)
    end_datetime = start_datetime + timedelta(hours=1)

    event_body = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": TIMEZONE,
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": TIMEZONE,
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 60},
                {"method": "popup", "minutes": 1440},
            ],
        },
    }

    result = (
        calendar_service.events()
        .insert(
            calendarId=CALENDAR_ID,
            body=event_body,
        )
        .execute()
    )

    return result.get("htmlLink", "")



def create_monthly_calendar_event(summary, day_of_month=9, hour=9):
    today = date.today()
    first_date = date(today.year, today.month, min(day_of_month, 28))
    if first_date < today:
        first_date = first_date + relativedelta(months=1)
    start_datetime = datetime.combine(first_date, time(hour, 0))
    end_datetime = start_datetime + timedelta(hours=1)
    event_body = {
        "summary": summary,
        "description": (
            "Έλεγχος πληρωμών, εκκρεμών υπολοίπων και του "
            "αυτόματου μηνιαίου προϋπολογισμού στο My Personal Hub."
        ),
        "start": {"dateTime": start_datetime.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end_datetime.isoformat(), "timeZone": TIMEZONE},
        "recurrence": [f"RRULE:FREQ=MONTHLY;BYMONTHDAY={day_of_month}"],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 60},
                {"method": "popup", "minutes": 1440},
            ],
        },
    }
    result = calendar_service.events().insert(
        calendarId=CALENDAR_ID,
        body=event_body,
    ).execute()
    return result.get("htmlLink", "")


def ensure_monthly_payment_reminder(reminders_dataframe):
    title = "Μηνιαίος έλεγχος πληρωμών και προϋπολογισμού"
    if not reminders_dataframe.empty and title in reminders_dataframe["τίτλος"].astype(str).tolist():
        return
    try:
        calendar_link = create_monthly_calendar_event(title, 9, 9)
        append_reminder(
            title=title,
            category="Οικονομικά",
            reminder_date=date.today(),
            reminder_time=time(9, 0),
            amount=0,
            recurrence="Κάθε μήνα στις 9",
            calendar_link=calendar_link,
            notes="Αυτόματη υπενθύμιση εφαρμογής.",
        )
    except Exception:
        pass


@st.cache_data(ttl=120)
def load_records(sheet_name):
    """
    Διαβάζει το ήδη φορτωμένο worksheet χωρίς νέο metadata request.
    """
    expected_headers = SHEET_SCHEMAS[sheet_name]
    worksheet = WORKSHEETS[sheet_name]

    try:
        values = get_all_values_with_retry(
            worksheet,
            attempts=5,
        )
    except gspread.exceptions.APIError:
        st.warning(
            f"Το φύλλο «{sheet_name}» δεν διαβάστηκε προσωρινά από την Google. "
            "Πάτησε «Ανανέωση δεδομένων» σε λίγο."
        )
        return pd.DataFrame(columns=expected_headers)

    if not values:
        worksheet.update("A1", [expected_headers])
        return pd.DataFrame(columns=expected_headers)

    actual_headers = [
        str(value).strip()
        for value in values[0]
    ]

    # Χαρτογράφηση κάθε γραμμής βάσει των πραγματικών headers.
    records = []

    for row in values[1:]:
        record = {
            header: row[index] if index < len(row) else ""
            for index, header in enumerate(actual_headers)
            if header
        }

        records.append({
            header: record.get(header, "")
            for header in expected_headers
        })

    if not records:
        return pd.DataFrame(columns=expected_headers)

    return pd.DataFrame(records, columns=expected_headers)


def refresh_data():
    load_records.clear()


def append_transaction(
    transaction_date,
    transaction_type,
    category,
    description,
    amount,
    payment_method="",
    recurring=False,
    money_source="Υπόλοιπο μήνα",
    savings_record_id="",
    file_link="",
    notes="",
    reference_year=None,
    reference_month=None,
    activity="Γενικά",
):
    transaction_id = create_id("KIN")
    transaction_date = (
        transaction_date
        if isinstance(transaction_date, date)
        else pd.Timestamp(transaction_date).date()
    )
    reference_year = int(reference_year or transaction_date.year)
    reference_month = int(reference_month or transaction_date.month)

    transactions_ws.append_row(
        [
            transaction_id,
            transaction_date.isoformat(),
            reference_year,
            reference_month,
            transaction_type,
            category,
            description,
            float(amount),
            payment_method,
            "Ναι" if recurring else "Όχι",
            money_source,
            savings_record_id,
            file_link,
            notes,
            datetime.now().isoformat(timespec="seconds"),
            activity or "Γενικά",
        ],
        value_input_option="USER_ENTERED",
    )

    refresh_data()
    return transaction_id


def append_reminder(
    title,
    category,
    reminder_date,
    reminder_time,
    amount,
    recurrence,
    calendar_link="",
    file_link="",
    notes="",
):
    reminders_ws.append_row(
        [
            create_id("YP"),
            title,
            category,
            reminder_date.isoformat(),
            reminder_time.strftime("%H:%M"),
            float(amount),
            recurrence,
            "Ενεργή",
            calendar_link,
            file_link,
            notes,
            datetime.now().isoformat(timespec="seconds"),
        ],
        value_input_option="USER_ENTERED",
    )

    refresh_data()


def append_task(
    title,
    category,
    deadline,
    priority,
    notes="",
    item_type="Εκκρεμότητα",
    amount=0.0,
    recurrence="Καμία",
    rf="",
):
    amount = float(amount)
    now_text = datetime.now().isoformat(timespec="seconds")
    tasks_ws.append_row(
        [
            create_id("TASK"),
            item_type,
            title,
            category,
            deadline.isoformat(),
            deadline.isoformat(),
            amount,
            0.0,
            amount,
            "Προς πληρωμή" if item_type == "Λογαριασμός" else "Ανοιχτή",
            rf.strip(),
            recurrence,
            priority,
            "Ανοιχτή",
            notes,
            now_text,
            now_text,
        ],
        value_input_option="USER_ENTERED",
    )
    refresh_data()


def update_record_fields(worksheet, record_id, updates):
    """
    Ενημερώνει μία εγγραφή με ένα μόνο αίτημα προς τη Google.
    Η προηγούμενη υλοποίηση έκανε update_cell για κάθε πεδίο,
    προκαλώντας πολλά API requests και quota errors.
    """
    values = get_all_values_with_retry(worksheet, attempts=3)
    if not values:
        return False

    headers = values[0]
    if "id" not in headers:
        return False

    id_index = headers.index("id")

    for row_number, row in enumerate(values[1:], start=2):
        current_id = row[id_index] if id_index < len(row) else ""
        if str(current_id) != str(record_id):
            continue

        updated_row = list(row) + [""] * max(0, len(headers) - len(row))
        updated_row = updated_row[:len(headers)]

        changed = False
        for column_name, value in updates.items():
            if column_name not in headers:
                continue
            column_index = headers.index(column_name)
            normalized_value = "" if value is None else value
            if str(updated_row[column_index]) != str(normalized_value):
                updated_row[column_index] = normalized_value
                changed = True

        if not changed:
            return True

        end_column = gspread.utils.rowcol_to_a1(
            row_number,
            len(headers),
        )
        start_cell = f"A{row_number}"

        try:
            worksheet.update(
                range_name=f"{start_cell}:{end_column}",
                values=[updated_row],
                value_input_option="USER_ENTERED",
            )
            refresh_data()
            return True
        except gspread.exceptions.APIError:
            st.warning(
                "Η Google δεν απάντησε προσωρινά στην αποθήκευση. "
                "Δεν έγινε αλλαγή σε αυτή την εγγραφή. "
                "Δοκίμασε ξανά σε λίγο."
            )
            return False

    return False


def delete_record_by_id(worksheet, record_id):
    values = get_all_values_with_retry(worksheet, attempts=3)
    if not values or "id" not in values[0]:
        return False
    id_index = values[0].index("id")
    for row_number, row in enumerate(values[1:], start=2):
        current_id = row[id_index] if id_index < len(row) else ""
        if str(current_id) == str(record_id):
            worksheet.delete_rows(row_number)
            refresh_data()
            return True
    return False


def replace_worksheet_records(worksheet, sheet_name, dataframe):
    headers = SHEET_SCHEMAS[sheet_name]
    clean_df = dataframe.copy()
    clean_df = clean_df.drop(columns=["διαγραφή"], errors="ignore")
    for header in headers:
        if header not in clean_df.columns:
            clean_df[header] = ""
    clean_df = clean_df[headers].fillna("")
    rows = []
    for _, row in clean_df.iterrows():
        values = []
        for header in headers:
            value = row[header]
            if isinstance(value, pd.Timestamp):
                value = value.strftime("%Y-%m-%d") if not pd.isna(value) else ""
            elif isinstance(value, (date, datetime)):
                value = value.isoformat()
            values.append(value)
        rows.append(values)
    worksheet.clear()
    worksheet.update(values=[headers] + rows, range_name="A1")
    refresh_data()


def next_month_date(current_date):
    return (current_date.replace(day=1) + relativedelta(months=1))


def record_bill_payment(task_row, paid_now, payment_method, notes=""):
    remaining_before = parse_number(task_row.get("υπόλοιπο", 0))
    paid_now = min(max(float(paid_now), 0), remaining_before)
    if paid_now <= 0:
        return False

    transaction_id = append_transaction(
        transaction_date=date.today(),
        transaction_type="Έξοδο",
        category=task_row.get("κατηγορία", "Λογαριασμοί"),
        description=task_row.get("τίτλος", "Πληρωμή"),
        amount=paid_now,
        payment_method=payment_method,
        recurring=task_row.get("επανάληψη", "Καμία") != "Καμία",
        money_source="Υπόλοιπο μήνα",
        notes=(
            f"Πληρωμή υποχρέωσης {task_row.get('id', '')}. "
            f"RF: {task_row.get('rf', '')}. {notes}"
        ).strip(),
    )

    paid_total = parse_number(task_row.get("πληρωμένο_ποσό", 0)) + paid_now
    remaining = max(parse_number(task_row.get("ποσό", 0)) - paid_total, 0)
    updates = {
        "πληρωμένο_ποσό": paid_total,
        "υπόλοιπο": remaining,
        "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
    }
    if remaining <= 0.005:
        updates.update({
            "κατάσταση_πληρωμής": "Ολοκληρωμένη",
            "κατάσταση": "Ολοκληρωμένη",
        })
    else:
        current_due = task_row.get("προθεσμία")
        if pd.isna(current_due):
            current_due = pd.Timestamp(date.today())
        updates.update({
            "κατάσταση_πληρωμής": "Μερικώς πληρωμένη",
            "κατάσταση": "Ανοιχτή",
            "προθεσμία": next_month_date(current_due.date()).isoformat(),
        })
    update_record_fields(tasks_ws, task_row.get("id"), updates)
    return True


def update_record_status(worksheet, record_id, status_column_name, new_status):
    all_values = worksheet.get_all_values()

    if not all_values:
        return False

    headers = all_values[0]

    if "id" not in headers or status_column_name not in headers:
        return False

    id_column = headers.index("id") + 1
    status_column = headers.index(status_column_name) + 1

    for row_number, row in enumerate(all_values[1:], start=2):
        if len(row) >= id_column and row[id_column - 1] == record_id:
            worksheet.update_cell(row_number, status_column, new_status)
            refresh_data()
            return True

    return False





def prepare_financial_closes(df):
    columns = SHEET_SCHEMAS[FINANCIAL_CLOSES_SHEET]
    if df.empty:
        return pd.DataFrame(columns=columns)

    result = df.copy()
    for column, default in {
        "id": "",
        "τύπος_περιόδου": "",
        "έτος": 0,
        "μήνας": 0,
        "κατηγορία": "Όλες",
        "περιγραφή": "Όλες",
        "έσοδα": 0.0,
        "έξοδα": 0.0,
        "υπόλοιπο": 0.0,
        "αποταμίευση": 0.0,
        "σημειώσεις": "",
        "κλείστηκε": "",
    }.items():
        if column not in result.columns:
            result[column] = default

    result["έτος"] = result["έτος"].apply(
        lambda value: int(parse_number(value))
    )
    result["μήνας"] = result["μήνας"].apply(
        lambda value: int(parse_number(value))
    )
    for column in ["έσοδα", "έξοδα", "υπόλοιπο", "αποταμίευση"]:
        result[column] = result[column].apply(parse_number)
    result["κλείστηκε"] = pd.to_datetime(
        result["κλείστηκε"],
        errors="coerce",
    )
    return result


def prepare_analytics_targets(df):
    columns = SHEET_SCHEMAS[ANALYTICS_TARGETS_SHEET]
    if df.empty:
        return pd.DataFrame(columns=columns)

    result = df.copy()
    for column, default in {
        "id": "",
        "έτος": date.today().year,
        "κατηγορία": "Όλες",
        "περιγραφή": "Όλες",
        "τύπος": "Μέγιστο έξοδο",
        "ποσό_στόχου": 0.0,
        "σημειώσεις": "",
        "ενημερώθηκε": "",
    }.items():
        if column not in result.columns:
            result[column] = default

    result["έτος"] = result["έτος"].apply(
        lambda value: int(parse_number(value))
    )
    result["ποσό_στόχου"] = result["ποσό_στόχου"].apply(parse_number)
    return result


def filter_financial_transactions(
    dataframe,
    year=None,
    month=None,
    category="Όλες",
    description="Όλες",
):
    if dataframe.empty:
        return dataframe.copy()

    result = dataframe.copy()
    result = result[result["ημερομηνία"].notna()]

    if year is not None:
        result = result[result["έτος_αναφοράς"] == int(year)]
    if month is not None:
        result = result[result["μήνας_αναφοράς"] == int(month)]
    if category and category != "Όλες":
        result = result[result["κατηγορία"].astype(str) == str(category)]
    if description and description != "Όλες":
        result = result[result["περιγραφή"].astype(str) == str(description)]

    return result.copy()


def financial_summary(dataframe):
    if dataframe.empty:
        return {
            "income": 0.0,
            "expenses": 0.0,
            "expenses_from_balance": 0.0,
            "balance": 0.0,
            "transactions": 0,
        }

    income = dataframe.loc[
        dataframe["τύπος"] == "Έσοδο",
        "ποσό",
    ].sum()
    expenses = dataframe.loc[
        dataframe["τύπος"] == "Έξοδο",
        "ποσό",
    ].sum()
    expenses_from_balance = dataframe.loc[
        (dataframe["τύπος"] == "Έξοδο")
        & (dataframe["πηγή_χρημάτων"] != "Αποταμίευση"),
        "ποσό",
    ].sum()

    return {
        "income": float(income),
        "expenses": float(expenses),
        "expenses_from_balance": float(expenses_from_balance),
        "balance": float(income - expenses_from_balance),
        "transactions": int(len(dataframe)),
    }


def save_financial_close(
    period_type,
    year,
    month,
    category,
    description,
    summary,
    savings_value,
    notes="",
):
    existing = prepare_financial_closes(
        load_records(FINANCIAL_CLOSES_SHEET)
    )

    matches = existing[
        (existing["τύπος_περιόδου"].astype(str) == str(period_type))
        & (existing["έτος"] == int(year))
        & (existing["μήνας"] == int(month))
        & (existing["κατηγορία"].astype(str) == str(category))
        & (existing["περιγραφή"].astype(str) == str(description))
    ]

    values = {
        "τύπος_περιόδου": period_type,
        "έτος": int(year),
        "μήνας": int(month),
        "κατηγορία": category,
        "περιγραφή": description,
        "έσοδα": summary["income"],
        "έξοδα": summary["expenses"],
        "υπόλοιπο": summary["balance"],
        "αποταμίευση": float(savings_value),
        "σημειώσεις": notes,
        "κλείστηκε": datetime.now().isoformat(timespec="seconds"),
    }

    if not matches.empty:
        return update_record_fields(
            financial_closes_ws,
            matches.iloc[-1]["id"],
            values,
        )

    values["id"] = create_id("CLOSE")
    append_generic_record(
        financial_closes_ws,
        FINANCIAL_CLOSES_SHEET,
        values,
    )
    return True


def save_analytics_target(
    year,
    category,
    description,
    target_type,
    target_amount,
    notes="",
):
    existing = prepare_analytics_targets(
        load_records(ANALYTICS_TARGETS_SHEET)
    )
    matches = existing[
        (existing["έτος"] == int(year))
        & (existing["κατηγορία"].astype(str) == str(category))
        & (existing["περιγραφή"].astype(str) == str(description))
        & (existing["τύπος"].astype(str) == str(target_type))
    ]

    values = {
        "έτος": int(year),
        "κατηγορία": category,
        "περιγραφή": description,
        "τύπος": target_type,
        "ποσό_στόχου": float(target_amount),
        "σημειώσεις": notes,
        "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
    }

    if not matches.empty:
        return update_record_fields(
            analytics_targets_ws,
            matches.iloc[-1]["id"],
            values,
        )

    values["id"] = create_id("TARGET")
    append_generic_record(
        analytics_targets_ws,
        ANALYTICS_TARGETS_SHEET,
        values,
    )
    return True


def available_financial_categories(dataframe):
    if dataframe.empty or "κατηγορία" not in dataframe.columns:
        return ["Όλες"]

    values = sorted(
        {
            str(value).strip()
            for value in dataframe["κατηγορία"].tolist()
            if str(value).strip()
        }
    )
    return ["Όλες"] + values


def available_financial_descriptions(dataframe, category="Όλες"):
    if dataframe.empty or "περιγραφή" not in dataframe.columns:
        return ["Όλες"]

    working = dataframe
    if category != "Όλες":
        working = working[
            working["κατηγορία"].astype(str) == str(category)
        ]

    values = sorted(
        {
            str(value).strip()
            for value in working["περιγραφή"].tolist()
            if str(value).strip()
        }
    )
    return ["Όλες"] + values


def prepare_transactions(df):
    if df.empty:
        return pd.DataFrame(columns=SHEET_SCHEMAS[TRANSACTIONS_SHEET])

    result = df.copy()
    for column, default in {
        "έτος_αναφοράς": 0,
        "μήνας_αναφοράς": 0,
        "τρόπος_πληρωμής": "",
        "πάγιο": "Όχι",
        "πηγή_χρημάτων": "Υπόλοιπο μήνα",
        "σχετική_αποταμίευση": "",
        "αρχείο": "",
        "σημειώσεις": "",
        "δραστηριότητα": "Γενικά",
    }.items():
        if column not in result.columns:
            result[column] = default

    result["ημερομηνία"] = pd.to_datetime(
        result["ημερομηνία"],
        errors="coerce",
    )
    result["ποσό"] = result["ποσό"].apply(parse_number)
    result["πηγή_χρημάτων"] = result["πηγή_χρημάτων"].replace(
        "",
        "Υπόλοιπο μήνα",
    )
    result["δραστηριότητα"] = result["δραστηριότητα"].replace(
        "",
        "Γενικά",
    )
    result["δραστηριότητα"] = result["δραστηριότητα"].replace(
        {"Προσωπικό": "Γενικά", "Υπηρεσία": "Γενικά"}
    )

    result["έτος_αναφοράς"] = result.apply(
        lambda row: int(parse_number(row.get("έτος_αναφοράς", 0)))
        or (
            int(row["ημερομηνία"].year)
            if not pd.isna(row["ημερομηνία"])
            else 0
        ),
        axis=1,
    )
    result["μήνας_αναφοράς"] = result.apply(
        lambda row: int(parse_number(row.get("μήνας_αναφοράς", 0)))
        or (
            int(row["ημερομηνία"].month)
            if not pd.isna(row["ημερομηνία"])
            else 0
        ),
        axis=1,
    )
    result["ημερομηνία_αναφοράς"] = pd.to_datetime(
        dict(
            year=result["έτος_αναφοράς"],
            month=result["μήνας_αναφοράς"],
            day=1,
        ),
        errors="coerce",
    )
    return result


def prepare_reminders(df):
    if df.empty:
        return df.copy()

    result = df.copy()
    result["ημερομηνία"] = pd.to_datetime(
        result["ημερομηνία"],
        errors="coerce",
    )
    result["ποσό"] = result["ποσό"].apply(parse_number)
    return result


def prepare_tasks(df):
    if df.empty:
        return df.copy()

    result = df.copy()
    defaults = {
        "τύπος": "Εκκρεμότητα",
        "αρχική_προθεσμία": "",
        "ποσό": 0.0,
        "πληρωμένο_ποσό": 0.0,
        "υπόλοιπο": 0.0,
        "κατάσταση_πληρωμής": "Προς πληρωμή",
        "rf": "",
        "επανάληψη": "Καμία",
        "προτεραιότητα": "Κανονική",
        "κατάσταση": "Ανοιχτή",
        "ενημερώθηκε": "",
    }
    for column, default_value in defaults.items():
        if column not in result.columns:
            result[column] = default_value

    for column in ["προθεσμία", "αρχική_προθεσμία"]:
        result[column] = pd.to_datetime(result[column], errors="coerce")

    for column in ["ποσό", "πληρωμένο_ποσό", "υπόλοιπο"]:
        result[column] = result[column].apply(parse_number)

    missing_remaining = result["υπόλοιπο"] <= 0
    still_open = result["κατάσταση"] != "Ολοκληρωμένη"
    result.loc[missing_remaining & still_open, "υπόλοιπο"] = (
        result.loc[missing_remaining & still_open, "ποσό"]
        - result.loc[missing_remaining & still_open, "πληρωμένο_ποσό"]
    ).clip(lower=0)
    result["τύπος"] = result["τύπος"].replace("", "Εκκρεμότητα")
    result["επανάληψη"] = result["επανάληψη"].replace("", "Καμία")
    return result


def prepare_debts(df):
    result = df.copy()

    required_columns = {
        "id": "",
        "όνομα": "",
        "είδος": "Δάνειο",
        "πιστωτής": "",
        "αρχικό_ποσό": 0.0,
        "προεπιλεγμένη_δόση": 0.0,
        "ετήσιο_επιτόκιο": 0.0,
        "συνολικές_δόσεις": 0,
        "ημερομηνία_πρώτης_δόσης": "",
        "τύπος_επιτοκίου": "Χωρίς επιτόκιο",
        "ενεργό": "Ναι",
        "σημειώσεις": "",
        "ενημερώθηκε": "",
    }

    for column_name, default_value in required_columns.items():
        if column_name not in result.columns:
            result[column_name] = default_value

    result["αρχικό_ποσό"] = result["αρχικό_ποσό"].apply(parse_number)
    result["προεπιλεγμένη_δόση"] = result["προεπιλεγμένη_δόση"].apply(parse_number)
    result["ετήσιο_επιτόκιο"] = result["ετήσιο_επιτόκιο"].apply(parse_number)
    result["συνολικές_δόσεις"] = result["συνολικές_δόσεις"].apply(
        lambda value: int(parse_number(value))
    )
    result["ημερομηνία_πρώτης_δόσης"] = pd.to_datetime(
        result["ημερομηνία_πρώτης_δόσης"],
        errors="coerce",
    )
    return result


def prepare_debt_movements(df):
    if df.empty:
        return df.copy()

    result = df.copy()
    result["ημερομηνία"] = pd.to_datetime(
        result["ημερομηνία"],
        errors="coerce",
    )
    result["ποσό"] = result["ποσό"].apply(parse_number)
    return result






def prepare_debts(df):
    result = df.copy()

    required_columns = {
        "id": "",
        "όνομα": "",
        "είδος": "Δάνειο",
        "πιστωτής": "",
        "αρχικό_ποσό": 0.0,
        "προεπιλεγμένη_δόση": 0.0,
        "ετήσιο_επιτόκιο": 0.0,
        "συνολικές_δόσεις": 0,
        "ημερομηνία_πρώτης_δόσης": "",
        "τύπος_επιτοκίου": "Χωρίς επιτόκιο",
        "ενεργό": "Ναι",
        "σημειώσεις": "",
        "ενημερώθηκε": "",
    }

    for column_name, default_value in required_columns.items():
        if column_name not in result.columns:
            result[column_name] = default_value

    result["αρχικό_ποσό"] = result["αρχικό_ποσό"].apply(parse_number)
    result["προεπιλεγμένη_δόση"] = result["προεπιλεγμένη_δόση"].apply(parse_number)
    result["ετήσιο_επιτόκιο"] = result["ετήσιο_επιτόκιο"].apply(parse_number)
    result["συνολικές_δόσεις"] = result["συνολικές_δόσεις"].apply(
        lambda value: int(parse_number(value))
    )
    result["ημερομηνία_πρώτης_δόσης"] = pd.to_datetime(
        result["ημερομηνία_πρώτης_δόσης"],
        errors="coerce",
    )
    return result


def prepare_debt_movements(df):
    if df.empty:
        return df.copy()

    result = df.copy()
    result["ημερομηνία"] = pd.to_datetime(
        result["ημερομηνία"],
        errors="coerce",
    )
    result["ποσό"] = result["ποσό"].apply(parse_number)
    return result

def update_debt_settings(debt_id, initial_amount, default_payment):
    values = debts_ws.get_all_values()

    if not values:
        return False

    headers = values[0]
    id_col = headers.index("id")
    initial_col = headers.index("αρχικό_ποσό") + 1
    payment_col = headers.index("προεπιλεγμένη_δόση") + 1
    updated_col = headers.index("ενημερώθηκε") + 1

    for row_number, row in enumerate(values[1:], start=2):
        if len(row) > id_col and row[id_col] == debt_id:
            debts_ws.update_cell(row_number, initial_col, float(initial_amount))
            debts_ws.update_cell(row_number, payment_col, float(default_payment))
            debts_ws.update_cell(
                row_number,
                updated_col,
                datetime.now().isoformat(timespec="seconds"),
            )
            refresh_data()
            return True

    return False


def append_debt_movement(
    debt_id,
    debt_name,
    movement_date,
    movement_type,
    amount,
    notes="",
    related_transaction_id="",
    money_source="",
):
    movement_id = create_id("DM")
    debt_movements_ws.append_row(
        [
            movement_id,
            debt_id,
            debt_name,
            movement_date.isoformat(),
            movement_type,
            float(amount),
            related_transaction_id,
            money_source,
            notes,
            datetime.now().isoformat(timespec="seconds"),
        ],
        value_input_option="USER_ENTERED",
    )
    refresh_data()
    return movement_id


def calculate_fixed_installment(principal, annual_rate_percent, total_installments):
    principal = float(principal)
    total_installments = int(total_installments)
    monthly_rate = float(annual_rate_percent) / 100 / 12

    if principal <= 0 or total_installments <= 0:
        return 0.0

    if monthly_rate == 0:
        return principal / total_installments

    return (
        principal
        * monthly_rate
        / (1 - (1 + monthly_rate) ** (-total_installments))
    )






def calculate_debt_balance(debt_row, debt_movements):
    """Υπολογίζει γενικά το υπόλοιπο κάθε δανείου ή κάρτας."""
    initial_amount = parse_number(debt_row.get("αρχικό_ποσό", 0))

    if debt_movements.empty:
        return max(initial_amount, 0.0)

    relevant = debt_movements[
        debt_movements["debt_id"].astype(str) == str(debt_row["id"])
    ]

    payments = relevant.loc[
        relevant["τύπος"] == "Πληρωμή",
        "ποσό",
    ].sum()
    increases = relevant.loc[
        relevant["τύπος"] == "Αύξηση οφειλής",
        "ποσό",
    ].sum()
    decreases = relevant.loc[
        relevant["τύπος"] == "Μείωση οφειλής",
        "ποσό",
    ].sum()

    return max(initial_amount + increases - decreases - payments, 0.0)


def set_debt_current_balance(debt_row, target_balance, debt_movements, note):
    current_balance = calculate_debt_balance(debt_row, debt_movements)
    difference = float(target_balance) - current_balance

    if abs(difference) < 0.005:
        return False

    movement_type = (
        "Αύξηση οφειλής"
        if difference > 0
        else "Μείωση οφειλής"
    )

    append_debt_movement(
        debt_id=debt_row["id"],
        debt_name=debt_row["όνομα"],
        movement_date=date.today(),
        movement_type=movement_type,
        amount=abs(difference),
        notes=note or "Χειροκίνητη διόρθωση υπολοίπου",
    )
    return True


def prepare_monthly_budget(df):
    if df.empty:
        return df.copy()

    result = df.copy()

    numeric_columns = [
        "έτος",
        "μήνας",
        "μισθός",
        "άλλο_σταθερό_έσοδο",
        "έκτακτο_έσοδο",
        "ενοίκιο",
        "κοινόχρηστα",
        "ρεύμα",
        "αέριο",
        "νερό",
        "κινητό_τηλέφωνο",
        "σταθερό_τηλέφωνο",
        "δάνειο_πειραιώς",
        "δάνειο_γεωργία",
        "δάνειο_θεία",
        "εφορία",
        "εφκα",
        "πιστωτική",
        "συνδρομές",
        "φαρμακείο",
        "γιατρός",
        "έξοδα_αυτοκινήτου",
        "ασφάλεια_αυτοκινήτου",
        "τέλη_κυκλοφορίας",
        "άλλο_ποσό",
        "μαξιλάρι_ασφαλείας",
    ]

    for column in numeric_columns:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = result[column].apply(parse_number)

    return result


def get_monthly_budget_record(budget_df, year, month):
    if budget_df.empty:
        return {}

    matches = budget_df[
        (budget_df["έτος"].astype(int) == int(year))
        & (budget_df["μήνας"].astype(int) == int(month))
    ]

    if matches.empty:
        return {}

    return matches.iloc[-1].to_dict()


def save_monthly_budget(year, month, values, notes=""):
    all_values = get_all_values_with_retry(
        monthly_budget_ws,
        attempts=5,
    )
    headers = SHEET_SCHEMAS[MONTHLY_BUDGET_SHEET]

    year_col = headers.index("έτος")
    month_col = headers.index("μήνας")

    target_row = None

    for row_number, row in enumerate(all_values[1:], start=2):
        row_year = row[year_col] if year_col < len(row) else ""
        row_month = row[month_col] if month_col < len(row) else ""

        if (
            int(parse_number(row_year)) == int(year)
            and int(parse_number(row_month)) == int(month)
        ):
            target_row = row_number
            break

    record = {
        "id": create_id("BUDGET"),
        "έτος": int(year),
        "μήνας": int(month),
        **values,
        "σημειώσεις": notes,
        "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
    }

    row_values = [record.get(header, "") for header in headers]

    if target_row is None:
        monthly_budget_ws.append_row(
            row_values,
            value_input_option="USER_ENTERED",
        )
    else:
        existing_id = (
            all_values[target_row - 1][0]
            if target_row - 1 < len(all_values)
            and all_values[target_row - 1]
            else ""
        )
        row_values[0] = existing_id or record["id"]
        monthly_budget_ws.update(
            values=[row_values],
            range_name=f"A{target_row}",
        )

    refresh_data()







def money_text_input(label, key, current_value=0.0, help_text=None):
    """
    Πεδίο ποσού χωρίς +/−.

    Η τιμή επαναφορτώνεται μόνο όταν αλλάζει η αποθηκευμένη τιμή
    που προέρχεται από Google Sheets ή από αυτόματη πρόταση.
    Έτσι, όταν επιστρέφουμε σε έναν αποθηκευμένο μήνα, τα επιμέρους
    πεδία γεμίζουν ξανά σωστά χωρίς να χάνουν προσωρινές αλλαγές.
    """
    numeric_value = float(parse_number(current_value))
    source_key = f"{key}__source_value"
    source_signature = round(numeric_value, 2)

    if (
        key not in st.session_state
        or st.session_state.get(source_key) != source_signature
    ):
        st.session_state[key] = (
            ""
            if abs(numeric_value) < 0.005
            else f"{numeric_value:.2f}".replace(".", ",")
        )
        st.session_state[source_key] = source_signature

    raw_value = st.text_input(
        label,
        key=key,
        placeholder="0,00",
        help=help_text,
    )
    return max(float(parse_number(raw_value)), 0.0)


def prepare_budget_status(df):
    columns = SHEET_SCHEMAS[BUDGET_STATUS_SHEET]
    if df.empty:
        return pd.DataFrame(columns=columns)

    result = df.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = ""

    result["έτος"] = result["έτος"].apply(
        lambda value: int(parse_number(value))
    )
    result["μήνας"] = result["μήνας"].apply(
        lambda value: int(parse_number(value))
    )
    return result


def get_budget_status_record(status_df, year, month, field_code):
    if status_df.empty:
        return {}

    matched = status_df[
        (status_df["έτος"] == int(year))
        & (status_df["μήνας"] == int(month))
        & (
            status_df["κωδικός_πεδίου"].astype(str)
            == str(field_code)
        )
    ]
    if matched.empty:
        return {}
    return matched.iloc[-1].to_dict()


def upsert_budget_status(
    year,
    month,
    field_code,
    description,
    item_type,
    is_recurring,
    frequency,
    completed,
    money_source,
    transaction_id="",
    recurring_id="",
):
    existing = prepare_budget_status(
        load_records(BUDGET_STATUS_SHEET)
    )
    record = get_budget_status_record(
        existing,
        year,
        month,
        field_code,
    )

    values = {
        "έτος": int(year),
        "μήνας": int(month),
        "κωδικός_πεδίου": str(field_code),
        "περιγραφή": description,
        "τύπος": item_type,
        "πάγιο": "Ναι" if is_recurring else "Όχι",
        "συχνότητα": frequency if is_recurring else "",
        "ολοκληρώθηκε": "Ναι" if completed else "Όχι",
        "πηγή_χρημάτων": money_source,
        "σχετική_κίνηση": transaction_id,
        "σχετικό_πάγιο": recurring_id,
        "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
    }

    if record:
        comparable_fields = [
            "έτος",
            "μήνας",
            "κωδικός_πεδίου",
            "περιγραφή",
            "τύπος",
            "πάγιο",
            "συχνότητα",
            "ολοκληρώθηκε",
            "πηγή_χρημάτων",
            "σχετική_κίνηση",
            "σχετικό_πάγιο",
        ]
        has_changes = any(
            str(record.get(field, "")) != str(values.get(field, ""))
            for field in comparable_fields
        )

        if has_changes:
            update_record_fields(
                budget_status_ws,
                record["id"],
                values,
            )
        return record["id"]

    values["id"] = create_id("BSTAT")
    append_generic_record(
        budget_status_ws,
        BUDGET_STATUS_SHEET,
        values,
    )
    return values["id"]


def create_or_update_budget_recurring(
    existing_recurring_id,
    name,
    category,
    item_type,
    amount,
    frequency,
    year,
    month,
):
    if amount <= 0:
        return existing_recurring_id or ""

    first_due = date(int(year), int(month), 1)
    record_values = {
        "όνομα": name,
        "κατηγορία": category,
        "τύπος": item_type,
        "ποσό": float(amount),
        "συχνότητα": frequency,
        "τελευταία_πληρωμή": "",
        "επόμενη_χρέωση": first_due.isoformat(),
        "rf": "",
        "τρόπος_πληρωμής": "Δεν ορίστηκε",
        "ενεργό": "Ναι",
        "υπενθύμιση_ημέρες": 3,
        "σημειώσεις": "Δημιουργήθηκε από τον μηνιαίο προϋπολογισμό.",
        "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
    }

    if existing_recurring_id:
        if update_record_fields(
            recurring_ws,
            existing_recurring_id,
            record_values,
        ):
            return existing_recurring_id

    record_values["id"] = create_id("REC")
    append_generic_record(
        recurring_ws,
        RECURRING_SHEET,
        record_values,
    )
    return record_values["id"]


def complete_budget_entry(
    year,
    month,
    field_code,
    description,
    category,
    item_type,
    amount,
    money_source,
    is_recurring=False,
):
    if amount <= 0:
        return ""

    transaction_date = date.today()
    if (
        transaction_date.year != int(year)
        or transaction_date.month != int(month)
    ):
        transaction_date = (
            date(int(year), int(month), 1)
            + relativedelta(months=1)
            - timedelta(days=1)
        )

    if item_type == "Έξοδο" and money_source == "Αποταμίευση":
        transaction_id = append_savings_withdrawal(
            withdrawal_date=transaction_date,
            amount=amount,
            transaction_type="Έξοδο",
            category=category,
            description=description,
            payment_method="Από προϋπολογισμό",
            recurring=is_recurring,
            notes=(
                f"Ολοκλήρωση από τον προϋπολογισμό "
                f"{int(month):02d}/{int(year)}"
            ),
            reference_year=year,
            reference_month=month,
        )
    else:
        transaction_id = append_transaction(
            transaction_date=transaction_date,
            transaction_type=item_type,
            category=category,
            description=description,
            amount=amount,
            payment_method="Από προϋπολογισμό",
            recurring=is_recurring,
            money_source=(
                money_source
                if item_type == "Έξοδο"
                else "Υπόλοιπο μήνα"
            ),
            notes=(
                f"Ολοκλήρωση από τον προϋπολογισμό "
                f"{int(month):02d}/{int(year)}"
            ),
            reference_year=year,
            reference_month=month,
        )

    return transaction_id


def clear_budget_completion_by_transaction(transaction_id):
    status_values = get_all_values_with_retry(
        budget_status_ws,
        attempts=3,
    )
    if not status_values or "σχετική_κίνηση" not in status_values[0]:
        return

    headers = status_values[0]
    tx_index = headers.index("σχετική_κίνηση")
    id_index = headers.index("id")

    for row in status_values[1:]:
        current_tx = row[tx_index] if tx_index < len(row) else ""
        if str(current_tx) == str(transaction_id):
            status_id = row[id_index] if id_index < len(row) else ""
            update_record_fields(
                budget_status_ws,
                status_id,
                {
                    "ολοκληρώθηκε": "Όχι",
                    "σχετική_κίνηση": "",
                    "πηγή_χρημάτων": "",
                    "ενημερώθηκε": datetime.now().isoformat(
                        timespec="seconds"
                    ),
                },
            )


def prepare_budget_items(df):
    if df.empty:
        return pd.DataFrame(
            columns=[
                "id",
                "έτος",
                "μήνας",
                "περιγραφή",
                "κατηγορία",
                "ποσό",
                "πηγή",
                "σημειώσεις",
                "ενημερώθηκε",
            ]
        )

    result = df.copy()

    for column, default in {
        "id": "",
        "έτος": 0,
        "μήνας": 0,
        "περιγραφή": "",
        "κατηγορία": "",
        "τύπος": "Έξοδο",
        "ποσό": 0.0,
        "πάγιο": "Όχι",
        "συχνότητα": "",
        "ολοκληρώθηκε": "Όχι",
        "πηγή_χρημάτων": "Υπόλοιπο μήνα",
        "σχετική_κίνηση": "",
        "πηγή": "Χειροκίνητη",
        "σημειώσεις": "",
        "ενημερώθηκε": "",
    }.items():
        if column not in result.columns:
            result[column] = default

    result["έτος"] = result["έτος"].apply(
        lambda value: int(parse_number(value))
    )
    result["μήνας"] = result["μήνας"].apply(
        lambda value: int(parse_number(value))
    )
    result["ποσό"] = result["ποσό"].apply(parse_number)
    return result


def normalize_budget_text(value):
    text = str(value or "").strip().lower()
    replacements = {
        "ά": "α",
        "έ": "ε",
        "ή": "η",
        "ί": "ι",
        "ό": "ο",
        "ύ": "υ",
        "ώ": "ω",
        "ϊ": "ι",
        "ΐ": "ι",
        "ϋ": "υ",
        "ΰ": "υ",
        "ς": "σ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def recurring_due_in_month(recurring_row, year, month):
    month_start = date(int(year), int(month), 1)
    month_end = (
        month_start + relativedelta(months=1) - timedelta(days=1)
    )

    frequency_months = {
        "Κάθε μήνα": 1,
        "Κάθε 2 μήνες": 2,
        "Κάθε 3 μήνες": 3,
        "Κάθε 6 μήνες": 6,
        "Κάθε χρόνο": 12,
    }.get(str(recurring_row.get("συχνότητα", "")), 1)

    next_charge = recurring_row.get("επόμενη_χρέωση")
    last_paid = recurring_row.get("τελευταία_πληρωμή")

    if not pd.isna(next_charge):
        candidate = pd.Timestamp(next_charge).date()
    elif not pd.isna(last_paid):
        candidate = (
            pd.Timestamp(last_paid).date()
            + relativedelta(months=frequency_months)
        )
    else:
        return None

    while candidate > month_end:
        candidate -= relativedelta(months=frequency_months)

    while candidate < month_start:
        candidate += relativedelta(months=frequency_months)

    if month_start <= candidate <= month_end:
        return candidate

    return None


def budget_fixed_field(description, category=""):
    combined = normalize_budget_text(
        f"{description} {category}"
    )

    aliases = [
        ("μισθός", ["μισθοσ", "μισθοδοσια"]),
        ("άλλο_σταθερό_έσοδο", ["σταθερο εσοδο", "συνταξη"]),
        ("έκτακτο_έσοδο", ["εκτακτο εσοδο", "επιστροφη χρηματων"]),
        ("δάνεια_κάρτες", ["δανειο", "καρτα", "πιστωτικη"]),
        (
            "πιστωτική",
            [
                "πιστωτικη",
                "πιστωτικη καρτα",
                "eurobank",
            ],
        ),
        ("ενοίκιο", ["ενοικιο"]),
        ("κοινόχρηστα", ["κοινοχρηστα"]),
        ("ρεύμα", ["ρευμα", "ηλεκτρικο"]),
        ("αέριο", ["φυσικο αεριο", "αεριο"]),
        ("νερό", ["νερο", "δευα"]),
        (
            "κινητό_τηλέφωνο",
            ["κινητο τηλεφωνο", "κινητο"],
        ),
        (
            "σταθερό_τηλέφωνο",
            [
                "σταθερο τηλεφωνο",
                "internet",
                "ιντερνετ",
            ],
        ),
        ("εφορία", ["εφορια", "φοροσ"]),
        ("εφκα", ["εφκα"]),
        (
            "συνδρομές",
            [
                "συνδρομη",
                "συνδρομεσ",
                "netflix",
                "spotify",
                "youtube",
                "cloud",
            ],
        ),
        (
            "φαρμακείο",
            ["φαρμακειο", "φαρμακα"],
        ),
        ("γιατρός", ["γιατροσ", "ιατροσ"]),
        (
            "ασφάλεια_αυτοκινήτου",
            ["ασφαλεια αυτοκινητου"],
        ),
        (
            "τέλη_κυκλοφορίας",
            ["τελη κυκλοφοριασ"],
        ),
        (
            "έξοδα_αυτοκινήτου",
            [
                "αυτοκινητο",
                "service",
                "κτεο",
                "ελαστικα",
                "βενζινη",
            ],
        ),
    ]

    for field, terms in aliases:
        if any(term in combined for term in terms):
            return field

    return None


def monthly_budget_suggestions(
    recurring_dataframe,
    tasks_dataframe,
    year,
    month,
):
    """
    Προτάσεις του μήνα μόνο από ενεργά πάγια.
    Οι υποχρεώσεις και οι υπενθυμίσεις έχουν αφαιρεθεί προσωρινά.
    """
    fixed_amounts = {}
    extra_rows = []

    if recurring_dataframe.empty:
        return fixed_amounts, extra_rows

    active = recurring_dataframe[
        recurring_dataframe["ενεργό"] == "Ναι"
    ].copy()

    for _, row in active.iterrows():
        due_date = recurring_due_in_month(row, year, month)
        if due_date is None:
            continue

        description = str(row.get("όνομα", "")).strip()
        category = str(row.get("κατηγορία", "")).strip()
        item_type = str(row.get("τύπος", "Έξοδο")).strip() or "Έξοδο"
        amount = float(parse_number(row.get("ποσό", 0)))

        if amount <= 0:
            continue

        field = budget_fixed_field(description, category)

        if field:
            fixed_amounts[field] = fixed_amounts.get(field, 0.0) + amount
        else:
            extra_rows.append(
                {
                    "Περιγραφή": description or category,
                    "Κατηγορία": category,
                    "Τύπος": item_type,
                    "Ποσό": amount,
                    "Πάγιο": "Ναι",
                    "Συχνότητα": str(row.get("συχνότητα", "")),
                    "Ολοκληρώθηκε": "Όχι",
                    "Πηγή χρημάτων": "Υπόλοιπο μήνα",
                    "Σχετική κίνηση": "",
                    "Πηγή": "Πάγιο",
                    "Σημειώσεις": (
                        f"Επόμενη ημερομηνία: "
                        f"{due_date.strftime('%d/%m/%Y')}"
                    ),
                }
            )

    return fixed_amounts, extra_rows


def get_budget_items_for_month(items_df, year, month):
    if items_df.empty:
        return pd.DataFrame(
            columns=[
                "Περιγραφή",
                "Κατηγορία",
                "Ποσό",
                "Πηγή",
                "Σημειώσεις",
            ]
        )

    selected = items_df[
        (items_df["έτος"] == int(year))
        & (items_df["μήνας"] == int(month))
    ].copy()

    if selected.empty:
        return pd.DataFrame(
            columns=[
                "Περιγραφή",
                "Κατηγορία",
                "Ποσό",
                "Πηγή",
                "Σημειώσεις",
            ]
        )

    selected = selected.rename(
        columns={
            "περιγραφή": "Περιγραφή",
            "κατηγορία": "Κατηγορία",
            "τύπος": "Τύπος",
            "ποσό": "Ποσό",
            "πάγιο": "Πάγιο",
            "συχνότητα": "Συχνότητα",
            "ολοκληρώθηκε": "Ολοκληρώθηκε",
            "πηγή_χρημάτων": "Πηγή χρημάτων",
            "σχετική_κίνηση": "Σχετική κίνηση",
            "πηγή": "Πηγή",
            "σημειώσεις": "Σημειώσεις",
        }
    )

    return selected[
        [
            "Περιγραφή",
            "Κατηγορία",
            "Τύπος",
            "Ποσό",
            "Πάγιο",
            "Συχνότητα",
            "Ολοκληρώθηκε",
            "Πηγή χρημάτων",
            "Σχετική κίνηση",
            "Πηγή",
            "Σημειώσεις",
        ]
    ].reset_index(drop=True)


def save_budget_items(year, month, edited_items):
    all_values = get_all_values_with_retry(
        budget_items_ws,
        attempts=5,
    )

    if all_values:
        headers = all_values[0]
        year_col = headers.index("έτος")
        month_col = headers.index("μήνας")

        rows_to_delete = []
        for row_number, row in enumerate(all_values[1:], start=2):
            row_year = row[year_col] if year_col < len(row) else ""
            row_month = row[month_col] if month_col < len(row) else ""

            if (
                int(parse_number(row_year)) == int(year)
                and int(parse_number(row_month)) == int(month)
            ):
                rows_to_delete.append(row_number)

        for row_number in reversed(rows_to_delete):
            budget_items_ws.delete_rows(row_number)

    if edited_items is None or edited_items.empty:
        refresh_data()
        return

    headers = SHEET_SCHEMAS[BUDGET_ITEMS_SHEET]
    rows = []

    for _, row in edited_items.iterrows():
        description = str(row.get("Περιγραφή", "")).strip()
        amount = float(parse_number(row.get("Ποσό", 0)))

        if not description and amount <= 0:
            continue

        record = {
            "id": create_id("BITEM"),
            "έτος": int(year),
            "μήνας": int(month),
            "περιγραφή": description,
            "κατηγορία": str(row.get("Κατηγορία", "")).strip(),
            "τύπος": str(row.get("Τύπος", "Έξοδο")).strip() or "Έξοδο",
            "ποσό": amount,
            "πάγιο": str(row.get("Πάγιο", "Όχι")).strip() or "Όχι",
            "συχνότητα": str(row.get("Συχνότητα", "")).strip(),
            "ολοκληρώθηκε": str(
                row.get("Ολοκληρώθηκε", "Όχι")
            ).strip() or "Όχι",
            "πηγή_χρημάτων": str(
                row.get("Πηγή χρημάτων", "Υπόλοιπο μήνα")
            ).strip() or "Υπόλοιπο μήνα",
            "σχετική_κίνηση": str(
                row.get("Σχετική κίνηση", "")
            ).strip(),
            "πηγή": str(row.get("Πηγή", "Χειροκίνητη")).strip()
            or "Χειροκίνητη",
            "σημειώσεις": str(row.get("Σημειώσεις", "")).strip(),
            "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
        }
        rows.append([record.get(header, "") for header in headers])

    if rows:
        budget_items_ws.append_rows(
            rows,
            value_input_option="USER_ENTERED",
        )

    refresh_data()



def infer_recurring_item_type(name, category, raw_type=""):
    """
    Διορθώνει προφανείς λανθασμένους χαρακτηρισμούς παγίων.

    Ο μισθός και άλλα σαφή έσοδα είναι Έσοδο.
    Ενοίκιο, κοινόχρηστα, λογαριασμοί, δάνεια κ.λπ. είναι Έξοδο,
    ακόμη κι αν παλιότερη εγγραφή αποθηκεύτηκε κατά λάθος ως Έσοδο.
    """
    text = normalize_budget_text(f"{name} {category}")

    expense_terms = [
        "ενοικιο",
        "κοινοχρηστα",
        "ρευμα",
        "ηλεκτρικο",
        "αεριο",
        "νερο",
        "τηλεφων",
        "internet",
        "ιντερνετ",
        "δανειο",
        "πιστωτικ",
        "εφορια",
        "εφκα",
        "συνδρομ",
        "ασφαλεια",
        "φαρμακ",
        "γιατρο",
        "ιατρο",
        "αυτοκινητο",
        "τελη κυκλοφοριασ",
    ]
    income_terms = [
        "μισθοσ",
        "μισθοδοσια",
        "συνταξη",
        "επιδομα",
        "σταθερο εσοδο",
        "παγιο εσοδο",
        "ενοικιο που εισπραττω",
        "εσοδο απο ενοικιο",
    ]

    if any(term in text for term in expense_terms):
        return "Έξοδο"

    if any(term in text for term in income_terms):
        return "Έσοδο"

    raw_type = str(raw_type or "").strip()
    return raw_type if raw_type in {"Έσοδο", "Έξοδο"} else "Έξοδο"


def repair_recurring_records_in_memory(raw_df):
    """
    Κανονικοποιεί τύπο και ενεργή κατάσταση παλιών εγγραφών.
    Επιστρέφει το διορθωμένο DataFrame και αν χρειάζεται αποθήκευση.
    """
    if raw_df.empty:
        return raw_df.copy(), False

    result = raw_df.copy()
    changed = False

    for column, default in {
        "τύπος": "Έξοδο",
        "ενεργό": "Ναι",
    }.items():
        if column not in result.columns:
            result[column] = default
            changed = True

    for index, row in result.iterrows():
        corrected_type = infer_recurring_item_type(
            row.get("όνομα", ""),
            row.get("κατηγορία", ""),
            row.get("τύπος", ""),
        )
        current_type = str(row.get("τύπος", "")).strip()

        if current_type != corrected_type:
            result.at[index, "τύπος"] = corrected_type
            changed = True

        current_active = str(row.get("ενεργό", "")).strip()
        if current_active not in {"Ναι", "Όχι"}:
            result.at[index, "ενεργό"] = "Ναι"
            changed = True

    return result, changed


def persist_recurring_repairs(repaired_df):
    """Αποθηκεύει όλες τις διορθώσεις παγίων με ένα μόνο API request."""
    if repaired_df.empty:
        return True

    headers = SHEET_SCHEMAS[RECURRING_SHEET]
    rows = []

    for _, row in repaired_df.iterrows():
        rows.append([
            "" if pd.isna(row.get(header, "")) else row.get(header, "")
            for header in headers
        ])

    try:
        recurring_ws.update(
            range_name=f"A1:{gspread.utils.rowcol_to_a1(len(rows) + 1, len(headers))}",
            values=[headers] + rows,
            value_input_option="USER_ENTERED",
        )
        return True
    except gspread.exceptions.APIError:
        st.warning(
            "Οι τύποι των παγίων διορθώθηκαν στην εμφάνιση, αλλά η Google "
            "δεν απάντησε προσωρινά για να αποθηκευτούν οι διορθώσεις."
        )
        return False


def restore_missing_budget_recurring(
    recurring_dataframe,
    status_dataframe,
    monthly_budget_dataframe,
):
    """
    Επαναφέρει πάγια που υπάρχουν στην κατάσταση προϋπολογισμού αλλά
    λείπουν από το φύλλο Πάγια και Συνδρομές.
    """
    if status_dataframe.empty:
        return recurring_dataframe

    existing_ids = set(
        recurring_dataframe.get("id", pd.Series(dtype=str))
        .astype(str)
        .str.strip()
        .tolist()
    )
    existing_signatures = set()

    if not recurring_dataframe.empty:
        for _, row in recurring_dataframe.iterrows():
            existing_signatures.add(
                (
                    normalize_budget_text(row.get("όνομα", "")),
                    infer_recurring_item_type(
                        row.get("όνομα", ""),
                        row.get("κατηγορία", ""),
                        row.get("τύπος", ""),
                    ),
                    str(row.get("συχνότητα", "")).strip(),
                )
            )

    rows_to_add = []

    for _, status in status_dataframe.iterrows():
        if str(status.get("πάγιο", "Όχι")).strip() != "Ναι":
            continue

        year = int(parse_number(status.get("έτος", 0)))
        month = int(parse_number(status.get("μήνας", 0)))
        field_code = str(status.get("κωδικός_πεδίου", "")).strip()
        name = str(status.get("περιγραφή", "")).strip()
        item_type = infer_recurring_item_type(
            name,
            "",
            status.get("τύπος", ""),
        )
        frequency = str(status.get("συχνότητα", "")).strip() or "Κάθε μήνα"
        linked_id = str(status.get("σχετικό_πάγιο", "")).strip()

        signature = (
            normalize_budget_text(name),
            item_type,
            frequency,
        )

        if linked_id in existing_ids or signature in existing_signatures:
            continue

        budget_record = get_monthly_budget_record(
            monthly_budget_dataframe,
            year,
            month,
        )
        amount = float(parse_number(budget_record.get(field_code, 0)))

        if amount <= 0 or not name or year <= 0 or not 1 <= month <= 12:
            continue

        recurring_id = linked_id or create_id("REC")
        first_due = date(year, month, 1)

        rows_to_add.append(
            {
                "id": recurring_id,
                "όνομα": name,
                "κατηγορία": (
                    "Έσοδα" if item_type == "Έσοδο" else "Προϋπολογισμός"
                ),
                "τύπος": item_type,
                "ποσό": amount,
                "συχνότητα": frequency,
                "τελευταία_πληρωμή": "",
                "επόμενη_χρέωση": first_due.isoformat(),
                "rf": "",
                "τρόπος_πληρωμής": "Δεν ορίστηκε",
                "ενεργό": "Ναι",
                "υπενθύμιση_ημέρες": 3,
                "σημειώσεις": (
                    "Επαναφέρθηκε από αποθηκευμένο μηνιαίο προϋπολογισμό."
                ),
                "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
            }
        )
        existing_ids.add(recurring_id)
        existing_signatures.add(signature)

    if not rows_to_add:
        return recurring_dataframe

    headers = SHEET_SCHEMAS[RECURRING_SHEET]
    values = [
        [record.get(header, "") for header in headers]
        for record in rows_to_add
    ]

    try:
        recurring_ws.append_rows(
            values,
            value_input_option="USER_ENTERED",
        )
    except gspread.exceptions.APIError:
        st.warning(
            "Βρέθηκαν πάγια από παλιούς προϋπολογισμούς, αλλά η Google "
            "δεν απάντησε προσωρινά για να επανέλθουν στην καρτέλα."
        )

    added_df = pd.DataFrame(rows_to_add)
    return pd.concat(
        [recurring_dataframe, added_df],
        ignore_index=True,
        sort=False,
    )



MONTH_NAMES_FULL = {
    1: "Ιανουάριος",
    2: "Φεβρουάριος",
    3: "Μάρτιος",
    4: "Απρίλιος",
    5: "Μάιος",
    6: "Ιούνιος",
    7: "Ιούλιος",
    8: "Αύγουστος",
    9: "Σεπτέμβριος",
    10: "Οκτώβριος",
    11: "Νοέμβριος",
    12: "Δεκέμβριος",
}


def month_start_date(year, month):
    return date(int(year), int(month), 1)


def month_year_text(value):
    if pd.isna(value) or value in ("", None):
        return ""
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return ""
    return f"{MONTH_NAMES_FULL[int(parsed.month)]} {int(parsed.year)}"


def append_budget_item_if_missing(
    year,
    month,
    description,
    category,
    item_type,
    amount,
    source="Πάγιο",
    notes="",
):
    existing = prepare_budget_items(
        load_records(BUDGET_ITEMS_SHEET)
    )
    normalized_description = normalize_budget_text(description)

    if not existing.empty:
        same = existing[
            (existing["έτος"] == int(year))
            & (existing["μήνας"] == int(month))
            & (
                existing["περιγραφή"]
                .astype(str)
                .apply(normalize_budget_text)
                == normalized_description
            )
            & (existing["τύπος"].astype(str) == str(item_type))
        ]
        if not same.empty:
            record_id = str(same.iloc[-1]["id"])
            update_record_fields(
                budget_items_ws,
                record_id,
                {
                    "κατηγορία": category,
                    "ποσό": float(amount),
                    "πάγιο": "Ναι",
                    "πηγή": source,
                    "σημειώσεις": notes,
                    "ενημερώθηκε": datetime.now().isoformat(
                        timespec="seconds"
                    ),
                },
            )
            return record_id

    record = {
        "id": create_id("BITEM"),
        "έτος": int(year),
        "μήνας": int(month),
        "περιγραφή": description,
        "κατηγορία": category,
        "τύπος": item_type,
        "ποσό": float(amount),
        "πάγιο": "Ναι",
        "συχνότητα": "",
        "ολοκληρώθηκε": "Όχι",
        "πηγή_χρημάτων": "Υπόλοιπο μήνα",
        "σχετική_κίνηση": "",
        "πηγή": source,
        "σημειώσεις": notes,
        "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
    }
    append_generic_record(
        budget_items_ws,
        BUDGET_ITEMS_SHEET,
        record,
    )
    return record["id"]


def append_generic_debt(
    name,
    debt_kind,
    creditor,
    initial_amount,
    default_installment=0.0,
    annual_rate=0.0,
    total_installments=0,
    first_due=None,
    rate_type="Χωρίς επιτόκιο",
    notes="",
):
    record = {
        "id": create_id("DEBT"),
        "όνομα": name,
        "είδος": debt_kind,
        "πιστωτής": creditor,
        "αρχικό_ποσό": float(initial_amount),
        "προεπιλεγμένη_δόση": float(default_installment),
        "ετήσιο_επιτόκιο": float(annual_rate),
        "συνολικές_δόσεις": int(total_installments),
        "ημερομηνία_πρώτης_δόσης": (
            first_due.isoformat() if first_due else ""
        ),
        "τύπος_επιτοκίου": rate_type,
        "ενεργό": "Ναι",
        "σημειώσεις": notes,
        "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
    }
    append_generic_record(
        debts_ws,
        DEBTS_SHEET,
        record,
    )
    return record["id"]


def prepare_recurring(df):
    if df.empty:
        return pd.DataFrame(columns=SHEET_SCHEMAS[RECURRING_SHEET])

    result = df.copy()

    for column, default in {
        "id": "",
        "όνομα": "",
        "κατηγορία": "",
        "τύπος": "Έξοδο",
        "ποσό": 0.0,
        "συχνότητα": "Κάθε μήνα",
        "τελευταία_πληρωμή": "",
        "επόμενη_χρέωση": "",
        "rf": "",
        "τρόπος_πληρωμής": "",
        "ενεργό": "Ναι",
        "υπενθύμιση_ημέρες": 0,
        "σημειώσεις": "",
        "ενημερώθηκε": "",
    }.items():
        if column not in result.columns:
            result[column] = default

    result["τύπος"] = result.apply(
        lambda row: infer_recurring_item_type(
            row.get("όνομα", ""),
            row.get("κατηγορία", ""),
            row.get("τύπος", ""),
        ),
        axis=1,
    )
    result["ενεργό"] = result["ενεργό"].apply(
        lambda value: (
            str(value).strip()
            if str(value).strip() in {"Ναι", "Όχι"}
            else "Ναι"
        )
    )
    result["συχνότητα"] = result["συχνότητα"].replace(
        "",
        "Κάθε μήνα",
    )
    result["ποσό"] = result["ποσό"].apply(parse_number)
    result["υπενθύμιση_ημέρες"] = result[
        "υπενθύμιση_ημέρες"
    ].apply(parse_number)

    for column in ["τελευταία_πληρωμή", "επόμενη_χρέωση"]:
        result[column] = pd.to_datetime(
            result[column],
            errors="coerce",
        )

    return result




def prepare_documents(df):
    if df.empty:
        return df.copy()
    result = df.copy()
    result["ποσό"] = result.get("ποσό", 0).apply(parse_number)
    for column in ["ημερομηνία_αγοράς", "ημερομηνία_λήξης"]:
        result[column] = pd.to_datetime(
            result.get(column),
            errors="coerce",
        )
    return result




def append_generic_record(worksheet, sheet_name, record):
    headers = SHEET_SCHEMAS[sheet_name]
    worksheet.append_row(
        [record.get(header, "") for header in headers],
        value_input_option="USER_ENTERED",
    )
    refresh_data()




def add_frequency(base_date, frequency):
    months = {
        "Κάθε μήνα": 1,
        "Κάθε 2 μήνες": 2,
        "Κάθε 3 μήνες": 3,
        "Κάθε 6 μήνες": 6,
        "Κάθε χρόνο": 12,
    }.get(frequency, 1)
    return base_date + relativedelta(months=months)


def append_recurring(
    name,
    category,
    item_type,
    amount,
    frequency,
    last_paid,
    payment_method,
    reminder_days,
    notes="",
    rf="",
):
    next_charge = add_frequency(last_paid, frequency)
    append_generic_record(
        recurring_ws,
        RECURRING_SHEET,
        {
            "id": create_id("REC"),
            "όνομα": name,
            "κατηγορία": category,
            "τύπος": item_type,
            "ποσό": float(amount),
            "συχνότητα": frequency,
            "τελευταία_πληρωμή": last_paid.isoformat(),
            "επόμενη_χρέωση": next_charge.isoformat(),
            "rf": rf.strip(),
            "τρόπος_πληρωμής": payment_method,
            "ενεργό": "Ναι",
            "υπενθύμιση_ημέρες": int(reminder_days),
            "σημειώσεις": notes,
            "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
        },
    )




def append_document(
    title,
    document_type,
    category,
    purchase_date,
    expiry_date,
    amount,
    provider,
    file_link,
    notes="",
):
    append_generic_record(
        documents_ws,
        DOCUMENTS_SHEET,
        {
            "id": create_id("DOC"),
            "τίτλος": title,
            "τύπος": document_type,
            "κατηγορία": category,
            "ημερομηνία_αγοράς": purchase_date.isoformat(),
            "ημερομηνία_λήξης": expiry_date.isoformat(),
            "ποσό": float(amount),
            "φορέας": provider,
            "αρχείο": file_link,
            "κατάσταση": "Ενεργό",
            "σημειώσεις": notes,
            "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
        },
    )


def monthly_equivalent(amount, frequency):
    factor = {
        "Κάθε μήνα": 1,
        "Κάθε 2 μήνες": 1 / 2,
        "Κάθε 3 μήνες": 1 / 3,
        "Κάθε 6 μήνες": 1 / 6,
        "Κάθε χρόνο": 1 / 12,
    }.get(frequency, 0)
    return float(amount) * factor







def prepare_savings(df):
    if df.empty:
        return df.copy()

    result = df.copy()
    result["ημερομηνία"] = pd.to_datetime(
        result.get("ημερομηνία"),
        errors="coerce",
    )
    result["έτος"] = result.get("έτος", 0).apply(parse_number)
    result["μήνας"] = result.get("μήνας", 0).apply(parse_number)
    result["ποσό"] = result.get("ποσό", 0).apply(parse_number)
    return result


def savings_total(dataframe):
    if dataframe.empty:
        return 0.0

    deposits = dataframe.loc[
        dataframe["τύπος"] == "Κατάθεση",
        "ποσό",
    ].sum()
    withdrawals = dataframe.loc[
        dataframe["τύπος"] == "Ανάληψη",
        "ποσό",
    ].sum()
    return float(deposits - withdrawals)


def append_savings_entry(
    entry_date,
    entry_type,
    amount,
    related_transaction_id="",
    notes="",
):
    savings_id = create_id("SAVE")
    savings_ws.append_row(
        [
            savings_id,
            entry_date.isoformat(),
            entry_date.year,
            entry_date.month,
            entry_type,
            float(amount),
            related_transaction_id,
            notes,
            datetime.now().isoformat(timespec="seconds"),
        ],
        value_input_option="USER_ENTERED",
    )
    refresh_data()
    return savings_id


def link_transaction_to_savings(transaction_id, savings_id):
    return update_record_fields(
        transactions_ws,
        transaction_id,
        {"σχετική_αποταμίευση": savings_id},
    )


def append_savings_deposit(deposit_date, amount, notes=""):
    amount = float(amount)
    transaction_id = append_transaction(
        transaction_date=deposit_date,
        transaction_type="Έξοδο",
        category="Αποταμίευση",
        description="Μεταφορά στην αποταμίευση",
        amount=amount,
        payment_method="Μεταφορά",
        recurring=False,
        money_source="Υπόλοιπο μήνα",
        notes=notes,
    )
    savings_id = append_savings_entry(
        deposit_date,
        "Κατάθεση",
        amount,
        related_transaction_id=transaction_id,
        notes=notes,
    )
    link_transaction_to_savings(transaction_id, savings_id)
    return transaction_id


def append_savings_withdrawal(
    withdrawal_date,
    amount,
    transaction_type,
    category,
    description,
    payment_method="",
    recurring=False,
    file_link="",
    notes="",
    reference_year=None,
    reference_month=None,
    activity="Γενικά",
):
    amount = float(amount)
    current_total = savings_total(
        prepare_savings(load_records(SAVINGS_SHEET))
    )
    if amount <= 0 or amount > current_total + 0.005:
        return ""

    transaction_id = append_transaction(
        transaction_date=withdrawal_date,
        transaction_type=transaction_type,
        category=category,
        description=description,
        amount=amount,
        payment_method=payment_method,
        recurring=recurring,
        money_source="Αποταμίευση",
        file_link=file_link,
        notes=notes,
        reference_year=reference_year,
        reference_month=reference_month,
        activity=activity,
    )
    savings_id = append_savings_entry(
        withdrawal_date,
        "Ανάληψη",
        amount,
        related_transaction_id=transaction_id,
        notes=(f"{transaction_type}: {description}. {notes}").strip(),
    )
    link_transaction_to_savings(transaction_id, savings_id)
    return transaction_id


def find_record_by_id(worksheet, record_id):
    values = get_all_values_with_retry(worksheet, attempts=3)
    if not values or "id" not in values[0]:
        return None
    headers = values[0]
    id_index = headers.index("id")
    for row in values[1:]:
        current_id = row[id_index] if id_index < len(row) else ""
        if str(current_id) == str(record_id):
            padded = row + [""] * max(0, len(headers) - len(row))
            return dict(zip(headers, padded[:len(headers)]))
    return None


def find_savings_by_transaction(transaction_id):
    values = get_all_values_with_retry(savings_ws, attempts=3)
    if not values or "σχετική_κίνηση" not in values[0]:
        return None
    headers = values[0]
    tx_index = headers.index("σχετική_κίνηση")
    for row in values[1:]:
        current = row[tx_index] if tx_index < len(row) else ""
        if str(current) == str(transaction_id):
            padded = row + [""] * max(0, len(headers) - len(row))
            return dict(zip(headers, padded[:len(headers)]))
    return None


def find_records_by_field(worksheet, field_name, field_value):
    values = get_all_values_with_retry(worksheet, attempts=3)
    if not values or field_name not in values[0]:
        return []
    headers = values[0]
    idx = headers.index(field_name)
    found = []
    for row in values[1:]:
        current = row[idx] if idx < len(row) else ""
        if str(current).strip() == str(field_value).strip():
            padded = row + [""] * max(0, len(headers) - len(row))
            found.append(dict(zip(headers, padded[:len(headers)])))
    return found


def find_transactions_for_task(task_id):
    values = get_all_values_with_retry(transactions_ws, attempts=3)
    if not values or "σημειώσεις" not in values[0]:
        return []
    headers = values[0]
    idx = headers.index("σημειώσεις")
    marker = f"Πληρωμή υποχρέωσης {task_id}."
    found = []
    for row in values[1:]:
        notes = row[idx] if idx < len(row) else ""
        if marker in str(notes):
            padded = row + [""] * max(0, len(headers) - len(row))
            found.append(dict(zip(headers, padded[:len(headers)])))
    return found


def delete_debt_movement_completely(movement_id, delete_transaction=True):
    movement = find_record_by_id(debt_movements_ws, movement_id)
    if not movement:
        return False
    transaction_id = str(movement.get("σχετική_κίνηση", "")).strip()
    deleted = delete_record_by_id(debt_movements_ws, movement_id)
    if deleted and delete_transaction and transaction_id:
        delete_transaction_completely(transaction_id, False)
    refresh_data()
    return deleted


def delete_transaction_completely(transaction_id, delete_debt_movements=True):
    transaction = find_record_by_id(transactions_ws, transaction_id)
    if not transaction:
        return False

    clear_budget_completion_by_transaction(transaction_id)

    if delete_debt_movements:
        for movement in find_records_by_field(
            debt_movements_ws, "σχετική_κίνηση", transaction_id
        ):
            movement_id = str(movement.get("id", "")).strip()
            if movement_id:
                delete_debt_movement_completely(movement_id, False)

    linked_savings_ids = {
        str(item.get("id", "")).strip()
        for item in find_records_by_field(
            savings_ws, "σχετική_κίνηση", transaction_id
        )
        if str(item.get("id", "")).strip()
    }
    direct_savings_id = str(
        transaction.get("σχετική_αποταμίευση", "")
    ).strip()
    if direct_savings_id:
        linked_savings_ids.add(direct_savings_id)

    deleted = delete_record_by_id(transactions_ws, transaction_id)
    if deleted:
        for savings_id in linked_savings_ids:
            delete_record_by_id(savings_ws, savings_id)

    refresh_data()
    return deleted


def delete_savings_completely(savings_id):
    savings_record = find_record_by_id(savings_ws, savings_id)
    if not savings_record:
        return False
    transaction_id = str(
        savings_record.get("σχετική_κίνηση", "")
    ).strip()
    if transaction_id:
        return delete_transaction_completely(transaction_id)
    return delete_record_by_id(savings_ws, savings_id)


def delete_task_completely(task_id):
    if not find_record_by_id(tasks_ws, task_id):
        return False
    for transaction in find_transactions_for_task(task_id):
        transaction_id = str(transaction.get("id", "")).strip()
        if transaction_id:
            delete_transaction_completely(transaction_id)
    deleted = delete_record_by_id(tasks_ws, task_id)
    refresh_data()
    return deleted


def delete_debt_completely(debt_id):
    if not find_record_by_id(debts_ws, debt_id):
        return False
    for movement in find_records_by_field(
        debt_movements_ws, "debt_id", debt_id
    ):
        movement_id = str(movement.get("id", "")).strip()
        if movement_id:
            delete_debt_movement_completely(movement_id)
    deleted = delete_record_by_id(debts_ws, debt_id)
    refresh_data()
    return deleted


def delete_savings_with_counterpart(savings_id):
    return delete_savings_completely(savings_id)


def delete_transaction_with_counterpart(transaction_id):
    return delete_transaction_completely(transaction_id)


def month_transaction_balance(dataframe, year, month):
    if dataframe.empty:
        return 0.0

    selected = dataframe[
        (dataframe["έτος_αναφοράς"] == int(year))
        & (dataframe["μήνας_αναφοράς"] == int(month))
    ].copy()

    income = selected.loc[
        selected["τύπος"] == "Έσοδο",
        "ποσό",
    ].sum()
    expenses_from_balance = selected.loc[
        (selected["τύπος"] == "Έξοδο")
        & (selected["πηγή_χρημάτων"] != "Αποταμίευση"),
        "ποσό",
    ].sum()

    return float(income - expenses_from_balance)




def hidden_custom_options(context):
    """Βασικές επιλογές που ο χρήστης έχει επιλέξει να κρύψει."""
    hidden_context = f"__hidden__::{context}"
    if custom_options_df.empty:
        return []

    matches = custom_options_df[
        custom_options_df["πλαίσιο"].astype(str) == hidden_context
    ]
    return [
        str(value).strip()
        for value in matches.get("τιμή", pd.Series(dtype=str)).tolist()
        if str(value).strip()
    ]


def option_usage_details(context, value):
    """
    Επιστρέφει πόσες ιστορικές εγγραφές χρησιμοποιούν την επιλογή.
    Η διαγραφή της επιλογής από το interface δεν αλλάζει τις εγγραφές.
    """
    cleaned = str(value).strip()
    count = 0
    amount = 0.0

    def match_rows(df, column):
        if df is None or df.empty or column not in df.columns:
            return pd.DataFrame()
        return df[df[column].astype(str).str.strip() == cleaned]

    if context.startswith("transaction_category_"):
        tx = match_rows(transactions_df, "κατηγορία")
        count += len(tx)
        if "ποσό" in tx.columns:
            amount += tx["ποσό"].apply(parse_number).sum()
        count += len(match_rows(tasks_df, "κατηγορία"))
        count += len(match_rows(recurring_df, "κατηγορία"))
        count += len(match_rows(budget_items_df, "κατηγορία"))
    elif context.startswith("transaction_description_"):
        tx = match_rows(transactions_df, "περιγραφή")
        count += len(tx)
        if "ποσό" in tx.columns:
            amount += tx["ποσό"].apply(parse_number).sum()
        count += len(match_rows(tasks_df, "τίτλος"))
        count += len(match_rows(recurring_df, "όνομα"))
        count += len(match_rows(budget_items_df, "περιγραφή"))
    elif context == "recurring_category":
        rows = match_rows(recurring_df, "κατηγορία")
        count += len(rows)
        if "ποσό" in rows.columns:
            amount += rows["ποσό"].apply(parse_number).sum()
    elif context in {"payment_method", "recurring_payment"}:
        tx = match_rows(transactions_df, "τρόπος_πληρωμής")
        count += len(tx)
        if "ποσό" in tx.columns:
            amount += tx["ποσό"].apply(parse_number).sum()
        count += len(match_rows(recurring_df, "τρόπος_πληρωμής"))
    elif context == "reminder_category":
        count += len(match_rows(reminders_df, "κατηγορία"))

    return {"count": int(count), "amount": float(amount)}


def find_custom_option_record(context, value):
    if custom_options_df.empty:
        return {}
    matches = custom_options_df[
        (custom_options_df["πλαίσιο"].astype(str) == str(context))
        & (
            custom_options_df["τιμή"].astype(str).str.casefold()
            == str(value).strip().casefold()
        )
    ]
    return matches.iloc[-1].to_dict() if not matches.empty else {}


def remove_option_from_interface(context, value, is_base_option=False):
    """
    Αφαιρεί μια επιλογή μόνο από το interface.
    Οι παλιές κινήσεις και τα ποσά τους παραμένουν αναλλοίωτα.
    """
    cleaned = str(value).strip()
    if not cleaned:
        return False

    if is_base_option:
        hidden_context = f"__hidden__::{context}"
        if cleaned.casefold() in [
            item.casefold() for item in saved_custom_options(hidden_context)
        ]:
            return True
        return save_custom_option(hidden_context, cleaned)

    record = find_custom_option_record(context, cleaned)
    if not record:
        return False
    return delete_record_by_id(custom_options_ws, record["id"])


def restore_hidden_option(context, value):
    hidden_context = f"__hidden__::{context}"
    record = find_custom_option_record(hidden_context, value)
    if not record:
        return False
    return delete_record_by_id(custom_options_ws, record["id"])


def base_options_for_context(context):
    if context == "transaction_category_Έξοδο":
        return list(EXPENSE_CATEGORIES.keys())
    if context == "transaction_category_Έσοδο":
        return list(INCOME_CATEGORIES.keys())
    if context == "payment_method":
        return list(PAYMENT_METHODS)
    if context == "recurring_category":
        return [
            "Σπίτι", "Τηλέφωνο / Internet", "Streaming",
            "Ασφάλεια", "Υγεία", "Αυτοκίνητο", "Λογισμικό", "Έσοδα",
        ]
    if context.startswith("transaction_description_Έξοδο_"):
        category = context.split("transaction_description_Έξοδο_", 1)[1]
        return list(EXPENSE_CATEGORIES.get(category, []))
    if context.startswith("transaction_description_Έσοδο_"):
        category = context.split("transaction_description_Έσοδο_", 1)[1]
        return list(INCOME_CATEGORIES.get(category, []))
    return []


def saved_custom_options(context):
    """Επιστρέφει τις ενεργές προσωπικές επιλογές ενός πεδίου."""
    if custom_options_df.empty:
        return []

    matches = custom_options_df[
        custom_options_df["πλαίσιο"].astype(str) == str(context)
    ]
    hidden = {
        item.casefold()
        for item in hidden_custom_options(context)
    }
    values = []
    for value in matches.get("τιμή", pd.Series(dtype=str)).tolist():
        cleaned = str(value).strip()
        if (
            cleaned
            and cleaned.casefold() not in hidden
            and cleaned not in values
        ):
            values.append(cleaned)
    return values


def parse_permanent_budget_line(value):
    """Μετατρέπει την αποθηκευμένη μόνιμη γραμμή σε λεξικό."""
    parts = str(value).split("|||", 2)
    if len(parts) != 3:
        return {}
    item_type, label, category = [part.strip() for part in parts]
    if item_type not in {"Έσοδο", "Έξοδο"} or not label:
        return {}
    return {
        "type": item_type,
        "label": label,
        "category": category or ("Άλλα έσοδα" if item_type == "Έσοδο" else "Άλλο έξοδο"),
    }


def permanent_budget_lines():
    """Επιστρέφει τις προσωπικές μόνιμες γραμμές προϋπολογισμού."""
    result = []
    seen = set()
    for raw_value in saved_custom_options("budget_permanent_line"):
        parsed = parse_permanent_budget_line(raw_value)
        if not parsed:
            continue
        signature = (
            parsed["type"],
            parsed["label"].casefold(),
            parsed["category"].casefold(),
        )
        if signature not in seen:
            seen.add(signature)
            result.append(parsed)
    return result


def save_permanent_budget_line(item_type, label, category):
    cleaned_label = str(label).strip()
    cleaned_category = str(category).strip()
    if not cleaned_label:
        return False
    encoded = f"{item_type}|||{cleaned_label}|||{cleaned_category}"
    return save_custom_option("budget_permanent_line", encoded)


def options_with_saved(base_options, context, include_other=True):
    """Συνδυάζει βασικές και προσωπικές επιλογές χωρίς διπλότυπα."""
    result = []
    hidden = {item.casefold() for item in hidden_custom_options(context)}
    for value in list(base_options) + saved_custom_options(context):
        cleaned = str(value).strip()
        if cleaned and cleaned.casefold() not in hidden and cleaned not in ["Άλλο", CUSTOM_OPTION] and cleaned not in result:
            result.append(cleaned)
    if include_other:
        result.append("Άλλο")
    return result


def save_custom_option(context, value):
    """Αποθηκεύει μία νέα προσωπική επιλογή, μόνο αν δεν υπάρχει ήδη."""
    cleaned = str(value).strip()
    if not cleaned or cleaned in ["Άλλο", CUSTOM_OPTION]:
        return False

    existing = [item.casefold() for item in saved_custom_options(context)]
    if cleaned.casefold() in existing:
        return False

    custom_options_ws.append_row(
        [
            create_id("OPT"),
            str(context),
            cleaned,
            datetime.now().isoformat(timespec="seconds"),
        ],
        value_input_option="USER_ENTERED",
    )
    refresh_data()
    return True




def render_debt_buttons(debts_dataframe, state_key, columns=2):
    """Εμφανίζει κάθε δάνειο ή κάρτα ως ξεχωριστό κουμπί."""
    if debts_dataframe.empty:
        return ""

    debt_names = debts_dataframe["όνομα"].astype(str).tolist()

    if (
        state_key not in st.session_state
        or st.session_state[state_key] not in debt_names
    ):
        st.session_state[state_key] = debt_names[0]

    selected_name = st.session_state[state_key]
    safe_columns = max(1, min(int(columns), len(debt_names)))

    for row_start in range(0, len(debt_names), safe_columns):
        row_names = debt_names[row_start:row_start + safe_columns]
        row_columns = st.columns(len(row_names))

        for position, debt_name in enumerate(row_names):
            matching = debts_dataframe[
                debts_dataframe["όνομα"].astype(str) == debt_name
            ]
            debt_kind = (
                str(matching.iloc[-1].get("είδος", "Δάνειο"))
                if not matching.empty
                else "Δάνειο"
            )
            icon = "💳" if "κάρτα" in debt_kind.lower() else "🏦"

            with row_columns[position]:
                if st.button(
                    f"{icon} {debt_name}",
                    key=f"{state_key}_{row_start + position}",
                    use_container_width=True,
                    type=(
                        "primary"
                        if selected_name == debt_name
                        else "secondary"
                    ),
                ):
                    st.session_state[state_key] = debt_name
                    selected_name = debt_name
                    st.rerun()

    return selected_name


def button_choice_with_persistent_add(
    label,
    base_options,
    context,
    key,
    add_label="Προσθήκη",
    placeholder="Γράψε νέα επιλογή",
    columns=3,
):
    """
    Mobile-friendly επιλογή με κουμπιά.

    Όλες οι βασικές και οι προσωπικές επιλογές εμφανίζονται ως
    κανονικά κουμπιά. Μόνο η προσθήκη νέας επιλογής ανοίγει μικρό
    popover με πεδίο κειμένου.
    """
    choices = []
    hidden = {item.casefold() for item in hidden_custom_options(context)}
    for value in list(base_options) + saved_custom_options(context):
        cleaned = str(value).strip()
        if cleaned and cleaned.casefold() not in hidden and cleaned not in choices:
            choices.append(cleaned)

    if key not in st.session_state:
        st.session_state[key] = choices[0] if choices else ""

    selected = st.session_state.get(key, "")
    safe_columns = max(1, min(int(columns), len(choices) or 1))

    st.markdown(f"#### {label}")

    for row_start in range(0, len(choices), safe_columns):
        row_options = choices[row_start:row_start + safe_columns]
        row_columns = st.columns(len(row_options))

        for row_position, option in enumerate(row_options):
            with row_columns[row_position]:
                if st.button(
                    option,
                    key=f"{key}_option_{row_start + row_position}",
                    use_container_width=True,
                    type="primary" if selected == option else "secondary",
                ):
                    st.session_state[key] = option
                    selected = option
                    st.rerun()

    with st.popover(
        f"＋ {add_label}",
        use_container_width=True,
    ):
        new_value = st.text_input(
            "Νέα επιλογή",
            placeholder=placeholder,
            key=f"{key}_new_value",
            label_visibility="collapsed",
        )
        add_clicked = st.button(
            "Αποθήκευση",
            key=f"{key}_save_new",
            use_container_width=True,
            type="primary",
        )
        if add_clicked:
            if not str(new_value).strip():
                st.warning("Γράψε πρώτα μία επιλογή.")
            elif save_custom_option(context, new_value):
                st.session_state[key] = str(new_value).strip()
                st.success("Η επιλογή αποθηκεύτηκε.")
                st.rerun()
            else:
                st.info("Η επιλογή υπάρχει ήδη.")

    return st.session_state.get(key, selected)



def render_choice_buttons(
    label,
    options,
    state_key,
    columns=2,
):
    """
    Εμφανίζει επιλογές σαν κουμπιά με σωστή σειρά και στο κινητό.

    Οι επιλογές δημιουργούνται ανά οριζόντια σειρά. Έτσι, όταν οι
    στήλες στοιβάζονται σε μικρή οθόνη, η σειρά παραμένει:
    1, 2, 3, 4 και όχι 1, 5, 9, 2, 6, 10.
    """
    st.markdown(f"#### {label}")

    if state_key not in st.session_state:
        st.session_state[state_key] = ""

    selected = st.session_state[state_key]
    safe_columns = max(1, min(int(columns), len(options) or 1))

    for row_start in range(0, len(options), safe_columns):
        row_options = options[row_start:row_start + safe_columns]
        row_columns = st.columns(len(row_options))

        for row_position, option in enumerate(row_options):
            index = row_start + row_position

            with row_columns[row_position]:
                is_selected = selected == option
                button_type = "primary" if is_selected else "secondary"

                if st.button(
                    option,
                    key=f"{state_key}_{index}",
                    use_container_width=True,
                    type=button_type,
                ):
                    st.session_state[state_key] = option
                    selected = option
                    st.rerun()

    return selected




def clean_export_dataframe(dataframe):
    """Καθαρίζει DataFrame για ασφαλή εξαγωγή."""
    if dataframe is None:
        return pd.DataFrame()

    result = dataframe.copy()

    for column in result.columns:
        if pd.api.types.is_datetime64_any_dtype(result[column]):
            result[column] = result[column].dt.strftime("%d/%m/%Y")
        else:
            result[column] = result[column].apply(
                lambda value: (
                    value.strftime("%d/%m/%Y")
                    if isinstance(value, (date, datetime))
                    else value
                )
            )

    return result.fillna("")


def make_excel_export(sheets):
    """Δημιουργεί κανονικό αρχείο Excel με ένα ή περισσότερα φύλλα."""
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#2E2205",
                "bg_color": "#F3C856",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )
        money_format = workbook.add_format({"num_format": '#,##0.00 "€"'})
        date_format = workbook.add_format({"num_format": "dd/mm/yyyy"})

        for raw_name, dataframe in sheets.items():
            sheet_name = str(raw_name)[:31] or "Δεδομένα"
            export_df = clean_export_dataframe(dataframe)
            export_df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
                startrow=1,
            )

            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(2, 0)
            worksheet.autofilter(
                1,
                0,
                max(len(export_df), 1),
                max(len(export_df.columns) - 1, 0),
            )

            worksheet.merge_range(
                0,
                0,
                0,
                max(len(export_df.columns) - 1, 0),
                sheet_name,
                workbook.add_format(
                    {
                        "bold": True,
                        "font_size": 15,
                        "font_color": "#2E2205",
                        "bg_color": "#FFF4C7",
                        "align": "left",
                        "valign": "vcenter",
                    }
                ),
            )
            worksheet.set_row(0, 26)
            worksheet.set_row(1, 24)

            for column_index, column_name in enumerate(export_df.columns):
                worksheet.write(1, column_index, column_name, header_format)

                values = export_df[column_name].astype(str).tolist()
                max_length = max(
                    [len(str(column_name))] + [len(value) for value in values[:300]]
                )
                width = min(max(max_length + 2, 12), 38)
                worksheet.set_column(
                    column_index,
                    column_index,
                    width,
                )

                lower_name = str(column_name).lower()
                if any(
                    term in lower_name
                    for term in [
                        "ποσό",
                        "έσοδα",
                        "έξοδα",
                        "υπόλοιπο",
                        "δόση",
                        "κεφάλαιο",
                        "τόκος",
                    ]
                ):
                    worksheet.set_column(
                        column_index,
                        column_index,
                        width,
                        money_format,
                    )
                elif any(
                    term in lower_name
                    for term in [
                        "ημερομηνία",
                        "προθεσμία",
                        "λήξη",
                        "χρέωση",
                        "κλείστηκε",
                        "ενημερώθηκε",
                    ]
                ):
                    worksheet.set_column(
                        column_index,
                        column_index,
                        width,
                        date_format,
                    )

            if export_df.empty:
                worksheet.write(2, 0, "Δεν υπάρχουν δεδομένα.")

    output.seek(0)
    return output.getvalue()






def render_export_buttons(title, sheets, filename_prefix, key_prefix):
    """Εμφανίζει μία καθαρή εξαγωγή σε Excel."""
    valid_sheets = {
        str(name): (
            dataframe if isinstance(dataframe, pd.DataFrame)
            else pd.DataFrame(dataframe)
        )
        for name, dataframe in sheets.items()
    }

    st.markdown("#### Εξαγωγή")
    st.download_button(
        "📗 Εξαγωγή Excel",
        data=make_excel_export(valid_sheets),
        file_name=f"{filename_prefix}.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        key=f"{key_prefix}_excel",
        use_container_width=True,
    )
    st.caption("Το Excel περιλαμβάνει όλα τα διαθέσιμα πεδία.")





def budget_plan_summary(year, month):
    saved = get_monthly_budget_record(monthly_budget_df, year, month)
    suggested_fixed, suggested_extra = monthly_budget_suggestions(
        recurring_df, tasks_df, year, month
    )
    income_fields = ["μισθός", "άλλο_σταθερό_έσοδο", "έκτακτο_έσοδο"]
    expense_fields = [
        "ενοίκιο", "κοινόχρηστα", "ρεύμα", "αέριο", "νερό",
        "κινητό_τηλέφωνο", "σταθερό_τηλέφωνο", "δάνειο_πειραιώς",
        "δάνειο_γεωργία", "δάνειο_θεία", "εφορία", "εφκα",
        "πιστωτική", "συνδρομές", "φαρμακείο", "γιατρός",
        "έξοδα_αυτοκινήτου", "ασφάλεια_αυτοκινήτου", "τέλη_κυκλοφορίας",
    ]
    def value(field):
        saved_value = float(parse_number(saved.get(field, 0)))
        return saved_value if saved_value > 0 else float(parse_number(suggested_fixed.get(field, 0)))
    income = sum(value(field) for field in income_fields)
    expenses = sum(value(field) for field in expense_fields)
    items = get_budget_items_for_month(budget_items_df, year, month)
    if items.empty and suggested_extra:
        items = pd.DataFrame(suggested_extra)
    if not items.empty:
        for _, row in items.iterrows():
            amount = float(parse_number(row.get("Ποσό", 0)))
            if str(row.get("Τύπος", "Έξοδο")) == "Έσοδο":
                income += amount
            else:
                expenses += amount
    safety = float(parse_number(saved.get("μαξιλάρι_ασφαλείας", 0)))
    return {
        "exists": bool(saved) or bool(suggested_fixed) or bool(suggested_extra) or not items.empty,
        "income": income,
        "expenses": expenses,
        "safety": safety,
        "available": income - expenses - safety,
    }

def display_hero():
    month_names = {
        1: "Ιανουάριος",
        2: "Φεβρουάριος",
        3: "Μάρτιος",
        4: "Απρίλιος",
        5: "Μάιος",
        6: "Ιούνιος",
        7: "Ιούλιος",
        8: "Αύγουστος",
        9: "Σεπτέμβριος",
        10: "Οκτώβριος",
        11: "Νοέμβριος",
        12: "Δεκέμβριος",
    }

    now = datetime.now()

    st.markdown(
        f"""
        <div class="hero">
            <h1>My Personal Hub</h1>
            <p>{month_names[now.month]} {now.year} · Η προσωπική σου εικόνα σε ένα σημείο</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# ΦΟΡΤΩΣΗ ΔΕΔΟΜΕΝΩΝ
# =========================================================

transactions_df = prepare_transactions(load_records(TRANSACTIONS_SHEET))



if st.session_state.pop("google_sheets_startup_warning", False):
    st.warning(
        "Η Google δεν απάντησε προσωρινά στον έλεγχο των οφειλών. "
        "Η εφαρμογή άνοιξε κανονικά και δεν έγινε καμία αλλαγή "
        "στα δεδομένα. Δοκίμασε ξανά αργότερα."
    )

debts_df = prepare_debts(load_records(DEBTS_SHEET))
debt_movements_df = prepare_debt_movements(
    load_records(DEBT_MOVEMENTS_SHEET)
)
monthly_budget_df = prepare_monthly_budget(
    load_records(MONTHLY_BUDGET_SHEET)
)
budget_items_df = prepare_budget_items(
    load_records(BUDGET_ITEMS_SHEET)
)
budget_status_df = prepare_budget_status(
    load_records(BUDGET_STATUS_SHEET)
)
raw_recurring_df = prepare_recurring(load_records(RECURRING_SHEET))
# Προσωρινά ανενεργές λειτουργίες. Τα παλιά φύλλα παραμένουν ανέπαφα.
reminders_df = pd.DataFrame(columns=SHEET_SCHEMAS[REMINDERS_SHEET])
tasks_df = pd.DataFrame(columns=SHEET_SCHEMAS[TASKS_SHEET])
repaired_recurring_df, recurring_repairs_needed = (
    repair_recurring_records_in_memory(raw_recurring_df)
)

if recurring_repairs_needed:
    persist_recurring_repairs(repaired_recurring_df)

recurring_df = prepare_recurring(repaired_recurring_df)
recurring_df = restore_missing_budget_recurring(
    recurring_df,
    budget_status_df,
    monthly_budget_df,
)
recurring_df = prepare_recurring(recurring_df)

documents_df = prepare_documents(load_records(DOCUMENTS_SHEET))
savings_df = prepare_savings(load_records(SAVINGS_SHEET))
custom_options_df = load_records(CUSTOM_OPTIONS_SHEET)
financial_closes_df = prepare_financial_closes(
    load_records(FINANCIAL_CLOSES_SHEET)
)
analytics_targets_df = prepare_analytics_targets(
    load_records(ANALYTICS_TARGETS_SHEET)
)
ensure_monthly_payment_reminder(reminders_df)


# =========================================================
# ΜΕΝΟΥ
# =========================================================

# Η αλλαγή σελίδας και ο καθαρισμός της φόρμας γίνονται
# πριν δημιουργηθεί το radio του μενού, όπως απαιτεί το Streamlit.
if st.session_state.pop("return_home_after_transaction", False):
    st.session_state["selected_page"] = "🏠 Με μια ματιά"

    for state_key in st.session_state.pop(
        "transaction_keys_to_clear",
        [],
    ):
        st.session_state.pop(state_key, None)

with st.sidebar:
    st.markdown("## 🌿 Personal Hub")
    st.caption("Καθαρή εικόνα πληρωμών και προϋπολογισμού")
    st.caption(f"Έκδοση: {APP_VERSION}")

    if "selected_page" not in st.session_state:
        st.session_state.selected_page = "🏠 Με μια ματιά"

    page = st.radio(
        "Μετάβαση",
        [
            "🏠 Με μια ματιά",
            "🧮 Καθημερινές κινήσεις",
            "💰 Αποταμίευση",
            "📈 Οικονομική οργάνωση",
            "📊 Ιστορικό",
            "💼 Φωτογραφία (επιχείρηση)",
            "💳 Δάνεια / Κάρτες",
            "✏️ Διαχείριση δεδομένων",
            "⚙️ Ρυθμίσεις",
        ],
        key="selected_page",
        label_visibility="collapsed",
    )

    st.divider()

    if st.button("🔄 Ανανέωση δεδομένων", use_container_width=True):
        refresh_data()
        st.rerun()


# =========================================================
# ΑΡΧΙΚΗ
# =========================================================

if page == "🏠 Με μια ματιά":
    display_hero()

    transaction_success_message = st.session_state.pop(
        "transaction_success_message",
        "",
    )
    if transaction_success_message:
        st.toast(transaction_success_message)

    current_month = pd.Timestamp.today()

    if transactions_df.empty:
        month_df = transactions_df.copy()
    else:
        month_df = transactions_df[
            (transactions_df["έτος_αναφοράς"] == current_month.year)
            & (transactions_df["μήνας_αναφοράς"] == current_month.month)
        ].copy()

    dashboard_categories = available_financial_categories(month_df)
    current_dashboard_category = st.session_state.get(
        "dashboard_category_filter",
        "Όλες",
    )
    if current_dashboard_category not in dashboard_categories:
        st.session_state["dashboard_category_filter"] = "Όλες"

    dashboard_category = render_choice_buttons(
        "Προβολή κατηγορίας",
        dashboard_categories,
        "dashboard_category_filter",
        columns=3,
    ) or "Όλες"

    if dashboard_category != "Όλες":
        month_df = month_df[
            month_df["κατηγορία"].astype(str)
            == str(dashboard_category)
        ].copy()

    monthly_income = month_df.loc[
        month_df["τύπος"] == "Έσοδο",
        "ποσό",
    ].sum()

    monthly_expenses = month_df.loc[
        month_df["τύπος"] == "Έξοδο",
        "ποσό",
    ].sum()

    monthly_expenses_from_balance = month_df.loc[
        (month_df["τύπος"] == "Έξοδο")
        & (month_df["πηγή_χρημάτων"] != "Αποταμίευση"),
        "ποσό",
    ].sum()

    monthly_balance = monthly_income - monthly_expenses_from_balance

    recurring_expenses = month_df.loc[
        (month_df["τύπος"] == "Έξοδο")
        & (month_df["πάγιο"] == "Ναι"),
        "ποσό",
    ].sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Έσοδα μήνα", format_currency(monthly_income), border=True)
    col2.metric("Έξοδα μήνα", format_currency(monthly_expenses), border=True)
    col3.metric("Υπόλοιπο μήνα", format_currency(monthly_balance), border=True)
    col4.metric("Πάγια μήνα", format_currency(recurring_expenses), border=True)

    if "δραστηριότητα" in month_df.columns and not month_df.empty:
        activity_col1, activity_col2 = st.columns(2)
        for activity_label, activity_col in zip(
            ["Γενικά", "Φωτογραφία"],
            [activity_col1, activity_col2],
        ):
            activity_rows = month_df[
                month_df["δραστηριότητα"] == activity_label
            ]
            activity_net = (
                activity_rows.loc[activity_rows["τύπος"] == "Έσοδο", "ποσό"].sum()
                - activity_rows.loc[activity_rows["τύπος"] == "Έξοδο", "ποσό"].sum()
            )
            activity_col.metric(
                activity_label,
                format_currency(activity_net),
                border=True,
            )

    st.subheader("Δάνεια και κάρτες")

    active_home_debts = (
        debts_df[debts_df["ενεργό"].astype(str) != "Όχι"].copy()
        if not debts_df.empty
        else debts_df.copy()
    )

    if active_home_debts.empty:
        st.caption(
            "Δεν υπάρχουν ακόμη δάνεια ή κάρτες. "
            "Πρόσθεσέ τα από την καρτέλα «Δάνεια / Κάρτες»."
        )
    else:
        selected_home_debt = render_debt_buttons(
            active_home_debts,
            "v55_home_selected_debt",
            columns=2,
        )

        home_debt_row = active_home_debts[
            active_home_debts["όνομα"].astype(str)
            == str(selected_home_debt)
        ].iloc[-1]

        home_initial_amount = float(
            parse_number(home_debt_row.get("αρχικό_ποσό", 0))
        )
        home_remaining_amount = calculate_debt_balance(
            home_debt_row,
            debt_movements_df,
        )
        home_paid_amount = max(
            home_initial_amount - home_remaining_amount,
            0.0,
        )
        home_paid_percentage = (
            max(
                min(
                    home_paid_amount / home_initial_amount,
                    1.0,
                ),
                0.0,
            )
            if home_initial_amount > 0
            else 0.0
        )

        with st.container(border=True):
            debt_metric1, debt_metric2, debt_metric3 = st.columns(3)
            debt_metric1.metric(
                "Αρχικό ποσό",
                format_currency(home_initial_amount),
                border=True,
            )
            debt_metric2.metric(
                "Υπόλοιπο",
                format_currency(home_remaining_amount),
                border=True,
            )
            debt_metric3.metric(
                "Έχει εξοφληθεί",
                format_currency(home_paid_amount),
                border=True,
            )
            st.progress(
                home_paid_percentage,
                text=f"Εξόφληση: {home_paid_percentage * 100:.1f}%",
            )

    st.divider()

    render_export_buttons(
        "My Personal Hub - Συνολική εικόνα",
        {
            "Κινήσεις": transactions_df,
                    "Πάγια": recurring_df,
            "Οφειλές": debts_df,
        },
        f"personal_hub_{date.today().isoformat()}",
        "home_export",
    )

    left_column, right_column = st.columns([1.4, 1])

    with left_column:
        st.subheader("Πού πήγαν τα χρήματα")

        expenses = month_df[
            month_df["τύπος"] == "Έξοδο"
        ].copy()

        if expenses.empty:
            st.info("Δεν υπάρχουν ακόμη έξοδα για τον τρέχοντα μήνα.")
        else:
            chart_data_full = (
                expenses
                .assign(
                    περιγραφή=expenses["περιγραφή"]
                    .astype(str)
                    .replace("", "Χωρίς περιγραφή")
                )
                .groupby("περιγραφή", as_index=False)["ποσό"]
                .sum()
                .sort_values("ποσό", ascending=False)
                .reset_index(drop=True)
            )

            chart_data = chart_data_full.head(12).copy()
            if len(chart_data_full) > 12:
                other_total = chart_data_full.iloc[12:]["ποσό"].sum()
                if other_total > 0:
                    chart_data = pd.concat(
                        [
                            chart_data,
                            pd.DataFrame(
                                [{
                                    "περιγραφή": "Λοιπά",
                                    "ποσό": other_total,
                                }]
                            ),
                        ],
                        ignore_index=True,
                    )

            dashboard_palette = THEMES.get(
                st.session_state.get("selected_app_theme", "Πετρόλ"),
                THEMES["Πετρόλ"],
            )

            chart = (
                alt.Chart(chart_data)
                .mark_bar(
                    cornerRadiusEnd=8,
                    color=dashboard_palette["main"],
                )
                .encode(
                    x=alt.X(
                        "ποσό:Q",
                        title="Ποσό (€)",
                        axis=alt.Axis(
                            labelColor=dashboard_palette["text"],
                            titleColor=dashboard_palette["text"],
                            gridColor=dashboard_palette["soft"],
                            domainColor=dashboard_palette["border"],
                            tickColor=dashboard_palette["border"],
                        ),
                    ),
                    y=alt.Y(
                        "περιγραφή:N",
                        sort="-x",
                        title=None,
                        axis=alt.Axis(
                            labelColor=dashboard_palette["text"],
                            domainColor=dashboard_palette["border"],
                            tickColor=dashboard_palette["border"],
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip("περιγραφή:N", title="Περιγραφή"),
                        alt.Tooltip("ποσό:Q", title="Ποσό", format=".2f"),
                    ],
                )
                .properties(
                    height=300,
                    background=dashboard_palette["soft_2"],
                )
                .configure_view(
                    stroke=dashboard_palette["border"],
                    strokeOpacity=0.30,
                )
            )

            st.altair_chart(chart, use_container_width=True)
            st.caption(
                "Το γράφημα δείχνει τις 12 μεγαλύτερες περιγραφές. "
                "Ο πλήρης πίνακας είναι ταξινομημένος από το μεγαλύτερο ποσό."
            )
            st.dataframe(
                chart_data_full.rename(
                    columns={
                        "περιγραφή": "Περιγραφή",
                        "ποσό": "Συνολικό ποσό",
                    }
                ),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Συνολικό ποσό": st.column_config.NumberColumn(
                        "Συνολικό ποσό",
                        format="%.2f €",
                    ),
                },
            )

        st.subheader("Τελευταίες κινήσεις")

        if transactions_df.empty:
            st.info("Δεν υπάρχουν ακόμη καταχωρημένες κινήσεις.")
        else:
            recent_transactions = (
                transactions_df
                .sort_values("ημερομηνία", ascending=False)
                .head(6)
            )

            for _, row in recent_transactions.iterrows():
                sign = "+" if row["τύπος"] == "Έσοδο" else "−"
                icon = "↗️" if row["τύπος"] == "Έσοδο" else "↘️"

                date_text = (
                    row["ημερομηνία"].strftime("%d/%m/%Y")
                    if not pd.isna(row["ημερομηνία"])
                    else ""
                )

                st.markdown(
                    f"""
                    <div class="soft-card">
                        <div class="small-label">
                            {icon} {row["κατηγορία"]} · {date_text}
                        </div>
                        <div style="display:flex;justify-content:space-between;gap:16px;">
                            <div>{row["περιγραφή"]}</div>
                            <div class="big-number">
                                {sign}{format_currency(row["ποσό"])}
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with right_column:
        st.subheader("Επόμενες υπενθυμίσεις")

        today = pd.Timestamp.today().normalize()
        next_30_days = today + pd.Timedelta(days=30)

        upcoming_reminders = reminders_df.copy()

        if not upcoming_reminders.empty:
            upcoming_reminders = upcoming_reminders[
                (upcoming_reminders["κατάσταση"] == "Ενεργή")
                & (upcoming_reminders["ημερομηνία"] >= today)
                & (upcoming_reminders["ημερομηνία"] <= next_30_days)
            ].sort_values("ημερομηνία")

        if upcoming_reminders.empty:
            st.markdown(
                """
                <div class="theme-message">
                    Δεν υπάρχει κάτι που να λήγει μέσα στις
                    επόμενες 30 ημέρες.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for _, row in upcoming_reminders.head(6).iterrows():
                days_left = (row["ημερομηνία"].normalize() - today).days

                if days_left == 0:
                    days_text = "Σήμερα"
                elif days_left == 1:
                    days_text = "Αύριο"
                else:
                    days_text = f"Σε {days_left} ημέρες"

                st.markdown(
                    f"""
                    <div class="warning-card">
                        <div class="small-label">
                            {row["κατηγορία"]} · {days_text}
                        </div>
                        <div>{row["τίτλος"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.subheader("Ανοιχτές εκκρεμότητες")

        open_tasks = tasks_df.copy()

        if not open_tasks.empty:
            open_tasks = open_tasks[
                open_tasks["κατάσταση"] == "Ανοιχτή"
            ].sort_values("προθεσμία")

        if open_tasks.empty:
            st.markdown(
                """
                <div class="theme-message">
                    Δεν έχεις ανοιχτές εκκρεμότητες.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for _, row in open_tasks.head(6).iterrows():
                deadline_text = (
                    row["προθεσμία"].strftime("%d/%m/%Y")
                    if not pd.isna(row["προθεσμία"])
                    else "Χωρίς προθεσμία"
                )

                st.markdown(
                    f"""
                    <div class="soft-card">
                        <div class="small-label">
                            {row["κατηγορία"]} · {deadline_text}
                        </div>
                        <div>{row["τίτλος"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# =========================================================
# ΝΕΑ ΚΑΤΑΧΩΡΗΣΗ
# =========================================================

# =========================================================
# ΥΠΕΝΘΥΜΙΣΕΙΣ
# =========================================================

elif page == "🧮 Καθημερινές κινήσεις":
    st.header("Καθημερινές κινήσεις")
    st.caption(
        "Καταχώρησε γρήγορα τα έσοδα και τα έξοδά σου και δες "
        "τα πάγια του μήνα."
    )

    month_short_names = {
        1: "Ιαν", 2: "Φεβ", 3: "Μαρ", 4: "Απρ",
        5: "Μαϊ", 6: "Ιουν", 7: "Ιουλ", 8: "Αυγ",
        9: "Σεπ", 10: "Οκτ", 11: "Νοε", 12: "Δεκ",
    }
    month_full_names = {
        1: "Ιανουάριος", 2: "Φεβρουάριος",
        3: "Μάρτιος", 4: "Απρίλιος", 5: "Μάιος",
        6: "Ιούνιος", 7: "Ιούλιος", 8: "Αύγουστος",
        9: "Σεπτέμβριος", 10: "Οκτώβριος",
        11: "Νοέμβριος", 12: "Δεκέμβριος",
    }

    selected_month_name = render_choice_buttons(
        "Μήνας",
        list(month_short_names.values()),
        "budget_month_buttons",
        columns=4,
    )
    if not selected_month_name:
        selected_month_name = month_short_names[date.today().month]
        st.session_state["budget_month_buttons"] = selected_month_name

    budget_month = next(
        number
        for number, name in month_short_names.items()
        if name == selected_month_name
    )
    budget_year = int(
        st.number_input(
            "Έτος",
            min_value=2020,
            max_value=2100,
            value=date.today().year,
            step=1,
            key="budget_year",
        )
    )

    st.divider()
    st.subheader("Γρήγορη νέα καταχώριση")
    st.caption(
        "Η ημερομηνία δείχνει πότε έγινε πραγματικά η πληρωμή/είσπραξη. "
        "Ο «μήνας που αφορά» καθορίζει σε ποιον μήνα θα υπολογιστεί στα "
        "σύνολα. Π.χ. αν ο μισθός μπαίνει 31/7 αλλά είναι για τα έξοδα "
        "του Αυγούστου, βάλε ημερομηνία 31/7 αλλά μήνας που αφορά = "
        "Αύγουστος, ώστε να υπολογιστεί μαζί με τα έξοδα εκείνου του μήνα."
    )

    quick_type = render_choice_buttons(
        "Τι θέλεις να καταχωρίσεις;",
        ["Έξοδο", "Έσοδο"],
        "v61_quick_type",
        columns=2,
    ) or "Έξοδο"

    quick_category_context = f"transaction_category_{quick_type}"
    quick_base_categories = (
        list(EXPENSE_CATEGORIES.keys())
        if quick_type == "Έξοδο"
        else list(INCOME_CATEGORIES.keys())
    )
    quick_category = button_choice_with_persistent_add(
        "Κατηγορία",
        quick_base_categories,
        quick_category_context,
        f"v61_quick_category_{quick_type}",
        add_label="Προσθήκη κατηγορίας",
        placeholder="π.χ. Επιχείρηση",
        columns=2,
    )

    quick_description_base = (
        EXPENSE_CATEGORIES.get(quick_category, [])
        if quick_type == "Έξοδο"
        else INCOME_CATEGORIES.get(quick_category, [])
    )
    quick_description_context = (
        f"transaction_description_{quick_type}_{quick_category}"
    )
    quick_description = button_choice_with_persistent_add(
        "Περιγραφή / υποκατηγορία",
        quick_description_base,
        quick_description_context,
        f"v61_quick_description_{quick_type}_{quick_category}",
        add_label="Προσθήκη περιγραφής",
        placeholder="π.χ. Ενοίκιο γραφείου",
        columns=2,
    )

    current_savings_available = savings_total(savings_df)
    if quick_type == "Έξοδο":
        quick_money_source = render_choice_buttons(
            "Από πού θα πληρωθεί;",
            ["Υπόλοιπο μήνα", "Αποταμίευση"],
            "v61_quick_money_source",
            columns=2,
        ) or "Υπόλοιπο μήνα"
    else:
        quick_money_source = render_choice_buttons(
            "Προέλευση εσόδου",
            ["Νέο έσοδο", "Από αποταμίευση"],
            "v61_quick_income_source",
            columns=2,
        ) or "Νέο έσοδο"

    if quick_money_source in {"Αποταμίευση", "Από αποταμίευση"}:
        st.caption(
            f"Διαθέσιμη αποταμίευση: "
            f"{format_currency(current_savings_available)}"
        )

    quick_activity = render_choice_buttons(
        "Δραστηριότητα",
        ["Γενικά", "Φωτογραφία"],
        "v61_quick_activity",
        columns=2,
    ) or "Γενικά"

    with st.form("v61_quick_transaction_form", clear_on_submit=True):
        quick_amount_text = st.text_input(
            "Ποσό",
            placeholder="0,00",
        )
        quick_transaction_date = st.date_input(
            "Πραγματική ημερομηνία πληρωμής ή είσπραξης",
            value=date.today(),
        )
        reference_col1, reference_col2 = st.columns(2)
        with reference_col1:
            quick_reference_month = st.selectbox(
                "Μήνας που αφορά",
                list(month_full_names.keys()),
                format_func=lambda value: month_full_names[value],
                index=budget_month - 1,
            )
        with reference_col2:
            quick_reference_year = int(
                st.number_input(
                    "Έτος που αφορά",
                    min_value=2020,
                    max_value=2100,
                    value=budget_year,
                    step=1,
                )
            )
        quick_notes = st.text_area(
            "Σημειώσεις, προαιρετικά",
            height=80,
        )
        submit_quick_transaction = st.form_submit_button(
            "Αποθήκευση καταχώρισης",
            use_container_width=True,
            type="primary",
        )

    if submit_quick_transaction:
        quick_amount = float(parse_number(quick_amount_text))
        uses_savings = quick_money_source in {
            "Αποταμίευση",
            "Από αποταμίευση",
        }

        if quick_amount <= 0:
            st.warning("Το ποσό πρέπει να είναι μεγαλύτερο από μηδέν.")
        elif uses_savings and quick_amount > current_savings_available:
            st.warning("Δεν επαρκεί η διαθέσιμη αποταμίευση.")
        else:
            if uses_savings:
                append_savings_withdrawal(
                    withdrawal_date=quick_transaction_date,
                    amount=quick_amount,
                    transaction_type=quick_type,
                    category=quick_category,
                    description=quick_description,
                    notes=quick_notes,
                    reference_year=quick_reference_year,
                    reference_month=quick_reference_month,
                    activity=quick_activity,
                )
            else:
                append_transaction(
                    transaction_date=quick_transaction_date,
                    transaction_type=quick_type,
                    category=quick_category,
                    description=quick_description,
                    amount=quick_amount,
                    money_source=(
                        quick_money_source
                        if quick_type == "Έξοδο"
                        else "Υπόλοιπο μήνα"
                    ),
                    notes=quick_notes,
                    reference_year=quick_reference_year,
                    reference_month=quick_reference_month,
                    activity=quick_activity,
                )

            st.success(
                "Η καταχώριση αποθηκεύτηκε στον μήνα "
                f"{month_full_names[quick_reference_month]} "
                f"{quick_reference_year}."
            )
            st.rerun()

    st.divider()
    st.subheader(
        f"Καταχωρίσεις {month_full_names[budget_month]} {budget_year}"
    )
    selected_period_transactions = transactions_df[
        (transactions_df["έτος_αναφοράς"] == budget_year)
        & (transactions_df["μήνας_αναφοράς"] == budget_month)
    ].copy()

    if selected_period_transactions.empty:
        st.caption("Δεν υπάρχουν ακόμη πραγματικές κινήσεις για αυτόν τον μήνα.")
    else:
        selected_period_transactions = selected_period_transactions.sort_values(
            "ημερομηνία",
            ascending=False,
        ).head(12)

        for _, quick_row in selected_period_transactions.iterrows():
            quick_row_id = str(quick_row["id"])
            with st.container(border=True):
                qcol1, qcol2 = st.columns([2.2, 1])
                with qcol1:
                    st.write(f"**{quick_row['περιγραφή']}**")
                    actual_date_text = (
                        quick_row["ημερομηνία"].strftime("%d/%m/%Y")
                        if not pd.isna(quick_row["ημερομηνία"])
                        else "Χωρίς ημερομηνία"
                    )
                    st.caption(
                        f"{quick_row['τύπος']} · {quick_row['κατηγορία']} · "
                        f"πληρωμή {actual_date_text}"
                    )
                with qcol2:
                    st.metric(
                        "Ποσό",
                        format_currency(quick_row["ποσό"]),
                        border=True,
                    )

                with st.expander("✏️ Επεξεργασία ή διαγραφή"):
                    with st.form(f"v61_edit_quick_{quick_row_id}"):
                        edit_quick_description = st.text_input(
                            "Περιγραφή",
                            value=str(quick_row["περιγραφή"]),
                        )
                        edit_quick_amount = st.number_input(
                            "Ποσό",
                            min_value=0.0,
                            value=float(quick_row["ποσό"]),
                            step=10.0,
                            format="%.2f",
                        )
                        edit_activity_options = ["Γενικά", "Φωτογραφία"]
                        edit_current_activity = str(
                            quick_row.get("δραστηριότητα", "Γενικά")
                        )
                        edit_quick_activity = st.selectbox(
                            "Δραστηριότητα",
                            edit_activity_options,
                            index=(
                                edit_activity_options.index(edit_current_activity)
                                if edit_current_activity in edit_activity_options
                                else 0
                            ),
                        )
                        edit_quick_date = st.date_input(
                            "Πραγματική ημερομηνία",
                            value=(
                                quick_row["ημερομηνία"].date()
                                if not pd.isna(quick_row["ημερομηνία"])
                                else date.today()
                            ),
                        )
                        edit_ref_col1, edit_ref_col2 = st.columns(2)
                        with edit_ref_col1:
                            edit_quick_month = st.selectbox(
                                "Μήνας που αφορά",
                                list(month_full_names.keys()),
                                format_func=lambda value: month_full_names[value],
                                index=int(quick_row["μήνας_αναφοράς"]) - 1,
                            )
                        with edit_ref_col2:
                            edit_quick_year = int(
                                st.number_input(
                                    "Έτος που αφορά",
                                    min_value=2020,
                                    max_value=2100,
                                    value=int(quick_row["έτος_αναφοράς"]),
                                    step=1,
                                )
                            )
                        save_quick_edit = st.form_submit_button(
                            "Αποθήκευση αλλαγών",
                            use_container_width=True,
                        )

                    if save_quick_edit:
                        update_record_fields(
                            transactions_ws,
                            quick_row_id,
                            {
                                "περιγραφή": edit_quick_description.strip(),
                                "ποσό": float(edit_quick_amount),
                                "ημερομηνία": edit_quick_date.isoformat(),
                                "έτος_αναφοράς": edit_quick_year,
                                "μήνας_αναφοράς": edit_quick_month,
                                "δραστηριότητα": edit_quick_activity,
                            },
                        )
                        st.success("Η καταχώριση ενημερώθηκε.")
                        st.rerun()

                    confirm_quick_delete = st.checkbox(
                        "Επιβεβαιώνω την πλήρη διαγραφή",
                        key=f"v61_confirm_quick_delete_{quick_row_id}",
                    )
                    if st.button(
                        "🗑️ Πλήρης διαγραφή",
                        key=f"v61_delete_quick_{quick_row_id}",
                        use_container_width=True,
                    ):
                        if not confirm_quick_delete:
                            st.warning("Επίλεξε πρώτα την επιβεβαίωση.")
                        elif delete_transaction_completely(quick_row_id):
                            st.success(
                                "Η κίνηση διαγράφηκε και το ποσό "
                                "επέστρεψε στην αρχική πηγή."
                            )
                            st.rerun()

    st.divider()
    st.subheader("Πάγια του μήνα")
    st.caption(
        "Εδώ βρίσκονται τα πάγια και οι συνδρομές που αντιστοιχούν "
        "στον επιλεγμένο μήνα."
    )

    (recurring_tab,) = st.tabs(
        [
            "Πάγια του μήνα",
        ]
    )

    selected_month_start = pd.Timestamp(
        year=budget_year,
        month=budget_month,
        day=1,
    )
    selected_month_end = selected_month_start + pd.offsets.MonthEnd(1)

    with recurring_tab:
        st.caption(
            "Εδώ εμφανίζονται τα ενεργά πάγια που αντιστοιχούν "
            "στον επιλεγμένο μήνα."
        )

        if recurring_df.empty:
            st.info("Δεν υπάρχουν ακόμη πάγια.")
        else:
            month_recurring = recurring_df[
                (recurring_df["ενεργό"].astype(str) != "Όχι")
                & recurring_df["επόμενη_χρέωση"].notna()
                & (recurring_df["επόμενη_χρέωση"] >= selected_month_start)
                & (recurring_df["επόμενη_χρέωση"] <= selected_month_end)
            ].copy()

            if month_recurring.empty:
                st.info("Δεν υπάρχουν πάγια για αυτόν τον μήνα.")
            else:
                for _, recurring_row in month_recurring.sort_values(
                    "επόμενη_χρέωση"
                ).iterrows():
                    item_type = infer_recurring_item_type(
                        recurring_row.get("όνομα", ""),
                        recurring_row.get("κατηγορία", ""),
                        recurring_row.get("τύπος", ""),
                    )
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1.4])
                        with col1:
                            st.write(f"**{recurring_row.get('όνομα', '')}**")
                            st.caption(
                                f"{item_type} · "
                                f"{recurring_row.get('κατηγορία', '')} · "
                                f"{recurring_row.get('συχνότητα', '')}"
                            )
                        with col2:
                            st.metric(
                                "Ποσό",
                                format_currency(recurring_row.get("ποσό", 0)),
                                border=True,
                            )

                        if st.button(
                            "Προσθήκη στο σχέδιο μήνα",
                            key=f"budget_add_recurring_{recurring_row.get('id', '')}_{budget_year}_{budget_month}",
                            use_container_width=True,
                        ):
                            append_budget_item_if_missing(
                                budget_year,
                                budget_month,
                                str(recurring_row.get("όνομα", "")),
                                str(recurring_row.get("κατηγορία", "")),
                                item_type,
                                float(parse_number(recurring_row.get("ποσό", 0))),
                                source="Πάγιο",
                                notes=str(recurring_row.get("σημειώσεις", "")),
                            )
                            st.success("Το πάγιο προστέθηκε στο σχέδιο του μήνα.")
                            st.rerun()

        with st.expander("➕ Νέο πάγιο"):
            recurring_name = st.text_input(
                "Όνομα παγίου",
                key=f"merged_recurring_name_{budget_year}_{budget_month}",
            )
            recurring_type = st.radio(
                "Τύπος παγίου",
                ["Έξοδο", "Έσοδο"],
                horizontal=True,
                key=f"merged_recurring_type_{budget_year}_{budget_month}",
            )
            recurring_category_options = options_with_saved(
                list(EXPENSE_CATEGORIES.keys())
                if recurring_type == "Έξοδο"
                else list(INCOME_CATEGORIES.keys()),
                f"transaction_category_{recurring_type}",
                include_other=False,
            )
            recurring_category = st.selectbox(
                "Κατηγορία",
                recurring_category_options,
                key=f"merged_recurring_category_{budget_year}_{budget_month}",
            )
            recurring_amount = st.number_input(
                "Ποσό παγίου",
                min_value=0.0,
                step=10.0,
                format="%.2f",
                key=f"merged_recurring_amount_{budget_year}_{budget_month}",
            )
            recurring_frequency = st.selectbox(
                "Συχνότητα",
                [
                    "Κάθε μήνα",
                    "Κάθε 2 μήνες",
                    "Κάθε 3 μήνες",
                    "Κάθε 6 μήνες",
                    "Κάθε χρόνο",
                ],
                key=f"merged_recurring_frequency_{budget_year}_{budget_month}",
            )
            recurring_rf = st.text_input(
                "RF, προαιρετικά",
                key=f"merged_recurring_rf_{budget_year}_{budget_month}",
            )
            if st.button(
                "Αποθήκευση νέου παγίου",
                key=f"save_merged_recurring_{budget_year}_{budget_month}",
                use_container_width=True,
                type="primary",
            ):
                if not recurring_name.strip() or not str(recurring_category).strip():
                    st.warning("Συμπλήρωσε όνομα και κατηγορία.")
                elif recurring_amount <= 0:
                    st.warning("Το ποσό πρέπει να είναι μεγαλύτερο από μηδέν.")
                else:
                    first_month = date(budget_year, budget_month, 1)
                    months_back = {
                        "Κάθε μήνα": 1,
                        "Κάθε 2 μήνες": 2,
                        "Κάθε 3 μήνες": 3,
                        "Κάθε 6 μήνες": 6,
                        "Κάθε χρόνο": 12,
                    }[recurring_frequency]
                    append_recurring(
                        recurring_name.strip(),
                        recurring_category.strip(),
                        recurring_type,
                        recurring_amount,
                        recurring_frequency,
                        first_month - relativedelta(months=months_back),
                        "",
                        0,
                        rf=recurring_rf,
                    )
                    append_budget_item_if_missing(
                        budget_year,
                        budget_month,
                        recurring_name.strip(),
                        recurring_category.strip(),
                        recurring_type,
                        recurring_amount,
                        source="Πάγιο",
                    )
                    st.success("Το πάγιο αποθηκεύτηκε και μπήκε στον μήνα.")
                    st.rerun()


elif page == "💳 Δάνεια / Κάρτες":
    st.header("Δάνεια / Κάρτες")
    st.caption(
        "Πρόσθεσε τραπεζικό ή ιδιωτικό δάνειο και πιστωτική κάρτα. "
        "Το επιτόκιο και ο αριθμός δόσεων είναι προαιρετικά."
    )

    with st.expander(
        "➕ Προσθήκη δανείου ή κάρτας",
        expanded=debts_df.empty,
    ):
        with st.form("v50_generic_debt_form", clear_on_submit=True):
            debt_kind = st.radio(
                "Είδος",
                [
                    "Τραπεζικό δάνειο",
                    "Ιδιωτικό δάνειο",
                    "Πιστωτική κάρτα",
                ],
                horizontal=True,
            )
            debt_name = st.text_input(
                "Όνομα",
                placeholder="π.χ. Δάνειο αυτοκινήτου ή Κάρτα Alpha",
            )
            creditor = st.text_input(
                "Τράπεζα ή πρόσωπο, προαιρετικά",
            )
            initial_amount_text = st.text_input(
                "Αρχικό ποσό",
                placeholder="0,00",
            )

            dcol1, dcol2 = st.columns(2)
            with dcol1:
                installment_text = st.text_input(
                    "Συνήθης δόση, προαιρετικά",
                    placeholder="0,00",
                )
            with dcol2:
                total_installments = st.number_input(
                    "Συνολικές δόσεις, προαιρετικά",
                    min_value=0,
                    max_value=600,
                    value=0,
                    step=1,
                )

            rate_type = st.selectbox(
                "Τύπος επιτοκίου",
                ["Χωρίς επιτόκιο", "Σταθερό", "Κυμαινόμενο"],
            )
            annual_rate = 0.0
            if rate_type != "Χωρίς επιτόκιο":
                annual_rate = st.number_input(
                    "Ετήσιο επιτόκιο %",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=0.1,
                    format="%.2f",
                )

            first_col1, first_col2 = st.columns(2)
            with first_col1:
                first_due_month = st.selectbox(
                    "Μήνας πρώτης δόσης",
                    list(MONTH_NAMES_FULL.keys()),
                    format_func=lambda x: MONTH_NAMES_FULL[x],
                    index=date.today().month - 1,
                )
            with first_col2:
                first_due_year = st.number_input(
                    "Έτος πρώτης δόσης",
                    min_value=2020,
                    max_value=2100,
                    value=date.today().year,
                    step=1,
                )

            debt_notes = st.text_area("Σημειώσεις, προαιρετικά")
            create_debt = st.form_submit_button(
                "Δημιουργία",
                use_container_width=True,
                type="primary",
            )

        if create_debt:
            initial_amount = float(parse_number(initial_amount_text))
            installment = float(parse_number(installment_text))
            if not debt_name.strip():
                st.warning("Συμπλήρωσε όνομα.")
            elif initial_amount <= 0:
                st.warning(
                    "Το αρχικό ποσό πρέπει να είναι μεγαλύτερο από μηδέν."
                )
            else:
                append_generic_debt(
                    debt_name.strip(),
                    debt_kind,
                    creditor.strip(),
                    initial_amount,
                    installment,
                    annual_rate,
                    total_installments,
                    month_start_date(first_due_year, first_due_month),
                    rate_type,
                    debt_notes,
                )
                st.success("Το δάνειο ή η κάρτα προστέθηκε.")
                st.rerun()

    render_export_buttons(
        "Δάνεια και κάρτες",
        {
            "Οφειλές": debts_df,
            "Κινήσεις οφειλών": debt_movements_df,
        },
        "daneia_kartes",
        "debts_export",
    )

    if debts_df.empty:
        st.info(
            "Δεν υπάρχουν ακόμη δάνεια ή κάρτες. "
            "Πρόσθεσε την πρώτη εγγραφή από το κουμπί επάνω."
        )
    else:
        active_debts = debts_df[
            debts_df["ενεργό"].astype(str) != "Όχι"
        ].copy()
        if active_debts.empty:
            active_debts = debts_df.copy()

        total_initial = active_debts["αρχικό_ποσό"].sum()
        total_remaining = sum(
            calculate_debt_balance(row, debt_movements_df)
            for _, row in active_debts.iterrows()
        )
        total_paid = max(total_initial - total_remaining, 0.0)

        m1, m2, m3 = st.columns(3)
        m1.metric(
            "Συνολικό αρχικό ποσό",
            format_currency(total_initial),
            border=True,
        )
        m2.metric(
            "Συνολικό υπόλοιπο",
            format_currency(total_remaining),
            border=True,
        )
        m3.metric(
            "Έχει εξοφληθεί",
            format_currency(total_paid),
            border=True,
        )

        st.subheader("Επίλεξε δάνειο ή κάρτα")
        selected_debt_name = render_debt_buttons(
            active_debts,
            "v55_selected_debt",
            columns=2,
        )
        debt_row = active_debts[
            active_debts["όνομα"] == selected_debt_name
        ].iloc[-1]

        current_balance = calculate_debt_balance(
            debt_row,
            debt_movements_df,
        )
        initial_amount = float(
            parse_number(debt_row.get("αρχικό_ποσό", 0))
        )
        default_installment = float(
            parse_number(debt_row.get("προεπιλεγμένη_δόση", 0))
        )
        paid_percentage = (
            max(
                min(
                    (initial_amount - current_balance) / initial_amount,
                    1,
                ),
                0,
            )
            if initial_amount > 0
            else 0
        )

        s1, s2, s3 = st.columns(3)
        s1.metric("Αρχικό ποσό", format_currency(initial_amount), border=True)
        s2.metric("Υπόλοιπο", format_currency(current_balance), border=True)
        s3.metric(
            "Συνήθης δόση",
            format_currency(default_installment),
            border=True,
        )
        st.progress(
            paid_percentage,
            text=f"Εξόφληση: {paid_percentage * 100:.1f}%",
        )

        details_tab, payment_tab, correction_tab, history_tab = st.tabs(
            [
                "Στοιχεία",
                "Καταχώρηση πληρωμής",
                "Διόρθωση υπολοίπου",
                "Ιστορικό",
            ]
        )

        with details_tab:
            with st.form(f"edit_debt_v50_{debt_row['id']}"):
                edit_name = st.text_input(
                    "Όνομα",
                    value=str(debt_row.get("όνομα", "")),
                )
                edit_creditor = st.text_input(
                    "Τράπεζα ή πρόσωπο",
                    value=str(debt_row.get("πιστωτής", "")),
                )
                edit_initial = st.number_input(
                    "Αρχικό ποσό",
                    min_value=0.0,
                    value=float(initial_amount),
                    step=10.0,
                    format="%.2f",
                )
                edit_installment = st.number_input(
                    "Συνήθης δόση",
                    min_value=0.0,
                    value=float(default_installment),
                    step=10.0,
                    format="%.2f",
                )
                edit_notes = st.text_area(
                    "Σημειώσεις",
                    value=str(debt_row.get("σημειώσεις", "")),
                )
                save_debt = st.form_submit_button(
                    "Αποθήκευση αλλαγών",
                    use_container_width=True,
                    type="primary",
                )
            if save_debt:
                update_record_fields(
                    debts_ws,
                    debt_row["id"],
                    {
                        "όνομα": edit_name.strip(),
                        "πιστωτής": edit_creditor.strip(),
                        "αρχικό_ποσό": float(edit_initial),
                        "προεπιλεγμένη_δόση": float(edit_installment),
                        "σημειώσεις": edit_notes,
                        "ενημερώθηκε": datetime.now().isoformat(
                            timespec="seconds"
                        ),
                    },
                )
                st.success("Οι αλλαγές αποθηκεύτηκαν.")
                st.rerun()

            confirm_delete = st.checkbox(
                "Επιβεβαιώνω τη διαγραφή",
                key=f"confirm_delete_debt_v50_{debt_row['id']}",
            )
            if st.button(
                "🗑️ Διαγραφή",
                key=f"delete_debt_v50_{debt_row['id']}",
                use_container_width=True,
            ):
                if not confirm_delete:
                    st.warning("Επίλεξε πρώτα την επιβεβαίωση.")
                elif delete_debt_completely(debt_row["id"]):
                    st.success("Η οφειλή διαγράφηκε.")
                    st.rerun()

        with payment_tab:
            payment_amount = st.number_input(
                "Ποσό πληρωμής",
                min_value=0.0,
                value=float(
                    min(default_installment, current_balance)
                    if default_installment > 0
                    else 0.0
                ),
                step=10.0,
                format="%.2f",
            )
            payment_date = st.date_input(
                "Ημερομηνία πληρωμής",
                value=date.today(),
            )
            payment_note = st.text_input("Σημείωση, προαιρετικά")
            payment_source = st.radio(
                "Αφαίρεση από",
                ["Υπόλοιπο μήνα", "Αποταμίευση"],
                horizontal=True,
            )
            if st.button(
                "Αποθήκευση πληρωμής",
                key=f"save_debt_payment_v50_{debt_row['id']}",
                use_container_width=True,
                type="primary",
            ):
                if payment_amount <= 0:
                    st.warning(
                        "Το ποσό πρέπει να είναι μεγαλύτερο από μηδέν."
                    )
                elif current_balance > 0 and payment_amount > current_balance:
                    st.warning(
                        "Το ποσό είναι μεγαλύτερο από το υπόλοιπο."
                    )
                elif (
                    payment_source == "Αποταμίευση"
                    and payment_amount > savings_total(savings_df)
                ):
                    st.warning("Δεν επαρκεί η αποταμίευση.")
                else:
                    if payment_source == "Αποταμίευση":
                        payment_transaction_id = append_savings_withdrawal(
                            withdrawal_date=payment_date,
                            amount=payment_amount,
                            transaction_type="Έξοδο",
                            category="Δάνεια / Κάρτες",
                            description=debt_row["όνομα"],
                            payment_method="Τραπεζική μεταφορά",
                            recurring=True,
                            notes=payment_note,
                        )
                    else:
                        payment_transaction_id = append_transaction(
                            transaction_date=payment_date,
                            transaction_type="Έξοδο",
                            category="Δάνεια / Κάρτες",
                            description=debt_row["όνομα"],
                            amount=payment_amount,
                            payment_method="Τραπεζική μεταφορά",
                            recurring=True,
                            notes=payment_note,
                            money_source="Υπόλοιπο μήνα",
                        )

                    append_debt_movement(
                        debt_row["id"],
                        debt_row["όνομα"],
                        payment_date,
                        "Πληρωμή",
                        payment_amount,
                        payment_note,
                        related_transaction_id=payment_transaction_id,
                        money_source=payment_source,
                    )
                    st.success("Η πληρωμή καταχωρίστηκε.")
                    st.rerun()

        with correction_tab:
            corrected_balance = st.number_input(
                "Πραγματικό οφειλόμενο ποσό",
                min_value=0.0,
                value=float(current_balance),
                step=10.0,
                format="%.2f",
            )
            correction_note = st.text_input(
                "Αιτιολογία",
                placeholder="π.χ. Νέα χρέωση κάρτας",
            )
            if st.button(
                "Ενημέρωση υπολοίπου",
                key=f"correct_debt_v50_{debt_row['id']}",
                use_container_width=True,
            ):
                if set_debt_current_balance(
                    debt_row,
                    corrected_balance,
                    debt_movements_df,
                    correction_note,
                ):
                    st.success("Το υπόλοιπο ενημερώθηκε.")
                    st.rerun()
                else:
                    st.info("Το ποσό είναι ήδη ίδιο.")

        with history_tab:
            history = debt_movements_df[
                debt_movements_df["debt_id"].astype(str)
                == str(debt_row["id"])
            ].copy()
            if history.empty:
                st.info("Δεν υπάρχουν ακόμη κινήσεις.")
            else:
                history = history.sort_values(
                    "ημερομηνία",
                    ascending=False,
                )
                display = history[
                    ["ημερομηνία", "τύπος", "ποσό", "σημειώσεις"]
                ].copy()
                display["ημερομηνία"] = (
                    display["ημερομηνία"].dt.strftime("%d/%m/%Y")
                )
                display["ποσό"] = display["ποσό"].apply(format_currency)
                st.dataframe(
                    display,
                    use_container_width=True,
                    hide_index=True,
                )


elif page == "💰 Αποταμίευση":
    st.header("Αποταμίευση")
    st.caption(
        "Μετέφερε εδώ το ποσό που περισσεύει, ώστε ο μήνας "
        "να κλείνει χωρίς υπόλοιπο που μεταφέρεται στον επόμενο."
    )

    month_names_savings = {
        1: "Ιαν",
        2: "Φεβ",
        3: "Μαρ",
        4: "Απρ",
        5: "Μαϊ",
        6: "Ιουν",
        7: "Ιουλ",
        8: "Αυγ",
        9: "Σεπ",
        10: "Οκτ",
        11: "Νοε",
        12: "Δεκ",
    }

    selected_savings_month_name = render_choice_buttons(
        "Μήνας",
        list(month_names_savings.values()),
        "savings_month_buttons",
        columns=4,
    )

    if not selected_savings_month_name:
        selected_savings_month_name = month_names_savings[date.today().month]
        st.session_state["savings_month_buttons"] = (
            selected_savings_month_name
        )

    selected_savings_month = next(
        month_number
        for month_number, short_name in month_names_savings.items()
        if short_name == selected_savings_month_name
    )

    selected_savings_year = st.number_input(
        "Έτος",
        min_value=2020,
        max_value=2100,
        value=date.today().year,
        step=1,
        key="savings_year",
    )

    selected_month_balance = month_transaction_balance(
        transactions_df,
        int(selected_savings_year),
        selected_savings_month,
    )
    current_savings_total = savings_total(savings_df)

    metric1, metric2 = st.columns(2)
    metric1.metric(
        "Διαθέσιμο υπόλοιπο μήνα",
        format_currency(selected_month_balance),
        border=True,
    )
    metric2.metric(
        "Συνολική αποταμίευση",
        format_currency(current_savings_total),
        border=True,
    )

    savings_action = render_choice_buttons(
        "Ενέργεια",
        ["Κατάθεση", "Ανάληψη"],
        "savings_action_buttons",
        columns=2,
    ) or "Κατάθεση"

    if savings_action == "Κατάθεση":
        st.markdown(
            """
            <div class="theme-message">
                Μπορείς να προσθέσεις οποιοδήποτε ποσό στην αποταμίευση,
                οποιαδήποτε στιγμή. Η κατάθεση μειώνει το υπόλοιπο του
                μήνα της ημερομηνίας που επιλέγεις.
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("savings_deposit_form"):
            suggested_amount = max(float(selected_month_balance), 0.0)
            amount_to_save = st.number_input(
                "Ποσό κατάθεσης",
                min_value=0.0,
                value=suggested_amount,
                step=10.0,
                format="%.2f",
            )
            transfer_date = st.date_input(
                "Ημερομηνία κατάθεσης",
                value=date.today(),
            )
            savings_notes = st.text_area(
                "Σημείωση",
                placeholder="π.χ. Υπόλοιπο μήνα ή έκτακτη αποταμίευση",
            )
            save_transfer = st.form_submit_button(
                "Κατάθεση στην αποταμίευση",
                use_container_width=True,
                type="primary",
            )
        if save_transfer:
            if amount_to_save <= 0:
                st.warning("Το ποσό πρέπει να είναι μεγαλύτερο από μηδέν.")
            else:
                append_savings_deposit(
                    transfer_date,
                    amount_to_save,
                    savings_notes,
                )
                st.success("Το ποσό προστέθηκε στην αποταμίευση.")
                st.rerun()
    else:
        st.markdown(
            """
            <div class="theme-message">
                Η ανάληψη δημιουργεί έσοδο στον επιλεγμένο μήνα και
                αφαιρεί το ίδιο ποσό από την αποταμίευση.
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("savings_withdrawal_form"):
            amount_to_withdraw = st.number_input(
                "Ποσό ανάληψης",
                min_value=0.0,
                max_value=max(float(current_savings_total), 0.0),
                step=10.0,
                format="%.2f",
            )
            withdrawal_date = st.date_input(
                "Ημερομηνία ανάληψης",
                value=date.today(),
            )
            withdrawal_notes = st.text_area(
                "Σημείωση",
                placeholder="π.χ. Ενίσχυση υπολοίπου μήνα",
            )
            withdraw_submit = st.form_submit_button(
                "Μεταφορά στο υπόλοιπο μήνα",
                use_container_width=True,
                type="primary",
            )
        if withdraw_submit:
            if amount_to_withdraw <= 0:
                st.warning("Το ποσό πρέπει να είναι μεγαλύτερο από μηδέν.")
            elif amount_to_withdraw > current_savings_total + 0.005:
                st.warning("Δεν υπάρχει αρκετή αποταμίευση.")
            else:
                append_savings_withdrawal(
                    withdrawal_date=withdrawal_date,
                    amount=amount_to_withdraw,
                    transaction_type="Έσοδο",
                    category="Αποταμίευση",
                    description="Ανάληψη από αποταμίευση",
                    payment_method="Μεταφορά",
                    notes=withdrawal_notes,
                )
                st.success("Το ποσό μεταφέρθηκε στο υπόλοιπο του μήνα.")
                st.rerun()

    st.divider()
    render_export_buttons(
        "Αποταμίευση",
        {"Αποταμίευση": savings_df},
        "apotamiefsi",
        "savings_export",
    )

    st.subheader("Ιστορικό αποταμίευσης")

    if savings_df.empty:
        st.info("Δεν υπάρχουν ακόμη κινήσεις αποταμίευσης.")
    else:
        visible_savings = savings_df.sort_values(
            "ημερομηνία",
            ascending=False,
        )

        for _, row in visible_savings.iterrows():
            date_text = (
                row["ημερομηνία"].strftime("%d/%m/%Y")
                if not pd.isna(row["ημερομηνία"])
                else ""
            )

            with st.container(border=True):
                st.write(
                    f"**{row['τύπος']} · "
                    f"{format_currency(row['ποσό'])}**"
                )
                st.caption(
                    f"{date_text} · "
                    f"{int(parse_number(row['μήνας'])):02d}/"
                    f"{int(parse_number(row['έτος']))}"
                )
                if str(row.get("σημειώσεις", "")).strip():
                    st.caption(str(row["σημειώσεις"]))

                savings_row_id = str(row["id"])
                with st.expander("🗑️ Διαγραφή κίνησης αποταμίευσης"):
                    confirm_savings_delete = st.checkbox(
                        "Επιβεβαιώνω τη διαγραφή",
                        key=f"confirm_savings_delete_{savings_row_id}",
                    )
                    if st.button(
                        "Διαγραφή",
                        key=f"delete_savings_{savings_row_id}",
                        use_container_width=True,
                    ):
                        if not confirm_savings_delete:
                            st.warning("Επίλεξε πρώτα την επιβεβαίωση.")
                        elif delete_savings_with_counterpart(savings_row_id):
                            st.success(
                                "Η κίνηση διαγράφηκε και τα ποσά "
                                "αντιλογίστηκαν αυτόματα."
                            )
                            st.rerun()


elif page == "🔁 Πάγια / Συνδρομές":
    st.header("Πάγια και περιοδικές πληρωμές")
    st.caption(
        "Ορίζεις μήνα και έτος εμφάνισης. Η εφαρμογή χρησιμοποιεί "
        "τη συχνότητα για τους επόμενους μήνες."
    )

    render_export_buttons(
        "Πάγια και συνδρομές",
        {"Πάγια": recurring_df},
        "pagia_syndromes",
        "recurring_export",
    )

    with st.expander("➕ Προσθήκη παγίου", expanded=False):
        recurring_name = st.text_input(
            "Όνομα",
            placeholder="π.χ. Ασφάλεια αυτοκινήτου ή Μισθός",
            key="v56_recurring_name",
        )
        recurring_type = st.radio(
            "Τύπος",
            ["Έξοδο", "Έσοδο"],
            horizontal=True,
            key="v56_recurring_type",
        )

        recurring_category_options = options_with_saved(
            list(EXPENSE_CATEGORIES.keys())
            if recurring_type == "Έξοδο"
            else list(INCOME_CATEGORIES.keys()),
            f"transaction_category_{recurring_type}",
            include_other=False,
        )
        recurring_category = st.selectbox(
            "Κατηγορία",
            recurring_category_options,
            key="v59_recurring_category",
        )

        recurring_amount = money_text_input(
            "Ποσό",
            "v56_new_recurring_amount",
        )

        freq_col, month_col, year_col = st.columns(3)
        with freq_col:
            recurring_frequency = st.selectbox(
                "Συχνότητα",
                [
                    "Κάθε μήνα",
                    "Κάθε 2 μήνες",
                    "Κάθε 3 μήνες",
                    "Κάθε 6 μήνες",
                    "Κάθε χρόνο",
                ],
                key="v56_recurring_frequency",
            )
        with month_col:
            target_month = st.selectbox(
                "Πρώτος μήνας",
                list(MONTH_NAMES_FULL.keys()),
                format_func=lambda value: MONTH_NAMES_FULL[value],
                index=date.today().month - 1,
                key="v56_recurring_month",
            )
        with year_col:
            target_year = st.number_input(
                "Έτος",
                min_value=2020,
                max_value=2100,
                value=date.today().year,
                step=1,
                key="v56_recurring_year",
            )

        recurring_rf = st.text_input(
            "RF, προαιρετικά",
            key="v56_recurring_rf",
        )
        recurring_notes = st.text_area(
            "Σημειώσεις, προαιρετικά",
            key="v56_recurring_notes",
        )

        recurring_submit = st.button(
            "Αποθήκευση παγίου",
            use_container_width=True,
            type="primary",
            key="v56_save_recurring",
        )

        if recurring_submit:
            final_category = recurring_category
            if not recurring_name.strip():
                st.warning("Συμπλήρωσε όνομα.")
            elif not final_category:
                st.warning("Συμπλήρωσε κατηγορία.")
            elif recurring_amount <= 0:
                st.warning("Το ποσό πρέπει να είναι μεγαλύτερο από μηδέν.")
            else:
                first_month = month_start_date(target_year, target_month)
                append_recurring(
                    recurring_name.strip(),
                    final_category,
                    recurring_type,
                    recurring_amount,
                    recurring_frequency,
                    first_month - relativedelta(
                        months={
                            "Κάθε μήνα": 1,
                            "Κάθε 2 μήνες": 2,
                            "Κάθε 3 μήνες": 3,
                            "Κάθε 6 μήνες": 6,
                            "Κάθε χρόνο": 12,
                        }[recurring_frequency]
                    ),
                    "",
                    0,
                    recurring_notes,
                    recurring_rf,
                )
                st.success(
                    f"Αποθηκεύτηκε για {MONTH_NAMES_FULL[target_month]} "
                    f"{int(target_year)}."
                )
                st.rerun()

    st.divider()

    active_recurring = (
        recurring_df[recurring_df["ενεργό"] == "Ναι"].copy()
        if not recurring_df.empty
        else recurring_df.copy()
    )

    if active_recurring.empty:
        st.info("Δεν υπάρχουν ενεργά πάγια.")
    else:
        active_recurring = active_recurring.sort_values(
            ["επόμενη_χρέωση", "όνομα"],
            na_position="last",
        )

        for _, row in active_recurring.iterrows():
            recurring_id = str(row["id"])
            item_type = infer_recurring_item_type(
                row.get("όνομα", ""),
                row.get("κατηγορία", ""),
                row.get("τύπος", ""),
            )
            next_charge = row.get("επόμενη_χρέωση")
            if pd.isna(next_charge):
                next_charge_date = date.today().replace(day=1)
            else:
                next_charge_date = pd.Timestamp(next_charge).date()

            with st.container(border=True):
                st.write(f"**{row['όνομα']}**")
                st.caption(
                    f"{item_type} · {row['κατηγορία']} · "
                    f"{row['συχνότητα']}"
                )
                metric_col1, metric_col2 = st.columns(2)
                metric_col1.metric(
                    "Ποσό",
                    format_currency(row["ποσό"]),
                    border=True,
                )
                metric_col2.metric(
                    "Μήνας προϋπολογισμού",
                    month_year_text(next_charge_date),
                    border=True,
                )

                if str(row.get("rf", "")).strip():
                    st.caption(f"RF: {row['rf']}")

                action_col1, action_col2 = st.columns([1.3, 1])
                with action_col1:
                    if st.button(
                        (
                            "Προσθήκη στις προς πληρωμή και "
                            "στον προϋπολογισμό"
                            if item_type == "Έξοδο"
                            else "Προσθήκη στο σχέδιο μήνα"
                        ),
                        key=f"send_recurring_{recurring_id}",
                        use_container_width=True,
                        type="primary",
                    ):
                        target_year = next_charge_date.year
                        target_month = next_charge_date.month

                        append_budget_item_if_missing(
                            target_year,
                            target_month,
                            str(row["όνομα"]),
                            str(row["κατηγορία"]),
                            item_type,
                            float(row["ποσό"]),
                            source="Πάγιο",
                            notes=str(row.get("σημειώσεις", "")),
                        )

                        if item_type == "Έξοδο":
                            month_deadline = (
                                month_start_date(target_year, target_month)
                                + relativedelta(months=1)
                                - timedelta(days=1)
                            )
                            append_task(
                                title=str(row["όνομα"]),
                                category=str(row["κατηγορία"]),
                                deadline=month_deadline,
                                priority="Κανονική",
                                notes=str(row.get("σημειώσεις", "")),
                                item_type="Λογαριασμός",
                                amount=float(row["ποσό"]),
                                recurrence=str(row["συχνότητα"]),
                                rf=str(row.get("rf", "")),
                            )

                        st.success(
                            f"Προστέθηκε στον προϋπολογισμό "
                            f"{MONTH_NAMES_FULL[target_month]} {target_year}."
                        )
                        st.rerun()

                with action_col2:
                    st.caption(
                        "Η συχνότητα συνεχίζει να το προτείνει "
                        "στους μήνες που του αναλογούν."
                    )

                with st.expander("✏️ Επεξεργασία ή διαγραφή"):
                    with st.form(f"edit_recurring_{recurring_id}"):
                        edit_name = st.text_input(
                            "Όνομα",
                            value=str(row["όνομα"]),
                        )
                        edit_type = st.radio(
                            "Τύπος",
                            ["Έξοδο", "Έσοδο"],
                            index=0 if item_type == "Έξοδο" else 1,
                            horizontal=True,
                        )
                        edit_amount = money_text_input(
                            "Ποσό",
                            f"edit_recurring_amount_v49_{recurring_id}",
                            current_value=row["ποσό"],
                        )
                        edit_frequency_options = [
                            "Κάθε μήνα",
                            "Κάθε 2 μήνες",
                            "Κάθε 3 μήνες",
                            "Κάθε 6 μήνες",
                            "Κάθε χρόνο",
                        ]
                        edit_frequency = st.selectbox(
                            "Συχνότητα",
                            edit_frequency_options,
                            index=(
                                edit_frequency_options.index(
                                    str(row["συχνότητα"])
                                )
                                if str(row["συχνότητα"])
                                in edit_frequency_options
                                else 0
                            ),
                        )
                        edit_month_col, edit_year_col = st.columns(2)
                        with edit_month_col:
                            edit_month = st.selectbox(
                                "Επόμενος μήνας",
                                list(MONTH_NAMES_FULL.keys()),
                                format_func=lambda value: MONTH_NAMES_FULL[value],
                                index=next_charge_date.month - 1,
                                key=f"edit_month_{recurring_id}",
                            )
                        with edit_year_col:
                            edit_year = st.number_input(
                                "Έτος",
                                min_value=2020,
                                max_value=2100,
                                value=next_charge_date.year,
                                step=1,
                                key=f"edit_year_{recurring_id}",
                            )
                        edit_rf = st.text_input(
                            "RF",
                            value=str(row.get("rf", "")),
                        )
                        save_edit = st.form_submit_button(
                            "Αποθήκευση αλλαγών",
                            use_container_width=True,
                        )

                    if save_edit:
                        update_record_fields(
                            recurring_ws,
                            recurring_id,
                            {
                                "όνομα": edit_name.strip(),
                                "τύπος": edit_type,
                                "ποσό": float(edit_amount),
                                "συχνότητα": edit_frequency,
                                "επόμενη_χρέωση": month_start_date(
                                    edit_year,
                                    edit_month,
                                ).isoformat(),
                                "rf": edit_rf.strip(),
                                "ενημερώθηκε": datetime.now().isoformat(
                                    timespec="seconds"
                                ),
                            },
                        )
                        st.success("Οι αλλαγές αποθηκεύτηκαν.")
                        st.rerun()

                    confirm_delete = st.checkbox(
                        "Επιβεβαιώνω τη διαγραφή",
                        key=f"delete_recurring_confirm_{recurring_id}",
                    )
                    if st.button(
                        "🗑️ Διαγραφή",
                        key=f"delete_recurring_v49_{recurring_id}",
                        use_container_width=True,
                    ):
                        if not confirm_delete:
                            st.warning("Επίλεξε πρώτα την επιβεβαίωση.")
                        elif delete_record_by_id(
                            recurring_ws,
                            recurring_id,
                        ):
                            st.success("Το πάγιο διαγράφηκε.")
                            st.rerun()


elif page == "💼 Φωτογραφία (επιχείρηση)":
    st.header("Φωτογραφία · Επιχειρηματική εικόνα")
    st.caption(
        "Τα ίδια χρήματα, ένα ταμείο· αλλά εδώ βλέπεις μόνο τις "
        "κινήσεις που έχεις σημειώσει ως «Φωτογραφία»."
    )

    business_df = transactions_df[
        transactions_df.get(
            "δραστηριότητα",
            pd.Series(dtype=str),
        )
        == "Φωτογραφία"
    ].copy() if not transactions_df.empty else transactions_df.copy()

    business_years = sorted(
        business_df["ημερομηνία"].dropna().dt.year.unique().tolist(),
        reverse=True,
    ) if not business_df.empty else []

    current_business_year = datetime.now().year
    if current_business_year not in business_years:
        business_years.insert(0, current_business_year)

    selected_business_year = st.number_input(
        "Έτος",
        min_value=2000,
        max_value=2100,
        value=current_business_year,
        step=1,
        key="business_year_filter",
    )

    business_month_labels = [
        "Όλοι",
        "Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαϊ", "Ιουν",
        "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ",
    ]
    selected_business_month_name = render_choice_buttons(
        "Μήνας",
        business_month_labels,
        "business_month_buttons",
        columns=4,
    )
    business_month_lookup = {
        "Όλοι": 0,
        "Ιαν": 1, "Φεβ": 2, "Μαρ": 3, "Απρ": 4,
        "Μαϊ": 5, "Ιουν": 6, "Ιουλ": 7, "Αυγ": 8,
        "Σεπ": 9, "Οκτ": 10, "Νοε": 11, "Δεκ": 12,
    }
    selected_business_month = business_month_lookup.get(
        selected_business_month_name, 0
    )

    if not business_df.empty:
        business_df = business_df[
            business_df["ημερομηνία"].dt.year == int(selected_business_year)
        ]
        if selected_business_month:
            business_df = business_df[
                business_df["ημερομηνία"].dt.month
                == int(selected_business_month)
            ]

    business_income = business_df.loc[
        business_df["τύπος"] == "Έσοδο", "ποσό"
    ].sum() if not business_df.empty else 0.0
    business_expenses = business_df.loc[
        business_df["τύπος"] == "Έξοδο", "ποσό"
    ].sum() if not business_df.empty else 0.0

    bcol1, bcol2, bcol3 = st.columns(3)
    bcol1.metric("Έσοδα φωτογραφίας", format_currency(business_income), border=True)
    bcol2.metric("Έξοδα φωτογραφίας", format_currency(business_expenses), border=True)
    bcol3.metric(
        "Καθαρό αποτέλεσμα",
        format_currency(business_income - business_expenses),
        border=True,
    )

    st.subheader("Κινήσεις φωτογραφίας")

    if business_df.empty:
        st.info(
            "Δεν υπάρχουν ακόμη κινήσεις με δραστηριότητα «Φωτογραφία» "
            "για αυτό το φίλτρο. Καταχώρησέ τες από τις "
            "«Καθημερινές κινήσεις», επιλέγοντας δραστηριότητα «Φωτογραφία»."
        )
    else:
        business_display = business_df.sort_values(
            "ημερομηνία", ascending=False
        ).copy()
        business_display["ημερομηνία"] = (
            business_display["ημερομηνία"].dt.strftime("%d/%m/%Y")
        )
        business_display["ποσό"] = business_display["ποσό"].apply(
            format_currency
        )

        st.dataframe(
            business_display[
                [
                    "ημερομηνία",
                    "τύπος",
                    "κατηγορία",
                    "περιγραφή",
                    "ποσό",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "ημερομηνία": "Ημερομηνία",
                "τύπος": "Τύπος",
                "κατηγορία": "Κατηγορία",
                "περιγραφή": "Περιγραφή",
                "ποσό": "Ποσό",
            },
        )

        business_csv = business_df.copy()
        business_csv["ημερομηνία"] = (
            business_csv["ημερομηνία"].dt.strftime("%Y-%m-%d")
        )
        st.download_button(
            "Λήψη κινήσεων φωτογραφίας σε CSV",
            data=business_csv.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"fotografia_{int(selected_business_year)}.csv",
            mime="text/csv",
        )


elif page == "📈 Οικονομική οργάνωση":
    st.header("Οικονομική οργάνωση")
    st.caption(
        "Ανάλυσε συνολικά ή ξεχωριστά κάθε κατηγορία, όπως "
        "«Επιχείρηση», και κάθε περιγραφή, όπως «Ρεύμα»."
    )

    analytics_tab, month_close_tab, year_close_tab, targets_tab = st.tabs(
        [
            "Στατιστικά",
            "Κλείσιμο μήνα",
            "Κλείσιμο έτους",
            "Στόχοι",
        ]
    )

    all_categories = available_financial_categories(transactions_df)

    with analytics_tab:
        current_year = date.today().year
        filter_col1, filter_col2, filter_col3 = st.columns(3)

        with filter_col1:
            analytics_year = int(
                st.number_input(
                    "Έτος ανάλυσης",
                    min_value=2020,
                    max_value=2100,
                    value=current_year,
                    step=1,
                    key="analytics_year",
                )
            )
        with filter_col2:
            analytics_category = st.selectbox(
                "Κατηγορία",
                all_categories,
                key="analytics_category",
            )
        with filter_col3:
            analytics_descriptions = available_financial_descriptions(
                transactions_df,
                analytics_category,
            )
            analytics_description = st.selectbox(
                "Περιγραφή",
                analytics_descriptions,
                key="analytics_description",
            )

        analytics_df = filter_financial_transactions(
            transactions_df,
            year=analytics_year,
            category=analytics_category,
            description=analytics_description,
        )
        previous_df = filter_financial_transactions(
            transactions_df,
            year=analytics_year - 1,
            category=analytics_category,
            description=analytics_description,
        )

        current_summary = financial_summary(analytics_df)
        previous_summary = financial_summary(previous_df)

        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric(
            "Έσοδα",
            format_currency(current_summary["income"]),
            delta=format_currency(
                current_summary["income"] - previous_summary["income"]
            ),
            border=True,
        )
        metric2.metric(
            "Έξοδα",
            format_currency(current_summary["expenses"]),
            delta=format_currency(
                current_summary["expenses"] - previous_summary["expenses"]
            ),
            delta_color="inverse",
            border=True,
        )
        metric3.metric(
            "Υπόλοιπο",
            format_currency(current_summary["balance"]),
            delta=format_currency(
                current_summary["balance"] - previous_summary["balance"]
            ),
            border=True,
        )
        metric4.metric(
            "Κινήσεις",
            str(current_summary["transactions"]),
            delta=(
                current_summary["transactions"]
                - previous_summary["transactions"]
            ),
            border=True,
        )

        st.caption(
            f"Οι μεταβολές συγκρίνουν το {analytics_year} "
            f"με το {analytics_year - 1}."
        )

        if analytics_df.empty:
            st.info("Δεν υπάρχουν κινήσεις για τα επιλεγμένα φίλτρα.")
        else:
            monthly_analysis = analytics_df.copy()
            monthly_analysis["μήνας"] = (
                monthly_analysis["μήνας_αναφοράς"]
            )
            monthly_grouped = (
                monthly_analysis
                .groupby(["μήνας", "τύπος"], as_index=False)["ποσό"]
                .sum()
            )
            monthly_grouped["Μήνας"] = monthly_grouped["μήνας"].map(
                {
                    1: "Ιαν",
                    2: "Φεβ",
                    3: "Μαρ",
                    4: "Απρ",
                    5: "Μαϊ",
                    6: "Ιουν",
                    7: "Ιουλ",
                    8: "Αυγ",
                    9: "Σεπ",
                    10: "Οκτ",
                    11: "Νοε",
                    12: "Δεκ",
                }
            )

            palette = THEMES.get(
                st.session_state.get(
                    "selected_app_theme",
                    "Πετρόλ",
                ),
                THEMES["Πετρόλ"],
            )

            monthly_chart = (
                alt.Chart(monthly_grouped)
                .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                .encode(
                    x=alt.X(
                        "Μήνας:N",
                        sort=[
                            "Ιαν", "Φεβ", "Μαρ", "Απρ",
                            "Μαϊ", "Ιουν", "Ιουλ", "Αυγ",
                            "Σεπ", "Οκτ", "Νοε", "Δεκ",
                        ],
                        title=None,
                    ),
                    y=alt.Y("ποσό:Q", title="Ποσό (€)"),
                    color=alt.Color(
                        "τύπος:N",
                        title="Τύπος",
                        scale=alt.Scale(
                            domain=["Έσοδο", "Έξοδο"],
                            range=[
                                palette["main"],
                                palette["deep"],
                            ],
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip("Μήνας:N"),
                        alt.Tooltip("τύπος:N", title="Τύπος"),
                        alt.Tooltip(
                            "ποσό:Q",
                            title="Ποσό",
                            format=".2f",
                        ),
                    ],
                )
                .properties(height=350)
            )
            st.altair_chart(monthly_chart, use_container_width=True)

            detail_grouped = (
                analytics_df
                .assign(
                    περιγραφή=analytics_df["περιγραφή"]
                    .astype(str)
                    .replace("", "Χωρίς περιγραφή")
                )
                .groupby(
                    ["κατηγορία", "περιγραφή", "τύπος"],
                    as_index=False,
                )["ποσό"]
                .sum()
                .sort_values("ποσό", ascending=False)
            )

            st.subheader("Ανάλυση ανά περιγραφή")
            st.dataframe(
                detail_grouped.rename(
                    columns={
                        "κατηγορία": "Κατηγορία",
                        "περιγραφή": "Περιγραφή",
                        "τύπος": "Τύπος",
                        "ποσό": "Ποσό",
                    }
                ),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Ποσό": st.column_config.NumberColumn(
                        "Ποσό",
                        format="%.2f €",
                    ),
                },
            )

            render_export_buttons(
                f"Οικονομική ανάλυση {analytics_year}",
                {
                    "Κινήσεις": analytics_df,
                    "Ανάλυση": detail_grouped,
                    "Μηνιαία σύνολα": monthly_grouped,
                },
                f"financial_analysis_{analytics_year}",
                f"financial_analysis_{analytics_year}",
            )

    with month_close_tab:
        close_col1, close_col2, close_col3 = st.columns(3)
        with close_col1:
            close_month = st.selectbox(
                "Μήνας",
                list(range(1, 13)),
                format_func=lambda value: MONTH_NAMES_FULL[value],
                index=date.today().month - 1,
                key="close_month",
            )
        with close_col2:
            close_month_year = int(
                st.number_input(
                    "Έτος",
                    min_value=2020,
                    max_value=2100,
                    value=date.today().year,
                    step=1,
                    key="close_month_year",
                )
            )
        with close_col3:
            close_month_category = st.selectbox(
                "Κατηγορία",
                all_categories,
                key="close_month_category",
            )

        month_descriptions = available_financial_descriptions(
            transactions_df,
            close_month_category,
        )
        close_month_description = st.selectbox(
            "Περιγραφή",
            month_descriptions,
            key="close_month_description",
        )

        month_close_df = filter_financial_transactions(
            transactions_df,
            year=close_month_year,
            month=close_month,
            category=close_month_category,
            description=close_month_description,
        )
        month_close_summary = financial_summary(month_close_df)

        close_metric1, close_metric2, close_metric3 = st.columns(3)
        close_metric1.metric(
            "Έσοδα περιόδου",
            format_currency(month_close_summary["income"]),
            border=True,
        )
        close_metric2.metric(
            "Έξοδα περιόδου",
            format_currency(month_close_summary["expenses"]),
            border=True,
        )
        close_metric3.metric(
            "Υπόλοιπο περιόδου",
            format_currency(month_close_summary["balance"]),
            border=True,
        )

        month_close_notes = st.text_area(
            "Σημειώσεις κλεισίματος μήνα",
            key="month_close_notes",
            placeholder=(
                "π.χ. αυξημένο ρεύμα, έκτακτη αγορά εξοπλισμού, "
                "καλύτερη απόδοση πωλήσεων"
            ),
        )

        if st.button(
            "Αποθήκευση κλεισίματος μήνα",
            use_container_width=True,
            type="primary",
            key="save_month_close_v54",
        ):
            if save_financial_close(
                "Μήνας",
                close_month_year,
                close_month,
                close_month_category,
                close_month_description,
                month_close_summary,
                savings_total(savings_df),
                month_close_notes,
            ):
                st.success("Το κλείσιμο μήνα αποθηκεύτηκε.")
                st.rerun()

    with year_close_tab:
        year_close_col1, year_close_col2 = st.columns(2)
        with year_close_col1:
            close_year = int(
                st.number_input(
                    "Έτος κλεισίματος",
                    min_value=2020,
                    max_value=2100,
                    value=date.today().year,
                    step=1,
                    key="close_year",
                )
            )
        with year_close_col2:
            close_year_category = st.selectbox(
                "Κατηγορία",
                all_categories,
                key="close_year_category",
            )

        year_descriptions = available_financial_descriptions(
            transactions_df,
            close_year_category,
        )
        close_year_description = st.selectbox(
            "Περιγραφή",
            year_descriptions,
            key="close_year_description",
        )

        year_close_df = filter_financial_transactions(
            transactions_df,
            year=close_year,
            category=close_year_category,
            description=close_year_description,
        )
        year_close_summary = financial_summary(year_close_df)

        previous_year_df = filter_financial_transactions(
            transactions_df,
            year=close_year - 1,
            category=close_year_category,
            description=close_year_description,
        )
        previous_year_summary = financial_summary(previous_year_df)

        year_metric1, year_metric2, year_metric3 = st.columns(3)
        year_metric1.metric(
            "Έσοδα έτους",
            format_currency(year_close_summary["income"]),
            delta=format_currency(
                year_close_summary["income"]
                - previous_year_summary["income"]
            ),
            border=True,
        )
        year_metric2.metric(
            "Έξοδα έτους",
            format_currency(year_close_summary["expenses"]),
            delta=format_currency(
                year_close_summary["expenses"]
                - previous_year_summary["expenses"]
            ),
            delta_color="inverse",
            border=True,
        )
        year_metric3.metric(
            "Υπόλοιπο έτους",
            format_currency(year_close_summary["balance"]),
            delta=format_currency(
                year_close_summary["balance"]
                - previous_year_summary["balance"]
            ),
            border=True,
        )

        year_close_notes = st.text_area(
            "Σημειώσεις κλεισίματος έτους",
            key="year_close_notes",
        )

        if st.button(
            "Αποθήκευση κλεισίματος έτους",
            use_container_width=True,
            type="primary",
            key="save_year_close_v54",
        ):
            if save_financial_close(
                "Έτος",
                close_year,
                0,
                close_year_category,
                close_year_description,
                year_close_summary,
                savings_total(savings_df),
                year_close_notes,
            ):
                st.success("Το κλείσιμο έτους αποθηκεύτηκε.")
                st.rerun()

        if not financial_closes_df.empty:
            saved_year_closes = financial_closes_df[
                financial_closes_df["τύπος_περιόδου"] == "Έτος"
            ].copy()
            if not saved_year_closes.empty:
                st.subheader("Αποθηκευμένα κλεισίματα ετών")
                st.dataframe(
                    saved_year_closes.sort_values(
                        "έτος",
                        ascending=False,
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

    with targets_tab:
        target_col1, target_col2 = st.columns(2)
        with target_col1:
            target_year = int(
                st.number_input(
                    "Έτος στόχου",
                    min_value=2020,
                    max_value=2100,
                    value=date.today().year,
                    step=1,
                    key="target_year_v54",
                )
            )
        with target_col2:
            target_category = st.selectbox(
                "Κατηγορία στόχου",
                all_categories,
                key="target_category_v54",
            )

        target_descriptions = available_financial_descriptions(
            transactions_df,
            target_category,
        )
        target_description = st.selectbox(
            "Περιγραφή στόχου",
            target_descriptions,
            key="target_description_v54",
        )
        target_type = st.radio(
            "Είδος στόχου",
            ["Μέγιστο έξοδο", "Ελάχιστο έσοδο"],
            horizontal=True,
            key="target_type_v54",
        )
        target_amount_text = st.text_input(
            "Ποσό στόχου",
            placeholder="0,00",
            key="target_amount_v54",
        )
        target_notes = st.text_area(
            "Σημειώσεις στόχου",
            key="target_notes_v54",
            placeholder="π.χ. Σύγκριση παρόχου ηλεκτρικής ενέργειας",
        )

        if st.button(
            "Αποθήκευση στόχου",
            use_container_width=True,
            type="primary",
            key="save_target_v54",
        ):
            target_amount = float(parse_number(target_amount_text))
            if target_amount <= 0:
                st.warning("Το ποσό στόχου πρέπει να είναι μεγαλύτερο από μηδέν.")
            elif save_analytics_target(
                target_year,
                target_category,
                target_description,
                target_type,
                target_amount,
                target_notes,
            ):
                st.success("Ο στόχος αποθηκεύτηκε.")
                st.rerun()

        if analytics_targets_df.empty:
            st.info("Δεν υπάρχουν ακόμη αποθηκευμένοι στόχοι.")
        else:
            st.subheader("Παρακολούθηση στόχων")

            for _, target in analytics_targets_df.sort_values(
                ["έτος", "κατηγορία", "περιγραφή"],
                ascending=[False, True, True],
            ).iterrows():
                target_data = filter_financial_transactions(
                    transactions_df,
                    year=int(target["έτος"]),
                    category=str(target["κατηγορία"]),
                    description=str(target["περιγραφή"]),
                )
                target_summary = financial_summary(target_data)
                actual = (
                    target_summary["expenses"]
                    if str(target["τύπος"]) == "Μέγιστο έξοδο"
                    else target_summary["income"]
                )
                target_amount = float(target["ποσό_στόχου"])
                progress = (
                    min(actual / target_amount, 1.0)
                    if target_amount > 0
                    else 0.0
                )

                with st.container(border=True):
                    st.write(
                        f"**{int(target['έτος'])} · "
                        f"{target['κατηγορία']} · "
                        f"{target['περιγραφή']}**"
                    )
                    st.caption(str(target["τύπος"]))
                    st.progress(
                        progress,
                        text=(
                            f"Πραγματικό {format_currency(actual)} από "
                            f"στόχο {format_currency(target_amount)}"
                        ),
                    )
                    if str(target.get("σημειώσεις", "")).strip():
                        st.caption(str(target["σημειώσεις"]))


elif page == "📊 Ιστορικό":
    st.header("Ιστορικό οικονομικών κινήσεων")
    render_export_buttons(
        "Ιστορικό οικονομικών κινήσεων",
        {"Ιστορικό": transactions_df},
        "istoriko_kiniseon",
        "history_export",
    )

    if transactions_df.empty:
        st.info("Δεν υπάρχουν ακόμη κινήσεις.")
    else:
        available_years = sorted(
            transactions_df["ημερομηνία"]
            .dropna()
            .dt.year
            .unique()
            .tolist(),
            reverse=True,
        )

        current_year = datetime.now().year

        if current_year not in available_years:
            available_years.insert(0, current_year)

        selected_year = st.number_input(
            "Έτος",
            min_value=2000,
            max_value=2100,
            value=datetime.now().year,
            step=1,
            key="history_year_buttons",
        )
        final_year = int(selected_year)

        month_labels = [
            "Όλοι",
            "Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαϊ", "Ιουν",
            "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ",
        ]

        selected_month_name = render_choice_buttons(
            "Μήνας",
            month_labels,
            "history_month_buttons",
            columns=4,
        )

        month_lookup = {
            "Όλοι": 0,
            "Ιαν": 1, "Φεβ": 2, "Μαρ": 3, "Απρ": 4,
            "Μαϊ": 5, "Ιουν": 6, "Ιουλ": 7, "Αυγ": 8,
            "Σεπ": 9, "Οκτ": 10, "Νοε": 11, "Δεκ": 12,
        }
        selected_month = month_lookup.get(selected_month_name, 0)

        final_type = render_choice_buttons(
            "Τύπος",
            ["Όλα", "Έσοδο", "Έξοδο"],
            "history_type_buttons",
            columns=3,
        ) or "Όλα"

        final_activity = render_choice_buttons(
            "Δραστηριότητα",
            ["Όλες", "Γενικά", "Φωτογραφία"],
            "history_activity_buttons",
            columns=3,
        ) or "Όλες"

        history_df = transactions_df[
            transactions_df["ημερομηνία"].dt.year == final_year
        ].copy()

        if selected_month:
            history_df = history_df[
                history_df["ημερομηνία"].dt.month == int(selected_month)
            ]

        if final_type != "Όλα":
            history_df = history_df[
                history_df["τύπος"] == final_type
            ]

        if final_activity != "Όλες":
            history_df = history_df[
                history_df["δραστηριότητα"] == final_activity
            ]

        history_income = history_df.loc[
            history_df["τύπος"] == "Έσοδο",
            "ποσό",
        ].sum()

        history_expenses = history_df.loc[
            history_df["τύπος"] == "Έξοδο",
            "ποσό",
        ].sum()

        metric1, metric2, metric3 = st.columns(3)

        metric1.metric("Έσοδα", format_currency(history_income), border=True)
        metric2.metric("Έξοδα", format_currency(history_expenses), border=True)
        metric3.metric(
            "Υπόλοιπο",
            format_currency(history_income - history_expenses),
            border=True,
        )

        st.subheader("Αναλυτικές κινήσεις")

        if history_df.empty:
            st.info("Δεν βρέθηκαν κινήσεις με αυτά τα φίλτρα.")
        else:
            display_df = history_df.sort_values(
                "ημερομηνία",
                ascending=False,
            ).copy()

            display_df["ημερομηνία"] = (
                display_df["ημερομηνία"]
                .dt.strftime("%d/%m/%Y")
            )

            display_df["ποσό"] = display_df["ποσό"].apply(format_currency)

            visible_columns = [
                "ημερομηνία",
                "έτος_αναφοράς",
                "μήνας_αναφοράς",
                "τύπος",
                "κατηγορία",
                "περιγραφή",
                "ποσό",
                "πηγή_χρημάτων",
                "δραστηριότητα",
            ]

            st.dataframe(
                display_df[visible_columns],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ημερομηνία": "Ημερομηνία",
                    "τύπος": "Τύπος",
                    "κατηγορία": "Κατηγορία",
                    "περιγραφή": "Περιγραφή",
                    "ποσό": "Ποσό",
                    "τρόπος_πληρωμής": "Τρόπος",
                    "πάγιο": "Πάγιο",
                    "δραστηριότητα": "Δραστηριότητα",
                    "αρχείο": st.column_config.LinkColumn(
                        "Αρχείο",
                        display_text="Άνοιγμα",
                    ),
                },
            )

            csv_df = history_df.copy()
            csv_df["ημερομηνία"] = (
                csv_df["ημερομηνία"]
                .dt.strftime("%Y-%m-%d")
            )

            csv_data = csv_df.to_csv(index=False).encode("utf-8-sig")

            st.download_button(
                "Λήψη κινήσεων σε CSV",
                data=csv_data,
                file_name=f"oikonomikes_kiniseis_{final_year}.csv",
                mime="text/csv",
            )

            with st.expander("Διαγραφή λανθασμένης καταχώρησης"):
                delete_options = {}

                for _, row in history_df.sort_values(
                    "ημερομηνία",
                    ascending=False,
                ).iterrows():
                    date_text = row["ημερομηνία"].strftime("%d/%m/%Y")

                    label = (
                        f"{date_text} · "
                        f"{row['περιγραφή']} · "
                        f"{format_currency(row['ποσό'])}"
                    )

                    delete_options[label] = row["id"]

                selected_delete_label = st.selectbox(
                    "Επίλεξε την κίνηση",
                    [CUSTOM_OPTION] + list(delete_options.keys()),
                )

                if selected_delete_label == CUSTOM_OPTION:
                    custom_delete_id = st.text_input(
                        "Γράψε το ID της κίνησης",
                        placeholder="Μόνο αν γνωρίζεις το ID",
                    )
                    selected_delete_id = custom_delete_id.strip()
                else:
                    selected_delete_id = delete_options[selected_delete_label]

                confirm_delete = st.checkbox(
                    "Επιβεβαιώνω ότι θέλω να διαγραφεί"
                )

                if st.button("Διαγραφή κίνησης"):
                    if not selected_delete_id:
                        st.warning("Επίλεξε μία κίνηση.")
                    elif not confirm_delete:
                        st.warning("Χρειάζεται επιβεβαίωση.")
                    elif delete_transaction_with_counterpart(selected_delete_id):
                        st.success("Η κίνηση διαγράφηκε.")
                        st.rerun()
                    else:
                        st.error("Η κίνηση δεν βρέθηκε.")


# =========================================================
# ΡΥΘΜΙΣΕΙΣ
# =========================================================

elif page == "✏️ Διαχείριση δεδομένων":
    st.header("Επεξεργασία και διαγραφή")
    st.caption("Εδώ μπορείς να διορθώσεις ή να διαγράψεις οποιαδήποτε καταχώρηση από όλες τις καρτέλες.")
    datasets={
        "Κινήσεις":(TRANSACTIONS_SHEET,transactions_ws,transactions_df),
        "Υπενθυμίσεις":(REMINDERS_SHEET,reminders_ws,reminders_df),
        "Προς πληρωμή":(TASKS_SHEET,tasks_ws,tasks_df),
        "Οφειλές":(DEBTS_SHEET,debts_ws,debts_df),
        "Κινήσεις οφειλών":(DEBT_MOVEMENTS_SHEET,debt_movements_ws,debt_movements_df),
        "Προϋπολογισμοί":(MONTHLY_BUDGET_SHEET,monthly_budget_ws,monthly_budget_df),
        "Γραμμές προϋπολογισμού":(BUDGET_ITEMS_SHEET,budget_items_ws,budget_items_df),
        "Κατάσταση προϋπολογισμού":(BUDGET_STATUS_SHEET,budget_status_ws,budget_status_df),
        "Πάγια":(RECURRING_SHEET,recurring_ws,recurring_df),
        "Έγγραφα":(DOCUMENTS_SHEET,documents_ws,documents_df),
        "Αποταμίευση":(SAVINGS_SHEET,savings_ws,savings_df),
        "Προσαρμοσμένες επιλογές":(
            CUSTOM_OPTIONS_SHEET,
            custom_options_ws,
            custom_options_df,
        ),
        "Κλεισίματα περιόδων":(
            FINANCIAL_CLOSES_SHEET,
            financial_closes_ws,
            financial_closes_df,
        ),
        "Στόχοι ανάλυσης":(
            ANALYTICS_TARGETS_SHEET,
            analytics_targets_ws,
            analytics_targets_df,
        ),
    }
    selected=render_choice_buttons("Δεδομένα",list(datasets.keys()),"manage_dataset",columns=3) or "Κινήσεις"
    sheet_name,worksheet,df=datasets[selected]
    editable=clean_export_dataframe(df)
    editable.insert(0,"διαγραφή",False)
    edited=st.data_editor(editable,use_container_width=True,hide_index=True,num_rows="dynamic",key=f"editor_{sheet_name}")
    st.warning("Τσέκαρε «διαγραφή» στις γραμμές που θέλεις να αφαιρέσεις και πάτησε Αποθήκευση.")
    if st.button("Αποθήκευση αλλαγών",use_container_width=True,type="primary",key=f"save_editor_{sheet_name}"):
        delete_mask = edited["διαγραφή"].fillna(False)
        deleted_ids = edited.loc[delete_mask, "id"].astype(str).tolist()             if "id" in edited.columns else []
        kept=edited[~delete_mask].copy()

        if selected == "Κινήσεις":
            for deleted_id in deleted_ids:
                delete_transaction_with_counterpart(deleted_id)
        elif selected == "Αποταμίευση":
            for deleted_id in deleted_ids:
                delete_savings_with_counterpart(deleted_id)

        replace_worksheet_records(worksheet,sheet_name,kept)
        st.success("Οι αλλαγές αποθηκεύτηκαν και τα συνδεδεμένα ποσά αντιλογίστηκαν.")
        st.rerun()


elif page == "⚙️ Ρυθμίσεις":
    st.header("Ρυθμίσεις")

    st.markdown(
        """
        <div class="theme-message">
            Η v50 χρησιμοποιεί νέα, καθαρά φύλλα με πρόθεμα
            <strong>PH v50</strong>. Τα παλιά δεδομένα παραμένουν
            ανέπαφα στα προηγούμενα φύλλα και δεν χρησιμοποιούνται
            από αυτή την έκδοση.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Δικές μου κατηγορίες και επιλογές")
    st.caption(
        "Οι βασικές επιλογές παραμένουν λίγες. Εδώ προσθέτεις όσα "
        "χρησιμοποιείς πραγματικά και μπορείς να τα διαγράψεις από "
        "τη Διαχείριση δεδομένων."
    )
    with st.form("custom_option_manager_v49", clear_on_submit=True):
        custom_context = st.selectbox(
            "Πού θα εμφανίζεται",
            [
                "Κατηγορία εξόδου",
                "Περιγραφή εξόδου",
                "Κατηγορία εσόδου",
                "Περιγραφή εσόδου",
                "Κατηγορία παγίου",
                "Τρόπος πληρωμής",
                "Κατηγορία υπενθύμισης",
            ],
        )
        context_map = {
            "Κατηγορία εξόδου": "transaction_category_Έξοδο",
            "Περιγραφή εξόδου": "transaction_description_Έξοδο_Άλλο",
            "Κατηγορία εσόδου": "transaction_category_Έσοδο",
            "Περιγραφή εσόδου": "transaction_description_Έσοδο_Άλλο",
            "Κατηγορία παγίου": "recurring_category",
            "Τρόπος πληρωμής": "payment_method",
            "Κατηγορία υπενθύμισης": "reminder_category",
        }
        custom_value = st.text_input(
            "Νέα επιλογή",
            placeholder="π.χ. Κατοικίδιο",
        )
        add_custom_value = st.form_submit_button(
            "Προσθήκη επιλογής",
            use_container_width=True,
        )
    if add_custom_value:
        if not custom_value.strip():
            st.warning("Γράψε μία επιλογή.")
        else:
            save_custom_option(
                context_map[custom_context],
                custom_value.strip(),
            )
            st.success("Η επιλογή αποθηκεύτηκε.")
            st.rerun()


    st.divider()
    st.subheader("Διαγραφή ή απόκρυψη επιλογών")
    st.caption(
        "Η επιλογή αφαιρείται μόνο από τα κουμπιά της εφαρμογής. "
        "Οι παλιές κινήσεις, οι μήνες και τα ποσά τους παραμένουν "
        "κανονικά στο ιστορικό και στα Google Sheets."
    )

    manage_group = st.selectbox(
        "Τι θέλεις να διαχειριστείς;",
        [
            "Κατηγορίες εξόδων",
            "Κατηγορίες εσόδων",
            "Περιγραφές εξόδων",
            "Περιγραφές εσόδων",
            "Κατηγορίες παγίων",
            "Τρόποι πληρωμής",
        ],
        key="v53_manage_option_group",
    )

    if manage_group == "Κατηγορίες εξόδων":
        manage_context = "transaction_category_Έξοδο"
    elif manage_group == "Κατηγορίες εσόδων":
        manage_context = "transaction_category_Έσοδο"
    elif manage_group == "Κατηγορίες παγίων":
        manage_context = "recurring_category"
    elif manage_group == "Τρόποι πληρωμής":
        manage_context = "payment_method"
    elif manage_group == "Περιγραφές εξόδων":
        description_category = st.selectbox(
            "Κατηγορία εξόδου",
            list(EXPENSE_CATEGORIES.keys())
            + saved_custom_options("transaction_category_Έξοδο"),
            key="v53_manage_expense_description_category",
        )
        manage_context = (
            f"transaction_description_Έξοδο_{description_category}"
        )
    else:
        description_category = st.selectbox(
            "Κατηγορία εσόδου",
            list(INCOME_CATEGORIES.keys())
            + saved_custom_options("transaction_category_Έσοδο"),
            key="v53_manage_income_description_category",
        )
        manage_context = (
            f"transaction_description_Έσοδο_{description_category}"
        )

    manage_base = base_options_for_context(manage_context)
    manage_custom = saved_custom_options(manage_context)
    hidden_values = hidden_custom_options(manage_context)
    active_values = []
    for option_value in manage_base + manage_custom:
        if option_value and option_value not in active_values:
            active_values.append(option_value)

    if not active_values:
        st.info("Δεν υπάρχουν ενεργές επιλογές σε αυτή την ενότητα.")
    else:
        selected_option_to_remove = st.selectbox(
            "Επιλογή",
            active_values,
            key="v53_option_to_remove",
        )
        usage = option_usage_details(
            manage_context,
            selected_option_to_remove,
        )
        is_base = selected_option_to_remove in manage_base

        if usage["count"] == 0:
            st.info(
                "Η επιλογή δεν χρησιμοποιείται σε καμία καταχώρηση "
                "και μπορεί να αφαιρεθεί άμεσα."
            )
            first_confirmation = True
            second_confirmation = True
        else:
            st.warning(
                f"Η επιλογή αυτή χρησιμοποιείται σε {usage['count']} "
                f"παλιές ή ενεργές εγγραφές, συνολικού ποσού "
                f"{format_currency(usage['amount'])} στις οικονομικές "
                "κινήσεις. Οι εγγραφές και τα ποσά δεν θα διαγραφούν."
            )
            first_confirmation = st.checkbox(
                "Καταλαβαίνω ότι η επιλογή θα φύγει μόνο από το interface.",
                key="v53_remove_first_confirm",
            )
            second_confirmation = st.checkbox(
                "Ναι, είμαι σίγουρη ότι θέλω να την αφαιρέσω.",
                key="v53_remove_second_confirm",
            )

        if st.button(
            "Αφαίρεση επιλογής",
            use_container_width=True,
            key="v53_remove_option_button",
            disabled=not (first_confirmation and second_confirmation),
        ):
            if remove_option_from_interface(
                manage_context,
                selected_option_to_remove,
                is_base_option=is_base,
            ):
                st.success(
                    "Η επιλογή αφαιρέθηκε από το interface. "
                    "Τα ιστορικά δεδομένα διατηρήθηκαν."
                )
                st.rerun()
            else:
                st.error("Η επιλογή δεν μπόρεσε να αφαιρεθεί.")

    if hidden_values:
        with st.expander("Επαναφορά κρυμμένης βασικής επιλογής"):
            restore_value = st.selectbox(
                "Κρυμμένη επιλογή",
                hidden_values,
                key="v53_restore_hidden_value",
            )
            if st.button(
                "Επαναφορά",
                use_container_width=True,
                key="v53_restore_hidden_button",
            ):
                if restore_hidden_option(manage_context, restore_value):
                    st.success("Η επιλογή επανήλθε στα κουμπιά.")
                    st.rerun()

    settings_export_df = pd.DataFrame(
        [
            {
                "Ρύθμιση": "Θέμα",
                "Τιμή": st.session_state.get(
                    "selected_app_theme",
                    "Πετρόλ",
                ),
            },
            {
                "Ρύθμιση": "Προεπιλεγμένος τρόπος πληρωμής",
                "Τιμή": st.session_state.get(
                    "preferred_payment_method",
                    "Κάρτα",
                ),
            },
            {
                "Ρύθμιση": "Μετά την αποθήκευση",
                "Τιμή": st.session_state.get(
                    "return_after_save_buttons",
                    "Επιστροφή στην αρχική",
                ),
            },
            {
                "Ρύθμιση": "Προβολή Υποχρεώσεων",
                "Τιμή": st.session_state.get(
                    "preferred_obligation_view",
                    "Ανοιχτές",
                ),
            },
            {
                "Ρύθμιση": "Έκδοση εφαρμογής",
                "Τιμή": APP_VERSION,
            },
        ]
    )

    render_export_buttons(
        "Ρυθμίσεις εφαρμογής",
        {"Ρυθμίσεις": settings_export_df},
        "rythmiseis_efarmogis",
        "settings_export",
    )
    st.caption("Θέμα, προεπιλογές και λειτουργία του προσωπικού control center.")

    st.subheader("Θέμα εφαρμογής")

    if "selected_app_theme" not in st.session_state:
        st.session_state["selected_app_theme"] = "Πετρόλ"

    selected_theme = render_choice_buttons(
        "Επίλεξε χρωματική παλέτα",
        list(THEMES.keys()),
        "selected_app_theme",
        columns=2,
    )

    if not selected_theme:
        selected_theme = "Πετρόλ"
        st.session_state["selected_app_theme"] = selected_theme

    current_palette = THEMES[selected_theme]

    st.markdown(
        f"""
        <div class="theme-preview">
            <div class="theme-preview-title">
                Θέμα: {selected_theme}
            </div>
            <div>
                Έτσι θα εμφανίζονται τα ενεργά κουμπιά,
                τα περιγράμματα και οι λεπτομέρειες της εφαρμογής.
            </div>
            <div class="theme-preview-dots">
                <span class="theme-preview-dot"
                    style="background:{current_palette['main']}"></span>
                <span class="theme-preview-dot"
                    style="background:{current_palette['deep']}"></span>
                <span class="theme-preview-dot"
                    style="background:{current_palette['border']}"></span>
                <span class="theme-preview-dot"
                    style="background:{current_palette['soft']}"></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Η αλλαγή εφαρμόζεται αμέσως σε όλη την εφαρμογή."
    )

    st.divider()
    st.subheader("Προεπιλεγμένος τρόπος πληρωμής")

    preferred_payment = render_choice_buttons(
        "Όταν ανοίγεις νέα καταχώρηση",
        [
            "Κάρτα",
            "Μετρητά",
            "Τραπεζική μεταφορά",
            "Πάγια εντολή",
            "IRIS",
        ],
        "preferred_payment_method",
        columns=2,
    )

    if not preferred_payment:
        st.session_state["preferred_payment_method"] = "Κάρτα"
        preferred_payment = "Κάρτα"

    st.caption(
        f"Η νέα καταχώρηση θα ξεκινά με επιλεγμένο: "
        f"{preferred_payment}."
    )

    st.divider()
    st.subheader("Μετά την αποθήκευση κίνησης")

    return_choice = render_choice_buttons(
        "Τι θέλεις να γίνεται;",
        ["Επιστροφή στην αρχική", "Παραμονή στην καταχώρηση"],
        "return_after_save_buttons",
        columns=2,
    )

    if not return_choice:
        return_choice = "Επιστροφή στην αρχική"
        st.session_state["return_after_save_buttons"] = return_choice

    st.session_state["return_home_after_save_preference"] = (
        return_choice == "Επιστροφή στην αρχική"
    )

    st.divider()
    st.subheader("Προεπιλεγμένη καρτέλα Υποχρεώσεων")

    preferred_obligation_view = render_choice_buttons(
        "Όταν ανοίγεις τις Υποχρεώσεις",
        ["Ανοιχτές", "Ολοκληρωμένα"],
        "preferred_obligation_view",
        columns=2,
    )

    if not preferred_obligation_view:
        st.session_state["preferred_obligation_view"] = "Ανοιχτές"
        preferred_obligation_view = "Ανοιχτές"

    st.caption(
        f"Οι Υποχρεώσεις θα ανοίγουν στην καρτέλα: "
        f"{preferred_obligation_view}."
    )

    st.divider()
    st.subheader("Συνδέσεις εφαρμογής")

    connection_col1, connection_col2, connection_col3 = st.columns(3)

    with connection_col1:
        st.markdown(
            """
            <div class="theme-status-card">
                <strong>Google Sheets</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Οικονομικά και υποχρεώσεις")

    with connection_col2:
        st.markdown(
            """
            <div class="theme-status-card">
                <strong>Google Drive</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Αποδείξεις και αρχεία")

    with connection_col3:
        st.markdown(
            """
            <div class="theme-status-card">
                <strong>Google Calendar</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Ραντεβού και υπενθυμίσεις")

    if st.button(
        "Έλεγχος σύνδεσης Google Sheets",
        use_container_width=True,
    ):
        try:
            spreadsheet.fetch_sheet_metadata()
            st.success("Η σύνδεση με το Google Sheet λειτουργεί.")
        except Exception as exc:
            st.error("Υπάρχει πρόβλημα σύνδεσης.")
            st.code(str(exc), language=None)

    st.markdown(
        """
        <div class="theme-info-box">
            Το θέμα και οι προσωπικές επιλογές ισχύουν
            για την τρέχουσα συνεδρία της εφαρμογής.
        </div>
        """,
        unsafe_allow_html=True,
    )
