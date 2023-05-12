import pandas as pd
from programme_costing_utilities import calculations


def determine_quantity(config):
    ...

def run(data, conn):
    """
    Create a dataframe of results.

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
        discount = discount_rate ** (i - start + 1)
        population = calculations.serve_population(i, conn)
        for component in components:
            for item, configuration in components.COMPONENT_MAP.items():
                quantity = determine_quantity(configuration)
                unit_price = calculations.get_item_price(
                    item, 
                    configuration, 
                    discount, 
                    conn)
                cost = quantity * unit_price
                record = {
                    "year": i,
                    "component": component,
                    "item": item,
                    "description": configuration.get("description", ""),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "cost": cost
                }
                results.append(record)

    df = pd.DataFrame(results)
    df.set_index('year', inplace=True)
    df = df.T
    return df