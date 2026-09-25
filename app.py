# app.py
import streamlit as st
import datetime
import pandas as pd
import models

# Initialize session state variables
if "attendance_db" not in st.session_state:
    st.session_state.attendance_db = []

if "session_active" not in st.session_state:
    st.session_state.session_active = False

if "active_subject" not in st.session_state:
    st.session_state.active_subject = ""

if "active_lab" not in st.session_state:
    st.session_state.active_lab = ""

if "lecturer_ip" not in st.session_state:
    st.session_state.lecturer_ip = ""

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

# Helper function to get real client IP from headers
def get_client_ip():
    headers = st.context.headers
    ip = headers.get("X-Forwarded-For", headers.get("Remote-Addr", "127.0.0.1"))
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
    return ip

# Helper function to extract network subnet prefix (e.g., first 3 octets for local net matching)
def get_subnet(ip_address):
    parts = ip_address.split(".")
    if len(parts) >= 3:
        return ".".join(parts[:3])
    return ip_address

# Styling helper function for soft-color row highlights
def colorize_attendance_row(row):
    """Applies soft green for Present and soft red for Absent rows."""
    if "Present" in str(row["Status"]):
        return ['background-color: #d4edda; color: #155724'] * len(row)
    else:
        return ['background-color: #f8d7da; color: #721c24'] * len(row)

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
        
    with st.form("lecturer_session_form"):
        st.subheader("Configure Class Session Parameters")
        lecturer_subject = st.selectbox("Select Lecture Subject", ["DFK50083 Python Programming", "DBF50123 Database Systems", "DTN50233 Network Security"])
        lecturer_lab = st.selectbox("Select Laboratory Location", ["Lab Alpha", "Lab Beta", "Lab Gamma", "Networking Lab 1"])
        
        activate_btn = st.form_submit_button("Get Attendance (Activate Session)")
        
        if activate_btn:
            # Capture the lecturer's current network IP address upon session activation
            st.session_state.lecturer_ip = get_client_ip()
            st.session_state.session_active = True
            st.session_state.active_subject = lecturer_subject
            st.session_state.active_lab = lecturer_lab
            st.success(f"Session activated for {lecturer_subject} at {lecturer_lab} (Host Network IP Recorded: {st.session_state.lecturer_ip}).")

    st.markdown("---")
    st.subheader("Attendance")
    
    if st.session_state.attendance_db:
        st.write(f"Total Subscriptions Logged: {len(st.session_state.attendance_db)}")
        mc_count = sum(1 for item in st.session_state.attendance_db if item.get("has_mc"))
        st.metric(label="Total Records with Medical Certificates / Memos", value=mc_count)
        
        # Fixed size, scrollable table with an increased height (450px)
        df_records = pd.DataFrame(st.session_state.attendance_db)
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
    
    if st.button("Log Out"):
        st.session_state.current_page = "Landing"
        st.rerun()
        
    # Real Network Subnet Verification Check
    student_ip = get_client_ip()
    
    if st.session_state.session_active:
        # Verify if student is on the exact same network subnet as the lecturer
        lecturer_subnet = get_subnet(st.session_state.lecturer_ip)
        student_subnet = get_subnet(student_ip)
        
        is_same_network = (lecturer_subnet == student_subnet) or (st.session_state.lecturer_ip in ["127.0.0.1", "localhost", student_ip])
        
        if not is_same_network:
            st.error("Network Verification Failed: You are not connected to the same local network as the lecturer. Attendance notification and submission are locked.")
        else:
            st.info(f"Network Verified: Connected to lecturer network segment. Active session for {st.session_state.active_subject} in {st.session_state.active_lab}.")
            
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
                        
                        # Modal trigger condition: student submitting absence with no uploaded file evidence
                        if attendance_status_type == "Absent with Medical Certificate / Memo" and file_name_str == "No File Attached":
                            st.session_state.show_absence_modal = True
                            st.session_state.pending_attendance_data = {
                                "Timestamp": str(f"{attendance_date} {attendance_time}"),
                                "Name": st.session_state.student_name,
                                "Matrix": st.session_state.student_matrix,
                                "Subject": st.session_state.active_subject,
                                "Lab": st.session_state.active_lab,
                                "Status": attendance_status_type,
                                "summary": f"Student: {st.session_state.student_name} | Matrix: {st.session_state.student_matrix} - Absent with No Evidence",
                                "has_mc": False,
                                "File Name": "No File Attached"
                            }
                        else:
                            record_obj = models.VerifiedAttendanceRecord(
                                student_name=st.session_state.student_name,
                                matrix_no=st.session_state.student_matrix,
                                lab_name=st.session_state.active_lab,
                                subject_name=st.session_state.active_subject,
                                has_mc=has_mc_flag,
                                mc_reason=mc_reason_input if has_mc_flag else "None"
                            )
                            
                            record_data = {
                                "Timestamp": str(f"{attendance_date} {attendance_time}"),
                                "Name": st.session_state.student_name,
                                "Matrix": st.session_state.student_matrix,
                                "Subject": st.session_state.active_subject,
                                "Lab": st.session_state.active_lab,
                                "Status": attendance_status_type,
                                "summary": record_obj.process_record_summary(),
                                "has_mc": has_mc_flag,
                                "File Name": file_name_str
                            }
                            st.session_state.attendance_db.append(record_data)
                            st.success("Attendance submitted and recorded into the database successfully.")
                            
                    except ValueError as ve:
                        st.error(f"Validation Error: {ve}")
                    except Exception as e:
                        st.error(f"An unexpected error occurred during processing: {e}")
            
            # Modal Warning implementation using Streamlit containers/warnings
            if st.session_state.show_absence_modal:
                st.warning("Warning Modal Reminder: You did not upload a medical certificate or memo. If you proceed, this will be counted as absence with no evidence. You can still confirm submission below.")
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    if st.button("Confirm Submit Without Evidence"):
                        st.session_state.attendance_db.append(st.session_state.pending_attendance_data)
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
        st.warning("Attendance session is currently closed. Please wait until the lecturer triggers the attendance session reminder.")