# app.py
import streamlit as st
import datetime
import pandas as pd
import math
from streamlit_js_eval import get_geolocation
import models

# ==========================================
# GLOBAL MODULE-LEVEL VARIABLES (Shared across tabs/users)
# ==========================================
if "GLOBAL_SESSION_ACTIVE" not in globals():
    GLOBAL_SESSION_ACTIVE = False
    GLOBAL_SUBJECT = ""
    GLOBAL_LAB = ""
    GLOBAL_LECTURER_LAT = None
    GLOBAL_LECTURER_LON = None
    GLOBAL_ATTENDANCE_DB = []

# Maximum allowable physical distance between student and lecturer (in meters)
MAX_ALLOWED_DISTANCE_METERS = 50.0

# Helper function: Calculate distance between two GPS coordinates using Haversine Formula
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

# Styling helper function for soft-color row highlights
def colorize_attendance_row(row):
    """Applies soft green for Present and soft red for Absent rows."""
    if "Present" in str(row["Status"]):
        return ['background-color: #d4edda; color: #155724'] * len(row)
    else:
        return ['background-color: #f8d7da; color: #721c24'] * len(row)

# Initialize session state variables
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

if "pending_attendance_data" not in st.session_state:
    st.session_state.pending_attendance_data = None

# ==========================================
# PAGE 1: LANDING / SEPARATE LOGIN GATEWAY
# ==========================================
if st.session_state.current_page == "Landing":
    st.title("Campus Attendance Management System")
    st.write("Please select your portal to proceed with authentication.")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Lecturer Portal")
        st.write("Access control dashboard to trigger attendance sessions and monitor records.")
        if st.button("Go to Lecturer Login"):
            st.session_state.current_page = "LecturerLogin"
            st.rerun()
            
    with col2:
        st.subheader("Student Portal")
        st.write("Access attendance submission forms during active class sessions.")
        if st.button("Go to Student Login"):
            st.session_state.current_page = "StudentLogin"
            st.rerun()

# ==========================================
# PAGE 2: LECTURER LOGIN PAGE
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
            try:
                if not lec_name_input.strip() or not lec_id_input.strip():
                    raise ValueError("Lecturer Name and ID cannot be empty.")
                st.session_state.lecturer_name = lec_name_input
                st.session_state.lecturer_id = lec_id_input
                st.session_state.current_page = "LecturerDashboard"
                st.rerun()
            except ValueError as ve:
                st.error(f"Login Validation Error: {ve}")

# ==========================================
# PAGE 3: STUDENT LOGIN PAGE
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
            try:
                if not stud_name_input.strip() or not stud_matrix_input.strip():
                    raise ValueError("Student Name and Matrix Number cannot be empty.")
                st.session_state.student_name = stud_name_input
                st.session_state.student_matrix = stud_matrix_input
                st.session_state.current_page = "StudentDashboard"
                st.rerun()
            except ValueError as ve:
                st.error(f"Login Validation Error: {ve}")

