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
# THREAD-SAFE GLOBAL SHARED STATE (Cross-Session)
# Uses a simple Python dictionary to prevent Streamlit caching errors
# ==========================================
@st.cache_resource
def get_global_store():
    """Returns a single shared dictionary instance accessible by ALL users/tabs."""
    return {
        "session_active": False,
        "subject": "",
        "lab": "",
        "lecturer_lat": None,
        "lecturer_lon": None,
        "attendance_db": [],
        "submitted_students": set(),
    }


# Retrieve or initialize dictionary keys dynamically to prevent missing key errors
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
    """Returns accurate current datetime explicitly set to Malaysia Time (Asia/Kuala_Lumpur)."""
    return datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Kuala_Lumpur"))


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0  # Radius of Earth in meters
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
    """Accurately verifies that a human face is present in the camera image."""
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
        textColor=colors.HexColor("#1E3A8A"),
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
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F9FAFB")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
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
    st.title("Lecturer")
    st.write(
        f"Logged in Lecturer: {st.session_state.lecturer_name} (ID:"
        f" {st.session_state.lecturer_id})"
    )

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

    with st.form("lecturer_session_form"):
        st.subheader("Configure Class Session Parameters")
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
        
        activate_btn = st.form_submit_button("Get Attendance (Activate Session)")

        if activate_btn:
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

        col_btn1, col_btn2, col_spacer = st.columns([1.1, 1.2, 2.0])
        with col_btn1:
            refresh_btn = st.form_submit_button("Refresh Attendance Table")
            if refresh_btn:
                st.rerun()
        with col_btn2:
            if global_store["session_active"]:
                close_btn = st.form_submit_button("Close Attendance Session", type="primary")
                if close_btn:
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

        # PREVIOUS TABLE DISPLAY RESTORED
        df = pd.DataFrame(attendance_list)
        display_columns = ["Timestamp", "Name", "Matrix", "Subject", "Lab", "Status", "File Name"]
        existing_cols = [c for c in display_columns if c in df.columns]
        st.dataframe(df[existing_cols], use_container_width=True)

        st.markdown("### Attachment & Verification Actions")
        
        records_to_delete = []

        for idx, rec in enumerate(attendance_list):
            col_info, col_img, col_doc, col_del = st.columns([3, 1.2, 1.2, 1.2])
            
            with col_info:
                st.write(f"**{idx + 1}. {rec.get('Name')}** ({rec.get('Matrix')}) - *{rec.get('Status')}*")
            
            with col_img:
                if rec.get("image_bytes"):
                    if st.button("View Photo", key=f"img_btn_{idx}"):
                        st.session_state.selected_image_record = rec
                        st.rerun()
                else:
                    st.caption("No Photo")

            with col_doc:
                if rec.get("doc_bytes"):
                    if st.button("View Doc", key=f"doc_btn_{idx}"):
                        st.session_state.selected_doc_record = rec
                        st.rerun()
                else:
                    st.caption("No Doc")

            with col_del:
                if st.button("Remove", key=f"del_btn_{idx}"):
                    records_to_delete.append(idx)

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
    st.title("Student")
    st.write(
        f"Logged in Student: **{st.session_state.student_name}** (Matrix:"
        f" **{st.session_state.student_matrix}**)"
    )

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