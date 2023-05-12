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


def calculate_daily_salary(country, cadre, conn):
    """
    Calculate the daily salary of a personnel.

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
        The daily salary.
        A tuple of the currency and currency_year
    """
    annual_salary, currency_information = calculate_personnel_annual_salary(country, cadre, conn)
    DAYS_WORKED_PER_YEAR = 230  # FIXME #1 - Should interrogate this assumption
    daily_salary = annual_salary / DAYS_WORKED_PER_YEAR
    return daily_salary, currency_information


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


def serve_meeting_costs(
    country,
    year,
    division,
    days,
    attendees,
    room_size,
    conn,
    preferred_vehicle="Corolla sedan 2014 model",
    frequency=1,
    annual_meetings=1
    ):
    """
    Return a list of who attended a meeting, and the cost of attending.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    division : str
        The statistical division of the meeting.
    days : int
        The number of days of the meeting.
    attendees : list
        The attendees of the meeting.
        List of tuples, with each tuple of the form:
        (label, local/visiting, number, travel)
            label : str
                The label of the attendee.
            local/visiting : str
                Whether the attendee is local or visiting.
            number : int
                The number of attendees.
            travel : bool
                Whether the attendee requires funding for travel
    room_size : int
        The size of the room in square meters.
    conn : sqlite3.Connection
        The connection to the database.
    preferred_vehicle : str, default "Corolla sedan 2014 model"
        The preferred vehicle for travel.
    frequency : int, default 1
        The frequency of the meeting.
    annual_meetings : int, default 1
        The number of annual meetings.

    Returns
    -------
    list
        each entry is a tuple of the form:
        item, cost, (currency, currency_year)
    """
    records = []
    number_of_annual_meetings = frequency * annual_meetings

    for meeting in range(number_of_annual_meetings):

        # room hire
        room_hire_cost_per_day, currency_information = calculate_room_hire(country, division, year, room_size, conn)
        room_hire_cost_total = room_hire_cost_per_day * days
        label = "Meeting {}: Room hire for {} Room, {}m2 for {} days".format(meeting, division, room_size, days)
        record = (label, room_hire_cost_total, currency_information)
        records.append(record)

        # per diems for visiting attendees
        # days * attendees * per_diems
        visiting_attendees = [a for a in attendees if a[1] == "visiting"]
        per_diems, currency_information = serve_per_diem(country, division, conn, True)
        for visiting_attendee in visiting_attendees:
            attendee_label, _, quantity, _ = visiting_attendee
            record_label = "Meeting {}: {}: Per diems for {} visiting attendees for {} days".format(meeting, attendee_label, quantity, days)
            cost = days * quantity * per_diems
            record = (record_label, cost, currency_information)
            records.append(record)

        # opportunity cost (days of salary) for local attendees
        local_attendees = [a for a in attendees if a[1] == "local"]
        cadre = 2  # FIXME #2 - Assuming cadre of support staff is 2
        daily_salary, currency_information = calculate_daily_salary(country, cadre, conn)
        for local_attendee in local_attendees:
            attendee_label, _, quantity, _ = local_attendee
            record_label = "Meeting {}: {}: Opportunity cost for {} local attendees for {} days".format(meeting, attendee_label, quantity, days)
            cost = days * quantity * daily_salary
            record = (record_label, cost, currency_information)
            records.append(record)

        # travel = attendees * ddist * operational cost of car
        travelling_attendees = [a for a in attendees if a[3]]
        vehicle_operating_cost_per_km, currency_information = serve_vehicle_operating_cost(preferred_vehicle, conn)
        distance_travelled_in_km = serve_distance_between_regions(country, "DDist95", conn)  # FIXME #3 - Interrogate this assumption
        cost_of_travel_per_attendee = distance_travelled_in_km * vehicle_operating_cost_per_km
        for travelling_attendee in travelling_attendees:
            attendee_label, _, quantity, _ = travelling_attendee
            record_label = "Meeting {}: {}: Travel for {} attendees".format(meeting, attendee_label, quantity)
            cost = quantity * cost_of_travel_per_attendee
            record = (record_label, cost, currency_information)
            records.append(record)

    return records


