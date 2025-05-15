
import scrapy
import pandas as pd
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from configparser import ConfigParser, ExtendedInterpolation
import os
from scrapper.utils.DateUtils import get_scrapper_year
from scrapper.settings import CONFIG, YEAR
from ..items import Course
from ..database.Database import Database
from dotenv import dotenv_values

class CourseSpider(scrapy.Spider):
    name = "courses"
    # allowed_domains = ['sigarra.up.pt']
    # login_page = 'https://sigarra.up.pt/feup/pt/'

    bachelors_url = "https://www.up.pt/portal/en/study/bachelors-and-integrated-masters-degrees/courses/"
    masters_url = "https://www.up.pt/portal/en/study/masters-degrees/courses/"
    doctors_url = "https://www.up.pt/portal/en/study/doctorates/courses/"
    start_urls = [bachelors_url, masters_url, doctors_url]
    
    # def open_config(self):
    #     """
    #     Reads and saves the configuration file. 
    #     """
    #     config_file = "./config.ini"
    #     self.config = ConfigParser(interpolation=ExtendedInterpolation())
    #     self.config.read(config_file) 

    def get_year(self):
        year = CONFIG[YEAR]
        if not year:
            return get_scrapper_year()
        return int(year)   
    

    # Get's the first letter of the course type and set it to upper case. 
    
    def parse(self, response):
        # self.open_config()

        hrefs = response.xpath('//*[@id="courseListComponent"]/div/dl/dd/ul/li/a/@href').extract()  
        for faculty_html in hrefs: 
            params = faculty_html.split("/")
            sql = """
            select id from faculty where acronym = ? 
            """
            db = Database()
        
            db.execute(sql, (params[-3],))
            result = db.cursor.fetchone()
   
            url = f"https://sigarra.up.pt/{params[-3]}/pt/cur_geral.cur_view?pv_ano_lectivo={self.get_year()}&pv_curso_id={params[-2]}"
            yield scrapy.Request(url= url, callback=self.get_course, meta={'faculty_acronym': result[0]})
    
    def get_acronym(self, response):
        acronym = response.xpath('//td[text()="Sigla: "]/following-sibling::td/text()').get()
        if not acronym:
            acronym = response.xpath('//td[text()="Acronym: "]/following-sibling::td/text()').get()
        return acronym
    def normalize_course_name(self, name: str) -> str:
        name = str(name)
        if " em " in name:
            return name.split(" em ", 1)[1].strip()
        return name

    def get_course_stats_from_xlsx(self, course_name, course_type):
        files = os.listdir(".")
        print(files)
        
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # directory of the spider script

        xlsx_path = os.path.join(BASE_DIR, "course_stat_spread", "Infocursos_2024.xlsx")
        all_sheets = pd.read_excel(xlsx_path, sheet_name=None, skiprows=4)
        
        result = {}
        #normalize course_name if contains word em get starting in word after else complete
        # course_name = course_name.split(" ")[0] + " " + course_name.split(" ")[1]
        course_name = self.normalize_course_name(course_name)
        print(f"Normalized course name: {course_name}")

        for sheet_name, df in all_sheets.items():
            if "CodigoEstabelecimento" in df.columns:
                df_filtered = df[
                    (df["CodigoEstabelecimento"] == 1100) &
                    (df["NomeCurso"]== course_name) &
                    (df["Grau"].str.contains(course_type, case=False, na=False))
                ]
                print(f"Filtering sheet '{sheet_name}' for course '{course_name}' of type '{course_type}'...")
                print(df_filtered)
                
       

                print(f"Found {len(df_filtered)} rows in sheet '{sheet_name}' for course '{course_name}' of type '{course_type}'.")

                # Convert each matching row to dict
                result[sheet_name] = [
                    row.dropna().to_dict()
                    for _, row in df_filtered.iterrows()
                ]
            else:
                print(f"Skipped sheet '{sheet_name}' — no 'CodigoEstabelecimento' column.")
                result[sheet_name] = []  # Still include the sheet name with empty list

        return result


    def get_course(self, response):
        for courseHtml in response.css('body'):
            if courseHtml.xpath(
                    '//*[@id="conteudoinner"]/div[1]/a').extract_first() is not None:  # tests if this page points to another one
                continue
            
            # Check if the course has an acronym
            # Some pages don't have an acronym, usually because they are not available for the current year
            acronym = self.get_acronym(response)

            
            if not acronym:
                continue

            course_type= response.xpath('//td[text()="Tipo de curso/ciclo de estudos: "]/following-sibling::td/text()').get()

            sigarra_id = response.url.split('=')[-1]
            course_name = response.xpath('//*[@id="conteudoinner"]/h1[2]').extract()[0][4:-5]
            fetch_course_stats = self.get_course_stats_from_xlsx( course_name, course_type)
            course = Course(
                id = sigarra_id,
                faculty_id = response.meta['faculty_acronym'],    # New parameter 
                name = course_name,
                acronym = acronym,
                course_type = course_type,
                year = self.get_year(),
                url = response.url,
                stats_json = json.dumps(fetch_course_stats),
                plan_url = f"cur_geral.cur_planos_estudos_view?pv_plano_id={sigarra_id}&pv_ano_lectivo={self.get_year()}",
                last_updated=datetime.now(),
            )

            yield course
