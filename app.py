# app.py
import streamlit as st
import datetime
import pandas as pd
import models

# Initialize session state storage for database simulation and authentication
if "attendance_db" not in st.session_state:
    st.session_state.attendance_db = []

if "session_active" not in st.session_state:
    st.session_state.session_active = False

if "active_subject" not in st.session_state:
    st.session_state.active_subject = ""

if "active_lab" not in st.session_state:
    st.session_state.active_lab = ""

if "lecturer_logged_in" not in st.session_state:
    st.session_state.lecturer_logged_in = False

if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False

if "current_student_name" not in st.session_state:
    st.session_state.current_student_name = ""

if "current_student_matrix" not in st.session_state:
    st.session_state.current_student_matrix = ""

st.title("Campus Attendance Management System")
st.write("Secure portal for academic session tracking, attendance verification, and medical exemption logging.")

# ==========================================
# NETWORK ACCESS VALIDATION (Requirement 4)
# ==========================================
st.sidebar.header("Network Security Gateway")
network_status = st.sidebar.selectbox("Select Network Connection", ["Campus Secure Wi-Fi (Authorized)", "External Public Network (Unauthorized)"])

is_authorized_network = (network_status == "Campus Secure Wi-Fi (Authorized)")

if not is_authorized_network:
    st.error("Network Access Restricted: You must be connected to the authorized campus network to access active session features.")
    st.stop()

# ==========================================
# SEPARATE LOGIN GATEWAY (Requirement 0 & 3)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.header("System Login Portal")
portal_selection = st.sidebar.radio("Select Portal Access", ["Lecturer Login", "Student Login"])

# ------------------------------------------
# LECTURER LOGIN & SECTION
# ------------------------------------------
if portal_selection == "Lecturer Login":
    if not st.session_state.lecturer_logged_in:
        st.subheader("Lecturer Authentication Section")
        with st.form("lecturer_login_form"):
            lec_name = st.text_input("Enter Lecturer Name:")
            lec_id = st.text_input("Enter Lecturer ID:")
            lec_login_btn = st.form_submit_button("Log In as Lecturer")
            
            if lec_login_btn:
                try:
                    if not lec_name.strip() or not lec_id.strip():
                        raise ValueError("Lecturer Name and ID fields cannot be left empty.")
                    st.session_state.lecturer_logged_in = True
                    st.session_state.lecturer_name = lec_name
                    st.session_state.lecturer_id = lec_id
                    st.success("Lecturer login successful.")
                    st.rerun()
                except ValueError as ve:
                    st.error(f"Login Validation Error: {ve}")
    else:
        st.success(f"Logged in Lecturer: {st.session_state.lecturer_name} (ID: {st.session_state.lecturer_id})")
        if st.button("Log Out Lecturer"):
            st.session_state.lecturer_logged_in = False
            st.rerun()

        st.header("Lecturer Control Dashboard")
        
        with st.form("lecturer_session_form"):
            st.subheader("Configure Class Session Parameters")
            lecturer_subject = st.selectbox("Select Lecture Subject", ["DFK50083 Python Programming", "DBF50123 Database Systems", "DTN50233 Network Security"])
            lecturer_lab = st.selectbox("Select Laboratory Location", ["Lab Alpha", "Lab Beta", "Lab Gamma", "Networking Lab 1"])
            
            activate_btn = st.form_submit_button("Get Attendance (Activate Session)")
            
            if activate_btn:
                st.session_state.session_active = True
                st.session_state.active_subject = lecturer_subject
                st.session_state.active_lab = lecturer_lab
                st.success(f"Session activated for {lecturer_subject} at {lecturer_lab}. Notification sent to student portals.")

        st.markdown("---")
        # Requirement 1: Section title changed to Attendance
        st.subheader("Attendance")
        
        if st.session_state.attendance_db:
            st.write(f"Total Subscriptions Logged: {len(st.session_state.attendance_db)}")
            mc_count = sum(1 for item in st.session_state.attendance_db if item.get("has_mc"))
            st.metric(label="Total Records with Medical Certificates / Memos", value=mc_count)
            
            # Requirement 2: Fixed size, scrollable table layout using Pandas dataframe with height constraint
            df_records = pd.DataFrame(st.session_state.attendance_db)
            st.dataframe(
                df_records[['timestamp', 'name', 'matrix', 'subject', 'lab', 'status', 'file_name']],
                height=300,
                use_container_width=True
            )
        else:
            st.info("No attendance records found in the database for the current session.")

