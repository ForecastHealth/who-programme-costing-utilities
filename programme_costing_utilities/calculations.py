"""
Provides the methods to calculate the personnel quantity and cost.
"""
import numpy as np
import json

def calculate_discount(discount_rate, year, start):
    """
    Calculate the discount for the given year

    Assumes the discount rate is 1 + r e.g. 1.03
    First year = year - year = 0 so discount is 1

    Parameters
    ----------
    discount_rate : float
        The discount rate.
    year : int
        The year.
    start : int
        The start year.

    Returns
    -------
    float
        The current discount to be applied this year
    """
    return discount_rate ** (year - start)


def get_personnel_records(component, conn, country, year, start_year):
    """
    Return the personnel records for a given component in a given year.
    Here, personnel records refer to lists of annual salaries for persons involved in the project.
    However, it also considers things like: 
    - office supplies for the programme
    - transport for the personnel in the programme

    Parameters
    ----------
    component : dict
        The component.
    conn : sqlite3.Connection
        The connection to the database.
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    _ : int
        The start year of the programme. (NOT USED)

    Component kwargs
    ----------------
    Programme Area : str
        arbitrary label, can be empty
        e.g. "Programme management (incl. M&E)",
    Role : str
        label of the personnel
        must correspond to a label in the personnel database
        e.g. "Programme Director",
    Division : str
        statistical division of the personnel
        national OR provincial OR district
    FTE : float 
        Full-time equivalent for the programme
        e.g. 0.250 for quart-time
    Activities : str
        arbitrary label, can be empty
        "Oversight; Monitoring; Reporting"
    """
    # iterate through personnel list, calculate annual salary
    records = []

    NEED_CARS_AND_TRAVEL = ["Transport Driver"]
    CAR_PREFERENCE = "Toyota Hiace passenger van"
    DONT_NEED_OFFICE_SUPPLIES = ["Cleaner", "Transport Driver"]
    OFFICE_SUPPLIES = [
        {
            "item": "Computer   ",
            "per person": 0.5,
            "useful life years": 5
        },
        {
            "item": "Multifunciton Photocopier, Fax, Printer and Scanner ",
            "per person": 0.125,
            "useful life years": 5
        }
        ]


    # add unit costs to OFFICE_SUPPLIES
    for item in OFFICE_SUPPLIES:
        unit_cost, currency_information = serve_supply_costs(item["item"], conn)
        item["unit cost"] = unit_cost
        item["currency"] = currency_information[0]
        item["currency year"] = currency_information[1]
        item["annualised cost"] = calculate_annualised_cost(unit_cost, item["useful life years"])


    # unpack kwargs
    programme_area = component["Programme Area"]
    role = component["Role"]
    division = component["Division"]
    fte = fit_FTE(component["FTE"], country, year, division, conn)
    activities = component["Activities"]

    # get annual salary
    cadre = serve_cadre_from_role(role)
    annual_salary, currency_information = serve_personnel_annual_salary(country, cadre, conn)

    # calculate salary for this year
    salary = annual_salary * fte

    # Write a log for this record
    log = f"Personnel: {role} ({cadre}) in {division} division, {fte} FTE, {activities} activities"
    resource_information = (role, division, fte)
    cost_information = (salary, currency_information[0], currency_information[1])

    # add to records
    record = (log, resource_information, cost_information)
    records.append(record)

    # determine their need for office supplies
    if role not in DONT_NEED_OFFICE_SUPPLIES:
        for item in OFFICE_SUPPLIES:
            cost = fte * item["per person"] * item["annualised cost"]

            cost_information = (cost, item["currency"], item["currency year"])
            log = f"Office supplies: {item['item']} for {role} ({cadre}) in {division} division, {fte} FTE, {activities} activities"
            resource_information = (role, division, fte * item["per person"])

            record = (log, resource_information, cost_information)
            records.append(record)

    if role in NEED_CARS_AND_TRAVEL:
        # Each FTE needs half a car  TODO #6 - Interrogate this rule
        cars_needed = fte * 0.5
        km_per_car = calculate_km_travelled_per_year(division, CAR_PREFERENCE)
        kms_driven = cars_needed * km_per_car
        operational_cost, currency_information = serve_vehicle_operating_cost(CAR_PREFERENCE, conn)
        fuel_cost, currency_information = serve_vehicle_fuel_consumption(CAR_PREFERENCE, conn)

        log = f"Transport: {role} ({cadre}) in {division} division, {fte} FTE, {activities} activities"
        resource_information = (role, division, fte)
        cost_information = (operational_cost, currency_information[0], currency_information[1])
        record = (log, resource_information, cost_information)
        records.append(record)

        log = f"Fuel: {role} ({cadre}) in {division} division, {fte} FTE, {activities} activities"
        resource_information = (role, division, kms_driven)
        cost_information = (fuel_cost, currency_information[0], currency_information[1])
        record = (log, resource_information, cost_information)
        records.append(record)

    return records


