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

class Housingestate:
    def getAllBerita(self, details, date=datetime.strftime(datetime.today(), '%Y/%m/%d')):
        """
        Untuk mengambil seluruh url carreview
        link pada indeks category tertentu
        category = all
        date = Y/m/d
        """

        # print("page ", page)
        date2 = datetime.strptime(date, '%Y/%m/%d')
        url = "http://housingestate.id/wp-admin/admin-ajax.php?action=alm_query_posts&order=DESC&orderby=date&month="+str(date2.date().month)+"&year="+str(date2.date().year)+"&day="+str(date2.date().day)
        print(url)
        # Make the request and create the response object: response
        try:
            response = requests.get(url)
        except ConnectionError:
            print("Connection Error, but it's still trying...")
            time.sleep(10)
            details = self.getAllBerita(details, page, date)
        # Extract HTML texts contained in Response object: html
        json_res = json.loads(response.text)
        # Create a BeautifulSoup object from the HTML: soup
        if json_res['html']:
            soup = BeautifulSoup(json_res['html'], "html5lib")
            indeks = soup.findAll('div', class_="item-box")
            for post in indeks:
                link = [post.find('a', href=True)['href'], ""]
                #check if there are a post with same url
                # con = mysql.connector.connect(user='root', password='', host='127.0.0.1', database='news_db')
                # cursor = con.cursor()
                # query = "SELECT count(*) FROM article WHERE url like '"+link[0]+"'"
                # cursor.execute(query)
                # result = cursor.fetchone()
                # cursor.close()
                # con.close()
                #comment sementara
                # if(result[0] > 0):
                #     flag = False
                #     break
                # else:
                detail = self.getDetailBerita(link)
                if detail:
                    if self.insertDB(detail):
                        # print("Insert berita ", articles['title'])
                        details.append(detail)
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
        html2 = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html2, "html5lib")
        print(url)
        #category
        articles['category'] = 'Properti'
        sb = soup.find('meta', {'property':'article:section'})
        articles['subcategory'] = sb['content'] if sb else ''

        articles['url'] = url

        article = soup.find('div', {'id':'post-content'})

        #extract date
        pubdate = soup.find('meta', {'property':'article:published_time'})
        pubdate = pubdate['content'] if pubdate else '1970-01-01T01:01:01+00:00'
        pubdate = pubdate[0:19].strip(' \t\n\r')
        articles['pubdate'] = datetime.strftime(datetime.strptime(pubdate, "%Y-%m-%dT%H:%M:%S"), '%Y-%m-%d %H:%M:%S')

        id = soup.find('div', {'id':'ajax-load-more'})
        articles['id'] = int(id['data-post-id']) if id else int(datetime.strptime(pubdate, "%Y-%m-%dT%H:%M:%S").timestamp()) + len(url)

        #extract author
        author = article.find('span', {'class':'author'})
        articles['author'] = author.get_text(strip=True) if author else ''

        #extract title
        title = soup.find('meta', {'property':'og:title'})
        articles['title'] = title['content'] if title else ''

        #source
        articles['source'] = 'housingestate'

        #extract comments count
        articles['comments'] = 0

        #extract tags
        tags = soup.find('meta', {'property':'article:tag'})
        articles['tags'] = tags['content'] if tags else ''

        #extract images
        images = soup.find("meta", attrs={'property':'og:image'})
        articles['images'] = images['content'] if images else ''

        #extract detail
        detail = article.find('div', attrs={'class':'content-txt'})

        #hapus video sisip
        if detail.findAll('div'):
            for div in detail.findAll('div'):
                if div.find('script'):
                    div.decompose()

        #hapus all script
        for script in detail.findAll('script'):
            script.decompose()

        #hapus all noscript
        for ns in detail.findAll('noscript'):
            ns.decompose()

        #hapus linksisip
        for ls in detail.findAll('p'):
            if ls.find('strong'):
                if 'baca' in ls.find('strong').get_text(strip=True).lower():
                    ls.decompose()

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
