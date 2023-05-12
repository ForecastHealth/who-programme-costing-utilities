"""
Provides the methods to calculate the personnel quantity and cost.
"""
import numpy as np

def serve_population(country, year, conn) :
    """
    Return the total population in given year

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    np.ndarray
        2 x 101 ndarray of the population of a country in a specific year.
    """
    if year < 1950:
        year = 1950
    elif year > 2100:
        year = 2100

    query = f"""
        SELECT PopMale, PopFemale
        FROM population
        WHERE LocID = ? 
        AND Time = ?
        """
    cursor = conn.cursor()
    cursor.execute(query, (country, year))

    result = cursor.fetchall()
    if result is None:
        return 0
    result = np.array(result).T
    result *= 1000  # convert from thousands to individuals
    result = np.sum(result)

    return result

def fit_FTE(FTE, country, year, division, conn):
    """
    If the FTE given is set to a standardized population, fit the FTE to the
    actual population.

    Parameters
    ----------
    FTE : float
        The FTE to fit.
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    division : str
        The statistical division of interest.
        National | Provincial | District
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    float
        The fitted (actual, real) FTE.
    """
    population = get_population(country, conn)


def calculate_personnel_annual_salary(country, cadre, conn):
    """
    Calculate the annual salary of a personnel.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    cadre : int
        The cadre of the personnel.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    float, tuple
        The annual salary.
        A tuple of the currency and currency_year
    """
    ISO3 = country
    ISCO_08_level = cadre

    query = f"""
    SELECT annual_salary, currency, year
    FROM costs_salaries
    WHERE ISO3 = ?
    AND ISCO_08_level = ?
    """

    cursor = conn.cursor()
    cursor.execute(query, (ISO3, ISCO_08_level))

    result = cursor.fetchone()
    if result is None:
        return None, None

    annual_salary, currency, year = result
    cost_tuple = (currency, year)
    return annual_salary, cost_tuple


def calculate_consumable_cost(consumable, unit_cost, quantity):
    """
    Calculate the cost of purchasing consumables.

    Parameters
    ----------
    consumable : str
        The type of consumable.
    unit_cost : float
        The unit cost of the consumable.
    quantity : float
        The quantity of the consumable.

    Returns
    -------
    float
        The cost of purchasing consumables.
    """
    return unit_cost * quantity


def calculate_annualised_cost(unit_cost, useful_life_years):
    """
    Calculate the annualised cost of a piece of equipment.

    Parameters
    ----------
    unit_cost : float
        The unit cost of the equipment.
    useful_life_years : float
        The useful life of the equipment in years.

    Returns
    -------
    float
        The annualised cost of the equipment.
    """
    return unit_cost / useful_life_years


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
    ...

def calculate_km_travelled_per_year(
    statistical_division,
    vehicle
    ):
    """
    Calculate the number of kilometers travelled per year by a vehicle.

    NOTE: 2023-05-12: It is unclear how this function works at the moment.

    Parameters
    ----------
    statistical_division : str
        The division of the personnel.
        National | Provincial | District
    vehicle : str
        The type of vehicle.

    Returns
    -------
    float
        The number of kilometers travelled per year.
    """
    return 1 * 2000 * 12


def calculate_fuel_price(country, vehicle, price_db):
    """
    Calculate the price of fuel per liter.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    vehicle : str
        The type of vehicle.
    price_db : sqlite3.Connection
        The connection to the price database.
    """
    ...