# app.py
import datetime
import io
import math
import zoneinfo
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_js_eval import get_geolocation

# ReportLab imports for generating PDF reports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ==========================================
# STREAMLIT PAGE CONFIG & COMPACT RESPONSIVE CSS
# ==========================================
st.set_page_config(
    page_title="Campus Attendance System",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    /* Global Reset & Base Styling */
    html, body, .stApp {
        background-color: #F8FAFC !important;
        color: #334155 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        font-size: 14px !important;
    }

    /* Fixed Compact Main Container Overrides */
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 1280px !important;
        margin: 0 auto !important;
    }

    /* Typography Tightening */
    h1 { font-size: 1.5rem !important; margin-bottom: 0.5rem !important; font-weight: 700 !important; }
    h2 { font-size: 1.2rem !important; margin-bottom: 0.4rem !important; font-weight: 600 !important; }
    h3 { font-size: 1.05rem !important; margin-bottom: 0.3rem !important; font-weight: 600 !important; }
    p, span, label { font-size: 0.85rem !important; }

    /* Compact Form & Card Containers */
    div[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
        margin-bottom: 8px !important;
    }

    /* Fixed Height Form Inputs & Selectboxes */
    .stTextInput > div > div > input, 
    .stSelectbox > div > div, 
    .stDateInput > div > div > input, 
    .stTimeInput > div > div > input {
        background-color: #F1F5F9 !important;
        border-radius: 6px !important;
        border: 1px solid #CBD5E1 !important;
        color: #1E293B !important;
        height: 34px !important;
        padding: 2px 8px !important;
        font-size: 0.82rem !important;
    }

    /* Compact Buttons Base Style */
    .stButton > button {
        height: 32px !important;
        padding: 0px 12px !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }

    /* Session Controls Layout Row */
    .session-btn-row {
        display: flex !important;
        gap: 6px !important;
        width: 100% !important;
    }
    .session-btn-row > div { flex: 1 !important; }

    /* Action Buttons Variant Styles */
    .btn-green .stButton > button {
        background-color: #16A34A !important;
        color: #FFFFFF !important;
        border: none !important;
        width: 100% !important;
    }
    .btn-green .stButton > button:hover { background-color: #15803D !important; }

    .btn-red .stButton > button {
        background-color: #DC2626 !important;
        color: #FFFFFF !important;
        border: none !important;
        width: 100% !important;
    }
    .btn-red .stButton > button:hover { background-color: #B91C1C !important; }

    .btn-refresh .stButton > button {
        width: 100% !important;
        background-color: #E2E8F0 !important;
        color: #334155 !important;
        border: 1px solid #CBD5E1 !important;
        margin-top: 4px !important;
    }

    /* Fixed Height & Compact Scrollable Table Container */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.scrollable-marker) {
        max-height: 280px !important;
        overflow-y: auto !important;
        padding: 6px 10px !important;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        background-color: #FFFFFF;
    }

    /* Table Action Micro-Buttons */
    .action-btn-wrap .stButton > button {
        width: 100% !important;
        height: 24px !important;
        min-height: 24px !important;
        font-size: 0.7rem !important;
        padding: 0px 2px !important;
        line-height: 1 !important;
    }

    .action-btn-del .stButton > button {
        background-color: #FEF2F2 !important;
        color: #DC2626 !important;
        border: 1px solid #FCA5A5 !important;
    }
    .action-btn-del .stButton > button:hover {
        background-color: #FEE2E2 !important;
    }

    /* Custom Compact Scrollbars */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #F1F5F9; }
    ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }

    /* RESPONSIVE MEDIA QUERIES */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        h1 { font-size: 1.25rem !important; }
        h2 { font-size: 1.05rem !important; }
        .stButton > button { height: 30px !important; font-size: 0.75rem !important; }
        div[data-testid="stForm"] { padding: 10px !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# THREAD-SAFE GLOBAL SHARED STATE
# ==========================================
@st.cache_resource
def get_global_store():
    return {
        "session_active": False,
        "subject": "",
        "lab": "",
        "lecturer_lat": None,
        "lecturer_lon": None,
        "attendance_db": [],
        "submitted_students": set(),
    }


global_store = get_global_store()
global_store.setdefault("session_active", False)
global_store.setdefault("subject", "")
global_store.setdefault("lab", "")
global_store.setdefault("lecturer_lat", None)
global_store.setdefault("lecturer_lon", None)
global_store.setdefault("attendance_db", [])
global_store.setdefault("submitted_students", set())

MAX_ALLOWED_DISTANCE_METERS = 50.0


def get_current_local_datetime():
    return datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Kuala_Lumpur"))


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def detect_face_in_image(image_bytes):
    if not image_bytes or len(image_bytes) == 0:
        return False

    try:
        file_bytes = np.asarray(bytearray(image_bytes), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            return False

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        cascade_files = [
            "haarcascade_frontalface_default.xml",
            "haarcascade_frontalface_alt.xml",
            "haarcascade_frontalface_alt2.xml",
            "haarcascade_profileface.xml",
        ]

        for cascade_file in cascade_files:
            cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + cascade_file
            )
            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.08,
                minNeighbors=3,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )
            if len(faces) > 0:
                return True

        return False
    except Exception:
        return len(image_bytes) > 1000


