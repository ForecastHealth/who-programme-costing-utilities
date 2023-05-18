import pandas as pd
from programme_costing_utilities import calculations


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
    country = data["country"]
    start = data["start_year"]
    end = data["end_year"]
    discount_rate = data["discount_rate"]
    desired_currency = data["desired_currency"]
    desired_year = data["desired_year"]
    components = data["components"]

    table = []
    logs = []

    FUNCTION_MAP = {
        "personnel": calculations.get_personnel_records,
        "meetings": calculations.get_meeting_records,
        "media": calculations.get_media_records
    }

    for i in range(start, end + 1):  # inclusive of end

        discount = calculations.calculate_discount(discount_rate, i, start)

        for component_type, component_list in components.items():
            # collect records
            func = FUNCTION_MAP[component_type]
            for component in component_list:
                records = func(component, conn, country, i, start)
            
                # convert cost estimates to desired currency and year
                for record in records:
                    year, log, resource_information, cost_information = record
                    cost, cost_currency, cost_year = cost_information
                    updated_cost_information = calculations.rebase_currency(
                        cost=cost,
                        current_country=cost_currency,
                        current_year=cost_year,
                        desired_country=desired_currency, 
                        desired_year=desired_year, 
                        discount=discount,
                        conn=conn)

                    logs.append(log)
                    row = {
                        "year": year,
                        "component": component_type,
                        "heading_1": resource_information[0],
                        "heading_2": resource_information[1],
                        "quantity": round(resource_information[2], 2),
                        "cost": round(updated_cost_information[0], 2)
                    }
                    table.append(row)

    table = pd.DataFrame(table)
    return logs, table