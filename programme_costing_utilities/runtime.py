import pandas as pd
from programme_costing_utilities import database_server


def determine_quantity(config):
    ...

def run(data, price_db, demography_db):
    """
    Create a dataframe of results.

    Parameters
    ----------
    data : dict
        The input data.
    price_db : sqlite3.Connection
        The price database.
    demography_db : sqlite3.Connection
        The demography database.

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
        population = database_server.serve_population(i, demography_db)
        for component in components:
            for item, configuration in components.COMPONENT_MAP.items():
                quantity = determine_quantity(configuration)
                unit_price = database_server.get_item_price(
                    item, 
                    configuration, 
                    discount, 
                    price_db)
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