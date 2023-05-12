"""A set of functions to access and transform data in the sqlite databases"""
import numpy as np
import sqlite3

def get_population(year, db):
    """
    Retrieve the population for a given year.

    Parameters
    ----------
    year : int
        The year.
    db : sqlite3.Connection
        The database connection.

    Returns
    -------
    int
        The population.
    """
    ...
def serve_population(cursor, **kwargs) -> np.ndarray:
    """
    Return 2 x 101 ndarray of the population of a country in a specific year.

    Parameters
    ----------
    cursor : sqlite cursor
    country : int
        unsd_m49 code representing a country
    year : int
        year of population data

    Returns
    -------
    np.ndarray
        2 x 101 ndarray of the population of a country in a specific year.
    """
    counter = kwargs["counter"]
    year = counter.ref
    if year < 1950:
        year = 1950
    elif year > 2100:
        year = 2100

    country = kwargs.get("country", 800)

    cursor.execute(
        f"""
        SELECT PopMale, PopFemale
        FROM population
        WHERE LocID = {country} AND Time = {year}
        ORDER BY AgeGrpStart
        """
        )
    
    results = cursor.fetchall()

    results = np.array(results).T

    results *= 1000  # convert from thousands to individuals

    return results


def serve_metadata_iso_code(cursor, **kwargs) -> str:
    """
    Return a 1X1 value which is a text region code (e.g. EMR).

    Parameters
    ----------
    cursor : sqlite cursor
        connected to CountryData.db
    country : int
        unsd_m49 code representing a country

    Returns
    -------
    str
        the ISO-3 code for the country
    """
    country = kwargs["country"]
    cursor.execute(
            """
            SELECT "ISO3" FROM "Metadata"
            WHERE "M49" = ?
            """, (country, )
            )

    return cursor.fetchall()[0][0]


def serve_cost_per_visit(cursor, **kwargs) -> float:
    """
    Return the cost in dollars of a visit.

    The cost_lookup is assumed to be the reference to the cost needed
    1 = INPATIENT
    2 = OUTPATIENT
    3 = INPATIENT SPECIALIST

    Parameters
    ----------
    country : int
    index : int

    Returns
    -------
    float
        cost in dollars (probably USD)
    """
    country = kwargs["country"]
    cost_index = int(kwargs["index"])
    cursor.execute(
            """
            SELECT * FROM "ResourceVisitCosts"
            WHERE M49 = ?
            """, (country, ))

    #  returns a list with 1 tuple
    x = (cursor.fetchall())

    # get"s the index from the tuple
    # the metadata is of length 1, so the cost == correct index
    x = x[0][cost_index]

    return x




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