# ==========================================
# PAGE 4: LECTURER DASHBOARD
# ==========================================
elif st.session_state.current_page == "LecturerDashboard":
    st.title("Lecturer Control Dashboard")
    st.write(f"Logged in Lecturer: {st.session_state.lecturer_name} (ID: {st.session_state.lecturer_id})")
    
    if st.button("Log Out"):
        st.session_state.current_page = "Landing"
        st.rerun()
        
    st.subheader("Classroom Location Verification")
    st.info("Please allow browser location access so the system can set the classroom boundary for students.")
    
    # Prompt browser for lecturer's GPS location immediately
    loc = get_geolocation()
    
    lec_lat = None
    lec_lon = None
    if loc and "coords" in loc:
        lec_lat = loc["coords"]["latitude"]
        lec_lon = loc["coords"]["longitude"]
        st.success(f"Classroom GPS Coordinates Captured: Lat {lec_lat:.5f}, Lon {lec_lon:.5f}")
    else:
        st.warning("Waiting for browser location authorization... Please click 'Allow' when prompted by your browser.")

    with st.form("lecturer_session_form"):
        st.subheader("Configure Class Session Parameters")
        lecturer_subject = st.selectbox("Select Lecture Subject", ["DFK50083 Python Programming", "DBF50123 Database Systems", "DTN50233 Network Security"])
        lecturer_lab = st.selectbox("Select Laboratory Location", ["Lab Alpha", "Lab Beta", "Lab Gamma", "Networking Lab 1"])
        
        activate_btn = st.form_submit_button("Get Attendance (Activate Session)")
        
        if activate_btn:
            if lec_lat is None or lec_lon is None:
                st.error("Cannot activate session without GPS location. Please allow browser location access and try again.")
            else:
                globals()["GLOBAL_SESSION_ACTIVE"] = True
                globals()["GLOBAL_SUBJECT"] = lecturer_subject
                globals()["GLOBAL_LAB"] = lecturer_lab
                globals()["GLOBAL_LECTURER_LAT"] = lec_lat
                globals()["GLOBAL_LECTURER_LON"] = lec_lon
                st.success(f"Session activated for {lecturer_subject} at {lecturer_lab}. Physical boundary set within {MAX_ALLOWED_DISTANCE_METERS} meters.")

    st.markdown("---")
    st.subheader("Attendance Records")
    
    if globals()["GLOBAL_ATTENDANCE_DB"]:
        st.write(f"Total Subscriptions Logged: {len(globals()['GLOBAL_ATTENDANCE_DB'])}")
        mc_count = sum(1 for item in globals()["GLOBAL_ATTENDANCE_DB"] if item.get("has_mc"))
        st.metric(label="Total Records with Medical Certificates / Memos", value=mc_count)
        
        df_records = pd.DataFrame(globals()["GLOBAL_ATTENDANCE_DB"])
        styled_df = df_records[['Timestamp', 'Name', 'Matrix', 'Subject', 'Lab', 'Status', 'File Name']].style.apply(colorize_attendance_row, axis=1)
        
        st.dataframe(styled_df, height=450, use_container_width=True)
    else:
        st.info("No attendance records found in the database for the current session.")