def get_meeting_records(component, conn, country, year, start_year):
    """
    Return a list of who attended a meeting, and the cost of attending.

    Parameters
    ----------
    component : dict
        The component kwargs
    conn : sqlite3.Connection
        The connection to the database.
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    start_year : int
        The start year of the programme.

    Component kwargs
    ----------------
    frequency : int, default 1
        The frequency of the meeting.
        if 0, hold meetings in the first year only
        if 1, hold meetings every year
        if 2, hold meetings every two years etc.
    scale: float, default 1
        The scale of the meeting.
        This multiplies against the # of statistical divisions.
        E.g. if there are 6 provinces, and the scale is 0.5
        then it is assumed that there are 3 meetings a year, 
        one in every second province.
        E.g. if there is 1 national centre, and the scale is 2,
        it is assumed there are 2 annual meetings.
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
            travel : int
                The number of attendees that need travel
    room_size : int
        The size of the room in square meters.
        If not present, will attempt to estimate the room size needed.
    preferred_vehicle : str, default "Corolla sedan 2014 model"
        The preferred vehicle for travel.

    Returns
    -------
    list
        each entry is a tuple of the form:
        item, cost, (currency, currency_year)
    """
    # unpack kwargs, or defaults
    frequency = component.get("frequency", 1)
    scale = component.get("scale", 1)
    division = component["division"]
    days = component["days"]
    attendees = component["attendees"]
    room_size = component["room_size"]
    preferred_vehicle = component.get("preferred_vehicle", "Corolla sedan 2014 model")

    # determine if function needs to run this year
    records = []
    idx = year - start_year

    if frequency == 0 and idx != 0:  # only run in first year if scale is 0
        return records
    elif frequency != 0 and idx % frequency != 0:  # only run if scale is not 0 and idx is not a multiple of scale
        return records

    number_of_meetings = serve_number_of_divisions(country, division, conn) * scale

    # room hire
    room_hire_cost_per_day, currency_information = calculate_room_hire(country, division, year, room_size, conn)
    room_hire_cost_total = room_hire_cost_per_day * days * number_of_meetings

    log = "Room hire for {} Room, {}m2 for {} days for {} meetings".format(division, room_size, days, number_of_meetings)
    resource_information = ("Room Size", division, room_size)
    cost_information = (room_hire_cost_total, currency_information[0], currency_information[1])
    record = (log, resource_information, cost_information)
    records.append(record)

    # per diems for visiting attendees
    # days * attendees * per_diems
    visiting_attendees = [a for a in attendees if a[1] == "visiting"]
    per_diems, currency_information = serve_per_diem(country, division, conn, True)
    for visiting_attendee in visiting_attendees:
        attendee_label, _, quantity, _ = visiting_attendee
        cost = days * quantity * per_diems * number_of_meetings

        log = "{}: Per diems for {} visiting attendees for {} days for {} meetings".format(attendee_label, quantity, days, number_of_meetings)
        resource_information = (attendee_label, division, quantity)
        cost_information = (cost, currency_information[0], currency_information[1])
        record = (log, resource_information, cost_information)
        records.append(record)

    # opportunity cost (days of salary) for local attendees
    local_attendees = [a for a in attendees if a[1] == "local"]
    cadre = 2  # FIXME #2 - Assuming cadre of support staff is 2
    daily_salary, currency_information = calculate_daily_salary(country, cadre, conn)
    for local_attendee in local_attendees:
        attendee_label, _, quantity, _ = local_attendee
        cost = days * quantity * daily_salary * number_of_meetings

        log = "{}: Opportunity cost for {} local attendees for {} days for {} meetings".format(attendee_label, quantity, days, number_of_meetings)
        resource_information = (attendee_label, division, quantity)
        cost_information = (cost, currency_information[0], currency_information[1])
        record = (log, resource_information, cost_information)
        records.append(record)

    # travel = attendees * ddist * operational cost of car
    vehicle_operating_cost_per_km, currency_information = serve_vehicle_operating_cost(preferred_vehicle, conn)
    distance_travelled_in_km = serve_distance_between_regions(country, "DDist95", conn)  # FIXME #3 - Interrogate this assumption
    cost_of_travel_per_attendee = distance_travelled_in_km * vehicle_operating_cost_per_km
    for attendee in attendees:
        attendee_label, _, _, quantity = attendee
        cost = quantity * cost_of_travel_per_attendee * number_of_meetings

        log = "{}: Travel for {} attendees for {} meetings".format(attendee_label, quantity, number_of_meetings)
        resource_information = (attendee_label, division, quantity)
        cost_information = (cost, currency_information[0], currency_information[1])
        record = (log, resource_information, cost_information)
        records.append(record)

    return records


