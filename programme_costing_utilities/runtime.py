import pandas as pd
from programme_costing_utilities import calculations



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


def run(data, conn):
    """
    Go through components, unpack them into individual elements and create a transaction record for that element.
    For example, a meeting will have elements such as room hire, and per diems.
    These records are then converted into a dataframe.

    Parameters
    ----------
    data : dict
        The input data.
    conn : sqlite3.Connection
        The database connection.

    Returns
    -------
    pandas.DataFrame
        The results.
    """
    country = data["country_iso3"]
    start = data["start_year"]
    end = data["end_year"]
    discount_rate = data["discount_rate"]
    currency = data["currency"]
    currency_year = data["currency_year"]
    components = data["components"]
    results = []

    for i in range(start, end + 1):  # inclusive of end

        current_discount = calculate_discount(discount_rate, i)

        for component_type, component_list in components:
            # collect records
            if component_type == "personnel":
                records = calculations.get_personnel_records(component_list, conn, country, i)
            elif component_type == "meeting":
                for component in component_list:
                    records = calculations.get_meeting_records(component, conn, country, i, start)
            elif component_type == "media":
                for component in component_list:
                    records = calculations.get_media_records(component, conn, country, i, start)
            
            # convert cost estimates to desired currency and year
            for record in records:
                record = calculations.rebase_currency(
                    record=record,
                    currency=currency,
                    currency_year=currency_year,
                    current_discount=current_discount,
                    recorded_currency = record[1][0],
                    recorded_currency_year = record[1][1]
                )
                results.append(record)

    df = pd.DataFrame(results)
    df.set_index('year', inplace=True)
    df = df.T
    return df