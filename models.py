# models.py

def calculate_attendance_rate(total_present: int, total_classes: int) -> float:
    """Performs data processing: Calculates attendance percentage."""
    if total_classes == 0:
        return 0.0
    return (total_present / total_classes) * 100.0

def evaluate_standing(rate: float) -> str:
    """Performs decision-making: Evaluates attendance compliance status."""
    if rate >= 80.0:
        return "Compliant - Full Attendance Standing"
    elif rate >= 60.0:
        return "Warning - Attendance Below Optimal Threshold"
    else:
        return "Non-Compliant - Action Required"

class BaseAttendanceRecord:
    """Base class containing four attributes and two processing methods."""
    def __init__(self, student_name: str, matrix_no: str, lab_name: str, subject_name: str):
        # Minimum four attributes
        self.student_name = student_name
        self.matrix_no = matrix_no
        self.lab_name = lab_name
        self.subject_name = subject_name

    def process_record_summary(self) -> str:
        """Method 1: Processes and formats basic record information."""
        return f"Student: {self.student_name} | Matrix: {self.matrix_no} | Subject: {self.subject_name} ({self.lab_name})"

    def calculate_metrics(self) -> int:
        """Method 2: Performs a data processing calculation on attributes."""
        return len(self.matrix_no) * 10

class VerifiedAttendanceRecord(BaseAttendanceRecord):
    """Subclass demonstrating inheritance with a modified feature (MC tracking)."""
    def __init__(self, student_name: str, matrix_no: str, lab_name: str, subject_name: str, has_mc: bool, mc_reason: str):
        super().__init__(student_name, matrix_no, lab_name, subject_name)
        self.has_mc = has_mc
        self.mc_reason = mc_reason

    def process_record_summary(self) -> str:
        """Overridden method incorporating subclass attributes."""
        base_summary = super().process_record_summary()
        mc_status = f"Verified MC/Memo Attached: {self.mc_reason}" if self.has_mc else "Absent with No Evidence"
        return f"{base_summary} - Status: {mc_status}"