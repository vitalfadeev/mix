#!/usr/bin/env python
#
# Very basic example of using Python 3 and IMAP to iterate over emails in a
# gmail folder/label. This code is released into the public domain.
#
# This script is example code from this blog post:
# http://www.voidynullness.net/blog/2013/07/25/gmail-email-with-python-via-imap/
#
# This is an updated version of the original -- modified to work with Python 3.4.
#
import sys
import imaplib
import getpass
import email
import email.header
from email.header import decode_header
import datetime
from collections import Counter
import csv
from html.parser import HTMLParser
from unicodedata import normalize
import re
import argparse


EMAIL_ACCOUNT = "aaa@yahoo.com"
EMAIL_PASSWORD = getpass.getpass('password')

# filters
SUBJECT = "raporu"
SENDER = ""

# Use 'INBOX' to read inbox. Note that whatever folder is specified,
# after successfully running this script all emails in that folder
# will be marked as read.
EMAIL_FOLDER = "INBOX"

def last_day_of_month(any_day):
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
    return next_month - datetime.timedelta(days=next_month.day)
       
#
class MonGraph(object):
    def __init__(self):
        self.subject_regex = SUBJECT
        self.sender_regex = SENDER
        self.names = {}
        self.counts = {}
        self.sums = {}
        self.count_by_day = {}
        self.M = None # IMAP connection
        self.l = 0

    def process(self):
        # detect period - month, year
        # connect to IMAP
        # select mailbox
        # queryy message ids for month
        # for each
        #   fetch message
        #   get body
        #   parse html
        #   update counters
        # close connection
        # write result
        self.get_args()
        print("Get period... ", end="")
        (year, month, date_from, date_to) = self.get_period()
        print("period: ", date_from, "- ", date_to, ".")
        print("Connect to IMAP... ", end="")
        self.connect_to_imap()
        print("Connected.")
        print("Select mailbox... ", end="")
        self.select_mailbox(EMAIL_FOLDER)
        print("selected.")
        print("Query ids... ", end="")
        ids = self.query_ids(date_from, date_to)
        print("finished.")
        print("ids: ", ids)
        if ids:
            print("Process ids... ")
            self.process_ids(ids)
            print("Process ids finished.")
        else:
            print("No messages ")
        print("Close connection... ", end="")
        self.close_connection()
        print("closed.")
        print("Result: ")
        self.write_result(date_to)
        
    def get_period(self):
        today = datetime.datetime.today()
        
        year = today.year
        month = today.month
                
        if self.l == 0:
            date_from = datetime.date(year, month, 1)
            date_to = last_day_of_month(date_from)
        else:
            date_from = datetime.date(year, month, 1)
            
            for x in range(0, self.l):
                date_from = date_from - datetime.timedelta(days=1)
                date_from = date_from.replace(day=1)
                
            date_to = last_day_of_month(date_from)
        
        return (year, month, date_from, date_to)

    def connect_to_imap(self):
        self.M = imaplib.IMAP4_SSL('imap.mail.yahoo.com')

        try:
            rv, data = self.M.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)            
        except imaplib.IMAP4.error as e:
            print (e)
            sys.exit(1)

        if rv != 'OK':
            print("Error: cannot login")
            sys.exit(1)
        
    def select_mailbox(self, mailbox):
        # list
        try:
            rv, mailboxes = self.M.list()
            print("mailboxes: ")
            for mbox in mailboxes:
                print(mbox)
        except imaplib.IMAP4.error as e:
            print (e)
            sys.exit(1)
        
        if rv != 'OK':
            print("Error: cannot list mailboxes")
            sys.exit(1)

        # select
        try:
            rv, data = self.M.select(mailbox)            
        except imaplib.IMAP4.error as e:
            print (e)
            sys.exit(1)
            
        if rv != 'OK':
            print("Error: cannot select mailbox: ", mailbox)
            sys.exit(1)
            
    def query_ids(self, date_from, date_to):
        # rum IMAP query
        try:
            result, data = self.M.search(None, '(SINCE "{}" BEFORE "{}")'.format(
                date_from.strftime("%d-%b-%Y"), 
                date_to.strftime("%d-%b-%Y")))
        except imaplib.IMAP4.error as e:
            print (e)
            sys.exit(1)
            
        if result != 'OK':
            print("Error: cannot get messages")
            sys.exit(1)

        # get message ids
        ids = data[0] # data is a list.
        id_list = ids.split() # ids is a space separated string

        return id_list

    def process_ids(self, ids):
        for _id in ids:
            print("  Fetch header ", _id, "... ", end="")
            rawhdr = self.fetch_header(_id)
            print("fetched.")
            hdr = email.message_from_string(rawhdr)
            print("Get day from subject...", end="")
            data_date = self.get_date(hdr)
            print("  Check subject and sender ", _id, "... ", end="")
            if self.match_header(hdr, data_date):
                print("OK.")
                print("  Fetch message ", _id, "... ", end="")
                eml = self.fetch_eml(_id)
                print("fethced.")
                print("  Parse message ", _id, "... ", end="")
                msg = email.message_from_string(eml)
                body = self.get_body(msg)
                html = self.parse_body(body)
                print("parsed.")
                print("  Parse HTML ", _id, "... ", end="")
                rows = self.parse_html(html)
                print("parsed.")
                print("  update statistics ", _id, "... ", end="")
                self.update_counters(data_date.day, rows)
                print("OK.")
            else:
                print("SKIP.")
        
    def fetch_header(self, _id):
        # fetch        
        try:
            result, data = self.M.fetch(_id, '(RFC822.HEADER)')
        except imaplib.IMAP4.error as e:
            print (e)
            sys.exit(1)

        if result != 'OK':
            print("Error: cannot fetch header: ", _id)
            sys.exit(1)            
            
        return self.decode_raw(data[0][1])
        
    def decode_raw(self, raw):
        if type(raw) == str:
            return raw
        else:
            #return raw.decode('UTF-8')
            #return "".join( chr(x) for x in bytearray(data) )
            # sys.getdefaultencoding()
            return raw.decode(encoding="ascii", errors="ignore")

    def decode_header(self, s):
        decoded = decode_header(s)
        
        if type(decoded) == list and len(decoded) > 0:
            result = ""
            for dec in decoded:
                result = result + self.decode_raw(dec[0])
        else:
            result = ""
            
        return result
        
    def get_date(self, hdr):
        # "Gün sonu raporu (8/4/2019)" - day/month/year
        subject = self.decode_header(hdr['Subject'])
        op = subject.find("(")
        cl = subject.find(")")
        
        if op == -1:
            return None
        if cl == -1:
            return None
        
        ds = subject[op+1:cl]
        
        # 8/4/2019
        splited = ds.split("/")
        
        if len(splited) != 3:
            return None
            
        d = int(splited[0])
        m = int(splited[1])
        y = int(splited[2])
        
        data_date = datetime.datetime(y, m, d)
        
        return data_date
        
    def match_header(self, hdr, data_date):
        if self.subject_regex and self.decode_header(hdr['Subject']).find(self.subject_regex) == -1:
            print("skip subject:", '"', hdr['Subject'], '" ', end="")
            return False
        
        if self.sender_regex and self.decode_header(hdr['From']).find(self.sender_regex) == -1:
            print("skip sender:", '"', hdr['From'], '" ', end="")
            return False
        
        if data_date is None:
            print("not found date in subject. expect (d/m/y) ", end="")
            return False
        
        return True
        
    def fetch_eml(self, _id):
        # fetch
        try:
            result, data = self.M.fetch(_id, '(RFC822)')
        except imaplib.IMAP4.error as e:
            print (e)
            sys.exit(1)
            
        if result != 'OK':
            print("Error: cannot fetch message: ", _id)
            sys.exit(1)
            
        return self.decode_raw(data[0][1])

    def get_body(self, msg):
        # get body
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get('Content-Disposition'))

                # skip any text/plain (txt) attachments
                if ctype == 'text/plain' and 'attachment' not in cdispo:
                    body = part.get_payload(decode=True)  # decode
                    break
        else:
            body = msg.get_payload(decode=True)

        return body

    def parse_body(self, body):
        html = self.decode_raw(body)
        return html

    def parse_html(self, html):
        parser = MyHTMLParser()
        parser.feed(html)
        return parser.rows
    
    def update_counters(self, day, rows):
        for k,name,v1,v2 in rows:
            if k in self.names:
                self.names[k] = name
                self.counts[k] = self.counts[k] + v1
                self.sums[k] = self.sums[k] + v2
                self.count_by_day[k][day] = v1
            else:
                self.names[k] = name
                self.counts[k] = v1
                self.sums[k] = v2
                self.count_by_day[k] = {day:v1}

    def close_connection(self):
        self.M.logout()

    def write_result(self, date_to, csv_file=None):
        if csv_file:
            with open(csv_file, 'w', newline='') as f:
                self._to_stream(f, date_to)
        else:
            self._to_stream(sys.stdout, date_to)
            
    def _to_stream(self, stream, date_to):
        self._to_stream_by_day(stream, date_to)
        
    def _to_stream_by_month(self, stream):
        # summ by month
        writer = csv.writer(stream, dialect='excel')
        
        for k,name in self.names.items():
            writer.writerow([k, name, self.counts[k], self.sums[k]])

    def _to_stream_by_day(self, stream, date_to):
        # by day
        writer = csv.writer(stream, dialect='excel')

        # header
        csvrow = ["code", "name"]
        for x in range(1, date_to.day+1):
            csvrow.append(x)
        writer.writerow(csvrow)
        
        # data
        for k,name in self.names.items():
            csvrow = [k, name]
            for d in range(1, date_to.day+1):
                if d in self.count_by_day[k]:
                    csvrow.append(self.count_by_day[k][d])
                else:
                    csvrow.append(0)
                    
            writer.writerow(csvrow)

    def get_args(self):
        parser = argparse.ArgumentParser(description='Month graph. Fetch imap mails, group by code, sum ')
        parser.add_argument('-l', type=int, action='store', dest='l', help='Last month. N=0 - current month, N=1 - prev month')
        parser.add_argument('-f', action='store', dest='f', help='upyter support')
        
        args = parser.parse_args()
        
        if args.l is None:
            self.l = 0
        else:
            self.l = args.l
    
