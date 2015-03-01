'''
TO DO:
-----
-Non-standard exchanges? probably should ignore those tickers for now...
-refresh_prices() rather than get_prices()
-graphing
-should limit how much price data we store
-ability to scrape more than just first page
-incorporate SQLAlchemy / Pony ORM?
-threading?
-Companies shouldn't allow multiples of the same ticker
-Should watch out for 'short' in title
'''

from bs4 import BeautifulSoup
import copy
import csv
import datetime
import re
import urllib2
from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine('mysql://project:project@localhost/cbff', echo=False) # Toggle echo to show db interactions
Base = declarative_base()
Session = scoped_session(sessionmaker(bind=engine))
session = Session()

class Creator(Base):
    __tablename__ = "creators"
    id = Column(Integer, primary_key = True)
    companies = relationship("Company", backref="creator", cascade="all")
    creator = Column(String(100), nullable=False, unique=True)
    def __init__(self, creator):
        self.creator = creator
    def __str__(self):
        return '%s' % self.creator
    def __repr__(self):
        return '%s' % self.creator

class Price(Base):
    __tablename__ = "prices"
    id = Column(Integer, primary_key = True)
    company_id = Column(Integer, ForeignKey('companies.id'))
    date = Column(DateTime, nullable=False)
    open_ = Column(Float) # open is a restricted name, hence the underscore
    high = Column(Float) # as an aside, a commenter on StackOverflow remarked that it might be preferrable for one column of prices to be represented as two separate columns of integers, for the numbers before/after the decimal place
    low = Column(Float) # further, should be aware of cross-country subtleties in terms of decimals, foreign currencies, etc.
    close = Column(Float) # we very well may just want to discard all data except closing prices
    adj_close = Column(Float)
    volume = Column(Integer)
    def __init__(self, date, open_, high, low, close, adj_close, volume):
        self.date = date
        self.open_ = open_
        self.high = high
        self.low = low
        self.close = close
        self.adj_close = adj_close
        self.volume = volume
    def __str__(self):
        return '[%s, %s, %s, %s, %s, %s, %s]' % (datetime.datetime.strftime(self.date, '%Y-%m-%d'), self.open_, self.high, self.low, self.close, self.adj_close, self.volume)
    def __repr__(self):
        return '[%s, %s, %s, %s, %s, %s, %s]' % (datetime.datetime.strftime(self.date, '%Y-%m-%d'), self.open_, self.high, self.low, self.close, self.adj_close, self.volume)
    @property
    def serialize(self):
        return {
            'date': dump_datetime(self.date),
            'adj_close': self.adj_close,
            'volume': self.volume
        }

        
#To do:

# class CreatorReturns(Base):
#     __tablename__ = "creator_returns"
#     id = Column(Integer, primary_key = True)
#     creator_id = Column(Integer, ForeignKey('creators.id'))
#     return_to_date = Column(Float)
#     last_refreshed = Column(DateTime, nullable=False)
#     def __init__(self):
#         return_to_date = 0
#         last_refreshed = datetime.datetime.min