# ==========================================
# PAGE 5: STUDENT DASHBOARD
# ==========================================
elif st.session_state.current_page == "StudentDashboard":
    st.title("Student Attendance Portal")
    st.write(f"Logged in Student: {st.session_state.student_name} (Matrix: {st.session_state.student_matrix})")
    
    col_out, col_ref = st.columns([1, 4])
    with col_out:
        if st.button("Log Out"):
            st.session_state.current_page = "Landing"
            st.rerun()
    with col_ref:
        if st.button("🔄 Refresh Session Status"):
            st.rerun()

    st.subheader("Student Location Verification")
    
    # CRITICAL FIX: Trigger get_geolocation() ALWAYS at the top level of Student Dashboard
    # so the browser pops up the 'Allow Location' permission prompt instantly upon login.
    student_loc = get_geolocation()
    
    student_lat = None
    student_lon = None

    if student_loc and "coords" in student_loc:
        student_lat = student_loc["coords"]["latitude"]
        student_lon = student_loc["coords"]["longitude"]
        st.success(f"Student GPS Coordinates Captured: Lat {student_lat:.5f}, Lon {student_lon:.5f}")
    else:
        st.warning("⚠️ Location access required: Please click 'Allow' on your browser popup to enable attendance submission.")

    st.markdown("---")

    # Check session state
    if globals()["GLOBAL_SESSION_ACTIVE"]:
        lec_lat = globals()["GLOBAL_LECTURER_LAT"]
        lec_lon = globals()["GLOBAL_LECTURER_LON"]
        
        if student_lat is None or student_lon is None:
            st.info("Awaiting student GPS authorization... Please ensure your device location is turned on and allowed in the browser.")
        else:
            # Calculate physical distance in meters between lecturer and student
            distance = calculate_distance(lec_lat, lec_lon, student_lat, student_lon)
            
            st.write(f"Calculated distance to classroom: **{distance:.1f} meters**")
            
            if distance > MAX_ALLOWED_DISTANCE_METERS:
                st.error(f"Location Verification Failed: You are {distance:.1f} meters away from the classroom. Submissions are restricted to within {MAX_ALLOWED_DISTANCE_METERS} meters.")
            else:
                st.success(f"Location Verified: You are within the classroom boundary ({distance:.1f}m away). Active session for {globals()['GLOBAL_SUBJECT']} in {globals()['GLOBAL_LAB']}.")
                
                with st.form("student_attendance_form"):
                    st.subheader("Submit Attendance Details")
                    
                    attendance_date = st.date_input("Select Date", value=datetime.date.today())
                    attendance_time = st.time_input("Select Time", value=datetime.datetime.now().time())
                    
                    attendance_status_type = st.selectbox("Attendance Status", ["Present", "Absent with Medical Certificate / Memo"])
                    mc_reason_input = st.text_input("Reason for Absence / Medical Condition (if applicable):")
                    uploaded_file = st.file_uploader("Upload Medical Certificate or Absence Memo (PDF/Image)", type=["pdf", "png", "jpg"])
                    
                    submit_attempt_btn = st.form_submit_button("Submit Attendance Record")
                    
                    if submit_attempt_btn:
                        try:
                            if attendance_status_type == "Absent with Medical Certificate / Memo" and not mc_reason_input.strip():
                                raise ValueError("Please provide a reason or details for your medical certificate/memo.")
                            
                            has_mc_flag = (attendance_status_type == "Absent with Medical Certificate / Memo")
                            file_name_str = uploaded_file.name if uploaded_file else "No File Attached"
                            
                            if attendance_status_type == "Absent with Medical Certificate / Memo" and file_name_str == "No File Attached":
                                st.session_state.show_absence_modal = True
                                st.session_state.pending_attendance_data = {
                                    "Timestamp": str(f"{attendance_date} {attendance_time}"),
                                    "Name": st.session_state.student_name,
                                    "Matrix": st.session_state.student_matrix,
                                    "Subject": globals()["GLOBAL_SUBJECT"],
                                    "Lab": globals()["GLOBAL_LAB"],
                                    "Status": attendance_status_type,
                                    "summary": f"Student: {st.session_state.student_name} | Matrix: {st.session_state.student_matrix} - Absent with No Evidence",
                                    "has_mc": False,
                                    "File Name": "No File Attached"
                                }
                            else:
                                record_obj = models.VerifiedAttendanceRecord(
                                    student_name=st.session_state.student_name,
                                    matrix_no=st.session_state.student_matrix,
                                    lab_name=globals()["GLOBAL_LAB"],
                                    subject_name=globals()["GLOBAL_SUBJECT"],
                                    has_mc=has_mc_flag,
                                    mc_reason=mc_reason_input if has_mc_flag else "None"
                                )
                                
                                record_data = {
                                    "Timestamp": str(f"{attendance_date} {attendance_time}"),
                                    "Name": st.session_state.student_name,
                                    "Matrix": st.session_state.student_matrix,
                                    "Subject": globals()["GLOBAL_SUBJECT"],
                                    "Lab": globals()["GLOBAL_LAB"],
                                    "Status": attendance_status_type,
                                    "summary": record_obj.process_record_summary(),
                                    "has_mc": has_mc_flag,
                                    "File Name": file_name_str
                                }
                                globals()["GLOBAL_ATTENDANCE_DB"].append(record_data)
                                st.success("Attendance submitted and recorded into the database successfully.")
                                
                        except ValueError as ve:
                            st.error(f"Validation Error: {ve}")
                        except Exception as e:
                            st.error(f"An unexpected error occurred during processing: {e}")
                
                # Modal Warning implementation using Streamlit containers
                if st.session_state.show_absence_modal:
                    st.warning("Warning Modal Reminder: You did not upload a medical certificate or memo. If you proceed, this will be counted as absence with no evidence. You can still confirm submission below.")
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        if st.button("Confirm Submit Without Evidence"):
                            globals()["GLOBAL_ATTENDANCE_DB"].append(st.session_state.pending_attendance_data)
                            st.session_state.show_absence_modal = False
                            st.session_state.pending_attendance_data = None
                            st.success("Absence recorded successfully without attached evidence.")
                            st.rerun()
                    with col_m2:
                        if st.button("Cancel & Go Back to Upload"):
                            st.session_state.show_absence_modal = False
                            st.session_state.pending_attendance_data = None
                            st.rerun()
    else:
        st.warning("Attendance session is currently closed. Please wait until the lecturer activates the attendance session, then click '🔄 Refresh Session Status'.")