# HTML parser
class MyHTMLParser(HTMLParser):

   def __init__(self):
       super().__init__()
       #Initializing lists
       self.lsStartTags = list()
       self.lsEndTags = list()
       self.lsStartEndTags = list()
       self.lsComments = list()
       self.lsData = list()
       self.rows = []
       
       self.row_count = 0
       self.row = []
       self.wait_td_content = False
       self.table_count = 0
   
   #HTML Parser Methods
   def handle_starttag(self, startTag, attrs):
       if startTag.upper() == 'TABLE':
           self.table_count = self.table_count + 1
           if self.table_count == 1:
               self.row_count = 0
               self.rows = []
           
       elif startTag.upper() == 'TR':
           if self.table_count == 1:
               self.row_count = self.row_count + 1
               
               # skip column names
               if self.row_count > 1:
                   self.row = []

       elif startTag.upper() == 'TD':
           if self.table_count == 1:
               # skip column names
               if self.row_count > 1:
                   self.wait_td_content = True
           
   def handle_endtag(self, endTag):
       if self.table_count == 1:
           if endTag.upper() == 'TR':
               # skip column names
               if self.row_count > 1:
                   self.rows.append(
                        [self.row[0], 
                         self.row[1], 
                         int(self.row[2]), 
                         float(self.row[3].replace(",", "."))]) # formated
                   self.row = []

   def handle_startendtag(self,startendTag, attrs):
       pass

   def handle_comment(self,data):
       pass
       
   def handle_data(self,data):
       if self.table_count == 1:
           if self.wait_td_content:
               self.row.append(normalize('NFKD', data).strip())
               self.wait_td_content = False
               


