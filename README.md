# who-programme-costing-utilities
A command-line utility for producing modular programme costs.

# Context
When building models, we tend to consider costs at the individual-level.
That is, costs that are incurred when an individual, or group of individuals do a particular thing.
However, there are often costs that are incurred by virtue of a programme being run.
For example, a law being passed on sugar-sweetened beverages still has a cost to pass the law.
For example, a breast-cancer screening intervention has costs to run the programme, train staff, etc.
For these costs, we have built a separate utility, which allows us to consider the costs of a programme, rather than the costs of an individual.
The hope is that this utility can be incorporated into specific modelling, once a simple method has been established.
Until then, it's more clear to have another utility which does this.
This is that utility.

# Use
- You must have the prerequisite databases (sqlite databases)
    - `./data/who_choice_price_database.db`
    - `./data/undpp_wpp.db`
- Clone the repository using `git clone`
- Install the requirements using `pip install -r requirements.txt`
- You can check the tests work by running `python -m unittest discover tests`
- Run the program by using `python main.py -i X -o Y`
    - where X is the input file and Y is the output file
    - Note, the input file must be a .JSON, utf-8 encoded file
    - Note, the output file will be a .CSV, utf-8 encoded file

# Input file
The input file must be a .JSON, utf-8 encoded file. 
These are the keys that should be included in the input file:
- `start_year`: int (DEFAULT: 2023)
    the year the programme starts
- `end_year`: int (DEFAULT: 2030)
    the year the programme ends
- `discount_rate`: float (DEFAULT: 1)
    the discount rate to use for the programme
- `currency`: str (DEFAULT: USD)
    The currency to use for the programme
- `currency_year`: int (DEFAULT: 2018)
    The year to use for the currency
- `modules`: list (DEFAULT: Programme costs template)
    The list of modules relevant to the programme