import requests
import time
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

class Viva:
    def getLoadMorePost(self, links, driver, date):
        """
        Mengambil semua post dengan pagination berupa 'load more'
        dibatasi sesuai tanggal yang telah ditentukan
        """
        soup = BeautifulSoup(driver.page_source, 'html5lib')
        tes = soup.find('ul', attrs={'id': 'load_terbaru_content'})
        lel = re.sub(r'\n|\t|\b|\r|\s','',tes.findAll('script', attrs={"type":"text/javascript"})[-1].text).strip(' \t\n\r')
        start = len(lel[lel.find('window.last_publish_date'):lel.find('window.last_publish_date')+27])+lel.find('window.last_publish_date')
        end = start + 19
        date_max = datetime.strftime(datetime.strptime(lel[start:end], "%Y-%m-%d %H:%M:%S"), '%Y-%m-%d')
        batas_el = tes.findAll('li', class_="content_center")
        if batas_el:
            li = batas_el[-1].findAllNext('li')
        else:
            li = tes.findAll('li')

        for post in li:
            if post.find('div', class_="date") :
                date_post = post.find('div', class_="date").text.split(' | ')[0]
                date_post = datetime.strftime(datetime.strptime(date_post, "%d %B %Y"), '%Y-%m-%d')
                if date_post == date:
                    link = [post.find('a', class_="title-content", href=True)['href'], ""]
                    print('masukan link ', link[0])
                    links.append(link)

                if date_max == date:
                    load_more = driver.find_element_by_id('load_terbaru_btn')
                    load_more.click()
                    time.sleep(10)
                    links = self.getLoadMorePost(links, driver, date)

        return links

    def getIndeksLink(self, links, date=datetime.strftime(datetime.today(), '%Y-%m-%d')):
        """
        Untuk mengambil seluruh url okezone
        link pada indeks category tertentu
        date format : YYYY-mm-dd
        """
        url = 'https://www.viva.co.id/indeks/'

        #scarp with selenium
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')  # Last I checked this was necessary.
        options.add_argument('--disable-extensions')

        driver = webdriver.Chrome("../chromedriver.exe", chrome_options=options)
        try:
            driver.get(url)
        except ConnectionError:
            print("Connection Error, but it's still trying...")
            time.sleep(10)

        links = self.getLoadMorePost(links, driver, date)

        return links

    def getDetailBerita(self, links):
        """
        Mengambil seluruh element dari halaman berita
        """
        all_articles = []
        for link in links:
            time.sleep(10)
            articles = {}
            #link
            url = link[0]
            response = requests.get(url)
            html = response.text
            # Create a BeautifulSoup object from the HTML: soup
            soup = BeautifulSoup(html, "html5lib")

            #extract scrip json ld
            scripts = soup.findAll('script', attrs={'type':'application/ld+json'})[-1].text
            scripts = json.loads(scripts)

            #extract subcategory from breadcrumb
            bc = soup.find('div', class_="leading-breadcrumb")
            if not bc:
                continue

            cat = bc.findAll('a')[-2].text
            sub = bc.findAll('a')[-1].text
            if ("foto" in sub.lower()) or  "video" in sub.lower():
                continue

            #category
            articles['category'] = cat
            articles['subcategory'] = sub

            articles['id'] = int(scripts['mainEntityOfPage']['@id'])

            articles['url'] = url

            article = soup.find('section', attrs={'id':'viva-content'})

            #extract date
            pubdate = scripts['datePublished']
            pubdate = pubdate[0:19].strip(' \t\n\r')
            articles['pubdate'] = datetime.strftime(datetime.strptime(pubdate, "%Y-%m-%dT%H:%M:%S"), '%Y-%m-%d %H:%M:%S')

            #extract author
            articles['author'] = scripts['author']['name']

            #extract title
            articles['title'] = article.find('div', class_="leading-title").find('h1').text

            #source
            articles['source'] = 'viva'

            #extract comments count
            articles['comments'] = int(article.find('comment-count').text.strip(' \t\n\r'))

            #extract tags
            tags = soup.find('meta', attrs={'name':'news_keywords'})['content']
            articles['tags'] = tags

            #extract images
            articles['images'] = soup.find("meta", attrs={'property':'og:image'})['content']

            #extract detail
            detail = article.find('div', attrs={"class":"article-detail article-detail-v2"})

            #hapus video sisip
            for div in detail.findAll('div'):
                div.decompose()

            #hapus all script
            for script in detail.findAll('script'):
                script.decompose()

            #extract content
            detail = BeautifulSoup(detail.decode_contents().replace('<br/>', ' '), "html5lib")
            content = re.sub(r'\n|\t|\b|\r','',detail.text)
            articles['content'] = content
            print('memasukkan berita id ', articles['id'])
            all_articles.append(articles)

        return all_articles