# class CompanyReturns(Base):
#     __tablename__ = "company_returns"
#     id = Column(Integer, primary_key = True)
#     company_id = Column(Integer, ForeignKey('companies.id'))
#     max_decline = Column(Float)
#     max_rise = Column(Float)
#     return_to_date = Column(Float)
#     last_refreshed = Column(DateTime, nullable=False)
#     def __init__(self):
#         max_decline = 0
#         max_rise = 0
#         return_to_date = 0
#         last_refreshed = datetime.datetime.min

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key = True)
    ticker = Column(String(20), unique=False, nullable=False) #Unique = False because idea might be submitted by different people
    company = Column(String(100), unique=False, nullable=False) #might want to revise string sizes at some point
    creator_id = Column(Integer, ForeignKey('creators.id'))
    link = Column(String(200), unique=True, nullable=False)
    replies = Column(Integer)
    views = Column(Integer)
    prices = relationship("Price", backref="company", cascade="all, delete")
    initial_price = Column(Float)
    # returns = relationship("CompanyReturns")
    return_to_date = Column(Float)
    creation_date = Column(DateTime, nullable=False)
    def __init__(self, ticker, company, creator, link):
        self.ticker = ticker
        self.company = company
        existing_creator = session.query(Creator).filter_by(creator=creator).first()
        if existing_creator:
            self.creator = existing_creator
        else:
            self.creator = Creator(creator)
        self.link = link
        self.replies = 0
        self.views = 0
        self.creation_date = self.get_creation_date()
    def __str__(self):
        return '%s - %s, created by %s' % (self.ticker, self.company, self.creator)
    def __repr__(self):
        return '%s - %s, created by %s' % (self.ticker, self.company, self.creator)
    def get_creation_date(self):
        url = urllib2.urlopen(self.link)
        soup = BeautifulSoup(url)
        text = soup.find('div', class_='smalltext').text
        text_re = re.compile("Today")
        if text_re.search(text):
            return datetime.datetime.today()
        else: 
            text_re = re.compile(r"(?<=on: )[a-zA-Z]*\s[0-9]{1,2},\s[0-9]{4}") #optional: add times to dates at some point
        date = text_re.search(text).group(0)
        return datetime.datetime.strptime(date, '%B %d, %Y')
    def get_prices(self):
        self.prices = []
        print "Fetching price data for ticker %s " % self.ticker 
        try:
            url = urllib2.urlopen("http://finance.yahoo.com/q/hp?s=" + self.ticker + "+Historical+Prices")
        except:
            print "Error: Could not find CSV file for ticker %s" % self.ticker
            return False
        soup = BeautifulSoup(url, "lxml")
        csv_link = soup.find_all('a', href=re.compile('http://ichart.finance.yahoo.com/table.csv'))
        if not csv_link:
            print "Error: Could not find CSV file for ticker %s" % self.ticker #import warnings module for this
            return False
        csv_link = str(csv_link[0])
        csv_link = csv_link[9:csv_link.find('csv"')+3]
        url = urllib2.urlopen(csv_link)
        csv_data = csv.reader(url, delimiter=',', quotechar='|')
        csv_data.next() #skip header row
        for row in csv_data:
            date = row[0].strip()
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            open_ = float(row[1])
            high = float(row[2])
            low = float(row[3])
            close = float(row[4])
            volume = int(row[5])
            adj_close = float(row[6])
            prices = Price(date = date, open_ = open_, high = high, low = low, close = close, adj_close = adj_close, volume = volume)
            self.prices.append(prices)
        try:
            nearest_date = session.query(Price.date).join(Company).filter(and_(Company.ticker==self.ticker, Price.date<=self.creation_date)).limit(1).one()[0] #returns a tuple
        except:
            print "Error: Insufficient price data for ticker %s" % self.ticker
            return False
        latest_price = self.prices[0].adj_close
        self.initial_price = session.query(Price.adj_close).join(Company).filter(and_(Company.ticker==self.ticker, Price.date==nearest_date)).one()[0] #returns a tuple
        self.return_to_date = ((latest_price / self.initial_price) - 1 )*100

Base.metadata.create_all(engine) 

# class Company_Snapshot(object):
#     pass

def dump_datetime(value):
    """Deserialize datetime object into string form for JSON processing.
    See: http://stackoverflow.com/questions/7102754/jsonify-a-sqlalchemy-result-set-in-flask"""
    if value is None:
        return None
    return value.strftime("%Y-%m-%d")


