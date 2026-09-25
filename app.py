# app.py
import streamlit as st
# Module implementation import (Requirement C)
import models

st.title("📋 Smart Class Attendance & Eligibility System")
st.write("Track attendance records, evaluate final exam eligibility, and process student participation data.")

# ==========================================
# GUI INPUTS & USER EVENTS (Requirement E)
# ==========================================
st.sidebar.header("Configuration Panel")
# Streamlit User Event 1: Selectbox
student_category = st.sidebar.selectbox("Select Student Profile Type", ["Standard Student", "Active Extracurricular Student"])

# At least THREE (3) different user inputs
name_input = st.text_input("Enter Student Full Name:")
id_input = st.text_input("Enter Student ID Number:")
attended_input = st.text_input("Enter Number of Classes Attended:")
total_input = st.text_input("Enter Total Classes Held:")

# Streamlit User Event 2: Slider for bonus activities
bonus_credits = st.slider("Select Extracurricular Bonus Credits", min_value=0, max_value=5, value=0)

# Streamlit User Event 3: Checkbox for medical/excusal adjustment
excuse_granted = st.checkbox("Include Approved Medical Leave / Excused Absence Adjustment (+2 Classes)")

# Button to trigger system processing
process_btn = st.button("Process Attendance Record")

# ==========================================
# EXCEPTION HANDLING & VALIDATION (Requirement F)
# ==========================================
if process_btn:
    try:
        # Detect empty required fields
        if not name_input.strip():
            raise ValueError("Student name field cannot be empty.")
        if not id_input.strip():
            raise ValueError("Student ID field cannot be empty.")
        if not attended_input.strip():
            raise ValueError("Classes attended field cannot be empty.")
        if not total_input.strip():
            raise ValueError("Total classes field cannot be empty.")

        # Validate numerical inputs (Error 1 & Error 2 handling)
        try:
            attended_val = int(attended_input)
        except ValueError:
            raise ValueError("Invalid format: Classes attended must be a valid whole number (integer).")

        try:
            total_val = int(total_input)
        except ValueError:
            raise ValueError("Invalid format: Total classes held must be a valid whole number (integer).")

        # Logical range validation
        if total_val <= 0:
            raise ValueError("Total classes must be greater than zero.")
        if attended_val < 0:
            raise ValueError("Classes attended cannot be a negative number.")
        if attended_val > total_val:
            raise ValueError("Logical Error: Classes attended cannot exceed total classes held.")

        # Adjust attendance if medical excuse is checked
        adjusted_attended = attended_val
        if excuse_granted:
            adjusted_attended += 2

        # ==========================================
        # OBJECT INSTANTIATION & EXECUTION
        # ==========================================
        if student_category == "Active Extracurricular Student":
            # Instantiate Subclass (Inheritance implementation)
            student_obj = models.ParticipatingStudent(
                student_name=name_input,
                student_id=id_input,
                attended_classes=adjusted_attended,
                total_classes=total_val,
                extra_bonus_classes=bonus_credits
            )
            profile_note = "Processed under Extracurricular Profile (Bonus points included)."
        else:
            # Instantiate Parent Class
            student_obj = models.AttendanceTracker(
                student_name=name_input,
                student_id=id_input,
                attended_classes=adjusted_attended,
                total_classes=total_val
            )
            profile_note = "Processed under Standard Student Profile."

        # Execute module functions and methods
        final_percentage = student_obj.calculate_percentage()
        status_result = models.evaluate_attendance_status(final_percentage)

        # ==========================================
        # PRESENTATION OF RESULTS (Requirement E & G)
        # ==========================================
        st.success("Attendance processed successfully!")
        
        st.subheader("📊 Attendance Summary Report")
        st.write(f"**{student_obj.get_student_info()}**")
        st.info(profile_note)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Total Classes Held", value=total_val)
        with col2:
            st.metric(label="Effective Attended", value=student_obj.attended_classes)
        with col3:
            st.metric(label="Attendance Rate", value=f"{final_percentage:.2f}%")

        st.markdown("---")
        st.subheader("🎓 Exam Eligibility Result")
        st.write(f"**Status Evaluation:** {status_result}")

    except ValueError as ve:
        # Display inputs/logical error using st.error()
        st.error(f"Input Validation Error: {ve}")
    
    except Exception as e:
        # Catch unexpected errors via try-except
        st.error(f"An unexpected system error occurred: {e}")