from enum import Enum

from handlers.handle_academic_calendar import handle_academic_calendar
from handlers.handle_daily_schedule import handle_daily_schedule
from handlers.handle_exams_program import handle_exams_program
from handlers.handle_office_hours import handle_office_hours
from handlers.handle_regulations import handle_regulations


class Sector(Enum):
    EXAMS_PROGRAM = "1"
    OFFICE_HOURS = "2"
    DAILY_CLASS_SCHEDULE = "3"
    ACADEMIC_CALENDAR = "4"
    DEPARTMENT_REGULATIONS = "5"

DIGIT_TO_SECTOR = {
    "1": Sector.EXAMS_PROGRAM,
    "2": Sector.OFFICE_HOURS,
    "3": Sector.DAILY_CLASS_SCHEDULE,
    "4": Sector.ACADEMIC_CALENDAR,
    "5": Sector.DEPARTMENT_REGULATIONS,
}

SECTOR_PROMPTS = {
    Sector.EXAMS_PROGRAM: "You selected Exams Schedule. What course are you interested in?",
    Sector.OFFICE_HOURS: "You selected Office Hours. Which professor would you like to meet?",
    Sector.DAILY_CLASS_SCHEDULE: "You selected Daily Schedule. What course or day are you interested in?",
    Sector.ACADEMIC_CALENDAR: "You selected Academic Calendar. Please describe your request.",
    Sector.DEPARTMENT_REGULATIONS: "You selected Study Guide. Please describe your request.",
}

HANDLERS = {
    Sector.EXAMS_PROGRAM: handle_exams_program,
    Sector.OFFICE_HOURS: handle_office_hours,
    Sector.DAILY_CLASS_SCHEDULE: handle_daily_schedule,
    Sector.ACADEMIC_CALENDAR: handle_academic_calendar,
    Sector.DEPARTMENT_REGULATIONS: handle_regulations,
}