def calc_returns_to_date(company, date):
    days = 7
    date_temp = date
    while days > 0: 
        price1 = company.find_price(date_temp)
        if price1:
            print price1, date_temp
            break
        else:
            date_temp = date_temp - datetime.timedelta(1,0)
            days -= 1
    if days == 0:
        print "Error: Could not calculate returns to date."
    days = 7
    date_temp = company.creation_date
    while days > 0: 
        price2 = company.find_price(date_temp)
        if price2:
            print price2, date_temp
            break
        else:
            date_temp = date_temp - datetime.timedelta(1,0)
            days -= 1
    if days == 0:
        print "Error: Could not calculate returns to date."
    print "Total return: %.02f%%" % (price1/price2-1)
    print "Annualized return: %.02f%%" % (price1/price2)**(1/(((date-company.creation_date).days)/365.)-1)

def pull_n(index=""):
    url = urllib2.urlopen("http://www.cornerofberkshireandfairfax.ca/forum/investment-ideas/" + str(index))
    print "http://www.cornerofberkshireandfairfax.ca/forum/investment-ideas/" + str(index)
    i = 0
    soup = BeautifulSoup(url)
    tbody = soup.find('tbody')
    row = tbody.find('tr')
    td = row.find_next('td')
    while True: #skips stickied threads
        if row.find(class_=re.compile("sticky")):
            row = row.find_next('tr')
            td = row.find_next('td')
            i += 1
        else:
            break
    lines = []
    links = []
    for y in range(15-i): #subtracts 1 from index if a stickied thread exists
        link = row.a['href']
        row = row.find_next('tr')
        links.append(link)
        line = []
        for x in range(5):
            line.append(td.text.strip())
            td = td.find_next('td')
        del line[0:2] #removes garbage
        lines.append(line)
    return lines, links

#Returns data from investment board page; bool_break returns True if the most recent most of the last thread on the page is older than when the thread data was last refreshed
def get_investment_page(last_refreshed, max_depth=None, index=""):
    print "http://www.cornerofberkshireandfairfax.ca/forum/investment-ideas/" + str(index)
    url = urllib2.urlopen("http://www.cornerofberkshireandfairfax.ca/forum/investment-ideas/" + str(index))
    i = 0
    soup = BeautifulSoup(url)
    if max_depth == None:
        max_depth_text = soup.find(class_="pagelinks floatleft")
        max_depth = max_depth_scan(max_depth_text)
    tbody = soup.find('tbody')
    row = tbody.find('tr')
    td = row.find_next('td')
    if row.find('strong'): #skips stickied thread
        row = row.find_next('tr')
        td = row.find_next('td')
        i = 1
    lines = []
    links = []
    for y in range(15-i): #subtracts 1 from index if a stickied thread exists
        try: #using try/except in case fewer than 15 threads per page (e.g. last page on board)
            link = row.a['href']
            row = row.find_next('tr')
            links.append(link)
            line = []
            for x in range(5):
                line.append(td.text.strip())
                td = td.find_next('td')
            del line[0:2] #removes garbage
            lines.append(line)
        except:
            break
    ####### On the last page of the investment board, you will often have fewer than 15 threads on the page. The above code will result in a link back to the board index erroneously being classified as a thread link. This code below strips it out. Ideally there should be a better way of determining how many valid threads are on the page rather than resoting to this.        
    if (len(links) != len(lines)) and max_depth==(index/15+1):
        re_text=re.compile("index.php")
        if re_text.search(links[-1]):
            del links[-1]
    #######
    dummy=[]
    dummy.append(lines[-1])
    last_reply = last_replies_scan(dummy) # without doing the above, lines[-1] will be malformed when passed to last_replies_scan()
    if (index/15+1) >= max_depth:
        bool_break = True
        return lines, links, bool_break, max_depth
    if last_reply[0] < last_refreshed:
        bool_break = True # will instruct infinite loop from calling function to break
    else:
        bool_break = False
    return lines, links, bool_break, max_depth

#start at page 1 and go n-1 pages back
def pull_n_pages(n):
    index = (n-1)*15 #15 threads to a page
    lines = []
    links = []
    for x in range(n):
        a, b = pull_n(index)
        lines = a + lines
        links = b + links
        index -= 15
    return lines, links