def serve_vehicle_operating_cost(vehicle, conn):
    """
    Return the operating cost of a vehicle per km.

    Parameters
    ----------
    vehicle : str
        The type of vehicle.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    float, tuple
        The operating cost of the vehicle.
        The current information of the cost
    """
    query = f"""
        SELECT operating_cost_per_km, currency, year
        FROM costs_transport
        WHERE vehicle_model = ?
        """
    cursor = conn.cursor()
    cursor.execute(query, (vehicle, ))

    result = cursor.fetchone()
    vehicle_operating_cost, currency, year = result

    return vehicle_operating_cost, (currency, year)


def serve_vehicle_fuel_consumption(vehicle, conn):
    """
    Return the fuel consumption of a vehicle per km.

    Parameters
    ----------
    vehicle : str
        The type of vehicle.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    float, tuple
        The operating cost of the vehicle.
        The current information of the cost
    """
    query = f"""
        SELECT consumption_litres_per_km, currency, year
        FROM costs_transport
        WHERE vehicle_model = ?
        """
    cursor = conn.cursor()
    cursor.execute(query, (vehicle, ))

    result = cursor.fetchone()
    vehicle_operating_cost, currency, year = result

    return vehicle_operating_cost, (currency, year)


def serve_distance_between_regions(country, ddist, conn):
    """
    Return the distance between areas in a country in km.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    ddist : str
        The distance between two areas
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    float
        The distance between the two areas in km.
    """
    query = f"""
        SELECT {ddist}
        FROM distance_between_regions
        WHERE ISO3 = ?
        """
    cursor = conn.cursor()
    cursor.execute(query, (country, ))

    result = cursor.fetchone()
    distance_km = result[0]

    return distance_km

def calculate_room_hire(country, division, year, room_size, conn):
    """
    Calculate the cost of hiring a room in a country at a given m2.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    division : str
        The statistical division of the room being hired.    
        Either: National OR Provincial OR District
    year : int
        The year of calculation.
    room_size : int
        The size of the room in square meters.
    conn : sqlite3.Connection
        The connection to the database.
    """
    per_diems, cost_information = serve_per_diem(country, division, conn, False)
    room_cost_per_m2 = per_diems / 35 * 0.6  # FIXME #4 - This is the odd bit
    room_cost = room_cost_per_m2 * room_size
    return room_cost, cost_information


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
    return 1 * 2000 * 12  # TODO #5 What is the rationale of this method?


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

def serve_per_diem(country, division, conn, local=False):
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


def rebase_currency(cursor,  **kwargs):
    """
    Rebase a currency to a different currency and year (potentially).

    Parameters
    ----------
    cursor : sqlite3.Connection.Cursor
    cost : float
        The original cost of the item
        NB - Currently assumes USD 2018
    presentation_currency : str
        The ISO-3 CODE for the country whose currency will be presented
    currency_year : int
        The desired year of the presented currency

    Returns
    -------
    float
        The rebased cost

    Notes
    -----
    Currently assumes the currency and year is USD 2018.
    Providing a different ISO-3 CODE will change via WB-PPP Rates.
    Providing a different year will chagne via WB GDP-deflators.
    Providing a different ISO-3 CODE and year will:
    - Change to different currency via WB-PPP rates
    - Rebase to desired year using WB-GDP deflators
    """
    cost = kwargs["cost"]
    presentation_currency = kwargs["presentation_currency"]
    presentation_year = kwargs["presentation_year"]

    if presentation_currency != "USA":
        cursor.execute(
            """
            SELECT "2018" FROM "PPP_Conversion_Factor"
            WHERE "Country Code" = ?
            """, (presentation_currency, )
            )
        PPP_conversion_factor = cursor.fetchall()[0][0]
        cost = cost * PPP_conversion_factor

    if presentation_year != 2018:
        cursor.execute(
            """
            SELECT * FROM "GDP_Deflator"
            WHERE "Country Code" = ?
            """, (presentation_currency,)
        )
        gdp_deflators = cursor.fetchall()[0]

        first_year = 1960
        requested_index = presentation_year - first_year + 1  # country column is index 0
        current_index = 2018 - first_year + 1
        gdp_deflator_current = gdp_deflators[current_index]
        gdp_deflator_requested = gdp_deflators[requested_index]

        deflation_rate = gdp_deflator_requested / gdp_deflator_current
        cost = cost * deflation_rate

    return cost