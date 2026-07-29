import io
import os
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
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


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

TRANSACTIONS_SHEET = "Κινήσεις"
REMINDERS_SHEET = "Υπενθυμίσεις"
TASKS_SHEET = "Εκκρεμότητες"
DEBTS_SHEET = "Οφειλές"
DEBT_MOVEMENTS_SHEET = "Κινήσεις Οφειλών"
MONTHLY_BUDGET_SHEET = "Μηνιαίος Προϋπολογισμός"
GOALS_SHEET = "Οικονομικοί Στόχοι"
RECURRING_SHEET = "Πάγια και Συνδρομές"
ACCOUNTS_SHEET = "Υπόλοιπα Λογαριασμών"
DOCUMENTS_SHEET = "Έγγραφα και Εγγυήσεις"
MONTH_CLOSES_SHEET = "Κλεισίματα Μήνα"

APP_VERSION = "2026.07.29-unified-payments-fix-v37"

CUSTOM_OPTION = "➕ Προσθήκη δικής μου επιλογής"

PIRAEUS_LOAN_NAME = "Δάνειο Πειραιώς"
PIRAEUS_INITIAL_AMOUNT = 15989.04
PIRAEUS_ANNUAL_RATE = 13.15
PIRAEUS_TOTAL_INSTALLMENTS = 96
PIRAEUS_ACTUAL_INSTALLMENT = 269.98
PIRAEUS_FIRST_DUE_DATE = date(2024, 12, 14)


# =========================================================
# ΕΤΟΙΜΕΣ ΕΠΙΛΟΓΕΣ
# =========================================================

EXPENSE_CATEGORIES = {
    "Δάνεια / Κάρτες": [
        "Δάνειο Πειραιώς",
        "Δάνειο Θεία",
        "Δάνειο Γεωργία",
        "Πιστωτική κάρτα Eurobank",
    ],
    "Σπίτι": [
        "Ρεύμα",
        "Νερό",
        "Φυσικό αέριο",
        "Κοινόχρηστα",
        "Ενοίκιο",
        "Internet",
        "Σταθερό τηλέφωνο",
        "Καθαριστικά",
        "Είδη σπιτιού",
        "Μικροεπισκευές",
        "Έπιπλα ή διακόσμηση",
    ],
    "Σούπερ μάρκετ": [
        "Σούπερ μάρκετ",
        "Μανάβικο",
        "Φούρνος",
        "Κρεοπωλείο",
        "Καφές για το σπίτι",
        "Απορρυπαντικά",
        "Είδη προσωπικής φροντίδας",
    ],
    "Μετακινήσεις": [
        "Βενζίνη",
        "Parking",
        "Διόδια",
        "Ταξί",
        "Λεωφορείο",
        "Τρένο",
        "Αεροπορικά εισιτήρια",
    ],
    "Αυτοκίνητο": [
        "Αέριο",
        "Βενζίνη",
        "Ασφάλεια αυτοκινήτου",
        "ΚΤΕΟ",
        "Service",
        "Τέλη κυκλοφορίας",
        "Επισκευή",
        "Ελαστικά",
        "Πλύσιμο αυτοκινήτου",
        "Αξεσουάρ αυτοκινήτου",
    ],
    "Υγεία": [
        "Γιατρός",
        "Φάρμακα",
        "Ιατρικές εξετάσεις",
        "Οδοντίατρος",
        "Γυαλιά ή φακοί",
        "Φυσικοθεραπεία",
        "Συμπληρώματα",
        "Ιδιωτική ασφάλιση",
    ],
    "Προσωπικά": [
        "Ρούχα",
        "Παπούτσια",
        "Καλλυντικά",
        "Κομμωτήριο",
        "Νύχια ή αισθητική",
        "Γυμναστήριο",
        "Βιβλία",
        "Μαθήματα",
        "Χόμπι",
        "Δώρο",
    ],
    "Έξοδος": [
        "Καφές",
        "Φαγητό",
        "Ποτό",
        "Delivery",
        "Σινεμά",
        "Θέατρο",
        "Συναυλία",
        "Εκδρομή",
    ],
    "Συνδρομές": [
        "Netflix",
        "Spotify",
        "YouTube",
        "Cloud",
        "Εφαρμογή",
        "Γυμναστήριο",
        "Τηλεφωνία",
        "Άλλη συνδρομή",
    ],
    "Ταξίδια": [
        "Διαμονή",
        "Αεροπορικά εισιτήρια",
        "Ακτοπλοϊκά εισιτήρια",
        "Καύσιμα ταξιδιού",
        "Φαγητό ταξιδιού",
        "Μετακινήσεις",
        "Δραστηριότητες",
        "Αγορές ταξιδιού",
    ],
    "Οικογένεια": [
        "Δώρο",
        "Οικογενειακή υποχρέωση",
        "Βοήθεια σε συγγενή",
        "Παιδιά",
        "Κατοικίδιο",
    ],
    "Εργασία": [
        "Επαγγελματική μετακίνηση",
        "Εξοπλισμός",
        "Εκτύπωση ή γραφική ύλη",
        "Σεμινάριο",
        "Επαγγελματικό γεύμα",
    ],
    "Άλλο": [
        "Διάφορα",
    ],
}

INCOME_CATEGORIES = {
    "Μισθός": [
        "Μισθός",
        "Επίδομα",
        "Υπερωρίες",
        "Bonus",
        "Αναδρομικά",
    ],
    "Επιπλέον έσοδο": [
        "Πρόσθετη αμοιβή",
        "Επιστροφή χρημάτων",
        "Πώληση αντικειμένου",
        "Δώρο",
        "Επιστροφή φόρου",
        "Επιστροφή από ασφάλεια",
    ],
    "Μεταφορά χρημάτων": [
        "Χρήματα από οικογένεια",
        "Επιστροφή από φίλο",
        "Κατάθεση",
    ],
    "Άλλο": [
        "Άλλο έσοδο",
    ],
}

PAYMENT_METHODS = [
    "Κάρτα",
    "Μετρητά",
    "Τραπεζική μεταφορά",
    "Πάγια εντολή",
    "IRIS",
    CUSTOM_OPTION,
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
    "Δάνειο Πειραιώς",
    "Δάνειο Θεία",
    "Δάνειο Γεωργία",
    "Πιστωτική κάρτα Eurobank",
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
    "Κροκί": {
        "main": "#E6A817",
        "deep": "#B87900",
        "border": "#E7B83F",
        "soft": "#FFF4C7",
        "soft_2": "#FFF9E8",
        "text": "#6A4300",
        "button_text": "#2E2205",
        "shadow": "230, 168, 23",
    },
    "Μπλε": {
        "main": "#4F86C6",
        "deep": "#315F9B",
        "border": "#79A6D8",
        "soft": "#EAF3FC",
        "soft_2": "#F6FAFF",
        "text": "#294F7A",
        "button_text": "#FFFFFF",
        "shadow": "79, 134, 198",
    },
    "Μωβ": {
        "main": "#8A63B8",
        "deep": "#65438F",
        "border": "#A98BCB",
        "soft": "#F2ECF8",
        "soft_2": "#FBF8FD",
        "text": "#563A78",
        "button_text": "#FFFFFF",
        "shadow": "138, 99, 184",
    },
    "Φούξια": {
        "main": "#C84D92",
        "deep": "#99346B",
        "border": "#DA79B1",
        "soft": "#FBEAF4",
        "soft_2": "#FFF7FB",
        "text": "#7E2C59",
        "button_text": "#FFFFFF",
        "shadow": "200, 77, 146",
    },
    "Πράσινο": {
        "main": "#4F8C70",
        "deep": "#35684F",
        "border": "#7AAA91",
        "soft": "#EAF4EF",
        "soft_2": "#F7FBF9",
        "text": "#315E49",
        "button_text": "#FFFFFF",
        "shadow": "79, 140, 112",
    },
    "Ροζ": {
        "main": "#D9869E",
        "deep": "#B55E78",
        "border": "#E5A9BA",
        "soft": "#FCEEF2",
        "soft_2": "#FFF8FA",
        "text": "#8D465B",
        "button_text": "#FFFFFF",
        "shadow": "217, 134, 158",
    },
    "Τερακότα": {
        "main": "#C87557",
        "deep": "#9E5037",
        "border": "#DA987F",
        "soft": "#F9ECE6",
        "soft_2": "#FFF9F6",
        "text": "#82422F",
        "button_text": "#FFFFFF",
        "shadow": "200, 117, 87",
    },
    "Πετρόλ": {
        "main": "#3F8790",
        "deep": "#28636B",
        "border": "#70A8AE",
        "soft": "#E8F3F4",
        "soft_2": "#F6FBFB",
        "text": "#285B61",
        "button_text": "#FFFFFF",
        "shadow": "63, 135, 144",
    },
}