def input_check(lines, links):
    #TO DO: need to make sure ticker / company / etc SQL buffers are OK otherwise will crash program (e.g. if ticker > 10 chars -- see PNL.Netherlands http://www.cornerofberkshireandfairfax.ca/forum/investment-ideas/pnl-netherlands-postnl/)
    company_re = re.compile(r"(?<=- )[a-zA-Z0-9.,\"+:/'&()\- ]*(?=\n)") #sanitizes input -- assume that lines that don't satisfy this re are miscategorized non-investment related threads
    ticker_re = re.compile(r"^[a-z](?:[a-z.-]*[a-z])?", flags=re.I)
    i = 0
    new_lines = []
    new_links = []
    for x in lines:
        if company_re.search(x[0]) and ticker_re.match(x[0]) and x[0].find('-') != -1: #searching for malformed thread subjects
            new_lines.append(lines[i])
            new_links.append(links[i])
        i+=1
    return new_lines, new_links

def ticker_scan(foo):
    tickers = []
    ticker_re = re.compile(r"^[a-z](?:[a-z.-]*[a-z])?", flags=re.I) #tickers can include '.' and '-' (e.g. FTP.TO or BAC-WTA) --> re prevents trailing '-' or '.', per http://stackoverflow.com/questions/18303401/regex-dealing-with-unpredictable-inputs-disallowed-trailing-but-otherwise-ok?noredirect=1#comment26856962_18303401
    for x in foo:
        if ticker_re.match(x[0]): #match looks only at beginning of string; search looks at entirety
            tickers.append(ticker_re.match(x[0]).group(0))
    return tickers

def company_scan(foo):
    companies = []
    company_re = re.compile(r"(?<=- )[a-zA-Z0-9.,\"'+/:()&\- ]*(?=\n)")#(?<=- ) looks for preceding "- "; stops when it finds \n
    for x in foo:
        print x
        if company_re.search(x[0]).group(0):
            companies.append(company_re.search(x[0]).group(0))
    return companies

def creator_scan(foo):
    creators = []
    creator_re = re.compile(r"(?<=Started by )[a-zA-Z0-9.,_ -]*((?=\n)|$)")#halts either by finding \n or end of line
    for x in foo:
        print x
        if creator_re.search(x[0]).group(0):
            print x[0]
            creators.append(creator_re.search(x[0]).group(0)) 
    return creators

def replies_scan(foo):
    replies = []
    replies_re = re.compile(r"[0-9]*(?= Replies)")
    for x in foo:
        if replies_re.search(x[1]).group(0):
            replies.append(int(replies_re.search(x[1]).group(0))) 
    return replies

def last_replies_scan(foo): # behavior varies based upon whether analyzing a single item or not. problem is that a single unit of our data is a list as well. so we need to be explicit.
    last_replies = []
    today_re = re.compile(r"(?<=Today at )[0-9]{2}:[0-9]{2}:[0-9]{2} [AMPM]{2}")
    last_replies_re = re.compile(r"[a-zA-Z]* [0-9]{2}, [0-9]{4}, [0-9]{2}:[0-9]{2}:[0-9]{2} [AMPM]{2}") # should match Month Day, Year format (e.g. August 08, 2013).. days always have two digits; includes time
    for x in foo:
        if today_re.search(x[2]):
            today = datetime.datetime.today().date()
            today = datetime.datetime.strftime(today, "%B %d, %Y")
            mins = today_re.search(x[2]).group(0)
            today = today + ", " + mins
            today = datetime.datetime.strptime(today, "%B %d, %Y, %I:%M:%S %p")
            last_replies.append(datetime.datetime.today()) #doing this will get the day right but won't record the actual time, but rather the time this call is made locally
        else:
            last_replies.append(datetime.datetime.strptime(last_replies_re.search(x[2]).group(0), "%B %d, %Y, %I:%M:%S %p")) # see http://docs.python.org/2/library/datetime.html
    return last_replies

