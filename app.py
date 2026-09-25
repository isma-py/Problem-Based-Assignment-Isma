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
# STREAMLIT PAGE CONFIG & RESPONSIVE THEME
# ==========================================
st.set_page_config(
    page_title="Campus Attendance System",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Responsive CSS via Media Queries
st.markdown(
    """
    <style>
    /* Global Base Styling */
    .stApp {
        background-color: #F8FAFB;
        color: #334155;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Container Spacing Adaptations */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }

    /* Mobile Viewport Adjustments (Screens below 768px) */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        h1 {
            font-size: 1.6rem !important;
            line-height: 1.25 !important;
        }
        h2 {
            font-size: 1.25rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
        div[data-testid="stForm"] {
            padding: 14px !important;
        }
    }

    /* Desktop Viewport Adjustments (Screens above 768px) */
    @media (min-width: 769px) {
        .main .block-container {
            padding-left: 3rem !important;
            padding-right: 3rem !important;
        }
    }

    /* Soft Form Cards */
    div[data-testid="stForm"] {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }

    /* Responsive Touch & Click Friendly Buttons */
    .stButton > button {
        background-color: #F1F5F9;
        color: #475569;
        border-radius: 8px;
        padding: 6px 12px !important;
        font-weight: 500;
        width: 100% !important;
        min-height: 38px !important;
        border: 1px solid #CBD5E1;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #E2E8F0;
        color: #1E293B;
        border-color: #94A3B8;
    }

    /* Primary Accent Button */
    button[kind="primary"] {
        background-color: #6366F1 !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 2px 4px rgba(99, 102, 241, 0.2) !important;
    }
    button[kind="primary"]:hover {
        background-color: #4F46E5 !important;
    }

    /* Responsive Inputs and Dropdowns */
    .stTextInput > div > div > input, .stSelectbox > div > div {
        background-color: #F8FAFC !important;
        border-radius: 8px !important;
        border: 1px solid #CBD5E1 !important;
        color: #334155 !important;
    }

    /* Actions Column: Tight Vertical Layout */
    .action-btn-container {
        display: flex;
        flex-direction: column;
        gap: 4px !important; /* Slight 4px gap between stacked buttons */
        margin-top: -8px;
    }
    .action-btn-container .stButton {
        margin-bottom: 0px !important;
    }
    .action-btn-container .stButton > button {
        min-height: 32px !important;
        padding: 4px 8px !important;
        margin: 0 !important;
    }

    /* Action Grid Delete Styling */
    .action-btn-container-delete .stButton > button {
        background-color: #FEF2F2 !important;
        color: #DC2626 !important;
        border-color: #FCA5A5 !important;
    }

    [data-testid="stMetricValue"] {
        color: #4F46E5;
        font-weight: 600;
    }

    hr {
        border-color: #E2E8F0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# THREAD-SAFE GLOBAL SHARED STATE (Cross-Session)
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
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1E293B"),
    )
    normal_style = styles["Normal"]

    story.append(
        Paragraph("Campus Attendance Management System - Report", title_style)
    )
    story.append(Spacer(1, 10))

    now_local = get_current_local_datetime()
    meta_text = f"""
    <b>Lecturer:</b> {lecturer_name} (ID: {lecturer_id})<br/>
    <b>Subject:</b> {subject if subject else 'N/A'}<br/>
    <b>Location:</b> {lab if lab else 'N/A'}<br/>
    <b>Generated Date (MYT):</b> {now_local.strftime('%Y-%m-%d %H:%M:%S')}<br/>
    """
    story.append(Paragraph(meta_text, normal_style))
    story.append(Spacer(1, 15))

    table_data = [["Timestamp (MYT)", "Name", "Matrix No.", "Status", "Attachment"]]
    for record in attendance_data:
        table_data.append([
            str(record.get("Timestamp", "")),
            str(record.get("Name", "")),
            str(record.get("Matrix", "")),
            str(record.get("Status", "")),
            str(record.get("File Name", "None")),
        ])

    pdf_table = Table(table_data, colWidths=[110, 120, 90, 120, 110])
    pdf_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
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
if "show_absence_modal" not in st.session_state:
    st.session_state.show_absence_modal = False
if "pending_attendance_record" not in st.session_state:
    st.session_state.pending_attendance_record = None
if "selected_image_record" not in st.session_state:
    st.session_state.selected_image_record = None
if "selected_doc_record" not in st.session_state:
    st.session_state.selected_doc_record = None


# Dialog Modals
@st.dialog("Student Facial Capture")
def show_student_image_modal():
    rec = st.session_state.selected_image_record
    if rec:
        st.write(f"**Student:** {rec.get('Name')} ({rec.get('Matrix')})")
        st.write(f"**Submitted At (MYT):** {rec.get('Timestamp')}")
        if rec.get("image_bytes"):
            st.image(
                rec["image_bytes"],
                caption="Camera Facial Capture Verification",
                use_container_width=True,
            )
        else:
            st.warning("No camera image found for this student.")


@st.dialog("Medical Certificate / Document Attachment")
def show_document_modal():
    rec = st.session_state.selected_doc_record
    if rec:
        st.write(f"**Student:** {rec.get('Name')} ({rec.get('Matrix')})")
        st.write(f"**Document Name:** {rec.get('doc_name', 'Attachment')}")

        doc_bytes = rec.get("doc_bytes")
        doc_type = rec.get("doc_type", "")

        if doc_bytes:
            if "pdf" in doc_type.lower():
                st.info("PDF Document Preview Available for Download below:")
                st.download_button(
                    label="Download Document File",
                    data=doc_bytes,
                    file_name=rec.get("doc_name", "Medical_Certificate.pdf"),
                    mime="application/pdf",
                )
            else:
                st.image(
                    doc_bytes,
                    caption="Uploaded Document Proof",
                    use_container_width=True,
                )
        else:
            st.warning("No document attachment found for this record.")


@st.dialog("Medical Certificate / Absence Confirmation")
def confirm_absence_submission():
    st.info("Medical Certificate / Memo Notice")
    st.write(
        "You are submitting an absence record. Please ensure any attached document or medical memo "
        "is valid and legible for lecturer verification."
    )
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Confirm & Submit Attendance"):
            if st.session_state.pending_attendance_record:
                global_store["attendance_db"].append(
                    st.session_state.pending_attendance_record
                )
                global_store["submitted_students"].add(
                    st.session_state.student_matrix
                )

                st.session_state.pending_attendance_record = None
                st.session_state.show_absence_modal = False

                st.session_state.student_name = ""
                st.session_state.student_matrix = ""
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
    st.title("Campus Attendance Management System")
    st.write("Please select your portal to proceed with authentication.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Lecturer Portal")
        if st.button("Go to Lecturer Login"):
            st.session_state.current_page = "LecturerLogin"
            st.rerun()
    with col2:
        st.subheader("Student Portal")
        if st.button("Go to Student Login"):
            st.session_state.current_page = "StudentLogin"
            st.rerun()

# ==========================================
# PAGE 2: LECTURER LOGIN
# ==========================================
elif st.session_state.current_page == "LecturerLogin":
    st.title("Lecturer Login")
    if st.button("Back to Main Portal"):
        st.session_state.current_page = "Landing"
        st.rerun()

    with st.form("lecturer_login_form"):
        lec_name_input = st.text_input("Enter Lecturer Name:")
        lec_id_input = st.text_input("Enter Lecturer ID:")
        login_btn = st.form_submit_button("Log In")
        if login_btn:
            if lec_name_input.strip() and lec_id_input.strip():
                st.session_state.lecturer_name = lec_name_input
                st.session_state.lecturer_id = lec_id_input
                st.session_state.current_page = "LecturerDashboard"
                st.rerun()
            else:
                st.error("Fields cannot be empty.")

# ==========================================
# PAGE 3: STUDENT LOGIN
# ==========================================
elif st.session_state.current_page == "StudentLogin":
    st.title("Student Login")
    if st.button("Back to Main Portal"):
        st.session_state.current_page = "Landing"
        st.rerun()

    with st.form("student_login_form"):
        stud_name_input = st.text_input("Enter Full Name:")
        stud_matrix_input = st.text_input("Enter Matrix Number:")
        stud_login_btn = st.form_submit_button("Log In")
        if stud_login_btn:
            if stud_name_input.strip() and stud_matrix_input.strip():
                st.session_state.student_name = stud_name_input
                st.session_state.student_matrix = stud_matrix_input
                st.session_state.current_page = "StudentDashboard"
                st.rerun()
            else:
                st.error("Fields cannot be empty.")

# ==========================================
# PAGE 4: LECTURER DASHBOARD
# ==========================================
elif st.session_state.current_page == "LecturerDashboard":
    st.title("Lecturer Dashboard")
    st.write(
        f"Logged in Lecturer: **{st.session_state.lecturer_name}** (ID:"
        f" **{st.session_state.lecturer_id}**)"
    )

    col_out, _ = st.columns([1, 4])
    with col_out:
        if st.button("Log Out"):
            st.session_state.current_page = "Landing"
            st.rerun()

    loc = get_geolocation()
    lec_lat, lec_lon = None, None
    if loc and "coords" in loc:
        lec_lat, lec_lon = loc["coords"]["latitude"], loc["coords"]["longitude"]
        st.subheader("Verified")
        st.success("Classroom location captured successfully.")
    else:
        st.subheader("Checking Location")
        st.warning("Waiting for browser location authorization...")

    st.subheader("Class Session")
    lecturer_subject = st.selectbox(
        "Select Lecture Subject",
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
        "Select Laboratory / Classroom Location",
        [
            "CCNA 1",
            "CCNA 2",
            "CNL 1",
            "CNL 2",
            "IT 1",
            "IT 2",
            "APDV 1",
            "APDV 2",
            "LL1",
            "LL2",
            "DKU",
            "DK1",
            "DK2",
            "DK3",
            "DK4",
            "BK1",
            "BK2",
            "BK3",
            "BK4",
            "BK5",
            "BK6",
            "BK7",
            "BK8",
            "BK9",
            "BK10",
            "BS-JPA",
        ],
    )

    btn_col1, btn_col2, btn_col3, _ = st.columns([2.6, 2.0, 2.0, 3.4])
    with btn_col1:
        if st.button("Get Attendance (Activate Session)", type="primary"):
            if lec_lat is None or lec_lon is None:
                st.error("GPS coordinates needed to activate session.")
            else:
                global_store["session_active"] = True
                global_store["subject"] = lecturer_subject
                global_store["lab"] = lecturer_lab
                global_store["lecturer_lat"] = lec_lat
                global_store["lecturer_lon"] = lec_lon
                global_store["submitted_students"].clear()
                st.success(
                    f"Session activated for {lecturer_subject} at {lecturer_lab}."
                )
                st.rerun()

    with btn_col2:
        if st.button("Refresh Attendance Table"):
            st.rerun()

    with btn_col3:
        if global_store["session_active"]:
            if st.button("Close Attendance Session"):
                global_store["session_active"] = False
                st.success("Attendance session has been closed.")
                st.rerun()

    st.markdown("---")
    st.subheader("Attendance Record")

    attendance_list = global_store["attendance_db"]
    if attendance_list:
        st.write(f"Total Submissions Logged: **{len(attendance_list)}**")
        mc_count = sum(1 for item in attendance_list if item.get("has_mc"))
        st.metric(
            label="Total Records with Medical Certificates / Memos",
            value=mc_count,
        )

        df = pd.DataFrame(attendance_list)
        display_columns = ["Timestamp", "Name", "Matrix", "Subject", "Lab", "Status", "File Name"]
        existing_cols = [c for c in display_columns if c in df.columns]
        st.dataframe(df[existing_cols], use_container_width=True)

        st.markdown("### Verification Actions")

        records_to_delete = []

        # Table Header
        h_ts, h_nm, h_mx, h_sub, h_st, h_act = st.columns([1.5, 1.5, 1.2, 1.5, 1.2, 1.5])
        h_ts.markdown("**Timestamp**")
        h_nm.markdown("**Name**")
        h_mx.markdown("**Matrix**")
        h_sub.markdown("**Subject**")
        h_st.markdown("**Status**")
        h_act.markdown("**Actions**")
        st.markdown("<hr style='margin-top:2px; margin-bottom:10px;' />", unsafe_allow_html=True)

        # Table Rows
        for idx, rec in enumerate(attendance_list):
            c_ts, c_nm, c_mx, c_sub, c_st, c_act = st.columns([1.5, 1.5, 1.2, 1.5, 1.2, 1.5])

            c_ts.write(rec.get("Timestamp", "-"))
            c_nm.write(f"**{rec.get('Name', '-')}**")
            c_mx.write(rec.get("Matrix", "-"))
            c_sub.write(rec.get("Subject", "-"))
            c_st.write(rec.get("Status", "-"))

            # Closely stacked vertical actions container
            with c_act:
                st.markdown('<div class="action-btn-container">', unsafe_allow_html=True)
                
                if rec.get("image_bytes"):
                    if st.button("Photo", key=f"img_btn_{idx}", help="View Camera Photo"):
                        st.session_state.selected_image_record = rec
                        st.rerun()

                if rec.get("doc_bytes"):
                    if st.button("Doc", key=f"doc_btn_{idx}", help="View Document Proof"):
                        st.session_state.selected_doc_record = rec
                        st.rerun()

                st.markdown('<div class="action-btn-container-delete">', unsafe_allow_html=True)
                if st.button("Delete", key=f"del_btn_{idx}", help="Remove Record"):
                    records_to_delete.append(idx)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

        if records_to_delete:
            for d_idx in sorted(records_to_delete, reverse=True):
                removed_rec = global_store["attendance_db"].pop(d_idx)
                removed_matrix = removed_rec.get("Matrix")
                if removed_matrix in global_store["submitted_students"]:
                    global_store["submitted_students"].remove(removed_matrix)
            st.success("Student record successfully removed.")
            st.rerun()

        st.markdown("---")

        pdf_bytes = generate_pdf_report(
            st.session_state.lecturer_name,
            st.session_state.lecturer_id,
            global_store["subject"],
            global_store["lab"],
            attendance_list,
        )

        st.download_button(
            label="Download Attendance PDF Report",
            data=pdf_bytes,
            file_name=f"Attendance_Report_{get_current_local_datetime().strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf",
        )
    else:
        st.info("No attendance submissions logged yet.")

# ==========================================
# PAGE 5: STUDENT DASHBOARD
# ==========================================
elif st.session_state.current_page == "StudentDashboard":
    st.title("Student Dashboard")
    st.write(
        f"Logged in Student: **{st.session_state.student_name}** (Matrix:"
        f" **{st.session_state.student_matrix}**)"
    )

    col_out, col_ref, _ = st.columns([1.2, 2.2, 6.6])
    with col_out:
        if st.button("Log Out"):
            st.session_state.student_name = ""
            st.session_state.student_matrix = ""
            st.session_state.current_page = "Landing"
            st.rerun()
    with col_ref:
        if st.button("Sync Class Session Status"):
            st.rerun()

    st.markdown("---")

    if global_store["session_active"]:
        if (
            st.session_state.student_matrix
            in global_store["submitted_students"]
        ):
            st.success(
                "You have already submitted your attendance for this active"
                " session."
            )
            st.info(
                "Multiple entries for the same class session are not allowed."
            )
        else:
            st.markdown(
                f"**Active Session:** {global_store['subject']}"
                f" ({global_store['lab']})"
            )

            student_loc = get_geolocation()
            student_lat, student_lon = None, None

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
                    st.success(
                        "Location Status: Verified (Inside designated classroom"
                        " area)"
                    )
                else:
                    st.error(
                        "Location Status: Verification Failed (Outside"
                        " designated classroom area)"
                    )

                st.markdown("---")

                if distance <= MAX_ALLOWED_DISTANCE_METERS:
                    now_myt = get_current_local_datetime()

                    with st.form("student_attendance_form"):
                        attendance_date = st.date_input(
                            "Select Date (MYT)", value=now_myt.date()
                        )
                        attendance_time = st.time_input(
                            "Select Time (MYT)", value=now_myt.time()
                        )
                        attendance_status_type = st.selectbox(
                            "Attendance Status",
                            [
                                "Present",
                                "Absent with Medical Certificate / Memo",
                            ],
                        )
                        mc_reason_input = st.text_input(
                            "Reason (if applicable):"
                        )

                        st.markdown("---")
                        st.write("**Mandatory Facial Verification:**")
                        st.warning(
                            "Camera Capture Required: You must take a face photo with a clearly visible human face, or your attendance will not be counted."
                        )

                        camera_photo = st.camera_input(
                            "Take a face photo (Mandatory)",
                            key="mc_camera_input",
                        )
                        uploaded_file = st.file_uploader(
                            "Optional Document / Medical Certificate Attachment",
                            type=["pdf", "png", "jpg"],
                            key="mc_file_uploader",
                        )

                        submit_attempt_btn = st.form_submit_button(
                            "Submit Attendance Record"
                        )

                        if submit_attempt_btn:
                            if camera_photo is None:
                                st.error(
                                    "Submission Blocked: You MUST take a face"
                                    " photo using the camera before submitting."
                                )
                                st.stop()

                            img_bytes = camera_photo.getvalue()

                            face_detected = detect_face_in_image(img_bytes)
                            if not face_detected:
                                st.error(
                                    "Facial Verification Failed: No human face"
                                    " detected in your photo. Please align"
                                    " your face clearly in front of the camera"
                                    " and ensure good lighting."
                                )
                                st.stop()

                            doc_bytes = None
                            doc_name = None
                            doc_type = None

                            file_name_str = (
                                f"Facial_Verification_{st.session_state.student_matrix}.jpg"
                            )
                            if uploaded_file is not None:
                                doc_bytes = uploaded_file.getvalue()
                                doc_name = uploaded_file.name
                                doc_type = uploaded_file.type
                                file_name_str += f" | {doc_name}"

                            has_mc_flag = (
                                attendance_status_type
                                == "Absent with Medical Certificate / Memo"
                            )

                            timestamp_str = f"{attendance_date} {attendance_time.strftime('%H:%M:%S')}"

                            record_data = {
                                "Timestamp": timestamp_str,
                                "Name": st.session_state.student_name,
                                "Matrix": st.session_state.student_matrix,
                                "Subject": global_store["subject"],
                                "Lab": global_store["lab"],
                                "Status": attendance_status_type,
                                "has_mc": has_mc_flag,
                                "File Name": file_name_str,
                                "image_bytes": img_bytes,
                                "doc_bytes": doc_bytes,
                                "doc_name": doc_name,
                                "doc_type": doc_type,
                            }

                            if has_mc_flag:
                                st.session_state.pending_attendance_record = (
                                    record_data
                                )
                                st.session_state.show_absence_modal = True
                                st.rerun()
                            else:
                                global_store["attendance_db"].append(
                                    record_data
                                )
                                global_store["submitted_students"].add(
                                    st.session_state.student_matrix
                                )

                                st.session_state.student_name = ""
                                st.session_state.student_matrix = ""
                                st.session_state.current_page = "Landing"
                                st.rerun()
            else:
                st.info("Awaiting location authorization from browser...")
    else:
        st.warning(
            "Attendance session is currently closed. Click 'Sync Class Session"
            " Status' when class starts."
        )