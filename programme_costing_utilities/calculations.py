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
        SELECT Value
        FROM population
        WHERE Iso3 = ? 
        AND Time = ?
        AND Variant = ?
        """
    cursor = conn.cursor()
    cursor.execute(query, (country, year, "Median"))

    result = cursor.fetchone()[0]
    if result is None:
        return 0

    return result


def serve_number_of_divisions(country, division, conn):
    """
    Return the number of divisions in a country.
    The divisions = National, Provincial, District

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    division : str
        The statistical division of interest.
        National | Provincial | District

    Returns
    -------
    int
        The number of divisions.
    """
    if division.lower() == "national":
        return 1

    query = f"""
    SELECT *
    FROM administrative_divisions
    WHERE ISO3 = ?
    """
    cursor = conn.cursor()
    cursor.execute(query, (country, ))
    result = cursor.fetchone()

    if division.lower() == "provincial":
        return result[1]
    elif division.lower() == "district":
        return result[2]

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
    population = serve_population(country, year, conn)
    if division.lower() == "national":
        return FTE * population / 50_000_000

    n_divisions = serve_number_of_divisions(country, division, conn)
    average_pop_per_division = population / n_divisions

    if division.lower() == "provincial":
        return FTE * average_pop_per_division / 5_000_000
    elif division.lower() == "district":
        return FTE * average_pop_per_division / 500_000
    
    else:
        return 0


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


def serve_consumable_cost(consumable, conn):
    """
    Calculate the cost of purchasing consumables.

    Parameters
    ----------
    consumable : str
        The type of consumable.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    float
        The cost of purchasing consumables.
    """
    query = f"""
        SELECT price, currency, year
        FROM office_supplies_and_furniture
        WHERE item = ?
        """
    cursor = conn.cursor()
    cursor.execute(query, (consumable, ))

    result = cursor.fetchone()
    consumable_price, currency, year = result

    return consumable_price, (currency, year)


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


def serve_meeting_records(
    country,
    year,
    days,
    attendees,
    room_size,
    conn
    ):
    """
    Calculate the cost of a meeting.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    days : int
        The number of days of the meeting.
    attendees : list
        A list of attendees with the following form:
        (label, number, travel)
        label : str
            The label of the attendee.
        number : int
            The number of attendees of this cadre.
        travel : bool
            Whether the attendee needs to travel.
    room_size : int
        The size of the room in metres squared.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    list
        each entry is a tuple of the form:
        item, cost, (currency, currency_year)
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

def serve_per_diem(country, division, conn, local=False, accommodation=False):
    """
    Retrieve the per diem rates for a country

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    division : str
        The division of the personnel.
    conn : sqlite3.Connection
        The connection to the database.
    local : bool
        Whether to retrieve the local per diem rate.
    """
    if division.lower() == "national":
        dsa = "dsa_national"
    elif division.lower() == "provincial":
        dsa = "dsa_upper"
    elif division.lower() == "district":
        dsa = "dsa_lower"

    query = f"""
        SELECT {dsa}, currency, year, local_proportion
        FROM costs_per_diems
        WHERE ISO3 = ?
        """

    cursor = conn.cursor()
    cursor.execute(query, (country, ))

    result = cursor.fetchone()
    per_diem, currency, year, local_proportion = result

    if local:
        per_diem *= local_proportion

    return per_diem, (currency, year)