def apply_selected_theme():
    selected_theme = st.session_state.get("selected_app_theme", "Κροκί")
    palette = THEMES.get(selected_theme, THEMES["Κροκί"])

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

            @media (max-width: 768px) {{
                [data-testid="stHorizontalBlock"] {{
                    gap: 0.45rem !important;
                }}

                [data-testid="column"] {{
                    min-width: 0 !important;
                }}

                .stButton > button,
                .stDownloadButton > button,
                .stFormSubmitButton > button {{
                    min-height: 48px !important;
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
        "τύπος",
        "κατηγορία",
        "περιγραφή",
        "ποσό",
        "τρόπος_πληρωμής",
        "πάγιο",
        "αρχείο",
        "σημειώσεις",
        "καταχωρήθηκε",
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
        "αρχικό_ποσό",
        "προεπιλεγμένη_δόση",
        "ετήσιο_επιτόκιο",
        "συνολικές_δόσεις",
        "ημερομηνία_πρώτης_δόσης",
        "τύπος_επιτοκίου",
        "ενεργό",
        "ενημερώθηκε",
    ],
    DEBT_MOVEMENTS_SHEET: [
        "id",
        "debt_id",
        "όνομα",
        "ημερομηνία",
        "τύπος",
        "ποσό",
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
    ],    GOALS_SHEET: [
        "id",
        "όνομα",
        "κατηγορία",
        "ποσό_στόχου",
        "ποσό_συγκεντρώθηκε",
        "ημερομηνία_στόχου",
        "προτεραιότητα",
        "κατάσταση",
        "σημειώσεις",
        "ενημερώθηκε",
    ],
    RECURRING_SHEET: [
        "id",
        "όνομα",
        "κατηγορία",
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
    ACCOUNTS_SHEET: [
        "id",
        "όνομα",
        "τύπος",
        "πραγματικό_υπόλοιπο",
        "υπολογισμένο_υπόλοιπο",
        "ημερομηνία",
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
    MONTH_CLOSES_SHEET: [
        "id",
        "έτος",
        "μήνας",
        "έσοδα",
        "έξοδα",
        "αποταμίευση",
        "πάγια",
        "μεγαλύτερη_κατηγορία",
        "ποσό_μεγαλύτερης_κατηγορίας",
        "εκκρεμείς_υποχρεώσεις",
        "σημειώσεις",
        "κλείστηκε",
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
goals_ws = ensure_worksheet_available(GOALS_SHEET)
recurring_ws = ensure_worksheet_available(RECURRING_SHEET)
accounts_ws = ensure_worksheet_available(ACCOUNTS_SHEET)
documents_ws = ensure_worksheet_available(DOCUMENTS_SHEET)
month_closes_ws = ensure_worksheet_available(MONTH_CLOSES_SHEET)


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
    payment_method,
    recurring,
    file_link="",
    notes="",
):
    transactions_ws.append_row(
        [
            create_id("KIN"),
            transaction_date.isoformat(),
            transaction_type,
            category,
            description,
            float(amount),
            payment_method,
            "Ναι" if recurring else "Όχι",
            file_link,
            notes,
            datetime.now().isoformat(timespec="seconds"),
        ],
        value_input_option="USER_ENTERED",
    )

    refresh_data()


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
    values = get_all_values_with_retry(worksheet, attempts=3)
    if not values:
        return False
    headers = values[0]
    if "id" not in headers:
        return False
    id_index = headers.index("id")
    for row_number, row in enumerate(values[1:], start=2):
        current_id = row[id_index] if id_index < len(row) else ""
        if str(current_id) == str(record_id):
            for column_name, value in updates.items():
                if column_name in headers:
                    worksheet.update_cell(
                        row_number,
                        headers.index(column_name) + 1,
                        value,
                    )
            refresh_data()
            return True
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

    append_transaction(
        transaction_date=date.today(),
        transaction_type="Έξοδο",
        category=task_row.get("κατηγορία", "Λογαριασμοί"),
        description=task_row.get("τίτλος", "Πληρωμή"),
        amount=paid_now,
        payment_method=payment_method,
        recurring=task_row.get("επανάληψη", "Καμία") != "Καμία",
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


def delete_record(worksheet, record_id):
    all_values = worksheet.get_all_values()

    if not all_values:
        return False

    headers = all_values[0]

    if "id" not in headers:
        return False

    id_column = headers.index("id") + 1

    for row_number, row in enumerate(all_values[1:], start=2):
        if len(row) >= id_column and row[id_column - 1] == record_id:
            worksheet.delete_rows(row_number)
            refresh_data()
            return True

    return False


def prepare_transactions(df):
    if df.empty:
        return df.copy()

    result = df.copy()
    result["ημερομηνία"] = pd.to_datetime(
        result["ημερομηνία"],
        errors="coerce",
    )
    result["ποσό"] = result["ποσό"].apply(parse_number)
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
        "αρχικό_ποσό": 0.0,
        "προεπιλεγμένη_δόση": 0.0,
        "ενεργό": "Ναι",
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


def merge_duplicate_piraeus_debts():
    """
    Κρατά μία μόνο εγγραφή για το Δάνειο Πειραιώς.

    Η συγχώνευση είναι εργασία συντήρησης. Αν το Google Sheets API
    έχει προσωρινό πρόβλημα ή όριο κλήσεων, η εφαρμογή συνεχίζει
    κανονικά χωρίς να εκτελέσει τη συγχώνευση σε αυτό το άνοιγμα.
    """
    try:
        debt_values = get_all_values_with_retry(debts_ws, attempts=3)
    except gspread.exceptions.APIError:
        return False

    if len(debt_values) <= 1:
        return False

    debt_headers = debt_values[0]

    if "id" not in debt_headers or "όνομα" not in debt_headers:
        return False

    id_index = debt_headers.index("id")
    name_index = debt_headers.index("όνομα")

    matching_rows = []

    for row_number, row in enumerate(debt_values[1:], start=2):
        row_id = row[id_index] if id_index < len(row) else ""
        row_name = row[name_index] if name_index < len(row) else ""

        normalized_name = str(row_name).strip()

        if normalized_name in {
            PIRAEUS_LOAN_NAME,
            "Δάνειο Πτυχίο",
        }:
            matching_rows.append(
                {
                    "row_number": row_number,
                    "id": str(row_id).strip(),
                    "name": normalized_name,
                    "row": row,
                }
            )

    if not matching_rows:
        return False

    # Προτιμά εγγραφή που έχει ήδη το νέο όνομα και συμπληρωμένο αρχικό ποσό.
    def priority(item):
        row = item["row"]
        initial_index = (
            debt_headers.index("αρχικό_ποσό")
            if "αρχικό_ποσό" in debt_headers
            else None
        )
        initial_amount = (
            parse_number(row[initial_index])
            if initial_index is not None and initial_index < len(row)
            else 0.0
        )

        return (
            1 if item["name"] == PIRAEUS_LOAN_NAME else 0,
            1 if initial_amount > 0 else 0,
            -item["row_number"],
        )

    matching_rows.sort(key=priority, reverse=True)
    primary = matching_rows[0]
    duplicates = matching_rows[1:]

    # Μετονομασία της κύριας εγγραφής, αν ήταν ακόμη με το παλιό όνομα.
    if primary["name"] != PIRAEUS_LOAN_NAME:
        debts_ws.update_cell(
            primary["row_number"],
            name_index + 1,
            PIRAEUS_LOAN_NAME,
        )

    if not duplicates:
        return primary["name"] != PIRAEUS_LOAN_NAME

    try:
        movement_values = get_all_values_with_retry(
            debt_movements_ws,
            attempts=3,
        )
    except gspread.exceptions.APIError:
        # Δεν διαγράφουμε διπλές οφειλές αν δεν μπορέσουμε πρώτα
        # να ελέγξουμε και να μεταφέρουμε με ασφάλεια τις κινήσεις.
        return False

    if movement_values:
        movement_headers = movement_values[0]

        if "debt_id" in movement_headers and "όνομα" in movement_headers:
            debt_id_col = movement_headers.index("debt_id") + 1
            movement_name_col = movement_headers.index("όνομα") + 1

            duplicate_ids = {
                item["id"]
                for item in duplicates
                if item["id"]
            }

            for movement_row_number, movement_row in enumerate(
                movement_values[1:],
                start=2,
            ):
                movement_debt_id = (
                    movement_row[debt_id_col - 1]
                    if debt_id_col - 1 < len(movement_row)
                    else ""
                )

                if str(movement_debt_id).strip() in duplicate_ids:
                    debt_movements_ws.update_cell(
                        movement_row_number,
                        debt_id_col,
                        primary["id"],
                    )
                    debt_movements_ws.update_cell(
                        movement_row_number,
                        movement_name_col,
                        PIRAEUS_LOAN_NAME,
                    )

    # Διαγράφουμε από κάτω προς τα πάνω για να μη μετακινηθούν οι γραμμές.
    for duplicate in sorted(
        duplicates,
        key=lambda item: item["row_number"],
        reverse=True,
    ):
        debts_ws.delete_rows(duplicate["row_number"])

    refresh_data()
    return True


def ensure_default_debts():
    """
    Ελέγχει τις βασικές οφειλές χωρίς να εμποδίζει την εκκίνηση.

    Αν το Google Sheets API αποτύχει προσωρινά, παραλείπεται μόνο
    η αυτόματη συντήρηση των οφειλών. Τα υπάρχοντα δεδομένα δεν
    τροποποιούνται και η εφαρμογή μπορεί να συνεχίσει να ανοίγει.
    """
    try:
        merge_duplicate_piraeus_debts()
        existing_values = get_all_values_with_retry(
            debts_ws,
            attempts=3,
        )
    except gspread.exceptions.APIError:
        st.session_state["google_sheets_startup_warning"] = True
        return False

    headers = SHEET_SCHEMAS[DEBTS_SHEET]

    if not existing_values:
        debts_ws.update(values=[headers], range_name="A1")
        existing_values = [headers]

    existing_records = []
    for row in existing_values[1:]:
        record = {
            header: row[index] if index < len(row) else ""
            for index, header in enumerate(headers)
        }
        existing_records.append(record)

    # Μετονομασία παλιάς εγγραφής, αν υπάρχει.
    for row_number, record in enumerate(existing_records, start=2):
        if str(record.get("όνομα", "")).strip() == "Δάνειο Πτυχίο":
            name_col = headers.index("όνομα") + 1
            debts_ws.update_cell(row_number, name_col, PIRAEUS_LOAN_NAME)
            record["όνομα"] = PIRAEUS_LOAN_NAME

    existing_names = {
        str(record.get("όνομα", "")).strip()
        for record in existing_records
    }

    defaults = {
        PIRAEUS_LOAN_NAME: {
            "αρχικό_ποσό": PIRAEUS_INITIAL_AMOUNT,
            "προεπιλεγμένη_δόση": PIRAEUS_ACTUAL_INSTALLMENT,
            "ετήσιο_επιτόκιο": PIRAEUS_ANNUAL_RATE,
            "συνολικές_δόσεις": PIRAEUS_TOTAL_INSTALLMENTS,
            "ημερομηνία_πρώτης_δόσης": PIRAEUS_FIRST_DUE_DATE.isoformat(),
            "τύπος_επιτοκίου": "Σταθερό",
        },
        "Δάνειο Θεία": {},
        "Δάνειο Γεωργία": {},
        "Πιστωτική κάρτα Eurobank": {},
    }

    added = False

    for debt_name, settings in defaults.items():
        if debt_name not in existing_names:
            debts_ws.append_row(
                [
                    create_id("DEBT"),
                    debt_name,
                    settings.get("αρχικό_ποσό", 0.0),
                    settings.get("προεπιλεγμένη_δόση", 0.0),
                    settings.get("ετήσιο_επιτόκιο", 0.0),
                    settings.get("συνολικές_δόσεις", 0),
                    settings.get("ημερομηνία_πρώτης_δόσης", ""),
                    settings.get("τύπος_επιτοκίου", ""),
                    "Ναι",
                    datetime.now().isoformat(timespec="seconds"),
                ],
                value_input_option="USER_ENTERED",
            )
            added = True

    # Ενημέρωση όρων Πειραιώς μόνο όταν τα αντίστοιχα πεδία είναι κενά/μηδενικά.
    refreshed_values = get_all_values_with_retry(debts_ws, attempts=5)
    for row_number, row in enumerate(refreshed_values[1:], start=2):
        record = {
            header: row[index] if index < len(row) else ""
            for index, header in enumerate(headers)
        }
        if str(record.get("όνομα", "")).strip() != PIRAEUS_LOAN_NAME:
            continue

        defaults_to_apply = {
            "αρχικό_ποσό": PIRAEUS_INITIAL_AMOUNT,
            "προεπιλεγμένη_δόση": PIRAEUS_ACTUAL_INSTALLMENT,
            "ετήσιο_επιτόκιο": PIRAEUS_ANNUAL_RATE,
            "συνολικές_δόσεις": PIRAEUS_TOTAL_INSTALLMENTS,
            "ημερομηνία_πρώτης_δόσης": PIRAEUS_FIRST_DUE_DATE.isoformat(),
            "τύπος_επιτοκίου": "Σταθερό",
        }

        for field, default_value in defaults_to_apply.items():
            current_value = str(record.get(field, "")).strip()
            should_fill = (
                current_value == ""
                or (field in {"αρχικό_ποσό", "προεπιλεγμένη_δόση", "ετήσιο_επιτόκιο", "συνολικές_δόσεις"}
                    and parse_number(current_value) == 0)
            )
            if should_fill:
                debts_ws.update_cell(
                    row_number,
                    headers.index(field) + 1,
                    default_value,
                )

    if added:
        refresh_data()

    merge_duplicate_piraeus_debts()

    return True


def prepare_debts(df):
    result = df.copy()

    required_columns = {
        "id": "",
        "όνομα": "",
        "αρχικό_ποσό": 0.0,
        "προεπιλεγμένη_δόση": 0.0,
        "ενεργό": "Ναι",
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
):
    debt_movements_ws.append_row(
        [
            create_id("DM"),
            debt_id,
            debt_name,
            movement_date.isoformat(),
            movement_type,
            float(amount),
            notes,
            datetime.now().isoformat(timespec="seconds"),
        ],
        value_input_option="USER_ENTERED",
    )
    refresh_data()


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


def calculate_piraeus_amortization(debt_row, debt_movements):
    principal = parse_number(debt_row["αρχικό_ποσό"])
    annual_rate = parse_number(debt_row["ετήσιο_επιτόκιο"])
    monthly_rate = annual_rate / 100 / 12

    relevant = debt_movements[
        (debt_movements["debt_id"].astype(str) == str(debt_row["id"]))
        & (debt_movements["τύπος"] == "Πληρωμή")
    ].copy()

    relevant = relevant.sort_values("ημερομηνία")

    balance = principal
    total_interest = 0.0
    total_principal_paid = 0.0

    for _, movement in relevant.iterrows():
        if balance <= 0:
            break

        interest = balance * monthly_rate
        payment = parse_number(movement["ποσό"])
        principal_paid = max(min(payment - interest, balance), 0.0)

        total_interest += interest
        total_principal_paid += principal_paid
        balance = max(balance - principal_paid, 0.0)

    return {
        "balance": balance,
        "interest_paid": total_interest,
        "principal_paid": total_principal_paid,
        "installments_paid": len(relevant),
    }


def add_piraeus_installments_until(debt_row, through_date):
    first_due = debt_row["ημερομηνία_πρώτης_δόσης"]

    if pd.isna(first_due):
        first_due_date = PIRAEUS_FIRST_DUE_DATE
    else:
        first_due_date = first_due.date()

    installment_amount = parse_number(debt_row["προεπιλεγμένη_δόση"])
    existing = debt_movements_df[
        (debt_movements_df["debt_id"].astype(str) == str(debt_row["id"]))
        & (debt_movements_df["τύπος"] == "Πληρωμή")
    ].copy()

    existing_dates = set(
        existing["ημερομηνία"].dropna().dt.date.tolist()
    )

    due_date = first_due_date
    added_count = 0

    while due_date <= through_date:
        if due_date not in existing_dates:
            note = f"Αυτόματη δόση {due_date.strftime('%m/%Y')}"

            append_debt_movement(
                debt_id=debt_row["id"],
                debt_name=debt_row["όνομα"],
                movement_date=due_date,
                movement_type="Πληρωμή",
                amount=installment_amount,
                notes=note,
            )

            append_transaction(
                transaction_date=due_date,
                transaction_type="Έξοδο",
                category="Δάνεια / Κάρτες",
                description=debt_row["όνομα"],
                amount=installment_amount,
                payment_method="Πάγια εντολή",
                recurring=True,
                notes=note,
            )
            added_count += 1

        due_date = due_date + relativedelta(months=1)

    return added_count


def calculate_debt_balance(debt_row, debt_movements):
    initial_amount = parse_number(debt_row["αρχικό_ποσό"])

    if str(debt_row["όνομα"]).strip() == PIRAEUS_LOAN_NAME:
        amortization = calculate_piraeus_amortization(
            debt_row,
            debt_movements,
        )

        relevant = debt_movements[
            debt_movements["debt_id"].astype(str) == str(debt_row["id"])
        ]

        increases = relevant.loc[
            relevant["τύπος"] == "Αύξηση οφειλής",
            "ποσό",
        ].sum()

        decreases = relevant.loc[
            relevant["τύπος"] == "Μείωση οφειλής",
            "ποσό",
        ].sum()

        return max(
            amortization["balance"] + increases - decreases,
            0.0,
        )

    if debt_movements.empty:
        return initial_amount

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



def prepare_goals(df):
    if df.empty:
        return df.copy()
    result = df.copy()
    for column in ["ποσό_στόχου", "ποσό_συγκεντρώθηκε"]:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = result[column].apply(parse_number)
    result["ημερομηνία_στόχου"] = pd.to_datetime(
        result.get("ημερομηνία_στόχου"),
        errors="coerce",
    )
    return result


def prepare_recurring(df):
    if df.empty:
        return df.copy()
    result = df.copy()
    for column, default in {
        "ποσό": 0.0,
        "υπενθύμιση_ημέρες": 0,
        "τελευταία_πληρωμή": "",
        "επόμενη_χρέωση": "",
        "rf": "",
        "ενεργό": "Ναι",
    }.items():
        if column not in result.columns:
            result[column] = default
    result["ποσό"] = result["ποσό"].apply(parse_number)
    result["υπενθύμιση_ημέρες"] = result["υπενθύμιση_ημέρες"].apply(parse_number)
    for column in ["τελευταία_πληρωμή", "επόμενη_χρέωση"]:
        result[column] = pd.to_datetime(result[column], errors="coerce")
    return result


def prepare_accounts(df):
    if df.empty:
        return df.copy()
    result = df.copy()
    for column in ["πραγματικό_υπόλοιπο", "υπολογισμένο_υπόλοιπο"]:
        result[column] = result.get(column, 0).apply(parse_number)
    result["ημερομηνία"] = pd.to_datetime(
        result.get("ημερομηνία"),
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


def prepare_month_closes(df):
    if df.empty:
        return df.copy()
    result = df.copy()
    for column in [
        "έτος", "μήνας", "έσοδα", "έξοδα", "αποταμίευση",
        "πάγια", "ποσό_μεγαλύτερης_κατηγορίας",
        "εκκρεμείς_υποχρεώσεις",
    ]:
        result[column] = result.get(column, 0).apply(parse_number)
    return result


def append_generic_record(worksheet, sheet_name, record):
    headers = SHEET_SCHEMAS[sheet_name]
    worksheet.append_row(
        [record.get(header, "") for header in headers],
        value_input_option="USER_ENTERED",
    )
    refresh_data()


def append_goal(
    name,
    category,
    target_amount,
    saved_amount,
    target_date,
    priority,
    notes="",
):
    append_generic_record(
        goals_ws,
        GOALS_SHEET,
        {
            "id": create_id("GOAL"),
            "όνομα": name,
            "κατηγορία": category,
            "ποσό_στόχου": float(target_amount),
            "ποσό_συγκεντρώθηκε": float(saved_amount),
            "ημερομηνία_στόχου": target_date.isoformat(),
            "προτεραιότητα": priority,
            "κατάσταση": "Ενεργός",
            "σημειώσεις": notes,
            "ενημερώθηκε": datetime.now().isoformat(timespec="seconds"),
        },
    )


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


def append_account_snapshot(
    name,
    account_type,
    actual_balance,
    calculated_balance,
    snapshot_date,
    notes="",
):
    append_generic_record(
        accounts_ws,
        ACCOUNTS_SHEET,
        {
            "id": create_id("ACC"),
            "όνομα": name,
            "τύπος": account_type,
            "πραγματικό_υπόλοιπο": float(actual_balance),
            "υπολογισμένο_υπόλοιπο": float(calculated_balance),
            "ημερομηνία": snapshot_date.isoformat(),
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


def save_month_close(year, month, values, notes=""):
    all_values = get_all_values_with_retry(month_closes_ws, attempts=3)
    headers = SHEET_SCHEMAS[MONTH_CLOSES_SHEET]
    target_row = None

    for row_number, row in enumerate(all_values[1:], start=2):
        old_year = int(parse_number(row[1] if len(row) > 1 else 0))
        old_month = int(parse_number(row[2] if len(row) > 2 else 0))
        if old_year == int(year) and old_month == int(month):
            target_row = row_number
            break

    record = {
        "id": create_id("CLOSE"),
        "έτος": int(year),
        "μήνας": int(month),
        **values,
        "σημειώσεις": notes,
        "κλείστηκε": datetime.now().isoformat(timespec="seconds"),
    }
    row_values = [record.get(header, "") for header in headers]

    if target_row:
        old_id = all_values[target_row - 1][0]
        row_values[0] = old_id or record["id"]
        month_closes_ws.update(
            values=[row_values],
            range_name=f"A{target_row}",
        )
    else:
        month_closes_ws.append_row(
            row_values,
            value_input_option="USER_ENTERED",
        )
    refresh_data()


def update_goal_saved_amount(goal_id, amount):
    values = get_all_values_with_retry(goals_ws, attempts=3)
    headers = SHEET_SCHEMAS[GOALS_SHEET]
    id_col = headers.index("id")
    amount_col = headers.index("ποσό_συγκεντρώθηκε")

    for row_number, row in enumerate(values[1:], start=2):
        current_id = row[id_col] if id_col < len(row) else ""
        if str(current_id) == str(goal_id):
            current = parse_number(
                row[amount_col] if amount_col < len(row) else 0
            )
            goals_ws.update_cell(
                row_number,
                amount_col + 1,
                current + float(amount),
            )
            goals_ws.update_cell(
                row_number,
                headers.index("ενημερώθηκε") + 1,
                datetime.now().isoformat(timespec="seconds"),
            )
            refresh_data()
            return True
    return False


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


def get_pdf_font_name():
    """Χρησιμοποιεί γραμματοσειρά που υποστηρίζει σωστά ελληνικά."""
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    for font_path in font_candidates:
        if os.path.exists(font_path):
            font_name = "PersonalHubGreek"
            if font_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(font_name, font_path))
            return font_name

    return "Helvetica"


def make_pdf_export(title, sheets):
    """Δημιουργεί PDF αναφορά με πίνακες και ελληνικούς χαρακτήρες."""
    output = io.BytesIO()
    font_name = get_pdf_font_name()

    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
        author="My Personal Hub",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "GreekTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#7A5200"),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "GreekSubtitle",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#7A5200"),
        spaceBefore=8,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "GreekBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=7.5,
        leading=9,
        wordWrap="CJK",
    )
    small_style = ParagraphStyle(
        "GreekSmall",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=7,
        leading=8,
        wordWrap="CJK",
    )

    story = [
        Paragraph(title, title_style),
        Paragraph(
            f"Εξαγωγή: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            body_style,
        ),
        Spacer(1, 6 * mm),
    ]

    for sheet_number, (sheet_name, dataframe) in enumerate(sheets.items()):
        if sheet_number > 0:
            story.append(PageBreak())

        story.append(Paragraph(str(sheet_name), subtitle_style))
        export_df = clean_export_dataframe(dataframe)

        if export_df.empty:
            story.append(Paragraph("Δεν υπάρχουν δεδομένα.", body_style))
            continue

        max_columns = 11
        visible_columns = list(export_df.columns[:max_columns])
        display_df = export_df[visible_columns].copy()

        if len(export_df.columns) > max_columns:
            story.append(
                Paragraph(
                    "Σημείωση: Στο PDF εμφανίζονται οι πρώτες "
                    f"{max_columns} στήλες. Το Excel περιλαμβάνει όλες.",
                    small_style,
                )
            )
            story.append(Spacer(1, 2 * mm))

        table_data = [
            [Paragraph(str(column), small_style) for column in visible_columns]
        ]

        max_pdf_rows = 250
        for _, row in display_df.head(max_pdf_rows).iterrows():
            table_data.append(
                [
                    Paragraph(str(row[column])[:180], small_style)
                    for column in visible_columns
                ]
            )

        if len(display_df) > max_pdf_rows:
            table_data.append(
                [
                    Paragraph(
                        f"... και ακόμη {len(display_df) - max_pdf_rows} εγγραφές",
                        small_style,
                    )
                ]
                + [""] * (len(visible_columns) - 1)
            )

        available_width = landscape(A4)[0] - 20 * mm
        column_width = available_width / max(len(visible_columns), 1)

        table = Table(
            table_data,
            colWidths=[column_width] * len(visible_columns),
            repeatRows=1,
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#F3C856"),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#2E2205"),
                    ),
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor("#D6AA36"),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor("#FFF9E8"),
                        ],
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)

    document.build(story)
    output.seek(0)
    return output.getvalue()


def render_export_buttons(title, sheets, filename_prefix, key_prefix):
    """Εμφανίζει κουμπιά εξαγωγής Excel και PDF."""
    valid_sheets = {
        str(name): (
            dataframe if isinstance(dataframe, pd.DataFrame)
            else pd.DataFrame(dataframe)
        )
        for name, dataframe in sheets.items()
    }

    st.markdown("#### Εξαγωγή")
    excel_column, pdf_column = st.columns(2)

    with excel_column:
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

    with pdf_column:
        st.download_button(
            "📕 Εξαγωγή PDF",
            data=make_pdf_export(title, valid_sheets),
            file_name=f"{filename_prefix}.pdf",
            mime="application/pdf",
            key=f"{key_prefix}_pdf",
            use_container_width=True,
        )

    st.caption(
        "Το Excel περιλαμβάνει όλα τα πεδία. "
        "Το PDF είναι συνοπτική εκτυπώσιμη αναφορά."
    )


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
reminders_df = prepare_reminders(load_records(REMINDERS_SHEET))
tasks_df = prepare_tasks(load_records(TASKS_SHEET))


ensure_default_debts()

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
goals_df = prepare_goals(load_records(GOALS_SHEET))
recurring_df = prepare_recurring(load_records(RECURRING_SHEET))
accounts_df = prepare_accounts(load_records(ACCOUNTS_SHEET))
documents_df = prepare_documents(load_records(DOCUMENTS_SHEET))
month_closes_df = prepare_month_closes(load_records(MONTH_CLOSES_SHEET))
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
    st.caption("Οργάνωση χωρίς πολλά πεδία")
    st.caption(f"Έκδοση: {APP_VERSION}")

    if "selected_page" not in st.session_state:
        st.session_state.selected_page = "🏠 Με μια ματιά"

    page = st.radio(
        "Μετάβαση",
        [
            "🏠 Με μια ματιά",
            "➕ Νέα καταχώρηση εξόδων / εσόδων",
            "🧮 Μηνιαίος προϋπολογισμός",
            "💳 Δάνεια / Κάρτες",
            "🎯 Στόχοι",
            "🔁 Πάγια / Συνδρομές",
            "🧾 Υποχρεώσεις",
            "🔔 Υπενθυμίσεις",
            "💼 Οικονομικός έλεγχος",
            "📁 Έγγραφα / Εγγυήσεις",
            "📊 Ιστορικό",
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
            (transactions_df["ημερομηνία"].dt.year == current_month.year)
            & (transactions_df["ημερομηνία"].dt.month == current_month.month)
        ].copy()

    monthly_income = month_df.loc[
        month_df["τύπος"] == "Έσοδο",
        "ποσό",
    ].sum()

    monthly_expenses = month_df.loc[
        month_df["τύπος"] == "Έξοδο",
        "ποσό",
    ].sum()

    monthly_balance = monthly_income - monthly_expenses

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

    today_date = date.today()
    days_in_month = (
        today_date.replace(day=28) + timedelta(days=4)
    ).replace(day=1) - timedelta(days=1)
    remaining_days = max(days_in_month.day - today_date.day + 1, 1)

    open_bill_total = 0.0
    if not tasks_df.empty:
        open_bill_total = tasks_df.loc[
            (tasks_df["κατάσταση"] == "Ανοιχτή")
            & (tasks_df["τύπος"] == "Λογαριασμός"),
            "ποσό",
        ].sum()

    safe_available = monthly_balance - open_bill_total
    safe_daily_limit = safe_available / remaining_days

    active_goal_total = 0.0
    if not goals_df.empty:
        active_goal_total = goals_df.loc[
            goals_df["κατάσταση"] == "Ενεργός",
            "ποσό_στόχου",
        ].sum() - goals_df.loc[
            goals_df["κατάσταση"] == "Ενεργός",
            "ποσό_συγκεντρώθηκε",
        ].sum()

    st.subheader("Οικονομικό control center")
    pro1, pro2, pro3, pro4 = st.columns(4)
    pro1.metric(
        "Ασφαλές διαθέσιμο",
        format_currency(safe_available),
        border=True,
    )
    pro2.metric(
        "Ημερήσιο ασφαλές όριο",
        format_currency(safe_daily_limit),
        border=True,
    )
    pro3.metric(
        "Ανοιχτοί λογαριασμοί",
        format_currency(open_bill_total),
        border=True,
    )
    pro4.metric(
        "Υπόλοιπο ενεργών στόχων",
        format_currency(max(active_goal_total, 0)),
        border=True,
    )

    st.write("")

    render_export_buttons(
        "My Personal Hub - Συνολική εικόνα",
        {
            "Κινήσεις": transactions_df,
            "Υποχρεώσεις": tasks_df,
            "Υπενθυμίσεις": reminders_df,
            "Στόχοι": goals_df,
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
            chart_data = (
                expenses
                .groupby("κατηγορία", as_index=False)["ποσό"]
                .sum()
                .sort_values("ποσό", ascending=False)
            )

            dashboard_palette = THEMES.get(
                st.session_state.get("selected_app_theme", "Κροκί"),
                THEMES["Κροκί"],
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
                        "κατηγορία:N",
                        sort="-x",
                        title=None,
                        axis=alt.Axis(
                            labelColor=dashboard_palette["text"],
                            domainColor=dashboard_palette["border"],
                            tickColor=dashboard_palette["border"],
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip("κατηγορία:N", title="Κατηγορία"),
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

elif page == "➕ Νέα καταχώρηση εξόδων / εσόδων":
    st.header("Νέα καταχώρηση εξόδων / εσόδων")
    render_export_buttons(
        "Οικονομικές κινήσεις",
        {"Κινήσεις": transactions_df},
        "oikonomikes_kiniseis",
        "transactions_export",
    )
    st.caption("Γρήγορη καταχώρηση με κουμπιά.")

    transaction_success_message = st.session_state.pop(
        "transaction_success_message",
        "",
    )
    if transaction_success_message:
        st.success(transaction_success_message)

    transaction_type = render_choice_buttons(
        "Τι θέλεις να καταχωρήσεις;",
        ["Έξοδο", "Έσοδο"],
        "button_transaction_type",
        columns=2,
    )

    if not transaction_type:
        transaction_type = "Έξοδο"
        st.session_state["button_transaction_type"] = transaction_type

    if transaction_type == "Έξοδο":
        basic_categories = [
            "Σπίτι",
            "Σούπερ μάρκετ",
            "Αυτοκίνητο",
            "Υγεία",
            "Προσωπικά",
            "Έξοδος",
            "Συνδρομές",
            "Δάνεια / Κάρτες",
            "Άλλο",
        ]
        categories = EXPENSE_CATEGORIES
    else:
        basic_categories = [
            "Μισθός",
            "Επιπλέον έσοδο",
            "Μεταφορά χρημάτων",
            "Άλλο",
        ]
        categories = INCOME_CATEGORIES

    category_state_key = f"button_category_{transaction_type}"

    # Καθαρίζει παλιά επιλογή κατηγορίας όταν αλλάζει τύπος.
    selected_category = st.session_state.get(category_state_key, "")
    if selected_category not in basic_categories:
        st.session_state[category_state_key] = ""
        selected_category = ""

    selected_category = render_choice_buttons(
        "Κατηγορία",
        basic_categories,
        category_state_key,
        columns=2,
    )

    custom_category = ""
    selected_description = ""
    custom_description = ""

    if selected_category == "Άλλο":
        custom_category = st.text_input(
            "Γράψε τη δική σου κατηγορία",
            placeholder="π.χ. Κατοικίδιο, Εκπαίδευση, Δώρο",
            key=f"button_custom_category_{transaction_type}",
        )
        custom_description = st.text_input(
            "Γράψε την περιγραφή",
            placeholder="π.χ. Τροφή σκύλου ή μάθημα Ιταλικών",
            key=f"button_custom_description_{transaction_type}",
        )

    elif selected_category:
        description_options = categories.get(selected_category, [])

        # Σε πολύ μεγάλες λίστες κρατάμε όλες τις επιλογές ως κουμπιά.
        description_state_key = (
            f"button_description_{transaction_type}_{selected_category}"
        )

        selected_description = render_choice_buttons(
            "Περιγραφή",
            description_options + ["Άλλο"],
            description_state_key,
            columns=2,
        )

        if selected_description == "Άλλο":
            custom_description = st.text_input(
                "Γράψε τη δική σου περιγραφή",
                placeholder="Γράψε τι ακριβώς αφορά",
                key=(
                    f"button_custom_description_"
                    f"{transaction_type}_{selected_category}"
                ),
            )

    payment_options = [
        "Κάρτα",
        "Μετρητά",
        "Τραπεζική μεταφορά",
        "Πάγια εντολή",
        "IRIS",
        "Άλλο",
    ]

    if "button_payment_method" not in st.session_state:
        st.session_state["button_payment_method"] = st.session_state.get(
            "preferred_payment_method",
            "Κάρτα",
        )

    selected_payment = render_choice_buttons(
        "Τρόπος πληρωμής",
        payment_options,
        "button_payment_method",
        columns=2,
    )

    custom_payment = ""
    if selected_payment == "Άλλο":
        custom_payment = st.text_input(
            "Γράψε τον τρόπο πληρωμής",
            placeholder="π.χ. Revolut ή PayPal",
            key="button_custom_payment",
        )

    with st.form("transaction_button_form", clear_on_submit=False):
        amount_col, date_col = st.columns(2)

        with amount_col:
            amount = st.number_input(
                "Ποσό",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                key="button_transaction_amount",
            )

        with date_col:
            transaction_date = st.date_input(
                "Ημερομηνία",
                value=date.today(),
                key="button_transaction_date",
            )

        recurring = False
        if transaction_type == "Έξοδο":
            recurring = st.checkbox(
                "Είναι πάγιο ή επαναλαμβανόμενο έξοδο",
                key="button_transaction_recurring",
            )

        with st.expander("Προαιρετικά στοιχεία"):
            notes = st.text_area(
                "Σημείωση",
                placeholder="Οτιδήποτε θέλεις να θυμάσαι",
                key="button_transaction_notes",
            )

            uploaded_file = st.file_uploader(
                "Απόδειξη ή σχετικό αρχείο",
                type=["pdf", "png", "jpg", "jpeg", "webp"],
                key="button_transaction_file",
            )

        submitted = st.form_submit_button(
            "Αποθήκευση καταχώρησης",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        final_category = (
            custom_category.strip()
            if selected_category == "Άλλο"
            else selected_category
        )

        final_description = (
            custom_description.strip()
            if selected_description == "Άλλο"
            or selected_category == "Άλλο"
            else selected_description
        )

        final_payment = (
            custom_payment.strip()
            if selected_payment == "Άλλο"
            else selected_payment
        )

        if not final_category:
            st.warning("Επίλεξε κατηγορία.")
        elif not final_description:
            st.warning("Επίλεξε ή γράψε περιγραφή.")
        elif not final_payment:
            st.warning("Επίλεξε ή γράψε τρόπο πληρωμής.")
        elif amount <= 0:
            st.warning("Το ποσό πρέπει να είναι μεγαλύτερο από μηδέν.")
        else:
            try:
                file_link = upload_to_drive(uploaded_file)

                append_transaction(
                    transaction_date=transaction_date,
                    transaction_type=transaction_type,
                    category=final_category,
                    description=final_description,
                    amount=amount,
                    payment_method=final_payment,
                    recurring=recurring,
                    file_link=file_link,
                    notes=notes,
                )

                if st.session_state.get(
                    "return_home_after_save_preference",
                    True,
                ):
                    st.session_state["return_home_after_transaction"] = True

                st.session_state["transaction_keys_to_clear"] = [
                    "button_transaction_type",
                    f"button_category_{transaction_type}",
                    (
                        f"button_description_{transaction_type}_"
                        f"{selected_category}"
                    ),
                    f"button_custom_category_{transaction_type}",
                    f"button_custom_description_{transaction_type}",
                    (
                        f"button_custom_description_{transaction_type}_"
                        f"{selected_category}"
                    ),
                    "button_payment_method",
                    "button_custom_payment",
                    "button_transaction_amount",
                    "button_transaction_date",
                    "button_transaction_recurring",
                    "button_transaction_notes",
                    "button_transaction_file",
                ]
                st.session_state["transaction_success_message"] = (
                    f"Καταχωρήθηκε {transaction_type.lower()} "
                    f"{format_currency(amount)}."
                )
                st.rerun()

            except Exception as exc:
                st.error("Η καταχώρηση δεν αποθηκεύτηκε.")
                st.exception(exc)


# =========================================================
# ΥΠΕΝΘΥΜΙΣΕΙΣ
# =========================================================

elif page == "🔔 Υπενθυμίσεις":
    st.header("Υπενθυμίσεις")
    render_export_buttons(
        "Υπενθυμίσεις",
        {"Υπενθυμίσεις": reminders_df},
        "ypenthymiseis",
        "reminders_export",
    )
    st.caption("Επίλεξε τις βασικές επιλογές με κουμπιά.")

    reminder_categories_buttons = [
        "Υγεία",
        "Αυτοκίνητο",
        "Ραντεβού",
        "Συνδρομή",
        "Έγγραφο",
        "Προσωπικό",
        "Άλλο",
    ]

    reminder_category = render_choice_buttons(
        "Κατηγορία",
        reminder_categories_buttons,
        "reminder_button_category",
        columns=2,
    )

    custom_reminder_category = ""
    reminder_title_choice = ""
    custom_reminder_title = ""

    if reminder_category == "Άλλο":
        custom_reminder_category = st.text_input(
            "Γράψε τη δική σου κατηγορία",
            placeholder="π.χ. Ταξίδι ή οικογενειακή υποχρέωση",
            key="reminder_custom_category_button",
        )
        custom_reminder_title = st.text_input(
            "Τίτλος υπενθύμισης",
            placeholder="Τι θέλεις να θυμηθείς;",
            key="reminder_custom_title_button",
        )

    elif reminder_category:
        reminder_titles = REMINDER_TITLES.get(
            reminder_category,
            ["Άλλη υπενθύμιση"],
        ) + ["Άλλο"]

        reminder_title_choice = render_choice_buttons(
            "Τίτλος",
            reminder_titles,
            f"reminder_button_title_{reminder_category}",
            columns=2,
        )

        if reminder_title_choice == "Άλλο":
            custom_reminder_title = st.text_input(
                "Γράψε τον τίτλο",
                placeholder="Τι θέλεις να θυμηθείς;",
                key=f"reminder_custom_title_{reminder_category}",
            )

    recurrence = render_choice_buttons(
        "Επανάληψη",
        [
            "Καμία",
            "Κάθε μήνα",
            "Κάθε 3 μήνες",
            "Κάθε 6 μήνες",
            "Κάθε χρόνο",
            "Άλλο",
        ],
        "reminder_button_recurrence",
        columns=2,
    )

    custom_recurrence = ""
    if recurrence == "Άλλο":
        custom_recurrence = st.text_input(
            "Γράψε τη δική σου επανάληψη",
            placeholder="π.χ. Κάθε 2 μήνες",
            key="reminder_custom_recurrence_button",
        )

    with st.form("reminder_button_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            reminder_date = st.date_input(
                "Ημερομηνία",
                value=date.today() + timedelta(days=7),
            )

        with col2:
            reminder_time = st.time_input(
                "Ώρα",
                value=time(9, 0),
            )

        reminder_amount = st.number_input(
            "Ποσό, αν υπάρχει",
            min_value=0.0,
            step=1.0,
        )

        add_to_calendar = st.checkbox(
            "Προσθήκη στο Google Calendar",
            value=True,
        )

        with st.expander("Προαιρετικά στοιχεία"):
            reminder_notes = st.text_area("Σημείωση")
            reminder_file = st.file_uploader(
                "Σχετικό αρχείο",
                type=["pdf", "png", "jpg", "jpeg", "webp"],
            )

        reminder_submitted = st.form_submit_button(
            "Αποθήκευση υπενθύμισης",
            use_container_width=True,
            type="primary",
        )

    if reminder_submitted:
        final_category = (
            custom_reminder_category.strip()
            if reminder_category == "Άλλο"
            else reminder_category
        )
        final_title = (
            custom_reminder_title.strip()
            if reminder_title_choice == "Άλλο"
            or reminder_category == "Άλλο"
            else reminder_title_choice
        )
        final_recurrence = (
            custom_recurrence.strip()
            if recurrence == "Άλλο"
            else recurrence
        )

        if not final_category:
            st.warning("Επίλεξε ή γράψε κατηγορία.")
        elif not final_title:
            st.warning("Επίλεξε ή γράψε τίτλο.")
        elif not final_recurrence:
            st.warning("Επίλεξε ή γράψε επανάληψη.")
        else:
            try:
                file_link = upload_to_drive(reminder_file)
                calendar_link = ""
                description_parts = []

                if reminder_amount > 0:
                    description_parts.append(
                        f"Ποσό: {format_currency(reminder_amount)}"
                    )
                if reminder_notes.strip():
                    description_parts.append(reminder_notes.strip())
                if file_link:
                    description_parts.append(f"Σχετικό αρχείο: {file_link}")

                if add_to_calendar:
                    calendar_link = create_calendar_event(
                        summary=final_title,
                        event_date=reminder_date,
                        event_time=reminder_time,
                        description="\n\n".join(description_parts),
                    )

                append_reminder(
                    title=final_title,
                    category=final_category,
                    reminder_date=reminder_date,
                    reminder_time=reminder_time,
                    amount=reminder_amount,
                    recurrence=final_recurrence,
                    calendar_link=calendar_link,
                    file_link=file_link,
                    notes=reminder_notes,
                )
                st.success("Η υπενθύμιση αποθηκεύτηκε.")
                st.rerun()

            except Exception as exc:
                st.error("Η υπενθύμιση δεν αποθηκεύτηκε.")
                st.exception(exc)

    st.divider()
    reminder_view = render_choice_buttons(
        "Προβολή",
        ["Ενεργές", "Ολοκληρωμένες", "Όλες"],
        "reminder_view_buttons",
        columns=3,
    )

    active_reminders = reminders_df.copy()

    if reminder_view == "Ενεργές":
        active_reminders = active_reminders[
            active_reminders["κατάσταση"] == "Ενεργή"
        ]
    elif reminder_view == "Ολοκληρωμένες":
        active_reminders = active_reminders[
            active_reminders["κατάσταση"] == "Ολοκληρωμένη"
        ]

    if active_reminders.empty:
        st.info("Δεν υπάρχουν υπενθυμίσεις σε αυτή την προβολή.")
    else:
        active_reminders = active_reminders.sort_values("ημερομηνία")

        for _, row in active_reminders.head(30).iterrows():
            date_text = (
                row["ημερομηνία"].strftime("%d/%m/%Y")
                if not pd.isna(row["ημερομηνία"])
                else ""
            )

            with st.container(border=True):
                st.write(f"**{row['τίτλος']}**")
                amount_text = (
                    f" · {format_currency(row['ποσό'])}"
                    if parse_number(row["ποσό"]) > 0
                    else ""
                )
                st.caption(
                    f"{row['κατηγορία']} · {date_text}{amount_text}"
                )

                if row["κατάσταση"] == "Ενεργή":
                    if st.button(
                        "✅ Ολοκληρώθηκε",
                        key=f"complete_reminder_{row['id']}",
                        use_container_width=True,
                    ):
                        if update_record_status(
                            reminders_ws,
                            row["id"],
                            "κατάσταση",
                            "Ολοκληρωμένη",
                        ):
                            st.rerun()


# =========================================================
# ΕΚΚΡΕΜΟΤΗΤΕΣ
# =========================================================

elif page == "🧾 Υποχρεώσεις":
    st.header("Προς πληρωμή")
    st.caption(
        "Μία καταχώρηση ενημερώνει αυτόματα τον προϋπολογισμό. "
        "Κάθε πληρωμή περνά και στα πραγματικά έξοδα."
    )

    action = render_choice_buttons(
        "Ενέργεια",
        ["➕ Νέα πληρωμή", "📋 Ανοιχτές", "✅ Ολοκληρωμένες"],
        "payments_action",
        columns=3,
    ) or "📋 Ανοιχτές"

    if action == "➕ Νέα πληρωμή":
        category = render_choice_buttons(
            "Κατηγορία",
            [
                "Ενοίκιο", "Κοινόχρηστα", "Ρεύμα", "Αέριο", "Νερό",
                "Κινητό", "Σταθερό", "Δάνειο Πειραιώς", "Δάνειο Γεωργία",
                "Δάνειο Θεία", "Εφορία", "ΕΦΚΑ", "Πιστωτική", "Συνδρομή",
                "Φαρμακείο", "Γιατρός", "Αυτοκίνητο", "Ασφάλεια αυτοκινήτου",
                "Άλλο",
            ],
            "quick_bill_category",
            columns=3,
        )
        custom_category = ""
        if category == "Άλλο":
            custom_category = st.text_input("Γράψε κατηγορία")
        recurrence = render_choice_buttons(
            "Επανάληψη",
            ["Καμία", "Κάθε μήνα", "Κάθε 2 μήνες", "Κάθε 3 μήνες", "Κάθε 6 μήνες", "Κάθε χρόνο"],
            "quick_bill_recurrence",
            columns=3,
        ) or "Καμία"
        with st.form("quick_bill_form"):
            title = st.text_input("Περιγραφή", placeholder="π.χ. Ρεύμα Αυγούστου")
            c1, c2 = st.columns(2)
            with c1:
                amount = st.number_input("Ποσό προς πληρωμή", min_value=0.0, step=1.0)
                due_date = st.date_input("Ημερομηνία λήξης", value=date.today()+timedelta(days=7))
            with c2:
                rf = st.text_input("RF, προαιρετικά", placeholder="RF...")
                notes = st.text_area("Σημείωση")
            submitted = st.form_submit_button("Αποθήκευση προς πληρωμή", use_container_width=True, type="primary")
        if submitted:
            final_category = custom_category.strip() if category == "Άλλο" else category
            final_title = title.strip() or final_category
            if not final_category or amount <= 0:
                st.warning("Συμπλήρωσε κατηγορία και ποσό.")
            else:
                append_task(
                    title=final_title,
                    category=final_category,
                    deadline=due_date,
                    priority="Κανονική",
                    notes=notes,
                    item_type="Λογαριασμός",
                    amount=amount,
                    recurrence=recurrence,
                    rf=rf,
                )
                st.success("Προστέθηκε και εμφανίζεται αυτόματα στον σωστό μήνα.")
                st.rerun()

    else:
        status_completed = action == "✅ Ολοκληρωμένες"
        visible = tasks_df[
            (tasks_df["τύπος"] == "Λογαριασμός")
            & ((tasks_df["κατάσταση"] == "Ολοκληρωμένη") if status_completed else (tasks_df["κατάσταση"] != "Ολοκληρωμένη"))
        ].copy()
        if visible.empty:
            st.info("Δεν υπάρχουν καταχωρήσεις σε αυτή την προβολή.")
        else:
            for _, row in visible.sort_values("προθεσμία").iterrows():
                with st.container(border=True):
                    due_text = row["προθεσμία"].strftime("%d/%m/%Y") if not pd.isna(row["προθεσμία"]) else ""
                    st.write(f"**{row['τίτλος']}**")
                    st.caption(
                        f"{row['κατηγορία']} · λήξη {due_text} · "
                        f"κατάσταση: {row['κατάσταση_πληρωμής']}"
                    )
                    c1,c2,c3=st.columns(3)
                    c1.metric("Αρχικό", format_currency(row["ποσό"]), border=True)
                    c2.metric("Πληρωμένο", format_currency(row["πληρωμένο_ποσό"]), border=True)
                    c3.metric("Υπόλοιπο", format_currency(row["υπόλοιπο"]), border=True)
                    if row.get("rf"):
                        st.code(str(row["rf"]), language=None)
                    if not status_completed:
                        with st.form(f"pay_{row['id']}"):
                            p1,p2=st.columns(2)
                            with p1:
                                payment_amount=st.number_input(
                                    "Ποσό που πληρώνω τώρα",
                                    min_value=0.0,
                                    max_value=float(max(row["υπόλοιπο"],0)),
                                    value=float(max(row["υπόλοιπο"],0)),
                                    step=1.0,
                                    key=f"amt_{row['id']}",
                                )
                            with p2:
                                method=st.selectbox(
                                    "Τρόπος πληρωμής",
                                    ["Κάρτα","Μετρητά","Τραπεζική μεταφορά","Πάγια εντολή","IRIS"],
                                    key=f"method_{row['id']}",
                                )
                            pay_notes=st.text_input("Σημείωση πληρωμής", key=f"note_{row['id']}")
                            pay_submit=st.form_submit_button("Καταχώρηση πληρωμής", use_container_width=True, type="primary")
                        if pay_submit:
                            if record_bill_payment(row, payment_amount, method, pay_notes):
                                st.success("Η πληρωμή καταχωρήθηκε. Το υπόλοιπο μεταφέρθηκε αυτόματα αν χρειάζεται.")
                                st.rerun()

    render_export_buttons(
        "Προς πληρωμή",
        {"Πληρωμές": tasks_df[tasks_df["τύπος"] == "Λογαριασμός"]},
        "pros_plirwmi",
        "payments_export",
    )


# =========================================================
# ΜΗΝΙΑΙΟΣ ΠΡΟΫΠΟΛΟΓΙΣΜΟΣ
# =========================================================

elif page == "🧮 Μηνιαίος προϋπολογισμός":
    st.header("Αυτόματος μηνιαίος προϋπολογισμός")
    st.caption(
        "Υπολογίζεται από τα πάγια, τις πληρωμές που λήγουν, "
        "τα μεταφερόμενα υπόλοιπα και τις πραγματικές κινήσεις."
    )
    month_names = ["Ιαν","Φεβ","Μαρ","Απρ","Μαϊ","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]
    selected_name = render_choice_buttons("Μήνας", month_names, "auto_budget_month", columns=4) or month_names[date.today().month-1]
    selected_month = month_names.index(selected_name)+1
    selected_year = int(st.number_input("Έτος", min_value=2020, max_value=2100, value=date.today().year, step=1))
    month_start = pd.Timestamp(date(selected_year, selected_month, 1))
    month_end = month_start + pd.offsets.MonthEnd(1)

    actual = transactions_df[
        (transactions_df["ημερομηνία"] >= month_start)
        & (transactions_df["ημερομηνία"] <= month_end)
    ].copy() if not transactions_df.empty else transactions_df.copy()
    actual_income = actual.loc[actual["τύπος"]=="Έσοδο","ποσό"].sum() if not actual.empty else 0.0
    actual_expenses = actual.loc[actual["τύπος"]=="Έξοδο","ποσό"].sum() if not actual.empty else 0.0

    due_bills = tasks_df[
        (tasks_df["τύπος"]=="Λογαριασμός")
        & (tasks_df["υπόλοιπο"]>0)
        & (tasks_df["προθεσμία"]>=month_start)
        & (tasks_df["προθεσμία"]<=month_end)
    ].copy() if not tasks_df.empty else tasks_df.copy()

    recurring_rows=[]
    if not recurring_df.empty:
        for _,rec in recurring_df[recurring_df["ενεργό"]=="Ναι"].iterrows():
            due=rec["επόμενη_χρέωση"]
            if pd.isna(due):
                continue
            while due < month_start:
                due=pd.Timestamp(add_frequency(due.date(), rec["συχνότητα"]))
            if month_start <= due <= month_end:
                recurring_rows.append({
                    "τίτλος":rec["όνομα"], "κατηγορία":rec["κατηγορία"],
                    "ημερομηνία":due, "ποσό":rec["ποσό"], "πηγή":"Πάγιο"
                })
    recurring_due=pd.DataFrame(recurring_rows)
    expected_bills=due_bills["υπόλοιπο"].sum() if not due_bills.empty else 0.0
    expected_recurring=recurring_due["ποσό"].sum() if not recurring_due.empty else 0.0
    expected_total=expected_bills+expected_recurring
    projected_balance=actual_income-actual_expenses-expected_total

    c1,c2,c3,c4=st.columns(4)
    c1.metric("Πραγματικά έσοδα",format_currency(actual_income),border=True)
    c2.metric("Ήδη πληρωμένα",format_currency(actual_expenses),border=True)
    c3.metric("Απομένουν προς πληρωμή",format_currency(expected_total),border=True)
    c4.metric("Προβλεπόμενο υπόλοιπο",format_currency(projected_balance),border=True)

    st.subheader("Πληρωμές που ανήκουν στον μήνα")
    combined=[]
    if not due_bills.empty:
        for _,r in due_bills.iterrows():
            combined.append({"Περιγραφή":r["τίτλος"],"Κατηγορία":r["κατηγορία"],"Ημερομηνία":r["προθεσμία"],"Ποσό":r["υπόλοιπο"],"Πηγή":"Προς πληρωμή","Κατάσταση":r["κατάσταση_πληρωμής"]})
    if not recurring_due.empty:
        for _,r in recurring_due.iterrows():
            combined.append({"Περιγραφή":r["τίτλος"],"Κατηγορία":r["κατηγορία"],"Ημερομηνία":r["ημερομηνία"],"Ποσό":r["ποσό"],"Πηγή":"Πάγιο","Κατάσταση":"Αναμένεται"})
    budget_detail=pd.DataFrame(combined)
    if budget_detail.empty:
        st.info("Δεν υπάρχουν γνωστές πληρωμές για αυτόν τον μήνα.")
    else:
        st.dataframe(budget_detail, use_container_width=True, hide_index=True)

    st.subheader("Πραγματικές κινήσεις του μήνα")
    if actual.empty:
        st.info("Δεν έχουν καταχωρηθεί πραγματικές κινήσεις.")
    else:
        st.dataframe(actual, use_container_width=True, hide_index=True)

    render_export_buttons(
        f"Προϋπολογισμός {selected_name} {selected_year}",
        {"Προβλεπόμενα":budget_detail,"Πραγματικές κινήσεις":actual},
        f"budget_{selected_year}_{selected_month:02d}",
        "auto_budget_export",
    )


# =========================================================
# ΔΑΝΕΙΑ / ΚΑΡΤΕΣ
# =========================================================

elif page == "💳 Δάνεια / Κάρτες":
    st.header("Δάνεια / Κάρτες")
    render_export_buttons(
        "Δάνεια και κάρτες",
        {
            "Οφειλές": debts_df,
            "Κινήσεις οφειλών": debt_movements_df,
        },
        "daneia_kartes",
        "debts_export",
    )
    st.caption(
        "Καταχώρισε το πραγματικό αρχικό ποσό κάθε οφειλής και μετά "
        "πέρασε αναδρομικά τις πληρωμές που έχουν ήδη γίνει."
    )

    if debts_df.empty:
        st.error("Δεν ήταν δυνατή η δημιουργία των οφειλών.")
    else:
        total_initial = debts_df["αρχικό_ποσό"].sum()
        total_remaining = sum(
            calculate_debt_balance(row, debt_movements_df)
            for _, row in debts_df.iterrows()
        )
        total_paid = max(total_initial - total_remaining, 0.0)

        metric1, metric2, metric3 = st.columns(3)
        metric1.metric(
            "Συνολικό αρχικό ποσό",
            format_currency(total_initial),
            border=True,
        )
        metric2.metric(
            "Συνολικό υπόλοιπο",
            format_currency(total_remaining),
            border=True,
        )
        metric3.metric(
            "Έχει εξοφληθεί",
            format_currency(total_paid),
            border=True,
        )

        st.divider()

        selected_debt_name = render_choice_buttons(
            "Επίλεξε δάνειο ή κάρτα",
            debts_df["όνομα"].tolist(),
            "selected_debt_button",
            columns=2,
        )

        if not selected_debt_name:
            selected_debt_name = debts_df["όνομα"].tolist()[0]
            st.session_state["selected_debt_button"] = selected_debt_name

        debt_row = debts_df[
            debts_df["όνομα"] == selected_debt_name
        ].iloc[0]

        current_balance = calculate_debt_balance(
            debt_row,
            debt_movements_df,
        )

        initial_amount = parse_number(debt_row["αρχικό_ποσό"])
        default_payment = parse_number(
            debt_row["προεπιλεγμένη_δόση"]
        )

        annual_rate = parse_number(debt_row.get("ετήσιο_επιτόκιο", 0))
        total_installments = int(
            parse_number(debt_row.get("συνολικές_δόσεις", 0))
        )
        theoretical_installment = calculate_fixed_installment(
            initial_amount,
            annual_rate,
            total_installments,
        )

        paid_percentage = (
            max(min((initial_amount - current_balance) / initial_amount, 1), 0)
            if initial_amount > 0
            else 0
        )

        summary1, summary2, summary3 = st.columns(3)

        summary1.metric(
            "Αρχικό ποσό",
            format_currency(initial_amount),
            border=True,
        )
        summary2.metric(
            "Τωρινό υπόλοιπο",
            format_currency(current_balance),
            border=True,
        )
        summary3.metric(
            "Προεπιλεγμένη δόση",
            format_currency(default_payment),
            border=True,
        )

        if selected_debt_name == PIRAEUS_LOAN_NAME:
            amortization = calculate_piraeus_amortization(
                debt_row,
                debt_movements_df,
            )

            info1, info2, info3, info4 = st.columns(4)
            info1.metric(
                "Θεωρητική δόση",
                format_currency(theoretical_installment),
                border=True,
            )
            info2.metric(
                "Πληρωμένες δόσεις",
                f"{amortization['installments_paid']} / {total_installments}",
                border=True,
            )
            info3.metric(
                "Κεφάλαιο που εξοφλήθηκε",
                format_currency(amortization["principal_paid"]),
                border=True,
            )
            info4.metric(
                "Τόκοι που πληρώθηκαν",
                format_currency(amortization["interest_paid"]),
                border=True,
            )

            st.caption(
                "Στοιχεία σύμβασης: αρχικό ποσό 15.989,04 €, "
                "σταθερό ετήσιο επιτόκιο 13,15%, 96 δόσεις, "
                "πρώτη δόση 14/12/2024. Η πραγματική δόση των "
                "269,98 € χρησιμοποιείται στις καταχωρήσεις."
            )

        st.progress(
            paid_percentage,
            text=f"Εξόφληση: {paid_percentage * 100:.1f}%",
        )

        if selected_debt_name == PIRAEUS_LOAN_NAME:
            (
                settings_tab,
                payment_tab,
                bulk_tab,
                correction_tab,
                history_tab,
            ) = st.tabs(
                [
                    "Όροι δανείου",
                    "Καταχώρηση πληρωμής",
                    "Μαζική καταχώρηση",
                    "Διόρθωση υπολοίπου",
                    "Ιστορικό",
                ]
            )
        else:
            settings_tab, payment_tab, correction_tab, history_tab = st.tabs(
                [
                    "Αρχικό ποσό / Δόση",
                    "Καταχώρηση πληρωμής",
                    "Διόρθωση υπολοίπου",
                    "Ιστορικό",
                ]
            )
            bulk_tab = None

        with settings_tab:
            st.subheader("Αρχικό ποσό και συνηθισμένη δόση")
            st.info(
                "Μπορείς να ξαναποθηκεύσεις το αρχικό ποσό όσες φορές "
                "χρειάζεται. Οι ήδη καταχωρημένες πληρωμές δεν διαγράφονται."
            )

            with st.form(
                f"debt_settings_{debt_row['id']}",
                clear_on_submit=False,
            ):
                new_initial_amount = st.number_input(
                    "Πραγματικό αρχικό ποσό οφειλής",
                    min_value=0.0,
                    value=float(initial_amount),
                    step=10.0,
                    format="%.2f",
                )

                new_default_payment = st.number_input(
                    "Συνηθισμένο μηνιαίο ποσό πληρωμής",
                    min_value=0.0,
                    value=float(default_payment),
                    step=1.0,
                    format="%.2f",
                    help=(
                        "Για το Δάνειο Πειραιώς βάλε την ακριβή τραπεζική δόση. "
                        "Στα άλλα μπορείς να βάλεις 0 ή ένα συνηθισμένο ποσό."
                    ),
                )

                save_settings = st.form_submit_button(
                    "Αποθήκευση αρχικού ποσού και δόσης",
                    use_container_width=True,
                    type="primary",
                )

            if save_settings:
                if update_debt_settings(
                    debt_row["id"],
                    new_initial_amount,
                    new_default_payment,
                ):
                    st.success(
                        "Το αρχικό ποσό και η προεπιλεγμένη δόση αποθηκεύτηκαν."
                    )
                    st.rerun()
                else:
                    st.error("Δεν βρέθηκε η συγκεκριμένη οφειλή.")

        with payment_tab:
            st.subheader("Καταχώρηση πληρωμής")

            payment_choices = ["Άλλο ποσό"]

            if default_payment > 0:
                payment_choices.insert(
                    0,
                    f"Προεπιλεγμένη δόση: {format_currency(default_payment)}",
                )

            selected_payment_choice = st.radio(
                "Ποσό πληρωμής",
                payment_choices,
                key=f"payment_choice_{debt_row['id']}",
            )

            if selected_payment_choice.startswith("Προεπιλεγμένη"):
                payment_amount = default_payment
                st.info(
                    f"Θα καταχωρηθεί πληρωμή {format_currency(payment_amount)}."
                )
            else:
                payment_amount = st.number_input(
                    "Γράψε το ποσό που πλήρωσες",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    key=f"custom_payment_amount_{debt_row['id']}",
                )

            payment_date = st.date_input(
                "Ημερομηνία πληρωμής",
                value=date.today(),
                key=f"debt_payment_date_{debt_row['id']}",
                help=(
                    "Για παλιές πληρωμές επίλεξε την πραγματική ημερομηνία "
                    "ώστε να τις περάσεις αναδρομικά."
                ),
            )

            payment_note = st.text_input(
                "Σημείωση",
                placeholder="π.χ. Δόση Ιανουαρίου 2025",
                key=f"debt_payment_note_{debt_row['id']}",
            )

            if st.button(
                "Αποθήκευση πληρωμής",
                key=f"save_debt_payment_{debt_row['id']}",
                use_container_width=True,
                type="primary",
            ):
                if payment_amount <= 0:
                    st.warning("Το ποσό πρέπει να είναι μεγαλύτερο από μηδέν.")
                elif payment_amount > current_balance and current_balance > 0:
                    st.warning(
                        "Το ποσό πληρωμής είναι μεγαλύτερο από το τωρινό υπόλοιπο."
                    )
                else:
                    append_debt_movement(
                        debt_id=debt_row["id"],
                        debt_name=debt_row["όνομα"],
                        movement_date=payment_date,
                        movement_type="Πληρωμή",
                        amount=payment_amount,
                        notes=payment_note,
                    )

                    append_transaction(
                        transaction_date=payment_date,
                        transaction_type="Έξοδο",
                        category="Δάνεια / Κάρτες",
                        description=debt_row["όνομα"],
                        amount=payment_amount,
                        payment_method="Τραπεζική πληρωμή",
                        recurring=True,
                        notes=payment_note,
                    )

                    st.success(
                        f"Καταχωρήθηκε πληρωμή {format_currency(payment_amount)}."
                    )
                    st.rerun()

        if bulk_tab is not None:
            with bulk_tab:
                st.subheader("Μαζική καταχώρηση παλιών δόσεων")
                st.info(
                    "Η πρώτη δόση είναι στις 14/12/2024. "
                    "Επίλεξε έως ποιον μήνα έχουν πληρωθεί οι δόσεις. "
                    "Η εφαρμογή θα προσθέσει μόνο όσες ημερομηνίες λείπουν."
                )

                bulk_through_date = st.date_input(
                    "Καταχώρηση δόσεων έως",
                    value=date(2026, 7, 14),
                    min_value=PIRAEUS_FIRST_DUE_DATE,
                    key=f"bulk_until_{debt_row['id']}",
                )

                if st.button(
                    "Καταχώρηση δόσεων που λείπουν",
                    key=f"bulk_add_{debt_row['id']}",
                    use_container_width=True,
                    type="primary",
                ):
                    added_count = add_piraeus_installments_until(
                        debt_row,
                        bulk_through_date,
                    )

                    if added_count:
                        st.success(
                            f"Προστέθηκαν {added_count} παλιές δόσεις "
                            f"των {format_currency(default_payment)}."
                        )
                        st.rerun()
                    else:
                        st.info(
                            "Όλες οι δόσεις μέχρι αυτή την ημερομηνία "
                            "είναι ήδη καταχωρημένες."
                        )

        with correction_tab:
            st.subheader("Χειροκίνητη διόρθωση υπολοίπου")
            st.caption(
                "Χρήσιμο κυρίως για την πιστωτική κάρτα, όπου προστίθενται "
                "τόκοι ή νέες χρεώσεις. Μπορεί να χρησιμοποιηθεί και για "
                "διόρθωση οποιουδήποτε δανείου."
            )

            corrected_balance = st.number_input(
                "Ποιο είναι το πραγματικό οφειλόμενο ποσό σήμερα;",
                min_value=0.0,
                value=float(current_balance),
                step=1.0,
                format="%.2f",
                key=f"corrected_balance_{debt_row['id']}",
            )

            correction_note = st.text_input(
                "Αιτιολογία διόρθωσης",
                placeholder="π.χ. Τόκοι Ιουλίου ή διόρθωση από ενημέρωση τράπεζας",
                key=f"correction_note_{debt_row['id']}",
            )

            if st.button(
                "Ενημέρωση τωρινού υπολοίπου",
                key=f"save_balance_correction_{debt_row['id']}",
                use_container_width=True,
            ):
                if set_debt_current_balance(
                    debt_row,
                    corrected_balance,
                    debt_movements_df,
                    correction_note,
                ):
                    st.success("Το τωρινό υπόλοιπο διορθώθηκε.")
                    st.rerun()
                else:
                    st.info("Το ποσό είναι ήδη ίδιο με το τωρινό υπόλοιπο.")

        with history_tab:
            st.subheader("Ιστορικό κινήσεων")

            debt_history = debt_movements_df[
                debt_movements_df["debt_id"].astype(str)
                == str(debt_row["id"])
            ].copy()

            if debt_history.empty:
                st.info("Δεν υπάρχουν ακόμη πληρωμές ή διορθώσεις.")
            else:
                debt_history = debt_history.sort_values(
                    "ημερομηνία",
                    ascending=False,
                )

                display_history = debt_history[
                    [
                        "ημερομηνία",
                        "τύπος",
                        "ποσό",
                        "σημειώσεις",
                    ]
                ].copy()

                display_history["ημερομηνία"] = (
                    display_history["ημερομηνία"]
                    .dt.strftime("%d/%m/%Y")
                )
                display_history["ποσό"] = (
                    display_history["ποσό"]
                    .apply(format_currency)
                )

                st.dataframe(
                    display_history,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ημερομηνία": "Ημερομηνία",
                        "τύπος": "Κίνηση",
                        "ποσό": "Ποσό",
                        "σημειώσεις": "Σημείωση",
                    },
                )


# =========================================================
# ΙΣΤΟΡΙΚΟ
# =========================================================


elif page == "🎯 Στόχοι":
    st.header("Οικονομικοί στόχοι")
    render_export_buttons(
        "Οικονομικοί στόχοι",
        {"Στόχοι": goals_df},
        "oikonomikoi_stoxoi",
        "goals_export",
    )
    st.caption("Αποταμίευση με καθαρό στόχο, προθεσμία και πρόοδο.")

    goal_action = render_choice_buttons(
        "Ενέργεια",
        ["Νέος στόχος", "Προσθήκη χρημάτων"],
        "goal_action_buttons",
        columns=2,
    ) or "Νέος στόχος"

    if goal_action == "Νέος στόχος":
        goal_category = render_choice_buttons(
            "Κατηγορία",
            [
                "Μαξιλάρι ασφαλείας", "Ταξίδι", "Αγορά",
                "Σπίτι", "Αυτοκίνητο", "Υγεία",
                "Αποπληρωμή οφειλής", "Άλλο",
            ],
            "goal_category_buttons",
            columns=2,
        )

        goal_priority = render_choice_buttons(
            "Προτεραιότητα",
            ["Χαμηλή", "Κανονική", "Υψηλή"],
            "goal_priority_buttons",
            columns=3,
        ) or "Κανονική"

        with st.form("new_goal_form"):
            goal_name = st.text_input(
                "Όνομα στόχου",
                placeholder="π.χ. Ταξίδι στην Ιταλία",
            )
            c1, c2 = st.columns(2)
            with c1:
                target_amount = st.number_input(
                    "Ποσό στόχου",
                    min_value=0.0,
                    step=50.0,
                )
                saved_amount = st.number_input(
                    "Έχω ήδη συγκεντρώσει",
                    min_value=0.0,
                    step=20.0,
                )
            with c2:
                target_date = st.date_input(
                    "Ημερομηνία στόχου",
                    value=date.today() + relativedelta(months=6),
                )
                goal_notes = st.text_area("Σημειώσεις")
            save_goal = st.form_submit_button(
                "Αποθήκευση στόχου",
                use_container_width=True,
                type="primary",
            )

        if save_goal:
            if not goal_name.strip() or not goal_category:
                st.warning("Συμπλήρωσε όνομα και κατηγορία.")
            elif target_amount <= 0:
                st.warning("Το ποσό στόχου πρέπει να είναι μεγαλύτερο από μηδέν.")
            else:
                append_goal(
                    goal_name.strip(),
                    goal_category,
                    target_amount,
                    saved_amount,
                    target_date,
                    goal_priority,
                    goal_notes,
                )
                st.success("Ο στόχος δημιουργήθηκε.")
                st.rerun()

    else:
        active_goals = goals_df[
            goals_df["κατάσταση"] == "Ενεργός"
        ] if not goals_df.empty else goals_df

        if active_goals.empty:
            st.info("Δεν υπάρχουν ενεργοί στόχοι.")
        else:
            selected_goal_name = render_choice_buttons(
                "Στόχος",
                active_goals["όνομα"].tolist(),
                "goal_deposit_choice",
                columns=2,
            )
            with st.form("goal_deposit_form"):
                deposit_amount = st.number_input(
                    "Ποσό προσθήκης",
                    min_value=0.0,
                    step=20.0,
                )
                deposit_submit = st.form_submit_button(
                    "Προσθήκη στον στόχο",
                    use_container_width=True,
                    type="primary",
                )
            if deposit_submit and selected_goal_name and deposit_amount > 0:
                goal_row = active_goals[
                    active_goals["όνομα"] == selected_goal_name
                ].iloc[0]
                update_goal_saved_amount(goal_row["id"], deposit_amount)
                st.success("Το ποσό προστέθηκε.")
                st.rerun()

    st.divider()
    st.subheader("Πρόοδος στόχων")
    if goals_df.empty:
        st.info("Δεν υπάρχουν ακόμη στόχοι.")
    else:
        for _, row in goals_df.sort_values(
            "ημερομηνία_στόχου"
        ).iterrows():
            target = max(parse_number(row["ποσό_στόχου"]), 0.01)
            saved = parse_number(row["ποσό_συγκεντρώθηκε"])
            progress = min(saved / target, 1.0)
            due = (
                row["ημερομηνία_στόχου"].strftime("%d/%m/%Y")
                if not pd.isna(row["ημερομηνία_στόχου"])
                else ""
            )
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**{row['όνομα']}**")
                    st.caption(
                        f"{row['κατηγορία']} · Στόχος {due} · "
                        f"{row['προτεραιότητα']}"
                    )
                    st.progress(progress)
                with c2:
                    st.metric(
                        "Πρόοδος",
                        f"{progress * 100:.0f}%",
                        border=True,
                    )
                st.caption(
                    f"{format_currency(saved)} από "
                    f"{format_currency(target)} · "
                    f"λείπουν {format_currency(max(target-saved, 0))}"
                )


elif page == "🔁 Πάγια / Συνδρομές":
    st.header("Πάγια και περιοδικές πληρωμές")
    st.caption("Δίνεις τελευταία πληρωμή και συχνότητα. Η επόμενη ημερομηνία υπολογίζεται αυτόματα.")
    category=render_choice_buttons("Κατηγορία",["Σπίτι","Τηλέφωνο / Internet","Streaming","Ασφάλεια","Υγεία","Αυτοκίνητο","Λογισμικό","Άλλο"],"recurring_category_buttons",columns=2)
    frequency=render_choice_buttons("Συχνότητα",["Κάθε μήνα","Κάθε 2 μήνες","Κάθε 3 μήνες","Κάθε 6 μήνες","Κάθε χρόνο"],"recurring_frequency_buttons",columns=2)
    payment=render_choice_buttons("Τρόπος πληρωμής",["Κάρτα","Πάγια εντολή","Μετρητά","Μεταφορά","IRIS"],"recurring_payment_buttons",columns=2) or "Κάρτα"
    with st.form("recurring_simple_form"):
        name=st.text_input("Όνομα",placeholder="π.χ. Ασφάλεια αυτοκινήτου")
        c1,c2=st.columns(2)
        with c1:
            amount=st.number_input("Ποσό",min_value=0.0,step=1.0)
            last_paid=st.date_input("Πότε πληρώθηκε τελευταία φορά",value=date.today())
        with c2:
            rf=st.text_input("RF, προαιρετικά")
            reminder_days=st.number_input("Υπενθύμιση ημέρες πριν",min_value=0,max_value=60,value=3,step=1)
        notes=st.text_area("Σημειώσεις")
        submit=st.form_submit_button("Αποθήκευση παγίου",use_container_width=True,type="primary")
    if submit:
        if not name.strip() or not category or not frequency or amount<=0:
            st.warning("Συμπλήρωσε όνομα, κατηγορία, συχνότητα και ποσό.")
        else:
            append_recurring(name.strip(),category,amount,frequency,last_paid,payment,reminder_days,notes,rf)
            st.success(f"Αποθηκεύτηκε. Επόμενη πληρωμή: {add_frequency(last_paid,frequency).strftime('%d/%m/%Y')}")
            st.rerun()
    st.divider()
    if recurring_df.empty:
        st.info("Δεν υπάρχουν πάγια.")
    else:
        for _,row in recurring_df[recurring_df["ενεργό"]=="Ναι"].sort_values("επόμενη_χρέωση").iterrows():
            with st.container(border=True):
                due=row["επόμενη_χρέωση"].strftime("%d/%m/%Y") if not pd.isna(row["επόμενη_χρέωση"]) else ""
                st.write(f"**{row['όνομα']}**")
                st.caption(f"{row['συχνότητα']} · επόμενη {due} · {format_currency(row['ποσό'])}")
                if row.get("rf"): st.code(str(row["rf"]),language=None)
    render_export_buttons("Πάγια και συνδρομές",{"Πάγια":recurring_df},"pagia_syndromes","recurring_export")


elif page == "💼 Οικονομικός έλεγχος":
    st.header("Οικονομικός έλεγχος")
    render_export_buttons(
        "Οικονομικός έλεγχος",
        {
            "Υπόλοιπα": accounts_df,
            "Κλεισίματα μήνα": month_closes_df,
            "Πάγια": recurring_df,
            "Υποχρεώσεις": tasks_df,
        },
        "oikonomikos_elegxos",
        "control_export",
    )
    st.caption("Cash flow, συμφωνία υπολοίπων και κλείσιμο μήνα.")

    control_section = render_choice_buttons(
        "Ενότητα",
        ["Cash flow 30/60/90", "Συμφωνία υπολοίπων", "Κλείσιμο μήνα"],
        "financial_control_section",
        columns=3,
    ) or "Cash flow 30/60/90"

    if control_section == "Cash flow 30/60/90":
        today_ts = pd.Timestamp.today().normalize()
        expected_income_monthly = (
            transactions_df.loc[
                transactions_df["τύπος"] == "Έσοδο", "ποσό"
            ].tail(6).mean()
            if not transactions_df.empty
            else 0.0
        )

        for horizon in [30, 60, 90]:
            end_date = today_ts + pd.Timedelta(days=horizon)
            bills = 0.0
            recurring_due = 0.0

            if not tasks_df.empty:
                bills = tasks_df.loc[
                    (tasks_df["κατάσταση"] == "Ανοιχτή")
                    & (tasks_df["τύπος"] == "Λογαριασμός")
                    & (tasks_df["προθεσμία"] >= today_ts)
                    & (tasks_df["προθεσμία"] <= end_date),
                    "ποσό",
                ].sum()

            if not recurring_df.empty:
                recurring_due = recurring_df.loc[
                    (recurring_df["ενεργό"] == "Ναι")
                    & (recurring_df["επόμενη_χρέωση"] >= today_ts)
                    & (recurring_df["επόμενη_χρέωση"] <= end_date),
                    "ποσό",
                ].sum()

            estimated_income = expected_income_monthly * (horizon / 30)
            expected_out = bills + recurring_due
            balance = estimated_income - expected_out

            with st.container(border=True):
                st.subheader(f"Επόμενες {horizon} ημέρες")
                c1, c2, c3 = st.columns(3)
                c1.metric(
                    "Εκτιμώμενα έσοδα",
                    format_currency(estimated_income),
                    border=True,
                )
                c2.metric(
                    "Γνωστές πληρωμές",
                    format_currency(expected_out),
                    border=True,
                )
                c3.metric(
                    "Προβλεπόμενη διαφορά",
                    format_currency(balance),
                    border=True,
                )

        st.caption(
            "Η πρόβλεψη βασίζεται στα καταχωρισμένα πάγια, "
            "στους ανοιχτούς λογαριασμούς και στον πρόσφατο μέσο όρο εσόδων."
        )

    elif control_section == "Συμφωνία υπολοίπων":
        account_type = render_choice_buttons(
            "Τύπος λογαριασμού",
            ["Τράπεζα", "Μετρητά", "Πιστωτική", "Ηλεκτρονικό πορτοφόλι"],
            "account_type_buttons",
            columns=2,
        )
        with st.form("account_reconciliation_form"):
            account_name = st.text_input(
                "Όνομα λογαριασμού",
                placeholder="π.χ. Eurobank κύριος λογαριασμός",
            )
            a1, a2 = st.columns(2)
            with a1:
                actual_balance = st.number_input(
                    "Πραγματικό υπόλοιπο",
                    step=10.0,
                )
            with a2:
                calculated_balance = st.number_input(
                    "Υπόλοιπο βάσει εφαρμογής",
                    value=float(
                        transactions_df.loc[
                            transactions_df["τύπος"] == "Έσοδο", "ποσό"
                        ].sum()
                        - transactions_df.loc[
                            transactions_df["τύπος"] == "Έξοδο", "ποσό"
                        ].sum()
                    ) if not transactions_df.empty else 0.0,
                    step=10.0,
                )
            account_notes = st.text_area("Σημειώσεις")
            account_submit = st.form_submit_button(
                "Αποθήκευση συμφωνίας",
                use_container_width=True,
                type="primary",
            )
        if account_submit:
            if not account_name.strip() or not account_type:
                st.warning("Συμπλήρωσε όνομα και τύπο.")
            else:
                append_account_snapshot(
                    account_name.strip(),
                    account_type,
                    actual_balance,
                    calculated_balance,
                    date.today(),
                    account_notes,
                )
                st.success("Η συμφωνία αποθηκεύτηκε.")
                st.rerun()

        if not accounts_df.empty:
            latest_accounts = (
                accounts_df.sort_values("ημερομηνία")
                .groupby("όνομα", as_index=False)
                .tail(1)
            )
            for _, row in latest_accounts.iterrows():
                difference = (
                    row["πραγματικό_υπόλοιπο"]
                    - row["υπολογισμένο_υπόλοιπο"]
                )
                with st.container(border=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric(
                        row["όνομα"],
                        format_currency(row["πραγματικό_υπόλοιπο"]),
                        border=True,
                    )
                    c2.metric(
                        "Βάσει εφαρμογής",
                        format_currency(row["υπολογισμένο_υπόλοιπο"]),
                        border=True,
                    )
                    c3.metric(
                        "Διαφορά",
                        format_currency(difference),
                        border=True,
                    )

    else:
        close_month_name = render_choice_buttons(
            "Μήνας",
            [
                "Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαϊ", "Ιουν",
                "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ",
            ],
            "close_month_buttons",
            columns=4,
        ) or [
            "Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαϊ", "Ιουν",
            "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ",
        ][date.today().month - 1]
        close_month_number = [
            "Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαϊ", "Ιουν",
            "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ",
        ].index(close_month_name) + 1
        close_year = st.number_input(
            "Έτος",
            min_value=2020,
            max_value=2100,
            value=date.today().year,
            step=1,
        )

        selected_df = transactions_df[
            (transactions_df["ημερομηνία"].dt.year == int(close_year))
            & (transactions_df["ημερομηνία"].dt.month == close_month_number)
        ] if not transactions_df.empty else transactions_df

        close_income = selected_df.loc[
            selected_df["τύπος"] == "Έσοδο", "ποσό"
        ].sum() if not selected_df.empty else 0.0
        close_expenses = selected_df.loc[
            selected_df["τύπος"] == "Έξοδο", "ποσό"
        ].sum() if not selected_df.empty else 0.0
        close_fixed = selected_df.loc[
            (selected_df["τύπος"] == "Έξοδο")
            & (selected_df["πάγιο"] == "Ναι"), "ποσό"
        ].sum() if not selected_df.empty else 0.0

        category_totals = (
            selected_df[selected_df["τύπος"] == "Έξοδο"]
            .groupby("κατηγορία")["ποσό"].sum()
            if not selected_df.empty
            else pd.Series(dtype=float)
        )
        top_category = category_totals.idxmax() if not category_totals.empty else ""
        top_amount = category_totals.max() if not category_totals.empty else 0.0
        open_count = len(tasks_df[tasks_df["κατάσταση"] == "Ανοιχτή"]) \
            if not tasks_df.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Έσοδα", format_currency(close_income), border=True)
        c2.metric("Έξοδα", format_currency(close_expenses), border=True)
        c3.metric(
            "Αποταμίευση",
            format_currency(close_income - close_expenses),
            border=True,
        )
        c4.metric("Πάγια", format_currency(close_fixed), border=True)

        with st.form("month_close_form"):
            close_notes = st.text_area(
                "Σημειώσεις κλεισίματος",
                placeholder="Τι πήγε καλά, τι θέλεις να αλλάξεις τον επόμενο μήνα;",
            )
            close_submit = st.form_submit_button(
                f"Κλείσιμο {close_month_name} {int(close_year)}",
                use_container_width=True,
                type="primary",
            )
        if close_submit:
            save_month_close(
                int(close_year),
                close_month_number,
                {
                    "έσοδα": close_income,
                    "έξοδα": close_expenses,
                    "αποταμίευση": close_income - close_expenses,
                    "πάγια": close_fixed,
                    "μεγαλύτερη_κατηγορία": top_category,
                    "ποσό_μεγαλύτερης_κατηγορίας": top_amount,
                    "εκκρεμείς_υποχρεώσεις": open_count,
                },
                close_notes,
            )
            st.success("Ο μήνας έκλεισε και αποθηκεύτηκε.")
            st.rerun()


elif page == "📁 Έγγραφα / Εγγυήσεις":
    st.header("Έγγραφα και εγγυήσεις")
    render_export_buttons(
        "Έγγραφα και εγγυήσεις",
        {"Έγγραφα": documents_df},
        "eggrafa_eggyiseis",
        "documents_export",
    )
    st.caption("Λήξεις, εγγυήσεις, αποδείξεις και σημαντικά αρχεία.")

    document_type = render_choice_buttons(
        "Τύπος",
        ["Έγγραφο", "Εγγύηση", "Συμβόλαιο", "Ιατρικό", "Άλλο"],
        "document_type_buttons",
        columns=2,
    )
    document_category = render_choice_buttons(
        "Κατηγορία",
        [
            "Προσωπικά", "Αυτοκίνητο", "Σπίτι", "Υγεία",
            "Ηλεκτρονικά", "Ασφάλειες", "Άλλο",
        ],
        "document_category_buttons",
        columns=2,
    )

    with st.form("document_form"):
        document_title = st.text_input(
            "Τίτλος",
            placeholder="π.χ. Εγγύηση πλυντηρίου ή Ασφάλεια αυτοκινήτου",
        )
        provider = st.text_input(
            "Εταιρεία / φορέας",
            placeholder="π.χ. Public, ασφαλιστική, ΚΕΠ",
        )
        d1, d2, d3 = st.columns(3)
        with d1:
            purchase_date = st.date_input(
                "Ημερομηνία αγοράς / έκδοσης",
                value=date.today(),
            )
        with d2:
            expiry_date = st.date_input(
                "Ημερομηνία λήξης",
                value=date.today() + relativedelta(years=1),
            )
        with d3:
            document_amount = st.number_input(
                "Ποσό, αν υπάρχει",
                min_value=0.0,
                step=10.0,
            )
        document_file = st.file_uploader(
            "Αρχείο ή φωτογραφία",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
        )
        document_notes = st.text_area("Σημειώσεις")
        document_submit = st.form_submit_button(
            "Αποθήκευση",
            use_container_width=True,
            type="primary",
        )

    if document_submit:
        if not document_title.strip() or not document_type:
            st.warning("Συμπλήρωσε τίτλο και τύπο.")
        else:
            file_link = upload_to_drive(document_file)
            append_document(
                document_title.strip(),
                document_type,
                document_category or "Άλλο",
                purchase_date,
                expiry_date,
                document_amount,
                provider,
                file_link,
                document_notes,
            )
            st.success("Το έγγραφο αποθηκεύτηκε.")
            st.rerun()

    st.divider()
    document_view = render_choice_buttons(
        "Προβολή",
        ["Ενεργά", "Λήγουν σύντομα", "Όλα"],
        "document_view_buttons",
        columns=3,
    ) or "Ενεργά"

    visible_documents = documents_df.copy()
    today_ts = pd.Timestamp.today().normalize()

    if document_view == "Ενεργά" and not visible_documents.empty:
        visible_documents = visible_documents[
            visible_documents["κατάσταση"] == "Ενεργό"
        ]
    elif document_view == "Λήγουν σύντομα" and not visible_documents.empty:
        visible_documents = visible_documents[
            (visible_documents["ημερομηνία_λήξης"] >= today_ts)
            & (
                visible_documents["ημερομηνία_λήξης"]
                <= today_ts + pd.Timedelta(days=60)
            )
        ]

    if visible_documents.empty:
        st.info("Δεν υπάρχουν έγγραφα σε αυτή την προβολή.")
    else:
        for _, row in visible_documents.sort_values(
            "ημερομηνία_λήξης"
        ).iterrows():
            expiry_text = (
                row["ημερομηνία_λήξης"].strftime("%d/%m/%Y")
                if not pd.isna(row["ημερομηνία_λήξης"])
                else ""
            )
            days_left = (
                (row["ημερομηνία_λήξης"].normalize() - today_ts).days
                if not pd.isna(row["ημερομηνία_λήξης"])
                else None
            )
            with st.container(border=True):
                st.write(f"**{row['τίτλος']}**")
                st.caption(
                    f"{row['τύπος']} · {row['κατηγορία']} · "
                    f"λήξη {expiry_text}"
                )
                if days_left is not None:
                    st.caption(
                        "Εκπρόθεσμο"
                        if days_left < 0
                        else f"Απομένουν {days_left} ημέρες"
                    )
                if row.get("αρχείο"):
                    st.link_button(
                        "Άνοιγμα αρχείου",
                        row["αρχείο"],
                        use_container_width=True,
                    )


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
            "Διαφορά",
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
                "τύπος",
                "κατηγορία",
                "περιγραφή",
                "ποσό",
                "τρόπος_πληρωμής",
                "πάγιο",
                "αρχείο",
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
                    elif delete_record(transactions_ws, selected_delete_id):
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
        "Στόχοι":(GOALS_SHEET,goals_ws,goals_df),
        "Πάγια":(RECURRING_SHEET,recurring_ws,recurring_df),
        "Υπόλοιπα":(ACCOUNTS_SHEET,accounts_ws,accounts_df),
        "Έγγραφα":(DOCUMENTS_SHEET,documents_ws,documents_df),
        "Κλεισίματα μήνα":(MONTH_CLOSES_SHEET,month_closes_ws,month_closes_df),
    }
    selected=render_choice_buttons("Δεδομένα",list(datasets.keys()),"manage_dataset",columns=3) or "Κινήσεις"
    sheet_name,worksheet,df=datasets[selected]
    editable=clean_export_dataframe(df)
    editable.insert(0,"διαγραφή",False)
    edited=st.data_editor(editable,use_container_width=True,hide_index=True,num_rows="dynamic",key=f"editor_{sheet_name}")
    st.warning("Τσέκαρε «διαγραφή» στις γραμμές που θέλεις να αφαιρέσεις και πάτησε Αποθήκευση.")
    if st.button("Αποθήκευση αλλαγών",use_container_width=True,type="primary",key=f"save_editor_{sheet_name}"):
        kept=edited[~edited["διαγραφή"].fillna(False)].copy()
        replace_worksheet_records(worksheet,sheet_name,kept)
        st.success("Οι αλλαγές αποθηκεύτηκαν.")
        st.rerun()


elif page == "⚙️ Ρυθμίσεις":
    st.header("Ρυθμίσεις")

    settings_export_df = pd.DataFrame(
        [
            {
                "Ρύθμιση": "Θέμα",
                "Τιμή": st.session_state.get(
                    "selected_app_theme",
                    "Κροκί",
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
        st.session_state["selected_app_theme"] = "Κροκί"

    selected_theme = render_choice_buttons(
        "Επίλεξε χρωματική παλέτα",
        list(THEMES.keys()),
        "selected_app_theme",
        columns=2,
    )

    if not selected_theme:
        selected_theme = "Κροκί"
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