def views_scan(foo):
    views = []
    views_re = re.compile(r"[0-9]*(?= Views)")
    for x in foo:
        if views_re.search(x[1]).group(0):
            views.append(int(views_re.search(x[1]).group(0))) 
    return views

def max_depth_scan(text):
    max_depth_re = re.compile("(?<=... )[0-9]{2,3}") # looks for a number 
    max_depth = max_depth_re.search(text.text).group(0)
    return int(max_depth)

def links_scan(foo):
    links = []
    links_re = re.compile(r"[a-zA-Z0-9:/.'()_\-]*(?=\?)") #do any other characters need to be whitelisted?
    for x in foo:
        if links_re.search(x).group(0):
            links.append(links_re.search(x).group(0))
    return links

def process_scraped_data(session, lines, links):
    if len(lines) != len(links):
        print "Error processing data: lines do not match links"
    lines, links = input_check(lines, links)
    tickers = ticker_scan(lines)
    company_names = company_scan(lines)
    print "test"
    creators = creator_scan(lines)
    replies = replies_scan(lines)
    views = views_scan(lines)
    links = links_scan(links)
    for x in range(len(lines)):
        company = Company(tickers[x], company_names[x], creators[x], links[x])
        company.replies = replies[x]
        company.views = views[x]
        session.add(company)
    return session

def initial_pull(session, n):
    lines, links = pull_n_pages(n)
    session = process_scraped_data(session, lines, links)
    companies = session.query(Company).all()
    bad_ticks = []
    for company in companies:
        if company.get_prices() == False:
            bad_ticks.append(company)
    for tick in bad_ticks:
        session.delete(tick)
    session.commit()
    return session

def process_scraped_data_dated(session, last_refreshed, lines, links):
    if len(lines) != len(links):
        print "Error processing data: lines do not match links"
    lines, links = input_check(lines, links)
    tickers = ticker_scan(lines)
    company_names = company_scan(lines)
    creators = creator_scan(lines)
    replies = replies_scan(lines)
    last_reply = last_replies_scan(lines)
    views = views_scan(lines)
    links = links_scan(links)
    new_companies = []
    existing_tickers = []
    existing_companies = []
    for x, in session.query(Company.ticker).all():
        existing_tickers.append(x)
    for x, in session.query(Company.company).all():
        existing_companies.append(x)
    for x in range(len(lines)):
        if last_reply[x] > last_refreshed: #for loop will never end if consistently True
            if tickers[x] not in existing_tickers and company_names[x] not in existing_companies:
                print tickers[x], company_names[x]
                company = Company(tickers[x], company_names[x], creators[x], links[x])
                company.replies = replies[x]
                company.views = views[x]
                session.add(company)
                print "Adding new company %s" % company_names[x]
                new_companies.append(company)
        else:
            print "Company %s already exists" % company_names[x]
    print "new companies", new_companies
    return session, new_companies

def dated_refresh(session, last_refreshed):
    index = 0 
    lines = []
    links = []
    max_depth = None
    while True: #Loop pulls successive investment board pages until the date of the most recent reply on the last thread is older than when the last refresh was performed. Then, bool_break returns True and the loop halts.
        a, b, bool_break, max_depth = get_investment_page(last_refreshed, max_depth, index)
        lines = a + lines
        links = b + links
        index += 15 #15 threads to a page
        if bool_break == True:
            break
    session, new_companies = process_scraped_data_dated(session, last_refreshed, lines, links)
    bad_ticks = []
    for company in new_companies:
        if company.get_prices() == False:
            bad_ticks.append(company)
            session.commit()
    for tick in bad_ticks:
        session.delete(tick)
    session.commit()
    return session

# last_refreshed = datetime.datetime.min
# last_refreshed = datetime.datetime(2013, 1, 3)
# session = dated_refresh(session, last_refreshed)

#
# companies = session.query(Company).all()
# print companies
# session = initial_pull(session, 1)
# last_refreshed = datetime.datetime(2013, 8, 9, 18, 18, 1, 217610)