def generate_pdf_report(
    lecturer_name, lecturer_id, subject, lab, attendance_data
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=14,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
    )
    normal_style = styles["Normal"]
    normal_style.fontSize = 8
    normal_style.leading = 10

    story.append(
        Paragraph("Campus Attendance Management System - Report", title_style)
    )
    story.append(Spacer(1, 8))

    now_local = get_current_local_datetime()
    meta_text = f"""
    <b>Lecturer:</b> {lecturer_name} | <b>ID:</b> {lecturer_id}<br/>
    <b>Subject:</b> {subject if subject else 'N/A'} | <b>Location:</b> {lab if lab else 'N/A'}<br/>
    <b>Date (MYT):</b> {now_local.strftime('%Y-%m-%d %H:%M:%S')}<br/>
    """
    story.append(Paragraph(meta_text, normal_style))
    story.append(Spacer(1, 10))

    table_data = [["Timestamp", "Name", "Matrix No.", "Class", "Status", "Attachment"]]
    for record in attendance_data:
        table_data.append([
            str(record.get("Timestamp", "")),
            str(record.get("Name", "")),
            str(record.get("Matrix", "")),
            str(record.get("Class", "")),
            str(record.get("Status", "")),
            str(record.get("File Name", "None")),
        ])

    pdf_table = Table(table_data, colWidths=[90, 110, 80, 50, 110, 100])
    pdf_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
        ])
    )

    story.append(pdf_table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# Session State Initialization
if "current_page" not in st.session_state:
    st.session_state.current_page = "Landing"
if "lecturer_name" not in st.session_state:
    st.session_state.lecturer_name = ""
if "lecturer_id" not in st.session_state:
    st.session_state.lecturer_id = ""
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "student_matrix" not in st.session_state:
    st.session_state.student_matrix = ""
if "student_class" not in st.session_state:
    st.session_state.student_class = ""
if "show_absence_modal" not in st.session_state:
    st.session_state.show_absence_modal = False
if "pending_attendance_record" not in st.session_state:
    st.session_state.pending_attendance_record = None
if "selected_image_record" not in st.session_state:
    st.session_state.selected_image_record = None
if "selected_doc_record" not in st.session_state:
    st.session_state.selected_doc_record = None


# Dialog Modals
@st.dialog("Facial Capture Preview")
def show_student_image_modal():
    rec = st.session_state.selected_image_record
    if rec:
        st.write(f"**Student:** {rec.get('Name')} ({rec.get('Matrix')})")
        st.write(f"**Class:** {rec.get('Class', 'N/A')} | **Timestamp:** {rec.get('Timestamp')}")
        if rec.get("image_bytes"):
            st.image(rec["image_bytes"], use_container_width=True)
        else:
            st.warning("No photo capture found.")


@st.dialog("Document Verification")
def show_document_modal():
    rec = st.session_state.selected_doc_record
    if rec:
        st.write(f"**Student:** {rec.get('Name')} ({rec.get('Matrix')})")
        st.write(f"**Document Name:** {rec.get('doc_name', 'Attachment')}")

        doc_bytes = rec.get("doc_bytes")
        doc_type = rec.get("doc_type", "")

        if doc_bytes:
            if "pdf" in doc_type.lower():
                st.download_button(
                    label="Download Document PDF",
                    data=doc_bytes,
                    file_name=rec.get("doc_name", "Medical_Certificate.pdf"),
                    mime="application/pdf",
                )
            else:
                st.image(doc_bytes, use_container_width=True)
        else:
            st.warning("No attached document found.")


@st.dialog("Absence Submission Confirmation")
def confirm_absence_submission():
    st.info("Medical Certificate / Absence Verification Notice")
    st.write("Confirm submission for absence approval?")
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Confirm"):
            if st.session_state.pending_attendance_record:
                global_store["attendance_db"].append(st.session_state.pending_attendance_record)
                global_store["submitted_students"].add(st.session_state.student_matrix)

                st.session_state.pending_attendance_record = None
                st.session_state.show_absence_modal = False
                st.session_state.student_name = ""
                st.session_state.student_matrix = ""
                st.session_state.student_class = ""
                st.session_state.current_page = "Landing"
                st.rerun()
    with col_cancel:
        if st.button("Cancel"):
            st.session_state.pending_attendance_record = None
            st.session_state.show_absence_modal = False
            st.rerun()


if st.session_state.show_absence_modal:
    confirm_absence_submission()

if st.session_state.selected_image_record:
    show_student_image_modal()
    st.session_state.selected_image_record = None

if st.session_state.selected_doc_record:
    show_document_modal()
    st.session_state.selected_doc_record = None

# ==========================================
# PAGE 1: LANDING
# ==========================================
if st.session_state.current_page == "Landing":
    st.title("Campus Attendance Portal")
    st.write("Select portal to proceed:")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Lecturer")
            if st.button("Lecturer Login", use_container_width=True):
                st.session_state.current_page = "LecturerLogin"
                st.rerun()
    with col2:
        with st.container(border=True):
            st.subheader("Student")
            if st.button("Student Login", use_container_width=True):
                st.session_state.current_page = "StudentLogin"
                st.rerun()

# ==========================================
# PAGE 2: LECTURER LOGIN
# ==========================================
elif st.session_state.current_page == "LecturerLogin":
    st.title("Lecturer Portal")
    if st.button("← Back"):
        st.session_state.current_page = "Landing"
        st.rerun()

    with st.form("lecturer_login_form"):
        lec_name_input = st.text_input("Lecturer Name:")
        lec_id_input = st.text_input("Lecturer ID:")
        login_btn = st.form_submit_button("Authenticate")
        if login_btn:
            if lec_name_input.strip() and lec_id_input.strip():
                st.session_state.lecturer_name = lec_name_input.strip()
                st.session_state.lecturer_id = lec_id_input.strip()
                st.session_state.current_page = "LecturerDashboard"
                st.rerun()
            else:
                st.error("Please fill in all fields.")

# ==========================================
# PAGE 3: STUDENT LOGIN
# ==========================================
elif st.session_state.current_page == "StudentLogin":
    st.title("Student Portal")
    if st.button("← Back"):
        st.session_state.current_page = "Landing"
        st.rerun()

    with st.form("student_login_form"):
        stud_name_input = st.text_input("Full Name:")
        stud_matrix_input = st.text_input("Matrix Number:")
        stud_class_input = st.text_input("Class:")
        stud_login_btn = st.form_submit_button("Authenticate")
        if stud_login_btn:
            if (
                stud_name_input.strip()
                and stud_matrix_input.strip()
                and stud_class_input.strip()
            ):
                # Automatic Uppercase Conversion
                st.session_state.student_name = stud_name_input.strip().upper()
                st.session_state.student_matrix = stud_matrix_input.strip().upper()
                st.session_state.student_class = stud_class_input.strip().upper()
                st.session_state.current_page = "StudentDashboard"
                st.rerun()
            else:
                st.error("Please fill in all fields.")

# ==========================================
# PAGE 4: LECTURER DASHBOARD
# ==========================================
elif st.session_state.current_page == "LecturerDashboard":
    col_hdr, col_out = st.columns([5, 1])
    with col_hdr:
        st.title("Lecturer Dashboard")
        st.caption(f"User: **{st.session_state.lecturer_name}** | ID: **{st.session_state.lecturer_id}**")
    with col_out:
        if st.button("Log Out"):
            st.session_state.current_page = "Landing"
            st.rerun()

    loc = get_geolocation()
    lec_lat, lec_lon = None, None
    if loc and "coords" in loc:
        lec_lat, lec_lon = loc["coords"]["latitude"], loc["coords"]["longitude"]
        st.success("GPS Verified: Classroom coordinates locked.", icon="📍")
    else:
        st.warning("Acquiring GPS location lock...", icon="⏳")

    # Compact Two-Column Grid Setup for Controls
    col_left, col_right = st.columns([3, 2])

    with col_left:
        with st.container(border=True):
            st.subheader("Session Config")
            lecturer_subject = st.selectbox(
                "Subject",
                [
                    "DFK50083 PYTHON PROGRAMMING",
                    "DFK50093 COMPUTER NETWORK SECURITY",
                    "DFN50563 ADVANCED SERVER ADMINISTRATION",
                    "DFT501X4 INTEGRATED PROJECT",
                    "MPU21072PENGHAYATAN ETIKA & PERADABAN",
                    "MPU22071KURSUS INTEGRITI DAN ANTIRASUAH",
                ],
            )
            lecturer_lab = st.selectbox(
                "Classroom / Lab Location",
                [
                    "CCNA 1", "CCNA 2", "CNL 1", "CNL 2", "IT 1", "IT 2",
                    "APDV 1", "APDV 2", "LL1", "LL2", "DKU", "DK1",
                    "DK2", "DK3", "DK4", "BK1", "BK2", "BK3", "BK4",
                    "BK5", "BK6", "BK7", "BK8", "BK9", "BK10", "BS-JPA",
                ],
            )

    with col_right:
        with st.container(border=True):
            st.subheader("Session Control")
            st.markdown('<div class="session-btn-row">', unsafe_allow_html=True)
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                st.markdown('<div class="btn-green">', unsafe_allow_html=True)
                if st.button("Activate"):
                    if lec_lat is None or lec_lon is None:
                        st.error("GPS required.")
                    else:
                        global_store["session_active"] = True
                        global_store["subject"] = lecturer_subject
                        global_store["lab"] = lecturer_lab
                        global_store["lecturer_lat"] = lec_lat
                        global_store["lecturer_lon"] = lec_lon
                        global_store["submitted_students"].clear()
                        st.success("Active!")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            with b_col2:
                st.markdown('<div class="btn-red">', unsafe_allow_html=True)
                if st.button("Close", disabled=not global_store["session_active"]):
                    global_store["session_active"] = False
                    st.success("Closed.")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="btn-refresh">', unsafe_allow_html=True)
            if st.button("Refresh Feed"):
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Attendance Log")
    attendance_list = global_store["attendance_db"]

    if attendance_list:
        df = pd.DataFrame(attendance_list)
        display_columns = ["Timestamp", "Name", "Matrix", "Class", "Subject", "Lab", "Status"]
        existing_cols = [c for c in display_columns if c in df.columns]
        
        st.dataframe(df[existing_cols], use_container_width=True, height=180)

        st.subheader("Actions Panel")
        records_to_delete = []

        COL_RATIOS = [1.2, 1.2, 0.8, 0.6, 1.5, 1.2, 1.5]
        h_ts, h_nm, h_mx, h_cl, h_sub, h_st, h_act = st.columns(COL_RATIOS)
        h_ts.caption("**Time**")
        h_nm.caption("**Name**")
        h_mx.caption("**Matrix**")
        h_cl.caption("**Class**")
        h_sub.caption("**Subject**")
        h_st.caption("**Status**")
        h_act.caption("**Manage**")

        with st.container(border=True):
            st.markdown('<div class="scrollable-marker"></div>', unsafe_allow_html=True)
            for idx, rec in enumerate(attendance_list):
                c_ts, c_nm, c_mx, c_cl, c_sub, c_st, c_act = st.columns(COL_RATIOS)

                c_ts.write(rec.get("Timestamp", "-"))
                c_nm.write(f"**{rec.get('Name', '-')}**")
                c_mx.write(rec.get("Matrix", "-"))
                c_cl.write(rec.get("Class", "-"))
                c_sub.write(rec.get("Subject", "-"))
                c_st.write(rec.get("Status", "-"))

                with c_act:
                    act_col1, act_col2, act_col3 = st.columns(3)
                    with act_col1:
                        if rec.get("image_bytes"):
                            st.markdown('<div class="action-btn-wrap">', unsafe_allow_html=True)
                            if st.button("Cam", key=f"img_btn_{idx}"):
                                st.session_state.selected_image_record = rec
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)

                    with act_col2:
                        if rec.get("doc_bytes"):
                            st.markdown('<div class="action-btn-wrap">', unsafe_allow_html=True)
                            if st.button("Doc", key=f"doc_btn_{idx}"):
                                st.session_state.selected_doc_record = rec
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)

                    with act_col3:
                        st.markdown('<div class="action-btn-wrap action-btn-del">', unsafe_allow_html=True)
                        if st.button("Del", key=f"del_btn_{idx}"):
                            records_to_delete.append(idx)
                        st.markdown('</div>', unsafe_allow_html=True)

        if records_to_delete:
            for d_idx in sorted(records_to_delete, reverse=True):
                removed_rec = global_store["attendance_db"].pop(d_idx)
                removed_matrix = removed_rec.get("Matrix")
                if removed_matrix in global_store["submitted_students"]:
                    global_store["submitted_students"].remove(removed_matrix)
            st.success("Record deleted.")
            st.rerun()

        pdf_bytes = generate_pdf_report(
            st.session_state.lecturer_name,
            st.session_state.lecturer_id,
            global_store["subject"],
            global_store["lab"],
            attendance_list,
        )

        st.download_button(
            label="Download PDF Report",
            data=pdf_bytes,
            file_name=f"Attendance_Report_{get_current_local_datetime().strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf",
        )
    else:
        st.info("No logs present for this session.")

