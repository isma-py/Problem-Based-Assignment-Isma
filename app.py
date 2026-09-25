# app.py
import streamlit as st
import datetime
import models

# Initialize session state storage for database simulation
if "attendance_db" not in st.session_state:
    st.session_state.attendance_db = []

if "session_active" not in st.session_state:
    st.session_state.session_active = False

if "active_subject" not in st.session_state:
    st.session_state.active_subject = ""

if "active_lab" not in st.session_state:
    st.session_state.active_lab = ""

st.title("Campus Attendance Management System")
st.write("Secure portal for academic session tracking, attendance verification, and medical exemption logging.")

# ==========================================
# NETWORK ACCESS VALIDATION (Requirement 4)
# ==========================================
# Simulating institutional network restriction check
st.sidebar.header("Network Security Gateway")
network_status = st.sidebar.selectbox("Select Network Connection", ["Campus Secure Wi-Fi (Authorized)", "External Public Network (Unauthorized)"])

is_authorized_network = (network_status == "Campus Secure Wi-Fi (Authorized)")

if not is_authorized_network:
    st.error("Network Access Restricted: You must be connected to the authorized campus network to access active session features.")
    st.stop()

# ==========================================
# ROLE SELECTION LOGIN PORTAL (Requirement 0)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.header("System Login Portal")
user_role = st.sidebar.radio("Select User Role", ["Student Portal", "Lecturer Portal"])

# ==========================================
# LECTURER PORTAL IMPLEMENTATION (Requirement 1)
# ==========================================
if user_role == "Lecturer Portal":
    st.header("Lecturer Control Dashboard")
    
    with st.form("lecturer_session_form"):
        st.subheader("Configure Class Session Parameters")
        # Requirement 1d: Select subject and lab before activating
        lecturer_subject = st.selectbox("Select Lecture Subject", ["DFK50083 Python Programming", "DBF50123 Database Systems", "DTN50233 Network Security"])
        lecturer_lab = st.selectbox("Select Laboratory Location", ["Lab Alpha", "Lab Beta", "Lab Gamma", "Networking Lab 1"])
        
        # Streamlit User Event: Activation Button
        activate_btn = st.form_submit_button("Activate Attendance Session")
        
        if activate_btn:
            st.session_state.session_active = True
            st.session_state.active_subject = lecturer_subject
            st.session_state.active_lab = lecturer_lab
            st.success(f"Session activated successfully for {lecturer_subject} at {lecturer_lab}. Students can now submit attendance.")

    st.markdown("---")
    st.subheader("Live Attendance Records & Absence Auditing")
    
    # Requirement 1a & 1b: Display day-to-day attendance details and absence/MC counts
    if st.session_state.attendance_db:
        st.write(f"Total Subscriptions Logged: {len(st.session_state.attendance_db)}")
        
        # Count absences/MCs logged
        mc_count = sum(1 for item in st.session_state.attendance_db if item.get("has_mc"))
        st.metric(label="Total Records with Medical Certificates / Memos", value=mc_count)
        
        for idx, record in enumerate(st.session_state.attendance_db, 1):
            st.markdown(f"**Record {idx}:** {record['summary']}")
            st.write(f"Date & Time: {record['timestamp']} | Matrix: {record['matrix']} | Name: {record['name']}")
            if record.get("file_name"):
                st.write(f"Uploaded Evidence File: {record['file_name']}")
            st.markdown("---")
    else:
        st.info("No attendance records found in the database for the current session.")

# ==========================================
# STUDENT PORTAL IMPLEMENTATION (Requirement 2)
# ==========================================
elif user_role == "Student Portal":
    st.header("Student Attendance Submission Portal")
    
    # Requirement 2: Enter matrix number and name for login display
    student_name_input = st.text_input("Enter Full Name:")
    student_matrix_input = st.text_input("Enter Matrix Number:")
    
    if student_name_input and student_matrix_input:
        st.success(f"Logged in as: {student_name_input} ({student_matrix_input})")
        
        # Check if lecturer has triggered the attendance session
        if st.session_state.session_active:
            st.info(f"Active Session Reminder: Lecturer has initiated attendance for {st.session_state.active_subject} in {st.session_state.active_lab}.")
            
            # Requirement 2a: Fields displayed ONLY if lecturer clicked the button
            with st.form("student_attendance_form"):
                st.subheader("Submit Attendance Details")
                
                # Streamlit User Inputs (Requirement E)
                attendance_date = st.date_input("Select Date", value=datetime.date.today())
                attendance_time = st.time_input("Select Time", value=datetime.datetime.now().time())
                
                attendance_status_type = st.selectbox("Attendance Status", ["Present", "Absent with Medical Certificate / Memo"])
                mc_reason_input = st.text_input("Reason for Absence / Medical Condition (if applicable):")
                
                # File upload component for memo/MC
                uploaded_file = st.file_uploader("Upload Medical Certificate or Absence Memo (PDF/Image)", type=["pdf", "png", "jpg"])
                
                submit_attendance_btn = st.form_submit_button("Submit Attendance Record")
                
                if submit_attendance_btn:
                    try:
                        # Exception Handling (Requirement F): Detect empty fields
                        if not student_name_input.strip() or not student_matrix_input.strip():
                            raise ValueError("Student name and matrix number cannot be empty.")
                        
                        if attendance_status_type == "Absent with Medical Certificate / Memo" and not mc_reason_input.strip():
                            raise ValueError("Please provide a reason or details for your medical certificate/memo.")
                        
                        has_mc_flag = (attendance_status_type == "Absent with Medical Certificate / Memo")
                        file_name_str = uploaded_file.name if uploaded_file else "No File Attached"
                        
                        # Instantiate subclass object implementing inheritance
                        record_obj = models.VerifiedAttendanceRecord(
                            student_name=student_name_input,
                            matrix_no=student_matrix_input,
                            lab_name=st.session_state.active_lab,
                            subject_name=st.session_state.active_subject,
                            has_mc=has_mc_flag,
                            mc_reason=mc_reason_input if has_mc_flag else "None"
                        )
                        
                        # Store in session state (local database simulation)
                        timestamp_str = f"{attendance_date} {attendance_time}"
                        record_data = {
                            "name": student_name_input,
                            "matrix": student_matrix_input,
                            "timestamp": timestamp_str,
                            "summary": record_obj.process_record_summary(),
                            "has_mc": has_mc_flag,
                            "file_name": file_name_str
                        }
                        st.session_state.attendance_db.append(record_data)
                        
                        st.success("Attendance submitted and recorded into the database successfully.")
                        
                    except ValueError as ve:
                        # Handle input errors using st.error()
                        st.error(f"Validation Error: {ve}")
                    except Exception as e:
                        # Catch unexpected errors via try-except
                        st.error(f"An unexpected error occurred during processing: {e}")
        else:
            st.warning("Attendance session is currently closed. Please wait until the lecturer triggers the attendance session reminder.")
    else:
                st.info("Please enter your name and matrix number above to access the portal dashboard.")