from cobff import Session, Company, Price, Creator
import datetime
from flask import abort, Blueprint, Flask, request, session, g, redirect, url_for, abort, render_template, flash, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
#Code requires using an unofficial flask-sqlalchemy release, otherwise crashes due to bug that has existed since 2011.
#See https://github.com/mitsuhiko/flask-sqlalchemy/pull/89
from sqlalchemy import *

app = Flask(__name__)
app.config['DEBUG'] = True
session = Session()

@app.template_filter('date')
def _jinja2_filter_datetime(date):
    return datetime.datetime.strftime(date, "%B %d, %Y")

@app.route('/cobff/faq')
def faq():
	return render_template('faq.html')

@app.route('/cobff/findings')
def findings():
	return render_template('findings.html')

@app.route('/cobff/get_json/<ticker>')
def get_json(ticker=''):
	if ticker == '':
		return False
	qryresult=session.query(Price).join(Company).filter(and_(Company.ticker==ticker, Price.date>=Company.creation_date)).all()
	return jsonify(json_list=[i.serialize for i in qryresult]) #See http://stackoverflow.com/questions/7102754/jsonify-a-sqlalchemy-result-set-in-flask

@app.route('/cobff/ticker/')
@app.route('/cobff/ticker/<ticker>')
@app.route('/cobff/ticker/sortby=<sortby>')
def show_company(ticker='', sortby='ca'):
	if session.query(Company).filter_by(ticker=ticker).first() == None:
		if sortby == "rd": #return descending
			companies = session.query(Company).order_by(Company.return_to_date.desc()).all()
		elif sortby == "ra": #return ascending
			companies = session.query(Company).order_by(Company.return_to_date.asc()).all()
		elif sortby == "ca": #return ascending
			companies = session.query(Company).order_by(Company.company.asc()).all()
		elif sortby == "cd": #return ascending
			companies = session.query(Company).order_by(Company.company.desc()).all()
#		else:
#			companies = session.query(Company).order_by(Company.company).all()
		return render_template('show_companies.html', companies=companies)
	else:
		company = session.query(Company).filter_by(ticker=ticker).one()
		return render_template('show_company.html', company=company)

#To Do: Page should show columns <user> <idea> <date created> <return to date>


#@app.route('/cobff/user/')
#@app.route('/cobff/user/sortby=<sortby>')
@app.route('/cobff/user/<user>')
def show_user(user='',sortby=''):
	user = session.query(Creator).filter_by(creator=user).first()
	print user
	return render_template('show_user.html', creator=user)
	# else:
	# 	if sortby == '':
	# 		users = session.query(Creator).all()
	# #TO DO: need to add # companies to Creator class... not the right place to run len() bc will get hit repeatedly on page refresh
	# 		for user in users:
	# 			user.num_cos = len(session.query(Company).join(Creator).filter(Creator.creator==user).all())
	return render_template('user_metrics.html', creators=users, sortby=sortby)

#Maybe eventually have a dynamic dropdown menu to show companies for any particular user?
@app.route('/cobff/usermetrics')
def user_metrics():
	users = session.query(Creator).all()
#TO DO: need to add # companies to Creator class... not the right place to run len() bc will get hit repeatedly on page refresh
	for user in users:
		user.num_cos = len(session.query(Company).join(Creator).filter(Creator.creator==user).all())
	return render_template('user_metrics.html', creators=users)

@app.route('/cobff/')
def show_entries():
	creators = session.query(Creator).order_by(Creator.creator).all()
	print creators
	return render_template('show_companies.html', creators=creators)

if __name__ == '__main__':
	app.run()