# ==========================================
# PAGE 5: STUDENT DASHBOARD
# ==========================================
elif st.session_state.current_page == "StudentDashboard":
    col_hdr, col_out = st.columns([4, 1])
    with col_hdr:
        st.title("Student Dashboard")
        st.caption(f"Name: **{st.session_state.student_name}** | ID: **{st.session_state.student_matrix}** | Class: **{st.session_state.student_class}**")
    with col_out:
        if st.button("Log Out"):
            st.session_state.student_name = ""
            st.session_state.student_matrix = ""
            st.session_state.student_class = ""
            st.session_state.current_page = "Landing"
            st.rerun()

    if st.button("Sync Session Status", use_container_width=True):
        st.rerun()

    if global_store["session_active"]:
        if st.session_state.student_matrix in global_store["submitted_students"]:
            st.success("Attendance verified and logged for this session.")
        else:
            st.info(f"Active Session: **{global_store['subject']}** ({global_store['lab']})")

            student_loc = get_geolocation()
            if student_loc and "coords" in student_loc:
                student_lat, student_lon = (
                    student_loc["coords"]["latitude"],
                    student_loc["coords"]["longitude"],
                )
                distance = calculate_distance(
                    global_store["lecturer_lat"],
                    global_store["lecturer_lon"],
                    student_lat,
                    student_lon,
                )

                if distance <= MAX_ALLOWED_DISTANCE_METERS:
                    st.success("Location Verified: Inside designated classroom area.")
                    now_myt = get_current_local_datetime()

                    with st.form("student_attendance_form"):
                        c_date, c_time = st.columns(2)
                        with c_date:
                            attendance_date = st.date_input("Date", value=now_myt.date())
                        with c_time:
                            attendance_time = st.time_input("Time", value=now_myt.time())

                        attendance_status_type = st.selectbox(
                            "Status",
                            ["Present", "Absent with Medical Certificate / Memo"],
                        )
                        
                        # Capitalize student reason input automatically
                        mc_reason_input = st.text_input("Reason (if applicable):")

                        camera_photo = st.camera_input("Mandatory Facial Capture", key="mc_camera_input")
                        uploaded_file = st.file_uploader(
                            "Optional Document Proof",
                            type=["pdf", "png", "jpg"],
                            key="mc_file_uploader",
                        )

                        submit_attempt_btn = st.form_submit_button("Submit Attendance", use_container_width=True)

                        if submit_attempt_btn:
                            if camera_photo is None:
                                st.error("Facial verification photo required.")
                                st.stop()

                            img_bytes = camera_photo.getvalue()
                            if not detect_face_in_image(img_bytes):
                                st.error("No clear human face detected. Please re-take photo.")
                                st.stop()

                            doc_bytes = None
                            doc_name = None
                            doc_type = None

                            file_name_str = f"Facial_Verification_{st.session_state.student_matrix}.jpg"
                            if uploaded_file is not None:
                                doc_bytes = uploaded_file.getvalue()
                                doc_name = uploaded_file.name
                                doc_type = uploaded_file.type
                                file_name_str += f" | {doc_name}"

                            has_mc_flag = (attendance_status_type == "Absent with Medical Certificate / Memo")
                            timestamp_str = f"{attendance_date} {attendance_time.strftime('%H:%M:%S')}"

                            record_data = {
                                "Timestamp": timestamp_str,
                                "Name": st.session_state.student_name.upper(),
                                "Matrix": st.session_state.student_matrix.upper(),
                                "Class": st.session_state.student_class.upper(),
                                "Subject": global_store["subject"],
                                "Lab": global_store["lab"],
                                "Status": attendance_status_type,
                                "Reason": mc_reason_input.strip().upper(),
                                "has_mc": has_mc_flag,
                                "File Name": file_name_str,
                                "image_bytes": img_bytes,
                                "doc_bytes": doc_bytes,
                                "doc_name": doc_name,
                                "doc_type": doc_type,
                            }

                            if has_mc_flag:
                                st.session_state.pending_attendance_record = record_data
                                st.session_state.show_absence_modal = True
                                st.rerun()
                            else:
                                global_store["attendance_db"].append(record_data)
                                global_store["submitted_students"].add(st.session_state.student_matrix)

                                st.session_state.student_name = ""
                                st.session_state.student_matrix = ""
                                st.session_state.student_class = ""
                                st.session_state.current_page = "Landing"
                                st.rerun()
                else:
                    st.error("Outside designated classroom radius. Attendance locked.")
            else:
                st.info("Awaiting browser location clearance...")
    else:
        st.warning("No session currently active. Check back when class starts.")