# ------------------------------------------
# STUDENT LOGIN & SECTION
# ------------------------------------------
elif portal_selection == "Student Login":
    if not st.session_state.student_logged_in:
        st.subheader("Student Authentication Section")
        with st.form("student_login_form"):
            stud_name = st.text_input("Enter Full Name:")
            stud_matrix = st.text_input("Enter Matrix Number:")
            stud_login_btn = st.form_submit_button("Log In as Student")
            
            if stud_login_btn:
                try:
                    if not stud_name.strip() or not stud_matrix.strip():
                        raise ValueError("Student Name and Matrix Number cannot be left empty.")
                    st.session_state.student_logged_in = True
                    st.session_state.current_student_name = stud_name
                    st.session_state.current_student_matrix = stud_matrix
                    st.success("Student login successful.")
                    st.rerun()
                except ValueError as ve:
                    st.error(f"Login Validation Error: {ve}")
    else:
        st.success(f"Logged in as: {st.session_state.current_student_name} (Matrix: {st.session_state.current_student_matrix})")
        if st.button("Log Out Student"):
            st.session_state.student_logged_in = False
            st.rerun()

        st.header("Student Attendance Portal")
        
        if st.session_state.session_active:
            st.info(f"Active Notification Reminder: Lecturer has initiated attendance for {st.session_state.active_subject} in {st.session_state.active_lab}.")
            
            with st.form("student_attendance_form"):
                st.subheader("Submit Attendance Details")
                
                attendance_date = st.date_input("Select Date", value=datetime.date.today())
                attendance_time = st.time_input("Select Time", value=datetime.datetime.now().time())
                
                attendance_status_type = st.selectbox("Attendance Status", ["Present", "Absent with Medical Certificate / Memo"])
                mc_reason_input = st.text_input("Reason for Absence / Medical Condition (if applicable):")
                
                uploaded_file = st.file_uploader("Upload Medical Certificate or Absence Memo (PDF/Image)", type=["pdf", "png", "jpg"])
                
                submit_attendance_btn = st.form_submit_button("Submit Attendance Record")
                
                if submit_attendance_btn:
                    try:
                        if attendance_status_type == "Absent with Medical Certificate / Memo" and not mc_reason_input.strip():
                            raise ValueError("Please provide a reason or details for your medical certificate/memo.")
                        
                        has_mc_flag = (attendance_status_type == "Absent with Medical Certificate / Memo")
                        file_name_str = uploaded_file.name if uploaded_file else "No File Attached"
                        
                        # Instantiate subclass object implementing inheritance
                        record_obj = models.VerifiedAttendanceRecord(
                            student_name=st.session_state.current_student_name,
                            matrix_no=st.session_state.current_student_matrix,
                            lab_name=st.session_state.active_lab,
                            subject_name=st.session_state.active_subject,
                            has_mc=has_mc_flag,
                            mc_reason=mc_reason_input if has_mc_flag else "None"
                        )
                        
                        timestamp_str = f"{attendance_date} {attendance_time}"
                        record_data = {
                            "timestamp": str(timestamp_str),
                            "name": st.session_state.current_student_name,
                            "matrix": st.session_state.current_student_matrix,
                            "subject": st.session_state.active_subject,
                            "lab": st.session_state.active_lab,
                            "status": attendance_status_type,
                            "summary": record_obj.process_record_summary(),
                            "has_mc": has_mc_flag,
                            "file_name": file_name_str
                        }
                        st.session_state.attendance_db.append(record_data)
                        
                        st.success("Attendance submitted and recorded into the database successfully.")
                        
                    except ValueError as ve:
                        st.error(f"Validation Error: {ve}")
                    except Exception as e:
                        st.error(f"An unexpected error occurred during processing: {e}")
        else:
            st.warning("Attendance session is currently closed. Please wait until the lecturer triggers the attendance session reminder.")