def get_media_records(component, conn, country, year, start_year):
    """
    Return the records for media campaigns.
    
    Parameters
    ----------
    component : dict
        The component of the intervention.
    conn : sqlite3.Connection
        The connection to the database.
    country : str
        The ISO3 code of the country.
    _ : int
        The year of interest NOT USED.
    _ : int
        The start year of the programme, NOT USED.

    Component Kwargs
    ----------------
    label : str
        The label of the component.
    division : str
        The statistical division of the media component.
        National OR Provincial OR District

    Returns
    -------
    list
        each entry is a tuple of the form:

    """
    records = []

    HEALTH_FACILITY_MAPPING = {
        "national": ["regional_hospitals"],
        "provincial": ["provincial_hospitals"],
        "district": ["district_hospitals", "health_centres", "health_posts"]
    }
    label = component["label"]
    division = component["division"]
    division_health_facilities = HEALTH_FACILITY_MAPPING[division]

    cost, currency_information = serve_supply_costs(label, conn)

    for health_facility_type in division_health_facilities:
        # get the number of health facilities
        number_of_health_facilities = serve_healthcare_facilities(country, health_facility_type, conn)
        # multiply by the cost
        cost_per_health_facility = number_of_health_facilities * cost
        # create the record
        log = "{}: {}".format(label, health_facility_type)
        resource_information = (label, health_facility_type, number_of_health_facilities)
        cost_information = (cost_per_health_facility, currency_information[0], currency_information[1])
        record = (log, resource_information, cost_information)
        records.append(record)
    return records


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


def serve_personnel_annual_salary(country, cadre, conn):
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
    annual_salary, currency_information = serve_personnel_annual_salary(country, cadre, conn)
    DAYS_WORKED_PER_YEAR = 230  # FIXME #1 - Should interrogate this assumption
    daily_salary = annual_salary / DAYS_WORKED_PER_YEAR
    return daily_salary, currency_information


def serve_supply_costs(consumable, conn):
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


