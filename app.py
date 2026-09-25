# app.py
import streamlit as st
import datetime
import pandas as pd
import math
import io
import cv2
import numpy as np
from streamlit_js_eval import get_geolocation

# ReportLab imports for generating PDF reports
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# THREAD-SAFE GLOBAL SHARED STATE (Cross-Session)
# ==========================================
class AttendanceSystemState:
    """Class to share global state across ALL user sessions and tabs."""
    def __init__(self):
        self.session_active = False
        self.subject = ""
        self.lab = ""
        self.lecturer_lat = None
        self.lecturer_lon = None
        self.attendance_db = []

@st.cache_resource
def get_global_system_state():
    """Returns a single shared instance accessible by ALL users/tabs."""
    return AttendanceSystemState()

global_state = get_global_system_state()
MAX_ALLOWED_DISTANCE_METERS = 50.0

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def detect_face_in_image(image_bytes):
    """Strictly checks if a human face is present in the image using OpenCV Haar Cascades."""
    try:
        file_bytes = np.asarray(bytearray(image_bytes), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load Haar Cascade face detector
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        return len(faces) > 0
    except Exception:
        return False

def colorize_attendance_row(row):
    if "Present" in str(row["Status"]):
        return ['background-color: #d4edda; color: #155724'] * len(row)
    else:
        return ['background-color: #f8d7da; color: #721c24'] * len(row)

# Helper function: Generate PDF binary stream
def generate_pdf_report(lecturer_name, lecturer_id, subject, lab, attendance_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#1E3A8A'))
    normal_style = styles['Normal']

    story.append(Paragraph("Campus Attendance Management System - Report", title_style))
    story.append(Spacer(1, 10))

    meta_text = f"""
    <b>Lecturer:</b> {lecturer_name} (ID: {lecturer_id})<br/>
    <b>Subject:</b> {subject if subject else 'N/A'}<br/>
    <b>Location:</b> {lab if lab else 'N/A'}<br/>
    <b>Generated Date:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    story.append(Paragraph(meta_text, normal_style))
    story.append(Spacer(1, 15))

    table_data = [["Timestamp", "Name", "Matrix No.", "Status", "Attachment"]]
    for record in attendance_data:
        table_data.append([
            str(record.get("Timestamp", "")),
            str(record.get("Name", "")),
            str(record.get("Matrix", "")),
            str(record.get("Status", "")),
            str(record.get("File Name", "None"))
        ])

    pdf_table = Table(table_data, colWidths=[110, 120, 90, 120, 110])
    pdf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))

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

# Separate Dialog Modal ONLY for Medical Certificate / Absence Acknowledgement
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
                global_state.attendance_db.append(st.session_state.pending_attendance_record)
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
    st.title("Lecturer Portal Authentication")
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
    st.title("Student Portal Authentication")
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
    st.title("Lecturer Control Dashboard")
    st.write(f"Logged in Lecturer: {st.session_state.lecturer_name} (ID: {st.session_state.lecturer_id})")
    
    col_l1, col_l2 = st.columns([1, 4])
    with col_l1:
        if st.button("Log Out"):
            st.session_state.current_page = "Landing"
            st.rerun()
    with col_l2:
        if st.button("Refresh Attendance Table"):
            st.rerun()
        
    st.subheader("Classroom Location Verification")
    loc = get_geolocation()
    lec_lat, lec_lon = None, None
    if loc and "coords" in loc:
        lec_lat, lec_lon = loc["coords"]["latitude"], loc["coords"]["longitude"]
        st.success("Classroom location captured successfully.")
    else:
        st.warning("Waiting for browser location authorization...")

    with st.form("lecturer_session_form"):
        st.subheader("Configure Class Session Parameters")
        lecturer_subject = st.selectbox("Select Lecture Subject", ["DFK50083 Python Programming", "DBF50123 Database Systems", "DTN50233 Network Security"])
        lecturer_lab = st.selectbox("Select Laboratory Location", ["Lab Alpha", "Lab Beta", "Lab Gamma", "Networking Lab 1"])
        activate_btn = st.form_submit_button("Get Attendance (Activate Session)")
        
        if activate_btn:
            if lec_lat is None or lec_lon is None:
                st.error("GPS coordinates needed to activate session.")
            else:
                global_state.session_active = True
                global_state.subject = lecturer_subject
                global_state.lab = lecturer_lab
                global_state.lecturer_lat = lec_lat
                global_state.lecturer_lon = lec_lon
                st.success(f"Session activated for {lecturer_subject} at {lecturer_lab}.")

    st.markdown("---")
    st.subheader("Live Attendance Records")
    
    if global_state.attendance_db:
        st.write(f"Total Submissions Logged: **{len(global_state.attendance_db)}**")
        mc_count = sum(1 for item in global_state.attendance_db if item.get("has_mc"))
        st.metric(label="Total Records with Medical Certificates / Memos", value=mc_count)
        
        df_records = pd.DataFrame(global_state.attendance_db)
        styled_df = df_records[['Timestamp', 'Name', 'Matrix', 'Subject', 'Lab', 'Status', 'File Name']].style.apply(colorize_attendance_row, axis=1)
        st.dataframe(styled_df, height=250, use_container_width=True)
        
        records_with_images = [r for r in global_state.attendance_db if r.get("image_bytes") is not None]
        if records_with_images:
            st.subheader("Submitted Evidence / Facial Captures")
            img_cols = st.columns(min(3, len(records_with_images)))
            for idx, rec in enumerate(records_with_images):
                with img_cols[idx % 3]:
                    st.image(
                        rec["image_bytes"],
                        caption=f"{rec['Name']} ({rec['Matrix']}) - {rec['File Name']}",
                        use_container_width=True
                    )
        
        st.markdown("---")
        
        pdf_bytes = generate_pdf_report(
            st.session_state.lecturer_name,
            st.session_state.lecturer_id,
            global_state.subject,
            global_state.lab,
            global_state.attendance_db
        )
        
        st.download_button(
            label="Download Attendance PDF Report",
            data=pdf_bytes,
            file_name=f"Attendance_Report_{datetime.date.today()}.pdf",
            mime="application/pdf"
        )
    else:
        st.info("No attendance submissions logged yet.")

# ==========================================
# PAGE 5: STUDENT DASHBOARD
# ==========================================
elif st.session_state.current_page == "StudentDashboard":
    st.title("Student Attendance Portal")
    st.write(f"Logged in Student: **{st.session_state.student_name}** (Matrix: **{st.session_state.student_matrix}**)")
    
    col_out, col_ref = st.columns([1, 4])
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

    if global_state.session_active:
        st.markdown(f"**Active Session:** {global_state.subject} ({global_state.lab})")
        
        student_loc = get_geolocation()
        student_lat, student_lon = None, None
        
        if student_loc and "coords" in student_loc:
            student_lat, student_lon = student_loc["coords"]["latitude"], student_loc["coords"]["longitude"]
            distance = calculate_distance(global_state.lecturer_lat, global_state.lecturer_lon, student_lat, student_lon)
            
            if distance <= MAX_ALLOWED_DISTANCE_METERS:
                st.success("Location Status: Verified (Inside designated classroom area)")
            else:
                st.error("Location Status: Verification Failed (Outside designated classroom area)")
                
            st.markdown("---")
            
            if distance <= MAX_ALLOWED_DISTANCE_METERS:
                with st.form("student_attendance_form"):
                    attendance_date = st.date_input("Select Date", value=datetime.date.today())
                    attendance_time = st.time_input("Select Time", value=datetime.datetime.now().time())
                    attendance_status_type = st.selectbox("Attendance Status", ["Present", "Absent with Medical Certificate / Memo"])
                    mc_reason_input = st.text_input("Reason (if applicable):")
                    
                    st.markdown("---")
                    st.write("**Identity & Verification Option:**")
                    st.warning("Facial Camera Requirement: Photo capture strictly requires a visible human face in the camera frame.")
                    
                    tab_upload, tab_camera = st.tabs(["Upload Document / Memo (Optional)", "Take Facial Camera Photo (Required if no file)"])
                    
                    with tab_upload:
                        uploaded_file = st.file_uploader("Upload Medical Certificate / Memo", type=["pdf", "png", "jpg"], key="mc_file_uploader")
                    
                    with tab_camera:
                        camera_photo = st.camera_input("Capture live facial verification photo", key="mc_camera_input")
                    
                    submit_attempt_btn = st.form_submit_button("Submit Attendance Record")
                    
                    if submit_attempt_btn:
                        file_name_str = "No File Attached"
                        img_bytes = None
                        
                        # Validate Camera Photo for Facial Presence
                        if camera_photo is not None:
                            img_bytes = camera_photo.getvalue()
                            face_detected = detect_face_in_image(img_bytes)
                            
                            if not face_detected:
                                st.error("Facial Verification Failed: No human face detected in the photo. Please frame your face clearly and try again.")
                                st.stop()
                            else:
                                file_name_str = f"Facial_Verification_{st.session_state.student_matrix}.jpg"
                        
                        elif uploaded_file is not None:
                            file_name_str = uploaded_file.name
                            if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
                                img_bytes = uploaded_file.getvalue()
                        
                        has_mc_flag = (attendance_status_type == "Absent with Medical Certificate / Memo")
                        
                        record_data = {
                            "Timestamp": str(f"{attendance_date} {attendance_time}"),
                            "Name": st.session_state.student_name,
                            "Matrix": st.session_state.student_matrix,
                            "Subject": global_state.subject,
                            "Lab": global_state.lab,
                            "Status": attendance_status_type,
                            "has_mc": has_mc_flag,
                            "File Name": file_name_str,
                            "image_bytes": img_bytes
                        }
                        
                        # Memo modal popup for absent status (can be submitted without strict face requirement)
                        if has_mc_flag:
                            st.session_state.pending_attendance_record = record_data
                            st.session_state.show_absence_modal = True
                            st.rerun()
                        else:
                            global_state.attendance_db.append(record_data)
                            st.session_state.student_name = ""
                            st.session_state.student_matrix = ""
                            st.session_state.current_page = "Landing"
                            st.rerun()
        else:
            st.info("Awaiting location authorization from browser...")
    else:
        st.warning("Attendance session is currently closed. Click 'Sync Class Session Status' when class starts.")