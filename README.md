# Corner of BerkScraper and FunFacts

CBFF is the first project of substance that I ever wrote. At the time, I was interested in value investing and I posted occassionally on a message board called [Corner of Berkshire and Fairfax](http://www.cornerofberkshireandfairfax.ca).

The board had a forum for members to submit investment ideas. Ideas were posted with a consistent format that allowed for stock tickers to be easily parsed. CBFF would scrape the investment ideas forum. Next it added board members and their investment ideas to a SQL database. It then pulled stock price data from Yahoo Finance and analyzed investment performance.

The results of this project can be found at [cobff.chrisdrane.com](http://cobff.chrisdrane.com/) (no longer maintainced).

## Dependencies

* [BeautifulSoup](http://www.crummy.com/software/BeautifulSoup/), for parsing. 
* [SQLAlchemy](http://www.sqlalchemy.org/), intermediary between Python and database
* [MySQL](http://www.mysql.com), database
* [Flask](https://github.com/mitsuhiko/flask), web framework
