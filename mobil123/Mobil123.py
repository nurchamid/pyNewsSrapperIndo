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

class Mobil123:
    def getAllBerita(self, details, page, date=datetime.strftime(datetime.today(), '%Y/%m/%d')):
        """
        Untuk mengambil seluruh url
        link pada indeks category tertentu
        date format : YYYY/mm/dd
        category : berita-otomotif, mobil-baru, review, panduan-pembeli,
        """

        print("page ", page)
        url = "https://www.mobil123.com/berita/terbaru?page_number="+str(page)
        print(url)

        # Make the request and create the response object: response
        try:
            response = requests.get(url)
        except ConnectionError:
            print("Connection Error, but it's still trying...")
            time.sleep(5)
            details = self.getAllBerita(details, page, date)
        # Extract HTML texts contained in Response object: html
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")
        indeks = soup.findAll('article', {'class':'article article--listing media push--bottom'})
        flag = True
        for post in indeks:
            link = [post.find('a', href=True)['href'], '']
            # check if there are a post with same url
            con = mysql.connector.connect(user='root', password='', host='127.0.0.1', database='news_db')
            cursor = con.cursor()
            query = "SELECT count(*) FROM article WHERE url like '"+link[0]+"'"
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            con.close()
            if(result[0] > 0):
                flag = False
                break
            else:
                detail = self.getDetailBerita(link)
                if detail:
                    if self.insertDB(detail):
                        details.append(detail)

        if flag:
            el_page = soup.find('ul', class_="pagination")
            if el_page:
                last_page = int(el_page.findAll('a')[-1]['data-page'])
                # active_page = int(el_page.find('li', class_="active").get_text(strip=True))

                if page <= last_page:
                    time.sleep(5)
                    details = self.getAllBerita(details, page+1, date)

        return 'berhasil ambil semua berita'

    def getDetailBerita(self, link):
        """
        Mengambil seluruh element dari halaman berita
        """
        time.sleep(5)
        articles = {}
        #link
        url = link[0]
        response = requests.get(url)
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")

        #extract subcategory from breadcrumb
        bc = soup.find('div', class_="article__content--header")
        if not bc:
            return False

        sub = bc.findAll('a')[0].get_text(strip=True)
        if ("foto" in sub.lower()) or  "video" in sub.lower():
            return False

        #category
        articles['category'] = 'Otomotif'
        articles['subcategory'] = sub

        #article_url
        articles['url'] = url

        #article
        article = soup.find('div', class_="article__story-more")

        #extract date
        pubdate = soup.find('div', class_="article__meta").find('span', attrs={"itemprop":"datePublished"}).get_text(strip=True)
        pubdate = pubdate.strip(' \t\n\r')
        articles['pubdate'] = datetime.strftime(datetime.strptime(pubdate, "%d %B %Y %H:%M"), "%Y-%m-%d %H:%M:%S")

        #articleid
        articles['id'] = int(soup.find('meta', attrs={"name":"ga:cns:details:news_id"})['content'])

        #extract editor
        author = soup.find('meta', attrs={"name":"ga:cns:details:author"})['content']
        articles['author'] = author

        #extract title
        title = soup.find('h1', class_="article__title push-quarter--bottom").get_text(strip=True)
        articles['title'] = title if title else ''

        #source
        articles['source'] = 'mobil123'

        #extract comments count
        articles['comments'] = 0

        #extract tags
        tags = soup.find('meta', attrs={"name":"keywords"})['content']
        articles['tags'] = tags

        #extract images
        image = soup.find('div', attrs={"itemprop":"image"}).find('img')['data-src']
        articles['images'] = image

        #hapus link sisip
        for baca in article.findAll('p'):
            if "baca juga" in baca.get_text(strip=True).lower():
                baca.decompose()

        for link in article.findAll('div'):
            link.decompose()

        for link in article.findAll('small'):
            link.decompose()

        for temu in article.findAll('p'):
            if "temukan mobil idaman dimobil123" in temu.get_text(strip=True).lower():
                temu.decompose()

        for mari in article.findAll('p'):
            if "mari bergabung bersama kami difacebookdantwitter" in mari.get_text(strip=True).lower():
                mari.decompose()


        #extract content
        detail = BeautifulSoup(article.decode_contents().replace('<br/>', ' '), "html5lib")
        content = re.sub(r'\n|\t|\b|\r','',unicodedata.normalize("NFKD",detail.get_text(strip=True)))
        articles['content'] = content
        #print('memasukkan berita id ', articles['id'])

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
