import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import locale
locale.setlocale(locale.LC_ALL, 'ID')
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import html
import json
import time
from requests.exceptions import ConnectionError
import unicodedata
import mysql.connector

class Idntimes:
    def getAllBerita(self, details, cat_link, page, date=datetime.strftime(datetime.today(), '%Y-%m-%d')):
        """
        Untuk mengambil seluruh url
        link pada indeks category tertentu
        date format : YYYY-mm-dd
        """

        print("page ", page)
        url = "https://www.idntimes.com/ajax/index?category="+cat_link+"&type=all&page="+str(page)+"&date="+date
        print(url)
        # Make the request and create the res
        try:
            response = requests.get(url)
        except ConnectionError:
            print("Connection Error, but it's still trying...")
            time.sleep(10)
            details = self.getAllBerita(details, cat_link, page, date)
        # Extract HTML texts contained in Response object: html
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")

        indeks = soup.findAll('div', class_="box-latest box-list ")
        if indeks:
            for post in indeks:
                link = [post.find('a', href=True)['href'], cat_link]
                detail = self.getDetailBerita(link)
                if detail:
                    if self.insertDB(detail):
                        details.append(detail)
            time.sleep(10)
            details = self.getAllBerita(details, cat_link, page+1, date)

        return 'berhasil ambil semua berita'

    def getDetailBerita(self, link):
        """
        Mengambil seluruh element dari halaman berita
        """
        time.sleep(10)
        articles = {}
        #link
        url = link[0]
        print(url)
        try:
            response = requests.get(url)
        except ConnectionError:
            print("Connection Error, but it's still trying...")
            time.sleep(20)
            details = self.getDetailBerita(link)
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")

        #extract scrip json ld
        scripts_all = soup.findAll('script', attrs={'type':'application/ld+json'})
        scripts = ''
        scripts2 = ''
        if len(scripts_all) >= 2:
            scripts = re.sub(r'\n|\t|\b|\r','',unicodedata.normalize("NFKD",scripts_all[-2].get_text(strip=True)))
            scripts = json.loads(scripts)
            scripts2 = re.sub(r'\n|\t|\b|\r','',unicodedata.normalize("NFKD",scripts_all[-1].get_text(strip=True)))
            scripts2 = json.loads(scripts2)
        else:
            return False

        #category
        articles['category'] = scripts2['itemListElement'][0]['item']['name']
        articles['subcategory'] = scripts2['itemListElement'][1]['item']['name']

        articles['url'] = url

        article = soup.find('section', class_="content-post clearfix")

        #extract date
        pubdate = soup.find('time', class_="date")
        pubdate = pubdate['datetime'] if pubdate else '1970-01-01'
        pubdate = pubdate.strip(' \t\n\r')
        articles['pubdate'] = datetime.strftime(datetime.strptime(pubdate, "%Y-%m-%d"), '%Y-%m-%d %H:%M:%S')

        articles['id'] = int(datetime.strptime(pubdate, "%Y-%m-%d").timestamp()) + len(url)

        #extract author
        articles['author'] = scripts['author']['name']

        #extract title
        articles['title'] = scripts['headline']

        #source
        articles['source'] = 'idntimes'

        #extract comments count
        # articles['comments'] = int(soup.find('span', class_="commentWidget-total").find('b').get_text(strip=True).strip(' \t\n\r'))
        articles['comments'] = 0

        #extract tags
        tags = article.find('div', class_="content-post-topic")
        articles['tags'] = ','.join([x.get_text(strip=True) for x in tags.findAll('a')]) if tags else ''

        #extract images
        articles['images'] = scripts['image']['url']

        #extract detail
        detail = article.find('article', attrs={'id':'article-content'})

        #hapus div
        if detail.findAll('div'):
            for div in detail.findAll('div'):
                if div.find('script'):
                    div.decompose()

        #hapus link sisip
        if detail.findAll('strong'):
            for b in detail.findAll('strong'):
                if ("baca juga" in b.get_text(strip=True).lower()):
                    b.decompose()

        #extract content
        detail = BeautifulSoup(detail.decode_contents().replace('<br/>', ' '), "html5lib")
        content = re.sub(r'\n|\t|\b|\r','',unicodedata.normalize("NFKD",detail.get_text(strip=True)))
        articles['content'] = content
        print('memasukkan berita id ', articles['id'])

        return articles

    def insertDB(self, articles):
        """
        Untuk memasukkan berita ke DB
        """
        con = mysql.connector.connect(user='root', password='', host='127.0.0.1', database='news_db')
        print("Insert berita ", articles['title'])
        cursor = con.cursor()
        query = "SELECT count(*) FROM article WHERE url like '"+articles['url']+"'"
        cursor.execute(query)
        result = cursor.fetchone()
        if result[0] <= 0:
            add_article = ("INSERT INTO article (post_id, author, pubdate, category, subcategory, content, comments, images, title, tags, url, source) VALUES (%(id)s, %(author)s, %(pubdate)s, %(category)s, %(subcategory)s, %(content)s, %(comments)s, %(images)s, %(title)s, %(tags)s, %(url)s, %(source)s)")
            # Insert article
            cursor.execute(add_article, articles)
            con.commit()
            print('masuk')
            cursor.close()
            con.close()
            return True
        else:
            cursor.close()
            print('salah2')
            con.close()
            return False
