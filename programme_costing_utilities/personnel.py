"""
Provides the methods to calculate the personnel quantity and cost.
"""
def fit_FTE(standardized_FTE, country, population, statistical_division):
    """
    If the FTE given is set to a standardized population, fit the FTE to the
    actual population.

    Parameters
    ----------
    standardized_FTE : float
        The FTE given in the standardized population.
    country : str
        The ISO3 code of the country.
    population : int
        The actual population.
    statistical_division : str
        The division of the personnel.
        National | Provincial | District

    Returns
    -------
    float
        The fitted (actual, real) FTE.
    """
    ...

def calculate_personnel_annual_salary(country, personnel):
    """
    Calculate the annual salary of a personnel.

    Parameters
    ----------
    country : str
        The ISO3 code of the country.
    personnel : str
        The type of personnel.

    Returns
    -------
    float
        The annual salary.
    """