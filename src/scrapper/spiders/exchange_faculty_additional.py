import getpass
import hashlib
import re
import scrapy
from datetime import datetime
from scrapy.http import Request, FormRequest
import urllib.parse
from configparser import ConfigParser, ExtendedInterpolation
import json
from datetime import time
import os

from scrapper.settings import CONFIG, PASSWORD, USERNAME

from ..database.Database import Database
from ..items import  ExchangeFaculty, ExchangeFacultyCourse
import pandas as pd

class ExchangeFacultyAditional(scrapy.Spider):
    name = "exchange_faculty_additional"

    allowed_domains = ['sigarra.up.pt']
    login_page_base = 'https://sigarra.up.pt/feup/pt/mob_val_geral.autentica'
    days = {'Segunda-feira': 0, 'Terça-feira': 1, 'Quarta-feira': 2,
            'Quinta-feira': 3, 'Sexta-feira': 4, 'Sábado': 5}

    def __init__(self, password=None, category=None, *args, **kwargs):
        super(ExchangeFacultyAditional, self).__init__(*args, **kwargs)
        self.open_config()
        self.user = USERNAME
        self.password = PASSWORD
        self.professor_name_pattern = "\d+\s-\s[A-zÀ-ú](\s[A-zÀ-ú])*"
        self.inserted_teacher_ids = set()

    def open_config(self):
        """
        Reads and saves the configuration file. 
        """
        config_file = "./config.ini"
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        self.config.read(config_file)

    def format_login_url(self):
        return '{}?{}'.format(self.login_page_base, urllib.parse.urlencode({
            'pv_login': self.user,
            'pv_password': self.password
        }))

    def start_requests(self):
        """This function is called before crawling starts."""

        if self.password is None:
            self.password = getpass.getpass(prompt='Password: ', stream=None)

        yield Request(url=self.format_login_url(), callback=self.check_login_response)

    def check_login_response(self, response):
        """Check the response returned by a login request to see if we are
        successfully logged in. Since we used the mobile login API endpoint,
        we can just check the status code.
        """
    
        if response.status == 200:
            response_body = json.loads(response.body)
            if response_body['authenticated']:
                print('Login successful.', flush=True)
                sql = """
                    SELECT faculty.acronym
                    FROM faculty
                """
                db = Database()
                db.cursor.execute(sql)
                db.connection.close()
                self.getMapInfo()
            else:
                message = 'Login failed. SIGARRA\'s response: error type "{}";\nerror message "{}"'.format(
                    response_body.erro, response_body.erro_msg)
                print(message, flush=True)
                self.log(message)
        else:
            print('Login Failed. HTTP Error {}'.format(
                response.status), flush=True)
            self.log('Login Failed. HTTP Error {}'.format(response.status))
    def func(self, error):
        print("An error has occurred: ", error)
        return

    def getMapInfo(self):
        """
        Get the map information from the response.
        """
        sql = """
            select name from exchange_faculty
        """
        db = Database()
        db.cursor.execute(sql)
        faculties = db.cursor.fetchall()


        os.chdir("scrapper/google-maps-scraper")
        file_path = "example-queries.txt"
        binary_path = "google-maps-scraper"

        os.system("npx playwright install-deps")

        os.system("apt-get update && apt-get install -y libnss3 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libxkbcommon0 libasound2 libatspi2.0-0")
        
        with open(file_path, 'w') as f:
            for faculty in faculties:
                f.write(f"{faculty[0]}\n")
        command = f"./{binary_path} -input {file_path} -results unis.csv -exit-on-inactivity 3m"
        os.system(command)

        if os.path.exists("unis.csv"):
            print("File unis.csv exists")

            df = pd.read_csv("unis.csv")

            df = df.loc[df.groupby('input_id')['review_count'].idxmax()]

            index =0
            for _, row in df.iterrows():

                sql = """
                    UPDATE exchange_faculty
                    SET latitude = ?, longitude = ?, address = ?, thumbnail = ?, website = ?
                    WHERE name = ?
                """
            

                print(f"latitude: {row['latitude']}")
                print(f"longitude: {row['longitude']}")
                print(f"address: {row['address']}") 
                print(f"thumbnail: {row['thumbnail']}")
                print(f"website: {row['website']}")
                print(f"faculties[index]: {faculties[index]}")

                db.cursor.execute(sql, (
                    row['latitude'],  # latitude
                    row['longitude'],  # longitude
                    row['address'],   # address
                    row['thumbnail'],  # thumbnail
                    row['website'],   # website
                    faculties[index][0]      # name
                ))
                index += 1
                
            else:
                print("File unis.csv does not exist")

            
            
    