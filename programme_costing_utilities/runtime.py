import pandas as pd

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
    return pd.DataFrame()