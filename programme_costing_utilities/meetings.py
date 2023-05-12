"""
Calculate the cost of components of meetings and workshops, 
put this information together coherently.
"""
def calculate_meeting(
    country,
    days,
    national_experts_in_attendance,
    travel_for_national_experts,
    local_staff_in_attendance,
    travel_for_local_staff,
    meeting_room_m2
    ):
    """
    Calculate the cost of a meeting.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    days : int
        The number of days of the meeting.
    national_experts_in_attendance : int
        The number of national experts in attendance.
    travel_for_national_experts : int
        The number of national experts who need travel.
    local_staff_in_attendance : int
        The number of local staff in attendance.
    travel_for_local_staff : int
        The number of local staff who need travel.
    meeting_room_m2 : int
        The size of the meeting room in square meters.

    Returns
    -------
    tuple
        The cost of the meeting in USD and the records of the meeting costs.
    """
    ...


def calculate_workshop(
    frequency,
    annual_number_of_meetings_needed,
    length_of_meeting
    ):
    """
    Calculate the cost of a workshop, an event which is a series of meetings.

    Parameters
    ----------
    frequency : float
        Some modifier of the workshop amount. It's unclear what this is needed for.
    annual_number_of_meetings_needed : int
        The number of meetings needed in a year.
    length_of_meeting : int
        The number of days of each meeting.
    """