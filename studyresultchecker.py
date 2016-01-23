#!/usr/bin/env python

# -*- coding: utf-8 -*-
import os.path
import requests
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from BeautifulSoup import BeautifulSoup
from lxml.html.diff import htmldiff

import secrets


def main():
    reload(sys)
    sys.setdefaultencoding('utf-8')
    studyresults = getstudyresults()
    if studyresults is None:
        print("Program exit")
        return

    oldresults = getpreviousresults()
    if oldresults != studyresults:
        print('changes')
        writenewresults(studyresults)
        sendmail(prettify(htmldiff(oldresults, studyresults)))
    else:
        print('No changes')
    print("Done")


# Gets previous results read from file, content is HTML
def getpreviousresults():
    savedfile = getresultsfile()
    results = savedfile.read()
    savedfile.close()
    return results


def writenewresults(studyresults):
    savedfile = getresultsfile()
    savedfile.seek(0)
    savedfile.write(studyresults)
    savedfile.truncate()
    savedfile.close()


# Get the saved version of the results from file
def getresultsfile():
    if not os.path.isfile(secrets.SAVE_FILE_NAME):
        open(secrets.SAVE_FILE_NAME, "w+").close()
    savedfile = open(secrets.SAVE_FILE_NAME, "r+")
    return savedfile


# Color encode the table entries if changed, deleted or added.
def prettify(content):
    soup = BeautifulSoup(content)
    for table in soup.findAll('table'):
        for tr in table.findAll('tr'):
            if "ins" in str(tr):
                if "del" in str(tr):
                    # Changed
                    tr.attrs.append(('style', "background:#ffffb3"))  # YELLOW
                else:
                    # Added
                    tr.attrs.append(('style', "background:#e6ffe6"))  # GREEN
            elif "del" in str(tr):
                # Deleted
                tr.attrs.append(('style', "background:#ffe6e6"))  # RED
    return str(soup)


# Gets the results from studentportalen and returns the tables that contains the data about the study results as HTML.
def getstudyresults():
    # Initial request to recieve the login and time parameter which are unique for each session.
    response = requests.get("https://www3.student.liu.se/portal/")
    soup = BeautifulSoup(response.text)
    login_para = None
    time = None
    for n in soup.findAll('input'):
        if hasattr(n, 'name'):
            if n.get('name') == "login_para":
                login_para = n.get('value')
            elif n.get('name') == "time":
                time = n.get('value')
    if login_para is None:
        print('login_para not found\nExiting')
        return None
    if time is None:
        print('time not found\nExiting')
        return None
    params = {'login_para': login_para, 'time': time, 'redirect': 1, 'recirect_url': "%/portal/studieresultat/",
              'user': secrets.LIU_USERNAME, 'pass2': secrets.LIU_PASSWORD}
    # Perform login
    response = requests.put("https://www3.student.liu.se/portal/login", data=params, cookies=response.cookies)
    # TODO: Check if login successful

    # Get the study results
    response = requests.get(
            "https://www3.student.liu.se/portal/studieresultat/resultat?show_oavslut=oavslut&show_prov=prov&show_splitt=splitt&post_button_select_filter=Submit",
            cookies=response.cookies)

    # Extract tables with studyresult information
    soup = BeautifulSoup(response.text)
    resulttable = None
    tabletotal = None
    for n in soup.findAll('table'):
        if n.get('class') == "resultlist":
            resulttable = n
        if n.prettify().find("Summa Hp") != -1:
            tabletotal = n

    if resulttable is None:
        print('Result table not found\nExiting')
        return None
    if tabletotal is None:
        print('Total result table not found\nExiting')
        return None

    return str(resulttable).encode('latin-1') + str(tabletotal).encode('latin-1')


# Sends mail through a relay server. If using Gmail, make sure to enable use of third party apps relaying through gmail smtp
def sendmail(message):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Studieresultat Uppdaterat"
    msg['From'] = secrets.FROM_ADDRESS
    msg['To'] = secrets.TO_ADDRESS
    content = """\
    <html>
        <head></head>
        <body>""" + message.encode('iso-8859-1') + """\
        </body>
    </html>
    """
    msg.attach(MIMEText(content, 'html', 'iso-8859-1'))

    server = smtplib.SMTP_SSL(secrets.SMTP_SERVER_ADDRESS)
    server.login(secrets.SMTP_USERNAME, secrets.SMTP_PASSWORD)
    server.sendmail(secrets.FROM_ADDRESS, secrets.TO_ADDRESS, msg.as_string())
    print('Sent mail to %s' % secrets.TO_ADDRESS)
    server.quit()


if __name__ == "__main__":
    main()
