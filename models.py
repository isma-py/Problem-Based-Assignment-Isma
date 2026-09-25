# models.py

# ==========================================
# FUNCTIONS (Requirement A)
# ==========================================
def calculate_attendance_percentage(attended: int, total: int) -> float:
    """Performs data processing: Calculates attendance percentage."""
    if total == 0:
        return 0.0
    return (attended / total) * 100.0

def evaluate_attendance_status(percentage: float) -> str:
    """Performs decision-making/result-generation based on attendance percentage."""
    if percentage >= 80.0:
        return "Eligible for Final Exam (Good Standing)."
    elif percentage >= 60.0:
        return "Conditional Eligibility (Warning: Below 80%)."
    else:
        return "Barred from Final Exam (Critical Attendance Deficit)."

# ==========================================
# CLASS & OBJECT IMPLEMENTATION (Requirement B)
# ==========================================
class AttendanceTracker:
    """Base class representing a student attendance record with 4 attributes and 2 methods."""
    
    def __init__(self, student_name: str, student_id: str, attended_classes: int, total_classes: int):
        # Minimum FOUR (4) attributes
        self.student_name = student_name
        self.student_id = student_id
        self.attended_classes = attended_classes
        self.total_classes = total_classes

    def calculate_percentage(self) -> float:
        """Method 1: Performs calculation and data processing."""
        if self.total_classes == 0:
            return 0.0
        return (self.attended_classes / self.total_classes) * 100.0

    def get_student_info(self) -> str:
        """Method 2: Returns a summary string of the student details."""
        return f"Student Name: {self.student_name} | ID: {self.student_id}"

# ==========================================
# INHERITANCE IMPLEMENTATION (Requirement D)
# ==========================================
class ParticipatingStudent(AttendanceTracker):
    """Subclass inheriting from AttendanceTracker with extra participation features."""
    
    def __init__(self, student_name: str, student_id: str, attended_classes: int, total_classes: int, extra_bonus_classes: int):
        # Inherit parent attributes using super()
        super().__init__(student_name, student_id, attended_classes, total_classes)
        # Additional/modified feature in the subclass
        self.extra_bonus_classes = extra_bonus_classes

    def calculate_percentage(self) -> float:
        """Overridden method: Includes bonus classes credited for active club/extracurricular participation."""
        effective_attended = self.attended_classes + self.extra_bonus_classes
        if effective_attended > self.total_classes:
            effective_attended = self.total_classes
        if self.total_classes == 0:
            return 0.0
        return (effective_attended / self.total_classes) * 100.0