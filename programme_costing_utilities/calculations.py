"""
Provides the methods to calculate the personnel quantity and cost.
"""
import numpy as np
import json
import warnings

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
    return 1 / discount_rate ** (year - start)


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
    start_year: int
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
    log = f"""
    Year: {year}
    Personnel to Support Programme Area: {programme_area}
    Personnel: {role} (ISCO-08: {cadre})
    In {division} division, at {fte:,.2f} FTE, performing {activities} activities
    Annual Salary @ 1FTE: {currency_information[0]}{currency_information[1]}: {annual_salary:,.2f}
    Total Salary: {currency_information[0]}{currency_information[1]}: {salary:,.2f}
    Total Salary Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
    """
    resource_information = (
        "Personnel", 
        role, 
        cadre, 
        division, 
        fte
        )
    cost_information = (salary, currency_information[0], currency_information[1])

    # add to records
    record = (year, log, resource_information, cost_information)
    records.append(record)

    # determine their need for office supplies
    if role not in DONT_NEED_OFFICE_SUPPLIES:
        for item in OFFICE_SUPPLIES:
            cost = fte * item["per person"] * item["annualised cost"]
            cost_information = (cost, item["currency"], item["currency year"])

            log = f"""
            Year: {year}
            Office Supplies for {role} in {division} supporting Programme {programme_area}
            Item: {item["item"]}
            Cost of Item: {item["currency"]}{item["currency year"]}: {cost:,.2f}
            Cost of Item Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
            """
            quantity = fte * item["per person"]
            resource_information = (
                "Office Supplies", 
                item["item"], 
                role, 
                division, 
                quantity
                )

            record = (year, log, resource_information, cost_information)
            records.append(record)

    if role in NEED_CARS_AND_TRAVEL:
        # Each FTE needs half a car  TODO #6 - Interrogate this rule
        cars_needed = fte * 0.5
        km_per_car = calculate_km_travelled_per_year(division, CAR_PREFERENCE)
        kms_driven = cars_needed * km_per_car
        operational_cost, currency_information = serve_vehicle_operating_cost(CAR_PREFERENCE, conn)
        total_operational_cost = operational_cost * kms_driven

        log = f"""
        Year: {year}
        Transport to support {role} in {division} division, supporting Programme {programme_area}
        Type of Car: {CAR_PREFERENCE}
        Proportion of Car needed to support role: {cars_needed:,.2f}
        Annual kms driven: {kms_driven:,.2f}
        Operational cost per km: {currency_information[0]}{currency_information[1]}: {operational_cost:,.2f}
        Therefore, total operational cost: {currency_information[0]}{currency_information[1]}: {total_operational_cost:,.2f}
        Total operational cost Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
        """
        resource_information = (
            "Transport - Operational Costs", 
            "KMs Driven * OpEx", 
            CAR_PREFERENCE, 
            division, 
            kms_driven
            )
        cost_information = (total_operational_cost, currency_information[0], currency_information[1])
        record = (year, log, resource_information, cost_information)
        records.append(record)

        fuel_cost, currency_information = serve_vehicle_fuel_consumption(CAR_PREFERENCE, conn)
        total_fuel_cost = fuel_cost * kms_driven
        log = f"""
        Year: {year}
        Fuel for {cars_needed:,.2f} x {CAR_PREFERENCE} to support {role} in {division} division, supporting Programme {programme_area}
        Annual kms driven: {kms_driven:,.2f}
        Fuel cost per km: {currency_information[0]}{currency_information[1]}: {fuel_cost:,.2f}
        Therefore, total fuel cost: {currency_information[0]}{currency_information[1]}: {total_fuel_cost:,.2f}
        Total fuel cost Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
        """
        resource_information = (
            "Transport - Fuel Costs", 
            "KMs Driven * Fuel", 
            CAR_PREFERENCE, 
            division, 
            kms_driven
            )
        cost_information = (total_fuel_cost, currency_information[0], currency_information[1])
        record = (year, log, resource_information, cost_information)
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

    log = f"""
    Year: {year}
    Room hire for {division} Room
    Room Size: {room_size}m2
    For {days} days per meeting.
    For {number_of_meetings:,.2f} meetings.
    Total Cost: {currency_information[0]}{currency_information[1]}: {room_hire_cost_total:,.2f}
    Total Cost Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
    """
    resource_information = (
        "Meeting", 
        "Room Hire Costs",
        division, 
        f"{room_size}m2", 
        number_of_meetings)
    cost_information = (room_hire_cost_total, currency_information[0], currency_information[1])
    record = (year, log, resource_information, cost_information)
    records.append(record)

    # per diems for visiting attendees
    # days * attendees * per_diems
    visiting_attendees = [a for a in attendees if a[1] == "visiting"]
    per_diems, currency_information = serve_per_diem(country, division, conn, True)
    for visiting_attendee in visiting_attendees:
        attendee_label, _, attendees_requiring_per_diems, _ = visiting_attendee
        cost = days * attendees_requiring_per_diems * per_diems * number_of_meetings

        log = f"""
        Year: {year}
        Per diems for visiting attendees for {days} days for {number_of_meetings:,.2f} meetings.
        Per diems: {currency_information[0]}{currency_information[1]}: {per_diems:,.2f}
        Total Cost: {currency_information[0]}{currency_information[1]}: {cost:,.2f}
        Total Cost Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
        """

        resource_information = (
            "Meeting", 
            "Per Diem Costs",
            attendee_label, 
            division, 
            attendees_requiring_per_diems
            )
        cost_information = (cost, currency_information[0], currency_information[1])
        record = (year, log, resource_information, cost_information)
        records.append(record)

    # opportunity cost (days of salary) for local attendees
    local_attendees = [a for a in attendees if a[1] == "local"]
    cadre = 2  # FIXME #2 - Assuming cadre of support staff is 2
    daily_salary, currency_information = calculate_daily_salary(country, cadre, conn)
    for local_attendee in local_attendees:
        attendee_label, _, quantity, _ = local_attendee
        cost = days * quantity * daily_salary * number_of_meetings

        log = f"""
        Year: {year}
        {attendee_label}: Salary for {quantity} local attendees for {days} days for {number_of_meetings:,.2f} meetings.
        Daily Salary: {currency_information[0]}{currency_information[1]}: {daily_salary:,.2f}
        Total Cost: {currency_information[0]}{currency_information[1]}: {cost:,.2f}
        Total Cost Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
        """

        resource_information = (
            "Meeting",
            "Local attendance costs",
            attendee_label, 
            division, 
            quantity
            )
        cost_information = (cost, currency_information[0], currency_information[1])
        record = (year, log, resource_information, cost_information)
        records.append(record)

    # travel = attendees * ddist * operational cost of car
    vehicle_operating_cost_per_km, currency_information = serve_vehicle_operating_cost(preferred_vehicle, conn)
    vehicle_fuel_consumption_per_km, currency_information = serve_vehicle_fuel_consumption(preferred_vehicle, conn)
    distance_travelled_in_km = serve_distance_between_regions(country, "DDist95", conn)  # FIXME #3 - Interrogate this assumption
    cost_of_travel_per_attendee = distance_travelled_in_km * vehicle_operating_cost_per_km * vehicle_fuel_consumption_per_km
    for attendee in attendees:
        attendee_label, _, _, quantity = attendee
        cost = quantity * cost_of_travel_per_attendee * number_of_meetings

        log = f"""
        Year: {year}
        {attendee_label}: Travel for {quantity} attendees for {number_of_meetings:,.2f} meetings
        Distance Travelled: {distance_travelled_in_km:,.2f}km
        Vehicle Operating Cost: {currency_information[0]}{currency_information[1]}: {vehicle_operating_cost_per_km:,.2f} 
        Vehicle Fuel Consumption: {vehicle_fuel_consumption_per_km:,.2f}L/km
        Total Cost: {currency_information[0]}{currency_information[1]}: {cost:,.2f}
        Total Cost Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
        """
        resource_information = (
            "Meeting",
            "Travel Costs for Attendees",
            attendee_label, 
            division, 
            quantity
            )
        cost_information = (cost, currency_information[0], currency_information[1])
        record = (year, log, resource_information, cost_information)
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
    Component kwargs are dependent on the type of media campaign.
    Therefore, they are explained in more detail in their respective functions.

    Returns
    -------
    list
        each entry is a tuple of the form:

    """
    media_to_function = {
        "Radio time (minutes)": get_airtime_records,
        "Television time (minutes)": get_airtime_records,
        "Newspapers (100 word insert)": get_newspaper_records,
        "Wall posters": get_wall_poster_records,
        "Flyers / leaflets (per leaflet)": get_flyers_leaflet_records,
        "Social media": get_social_media_records,
        "Text messaging": get_text_messaging_records
    }
    label = component["label"]
    records = media_to_function[label](component, country, year, conn)
    return  records


def get_text_messaging_records(component, country, year, conn):
    """
    Calculate the annual cost of providing text messaging.
    
    Parameters
    ----------
    component : dict
        The component of the intervention.
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    list
        a list of tuples of the form:
        record = (year, log, resource_information, cost_information)
    """
    # FIXME This is a placeholder
    return []


def get_social_media_records(component, country, year, conn):
    """
    Calculate the annual cost of providing social media.

    Parameters
    ----------
    component : dict
        The component of the intervention.
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    list
        a list of tuples of the form:
        record = (year, log, resource_information, cost_information)
    """
    # FIXME #4 - This is a placeholder function
    return []


def get_flyers_leaflet_records(component, country, year, conn):
    """
    Calculate the annual cost of providing flyers or leaflets.

    Parameters
    ----------
    component : dict
        The component of the intervention.
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    list
        a list of tuples of the form:
        record = (year, log, resource_information, cost_information)
    """
    ...


def get_newspaper_records(component, country, year, conn):
    """
    Calculate the annual cost of providing newspaper inserts.

    Newspapers are calculated by the number of words, and the number of inserts.

    The component should provide the following kwargs (e.g.):    
        "label": "Newspapers (100 word insert)",
        "division": "national",
        "Number of words per insert": 100,
        "inserts per year": 10

    NOTE - this function currently assumes 100 words per insert.

    Parameters
    ----------
    component : dict
        The component of the intervention.
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    list
        a list of tuples of the form:
        record = (year, log, resource_information, cost_information)
    """
    label = component["label"]
    division = component["division"]
    words_per_insert = component["Number of words per insert"]  # Currently a placeholder
    inserts_per_year = component["inserts per year"]
    inserts_per_year = fit_FTE(inserts_per_year, country, year, division, conn)
    cost, currency_information = calculate_mass_media_costs(label, country, year, conn)
    total_cost = cost * inserts_per_year
    log = f"""
    Year: {year}
    Mass Media Campaign Using Newspaper
    Words per insert: {words_per_insert}
    Inserts per year: {inserts_per_year:,.2f}
    Cost per insert: {currency_information[0]}{currency_information[1]}: {cost:,.2f}
    Total Cost: {currency_information[0]}{currency_information[1]}: {total_cost:,.2f}
    Total Cost Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
    """
    resource_information = (
        "Mass Media",
        "Newspaper",
        division, 
        None,
        inserts_per_year
        )
    record = (year, log, resource_information, (cost, *currency_information))
    return [record]


def get_airtime_records(component, country, year, conn):
    """
    Calculate the annual cost of providing airtime, either on radio or television.

    The component should provide the following kwargs (e.g.):
        "label": "Television time (minutes)",
        "division": "national",
        "campaigns per year": 2,
        "days per campaign": 28,
        "advertisements per day": 2,
        "minutes per advertisement": 0.5

    Note, these amounts are the amount assumed for a standardized population,
    and may need to be adjusted for the country of interest.

    Parameters
    ----------
    component : dict
        The component of the intervention.
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    list
        a list of tuples of the form:
        record = (year, log, resource_information, cost_information)
    """
    label = component["label"]
    division = component["division"]
    campaigns_per_year = component["campaigns per year"]
    days_per_campaign = component["days per campaign"]
    advertisements_per_day = component["advertisements per day"]
    minutes_per_advertisement = component["minutes per advertisement"]
    mass_media_cost, currency_information = calculate_mass_media_costs(label, country, year, conn)
    total_airtime = (
        campaigns_per_year
        * days_per_campaign
        * advertisements_per_day
        * minutes_per_advertisement
    )
    total_airtime = fit_FTE(total_airtime, country, year, division, conn)
    cost = mass_media_cost * total_airtime
    log = f"""
    Year: {year}
    Airtime for {label}
    Campaigns per year: {campaigns_per_year} 
    Days per campaign: {days_per_campaign}
    Advertisements per day: {advertisements_per_day}
    Minutes per advertisement: {minutes_per_advertisement}
    Total Airtime: {total_airtime:,.2f}
    Cost per minute: {currency_information[0]}{currency_information[1]}: {mass_media_cost:,.2f}
    Total Cost: {currency_information[0]}{currency_information[1]}: {cost:,.2f}
    Total Cost Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
    """
    resource_information = (
        "Airtime",
        label, 
        division, 
        None,
        total_airtime
        )
    record = (year, log, resource_information, (cost, *currency_information))
    return [record]


def get_wall_poster_records(component, country, year, conn):
    """
    Calculate the annual cost of providing wall posters.

    Wall posters are provided at health facility level, and can be adjusted according to scale.
    For example, if there is one national facility, but a scale of 2, then two posters would be
    provided to that facility.
    
    Parameters
    ----------
    component : dict
        The component of the intervention.
    country : str
        The ISO3 code of the country.
    year : int
        The year of interest.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    list
        a list of tuples of the form:
        record = (year, log, resource_information, cost_information)
    """
    label = component["label"]
    HEALTH_FACILITY_MAPPING = {
        "national": ["regional_hospitals"],
        "provincial": ["provincial_hospitals"],
        "district": ["district_hospitals", "health_centres", "health_posts"]
    }
    cost, currency_information = calculate_mass_media_costs(label, country, year, conn)

    division = component["division"]

    division_health_facilities = HEALTH_FACILITY_MAPPING[division]

    records = []
    for health_facility_type in division_health_facilities:
        # get the number of health facilities
        number_of_health_facilities = serve_healthcare_facilities(country, health_facility_type, conn)
        # multiply by the cost
        total_cost = number_of_health_facilities * cost
        # create the record
        log = f"""
        Year: {year}
        Wall posters for {health_facility_type} (A {division} facility)
        Cost per health facility: {currency_information[0]}{currency_information[1]}: {cost:,.2f}
        Total Cost: {currency_information[0]}{currency_information[1]}: {total_cost:,.2f}
        Total Cost Rebased: {{awaiting_currency}}{{awaiting_currency_year}}: {{awaiting_cost}}
        """
        resource_information = (
            "Wall Posters",
            health_facility_type, 
            division,
            None,
            number_of_health_facilities
            )
        cost_information = (total_cost, currency_information[0], currency_information[1])
        record = (year, log, resource_information, cost_information)
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
        return 0, (None, None)

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
    vehicle_fuel_consumption, currency, year = result

    return vehicle_fuel_consumption, (currency, year)


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

    if current_year < 1960:
        warnings.warn(
            f"Current year is {current_year}. "
            "This is before the earliest year of the WB-GDP deflators. "
            "Rebasing will not be accurate."
            )
        current_year = 1960
    if desired_year < 1960:
        warnings.warn(
            f"Desired year is {current_year}. "
            "This is before the earliest year of the WB-GDP deflators. "
            "Rebasing will not be accurate."
            )
        desired_year = 1960
    if current_year > 2021:
        warnings.warn(
            f"Current year is {current_year}. "
            "This is after the latest year of the WB-GDP deflators. "
            "Rebasing will not be accurate."
            )
        current_year = 2021
    if desired_year > 2021:
        warnings.warn(
            f"Desired year is {current_year}. "
            "This is after the latest year of the WB-GDP deflators. "
            "Rebasing will not be accurate."
            )
        desired_year = 2021

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
        requested_index = desired_year - first_year
        current_index = current_year - first_year
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


def calculate_mass_media_costs(media_type, country, year, conn):
    """
    Calculate the costs of mass media entries.

    FIXME #10 Media costs are a bit idiosyncratic at the moment, and should
    be reviewed in the future.

    Currently, some costs are a proportion of GDP per capita, and some are
    arbitrary.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    year : int
        The year of the costs.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    tuple
        (cost, currency, year)
    """
    # FIXME #9 Investigate the assumptions behind these costs
    PROPORTION_OF_GDP_PER_CAPITA = {
        "Television time (minutes)": 0.68,
        "Radio time (minutes)": 0.12,
     }
    ARBITRARY_COST = {
        "Newspapers (100 word insert)": 100,
        "Wall posters": 15,
        "Flyers / leaflets": 0.15
    }
    if media_type in PROPORTION_OF_GDP_PER_CAPITA:
        cost, _, _ = serve_gdp_per_capita(country, year, conn)
        cost *= PROPORTION_OF_GDP_PER_CAPITA[media_type]
    elif media_type in ARBITRARY_COST:
        cost = ARBITRARY_COST[media_type]
    else:
        warnings.warn("Media type not recognised. Cost set to 0.")
        cost = 0
    ASSUMED_CURRENCY = "USD"
    ASSUMED_CURRENCY_YEAR = 2019
    return cost, (ASSUMED_CURRENCY, ASSUMED_CURRENCY_YEAR)


def serve_gdp_per_capita(country, year, conn):
    """
    Return the GDP per capita of a country in a particular year.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    year : int
        The year of the GDP per capita.
    conn : sqlite3.Connection
        The connection to the database.

    Returns
    -------
    tuple
        (cost, currency, year)
    """
    # TODO #8 Get GDP Forecasts to 2100
    if year < 1960:
        warnings.warn(
            f"Year is {year}. "
            "This is before the earliest year of the WB-GDP deflators. "
            "Rebasing will not be accurate."
            )
        year = 1960
    if year > 2021:
        warnings.warn(
            f"Year is {year}. "
            "This is after the latest year of the WB-GDP deflators. "
            "Rebasing will not be accurate."
            )
        year = 2021
    query = f"""
        SELECT "{year} [YR{year}]" FROM "economic_statistics"
        WHERE "Country Code" = ?
        AND "Series Name" = "GDP per capita, PPP (current international $)"
        """
    cursor = conn.cursor()
    cursor.execute(query, (country, ))
    cost = float(cursor.fetchone()[0])

    return cost, "USD", year