def rebase_currency(
        cost,
        current_country,
        current_year,
        desired_country,
        desired_year,
        discount,
        conn
    ):
    """
    Rebase a currency to a different currency and year (potentially).
    FIXME #7 Haven't tested this thoroughly enough yet. Revisit.

    Parameters
    ----------
    cost : float
        The cost to rebase.
    current_country : str
        The ISO3 of the currency of the cost.
    current_year : int
        The year of the cost.
    desired_country : str
        The ISO3 of the currency to rebase to.
    desired_year : int
        The year to rebase to.
    discount : float
        The discount rate to apply.
        NOTE - Assumes the discount rate has already been calculated.
        e.g. a discount rate of 3% in year 2 is 1.03^2 = 1.0609

    Returns
    -------
    cost information
        The desired cost information in the form of a tuple.
        (cost, currency, year)

    Notes
    -----
    Providing a different ISO-3 CODE will change via WB-PPP Rates.
    Providing a different year will chagne via WB GDP-deflators.
    Providing a different ISO-3 CODE and year will:
    - Change to different currency via WB-PPP rates
    - Rebase to desired year using WB-GDP deflators
    """
    # if either currency is called USD, change this to USA
    if current_country == "USD":
        current_country = "USA"
    if desired_country == "USD":
        desired_country = "USA"

    cursor = conn.cursor()

    # convert to PPP, then convert from PPP to the desired country currency
    if desired_country != current_country:
        query = f"""
            SELECT "{current_year} [YR{current_year}]" FROM "economic_statistics"
            WHERE "Country Code" = ?
            AND "Series Name" = "PPP conversion factor, GDP (LCU per international $)"
            """
        cursor.execute(query, (current_country, ))
        to_PPP = float(cursor.fetchone()[0])
        ppp = cost / to_PPP

        query = f"""
            SELECT "{current_year} [YR{current_year}]" FROM "economic_statistics"
            WHERE "Country Code" = ?
            AND "Series Name" = "PPP conversion factor, GDP (LCU per international $)"
            """
        cursor.execute(query, (desired_country, ))
        to_PPP = float(cursor.fetchone()[0])
        cost = ppp * to_PPP

    # convert the current year to the desired year, using deflators
    if current_year != desired_year:
        query = """
            SELECT * FROM "economic_statistics"
            WHERE "Country Code" = ?
            AND "Series Name" = "GDP deflator (base year varies by country)"
            """
        cursor.execute(query, (current_country, ))
        gdp_deflators = cursor.fetchall()[0][4:]  # Before this is text

        first_year = 1960
        requested_index = desired_year - first_year + 1  # country column is index 0
        current_index = current_year - first_year + 1
        gdp_deflator_requested = float(gdp_deflators[requested_index])
        gdp_deflator_current = float(gdp_deflators[current_index])

        deflation_rate = gdp_deflator_requested / gdp_deflator_current
        cost = cost * deflation_rate

    # apply discount
    cost *= discount

    return cost, desired_country, desired_year


def serve_cadre_from_role(role):
    """
    Return the cadre of a role.
    Currently (2023-14-05T10:32:00) this is a simple lookup table.

    Parameters
    ----------
    role : str
        The role of the personnel.

    Returns
    -------
    int
        The cadre of the personnel.
        Between 1 - 5
    """
    query = """
        SELECT cadre
        FROM cadre
        WHERE role = ?
        """
    with open("./data/personnel_cadre.json", "r", encoding="utf-8") as f:
        cadre_lookup = json.load(f)

    cadre = cadre_lookup[role]

    return cadre


def serve_healthcare_facilities(country, label, conn):
    """
    Retrieve the number of health facilities in a country of a particular type.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    label : str
        The type of health facility.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    int
        The number of health facilities.
    """
    query = """
        SELECT {label}
        FROM healthcare_facilities
        WHERE ISO3 = ?
        """

    cursor = conn.cursor()
    cursor.execute(query.format(label=label), (country, ))

    result = cursor.fetchone()
    return result[0]