#### tests ####
def test_eml():
        s = """X-Apparently-To: mustafa.yildirim16@yahoo.com; Mon, 08 Apr 2019 19:16:07 +0000
Return-Path: <suleymaniyecikolatacisi@gmail.com>
Received-SPF: pass (domain of gmail.com designates 209.85.128.67 as permitted sender)
X-YMailISG: DoA.vToWLDvhjb8zDDIKID4bc7RRSHt9Rme4gw.N2KXrks7w
 kdGsv1uAd9XcsA80H1Xx2SxKk.5zOMbRENjfGDvEKVm7vX_X9BWoqwa8Rcj8
 GPSnUDTgE6bAnrEjMoDyWGMn2G3NHeR9SatpJMlh9l8UNCTARf3IThvwsCVC
 YJHeJ431ijL7R3C.xzaMnO5NCFct3aXgVCSvAZ9pD1j6szhMvQJxt1Nvno_L
 xmKPcwWyNs3q9DNhSkRJLzEF_cBoEja0RagjjlOnh1EUywcxgoxy_G8g6cVy
 RctrRXLrfyrkh8LPFCBZghJKngZap_8yPvMy9lJeymUtFyx57P_JytIg9KwL
 JUxUWVRLASWZFNwnVEj7yPaSoNVRA.ncQmJOWYLiqnAsrF5HpcNRf6sPdtH0
 3HV4HJ4HsM_XvXFZYl_Z1D1B0kBiVEWGpC3_iWKFCTZn.QHyMReZnqKLlQwB
 RMeyP_6mcdIOqcI4N4TSNPtxrL4EymtjgMHmDNFF8hbdIq57y7hkX7YkvQ2s
 yZ4ZdpmqIo9fzEFoKT5CcLYcAdFJxq0ZrVuuGqMo_ijuX16LfX1EcgbltKO_
 p3S8rha1AZjZcowREOj80ACXczn8H9k6bVQTh1nxTFBNGcQcqMkn.k.Dkm0b
 .mwmvs5b3aHSFkdc.uitQbLnmJGzUkcg80VjoIQd1HlyspHIDltVvrlGVXKd
 f_qYDY2HbWIuh2mFxFecHb3oabSdS6dz1xOjscc2sXsDvWog6Y.NTthlEMag
 s0gex1.3PoX1mjb_T9ITdayuje3DbVTPFO1OHcTC62hCbDs4S7QtgUbyWF5y
 7Q63JQPhed2pZlrskVG1ok9O.fwVkELeuwiNko1zDPMZGRnhXmREyGryGMr3
 gdbInTJFPb0Nm_3r18uSOuqk4KGtfFo.IJJnFEpR.OTVnUFNVB6Q4WW7h.vT
 H3V3ALVnM4P39GPzcn0CsUSb6ac7qHL7Iw8BIJBKaSRJCutBTDiTttUAJox5
 _.iGg7.NgR5_0fLKod6WjjS2vOkwH5UXNViELTwGfjKEkWOmUgxsG1j.JG1A
 TgjDcXERC8WBnbB9EDe1v8qrOj_oPMUmIzuCXQ--
X-Originating-IP: [209.85.128.67]
Authentication-Results: mta4162.mail.bf1.yahoo.com 
 header.i=@gmail.com; header.s=20161025; dkim=pass (ok)
Received: from 127.0.0.1  (EHLO mail-wm1-f67.google.com) (209.85.128.67)
  by mta4162.mail.bf1.yahoo.com with SMTPS; Mon, 08 Apr 2019 19:16:07 +0000
Received: by mail-wm1-f67.google.com with SMTP id v14so541286wmf.2
        for <mustafa.yildirim16@yahoo.com>; Mon, 08 Apr 2019 12:16:07 -0700 (PDT)
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=gmail.com; s=20161025;
        h=message-id:date:mime-version:from:to:subject
         :content-transfer-encoding;
        bh=llE1OcbLA24j5nu42mmJD/1tEcvTxtEM2m/DxNhn7DY=;
        b=aFV09kY3D3NNHJjkH9+ksD5UjHQR39Uymgkkzx1afieoRnqWeq9zoaVq3BGTOtrBUL
         7cre8XLYZDkNWsmdewHbrPonQJ/SQzG6EbwkO+tUKXnzG2rVaP72CDPakwPK7cePa+9M
         X41ofxbjXy4mOW1hsete+JJndm9dYX4oeIlImCkZ0tydI/5cOFhTmMnBh1XovzhhiEFO
         J69rznSI3a1AMaXVItJfDgbma08QkGl6AaPBw6grVkAqnzjFUzFm/lA4r6OLUSLRA/dS
         uS6ENwnCL/wlpScOqdywKkdYAo826TbFd0TalMM6fotxarZVaxh2ipNOlalNgs3rEUtq
         EV+Q==
X-Google-DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=1e100.net; s=20161025;
        h=x-gm-message-state:message-id:date:mime-version:from:to:subject
         :content-transfer-encoding;
        bh=llE1OcbLA24j5nu42mmJD/1tEcvTxtEM2m/DxNhn7DY=;
        b=o8ytUlK1XOxMKAUIup+K1hYv3WqoCPmsTGscM7pHwRn3Q5xit4MuNJgKxf8rebsRGP
         bVPMfNYCOkuJfxyK7KiP6SN6ueOcrj6FFErH5HnuU8fl+f26EJs81vjem8VEFhXVsyqz
         s5umSoSLMkpbzU7gMjHf11Xebv9lI1JhHmMB6lTZC7XVWBVVRpIn9iEDFTe8fBPtPE9X
         qrDU7wKPVpI0yYqY/L+C3YZCxx0nYm4g0hCEQE8ZQFCjwzramd4Pg8ZgR+EgSYHe7i8i
         63ygARDYcacbWkxiTBSUsCfxOD5uvQxBv59hjAaL1yRczmB+zHDXS/1BkLsmQJhmul45
         9cvA==
X-Gm-Message-State: APjAAAUiEMDBuB/29LeucMs9oLXmh4abxNO0G1aCpr5euuPPNkwEPLdv
    C3YdNm6Lq/yER6K14pokZ21uZ2skw8Y=
X-Google-Smtp-Source: APXvYqwEeVNXZJLDu/ecSuyITIjcV2ac5EtClPk/63d/1l8W8mmp60JmiwoYGQjOP7qR05i1gNmE/w==
X-Received: by 2002:a1c:ef08:: with SMTP id n8mr13048764wmh.85.1554750966724;
        Mon, 08 Apr 2019 12:16:06 -0700 (PDT)
Return-Path: <suleymaniyecikolatacisi@gmail.com>
Received: from POS-Bilgisayar ([85.96.239.88])
        by smtp.gmail.com with ESMTPSA id f11sm35918434wrm.30.2019.04.08.12.16.05
        (version=TLS1 cipher=ECDHE-RSA-AES128-SHA bits=128/128);
        Mon, 08 Apr 2019 12:16:06 -0700 (PDT)
Message-ID: <5cab9df6.1c69fb81.7ea85.3883@mx.google.com>
Date: Mon, 08 Apr 2019 12:16:06 -0700 (PDT)
X-Google-Original-Date: 8 Apr 2019 22:16:09 +0300
MIME-Version: 1.0
From: suleymaniyecikolatacisi@gmail.com
To: sytmehmet@gmail.com, seyfettinsayar@gmail.com,
 mustafa.yildirim16@yahoo.com, umranasan@gmail.com
Subject: =?utf-8?B?R8O8biBzb251IHJhcG9ydSAoOC80LzIwMTkp?=
Content-Type: text/html; charset=utf-8
Content-Transfer-Encoding: base64
Content-Length: 7360

IDx0YWJsZSBzdHlsZT0nd2lkdGg6NzAwcHg7IGZvbnQtZmFtaWx5OkNhbGlicmk7Jz48
dHIgc3R5bGU9J2ZvbnQtc2l6ZToxNnB4O2ZvbnQtd2VpZ2h0OjcwMDsnPiAgPHRkIHN0
eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNrO3dpZHRoOjEwMHB4Oyc+Jm5ic3A7S29k
dTwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazt3aWR0aDo0MDBw
eDsnPiZuYnNwO8OccsO8bi9IaXptZXQgQWTEsTwvdGQ+ICAgPHRkIHN0eWxlPSdib3Jk
ZXI6c29saWQgMXB4IGJsYWNrO3dpZHRoOjEwMHB4Oyc+Jm5ic3A7TWlrdGFyPC90ZD4g
IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazt3aWR0aDoxMDBweDsnPiZu
YnNwO1R1dGFyPC90ZD4gPC90cj4gIDx0cj48dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAx
cHggYmxhY2s7Jz4mbmJzcDtTMDAwMDE8L3RkPiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xp
ZCAxcHggYmxhY2s7Jz4mbmJzcDtCRVpNQVJBPC90ZD4gPHRkIHN0eWxlPSdib3JkZXI6
c29saWQgMXB4IGJsYWNrOyc+Jm5ic3A7MTY2PC90ZD4gIDx0ZCBzdHlsZT0nYm9yZGVy
OnNvbGlkIDFweCBibGFjazsnPiZuYnNwOzI5MDU8L3RkPjwvdHI+ICA8dHI+PHRkIHN0
eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNrOyc+Jm5ic3A7UzAwMDAyPC90ZD4gPHRk
IHN0eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNrOyc+Jm5ic3A7w4dBWTwvdGQ+IDx0
ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwOzE5MzwvdGQ+ICA8
dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDs2NzUsNTwvdGQ+
PC90cj4gIDx0cj48dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJz
cDtTMDAwMDM8L3RkPiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4m
bmJzcDtUw5xSSyBLQUhWRVPEsDwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFw
eCBibGFjazsnPiZuYnNwOzUwPC90ZD4gIDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFw
eCBibGFjazsnPiZuYnNwOzQ3NTwvdGQ+PC90cj4gIDx0cj48dGQgc3R5bGU9J2JvcmRl
cjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDtTMDAwMDQ8L3RkPiA8dGQgc3R5bGU9J2Jv
cmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDtTSUNBSyDDh8SwS09MQVRBPC90ZD4g
PHRkIHN0eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNrOyc+Jm5ic3A7MTM8L3RkPiAg
PHRkIHN0eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNrOyc+Jm5ic3A7MTQzPC90ZD48
L3RyPiAgPHRyPjx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNw
O1MwMDAwNTwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZu
YnNwO0jDnFJSRU08L3RkPiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7
Jz4mbmJzcDszPC90ZD4gIDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsn
PiZuYnNwOzQ1PC90ZD48L3RyPiAgPHRyPjx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFw
eCBibGFjazsnPiZuYnNwO1MwMDAwNjwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlk
IDFweCBibGFjazsnPiZuYnNwO0TEsEJFSyBLQUhWRVPEsDwvdGQ+IDx0ZCBzdHlsZT0n
Ym9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwOzI4PC90ZD4gIDx0ZCBzdHlsZT0n
Ym9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwOzMwODwvdGQ+PC90cj4gIDx0cj48
dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDtTMDAwMDc8L3Rk
PiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDtCRVJFRsWe
QU48L3RkPiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDs2
MDwvdGQ+ICA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDsx
MTcwPC90ZD48L3RyPiAgPHRyPjx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFj
azsnPiZuYnNwO1MwMDAwODwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBi
bGFjazsnPiZuYnNwO09TTUFOTEkgw4dBWUk8L3RkPiA8dGQgc3R5bGU9J2JvcmRlcjpz
b2xpZCAxcHggYmxhY2s7Jz4mbmJzcDsxPC90ZD4gIDx0ZCBzdHlsZT0nYm9yZGVyOnNv
bGlkIDFweCBibGFjazsnPiZuYnNwOzEzPC90ZD48L3RyPiAgPHRyPjx0ZCBzdHlsZT0n
Ym9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwO1MwMDAwOTwvdGQ+IDx0ZCBzdHls
ZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwO0suIFNJQ0FLIMOHxLBLT0xB
VEE8L3RkPiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDs0
PC90ZD4gIDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwOzUy
PC90ZD48L3RyPiAgPHRyPjx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsn
PiZuYnNwO1MwMDAxMDwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFj
azsnPiZuYnNwO09TTUFOTEkgxZ5FUkJFVMSwPC90ZD4gPHRkIHN0eWxlPSdib3JkZXI6
c29saWQgMXB4IGJsYWNrOyc+Jm5ic3A7ODwvdGQ+ICA8dGQgc3R5bGU9J2JvcmRlcjpz
b2xpZCAxcHggYmxhY2s7Jz4mbmJzcDs4MDwvdGQ+PC90cj4gIDx0cj48dGQgc3R5bGU9
J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDtTMDAwMTI8L3RkPiA8dGQgc3R5
bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDtLQVJJxZ5JSyDDh8SwS09M
QVRBPC90ZD4gPHRkIHN0eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNrOyc+Jm5ic3A7
Mjc5MzwvdGQ+ICA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJz
cDs0NDYsODg8L3RkPjwvdHI+ICA8dHI+PHRkIHN0eWxlPSdib3JkZXI6c29saWQgMXB4
IGJsYWNrOyc+Jm5ic3A7UzAwMDEzPC90ZD4gPHRkIHN0eWxlPSdib3JkZXI6c29saWQg
MXB4IGJsYWNrOyc+Jm5ic3A7RMSwQkVLIEtBSFZFU8SwIFBBS0VUPC90ZD4gPHRkIHN0
eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNrOyc+Jm5ic3A7MzwvdGQ+ICA8dGQgc3R5
bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDs0NTwvdGQ+PC90cj4gIDx0
cj48dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDtTMDAwMTc8
L3RkPiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDtUT1Ag
RE9ORFVSTUE8L3RkPiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4m
bmJzcDszPC90ZD4gIDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZu
YnNwOzEyPC90ZD48L3RyPiAgPHRyPjx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBi
bGFjazsnPiZuYnNwO1MwMDAyMjwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFw
eCBibGFjazsnPiZuYnNwO8OHxLBLT0xBVEFMSSBIw5xSUkVNPC90ZD4gPHRkIHN0eWxl
PSdib3JkZXI6c29saWQgMXB4IGJsYWNrOyc+Jm5ic3A7MTA8L3RkPiAgPHRkIHN0eWxl
PSdib3JkZXI6c29saWQgMXB4IGJsYWNrOyc+Jm5ic3A7MTgwPC90ZD48L3RyPiAgPHRy
Pjx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwO1MwMDAyMzwv
dGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwO0RSQUpF
IDEwIFRMPC90ZD4gPHRkIHN0eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNrOyc+Jm5i
c3A7MzwvdGQ+ICA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJz
cDszMDwvdGQ+PC90cj4gIDx0cj48dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxh
Y2s7Jz4mbmJzcDtTMDAwMjU8L3RkPiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHgg
YmxhY2s7Jz4mbmJzcDtEUkFKRSAyMCBUTDwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNv
bGlkIDFweCBibGFjazsnPiZuYnNwOzU8L3RkPiAgPHRkIHN0eWxlPSdib3JkZXI6c29s
aWQgMXB4IGJsYWNrOyc+Jm5ic3A7MTAwPC90ZD48L3RyPiAgPHRyPjx0ZCBzdHlsZT0n
Ym9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwO1MwMDAyNjwvdGQ+IDx0ZCBzdHls
ZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwO0JFWk1BUkEgUEFLRVQ8L3Rk
PiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDsyPC90ZD4g
IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNwOzM3PC90ZD48
L3RyPiAgPHRyPjx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZuYnNw
O1MwMDAzMDwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFjazsnPiZu
YnNwO0RPTi5CRVpNQVJBPC90ZD4gPHRkIHN0eWxlPSdib3JkZXI6c29saWQgMXB4IGJs
YWNrOyc+Jm5ic3A7MTA8L3RkPiAgPHRkIHN0eWxlPSdib3JkZXI6c29saWQgMXB4IGJs
YWNrOyc+Jm5ic3A7MjE1PC90ZD48L3RyPiAgPHRyPjx0ZCBzdHlsZT0nYm9yZGVyOnNv
bGlkIDFweCBibGFjazsnPiZuYnNwO3MwMDAzMTwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVy
OnNvbGlkIDFweCBibGFjazsnPiZuYnNwO0RPTi5CRVJFRsWeQU48L3RkPiA8dGQgc3R5
bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDsxMTwvdGQ+ICA8dGQgc3R5
bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDsyNTgsNTwvdGQ+PC90cj4g
IDx0cj48dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDtTMDAw
MzQ8L3RkPiA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxhY2s7Jz4mbmJzcDtL
QVJJxZ5JSyBEUkFKRTwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlkIDFweCBibGFj
azsnPiZuYnNwOzc2NzwvdGQ+ICA8dGQgc3R5bGU9J2JvcmRlcjpzb2xpZCAxcHggYmxh
Y2s7Jz4mbmJzcDs5MiwwNDwvdGQ+PC90cj4gIDwvdGFibGU+IDxiciAvPlNhdMSxxZ8g
VG9wbGFtIDogNzI4Miw5Mjxici8+IDx0YWJsZSBzdHlsZT0nd2lkdGg6NzAwcHg7IGZv
bnQtZmFtaWx5OkNhbGlicmk7Jz48dHIgc3R5bGU9J2ZvbnQtc2l6ZToxNnB4O2ZvbnQt
d2VpZ2h0OjcwMDsnPiAgPHRkIHN0eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNrO3dp
ZHRoOjEwMHB4Oyc+Jm5ic3A7S29kdTwvdGQ+IDx0ZCBzdHlsZT0nYm9yZGVyOnNvbGlk
IDFweCBibGFjazt3aWR0aDo0MDBweDsnPiZuYnNwO0NhcmkgQWTEsTwvdGQ+ICAgPHRk
IHN0eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNrO3dpZHRoOjEwMHB4Oyc+Jm5ic3A7
R2VsaXIvR2lkZXI8L3RkPiAgPHRkIHN0eWxlPSdib3JkZXI6c29saWQgMXB4IGJsYWNr
O3dpZHRoOjEwMHB4Oyc+Jm5ic3A7VHV0YXI8L3RkPiA8L3RyPiAgPC90YWJsZT4gPGJy
IC8+PGJyIC8+PGJyLz5Ub3BsYW0gR2VsaXIgOiA3MjgyLDkyPGJyLz5Ub3BsYW0gR2lk
ZXIgOiAwPGJyLz5Ub3BsYW0gTmV0IDogNzI4Miw5Mg==
"""        
        return s
        



#### main ####
def run():
    mg = MonGraph()
    mg.process()

# main
run()

