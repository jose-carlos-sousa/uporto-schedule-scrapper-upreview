import scrapy
import re  
from ..items import  CoursePath
from ..database.Database import Database
from urllib.parse import urlparse, parse_qs, urlencode


class CoursePathSpider(scrapy.Spider):
    name = "course_path" #This is the name of the table in the database it will be used for some queries
    allowed_domains = ['sigarra.up.pt'] #Domain we are going to scrape
    
    def __init__(self, *args, **kwargs):
        print("Initializing CoursePathSpider...")
        super(CoursePathSpider, self).__init__(*args, **kwargs)
        self.db = Database() 

        # All this is just to get the courses from the database

        sql = """
            SELECT course.id, year, faculty.acronym
            FROM course JOIN faculty                                
            ON course.faculty_id = faculty.acronym
        """
        
        self.db.cursor.execute(sql)
        self.courses = self.db.cursor.fetchall()   


    async def start(self): #For every course make request to the course page
        print("Starting requests...")
        for course in self.courses:         
            course_id, year, faculty_acronym = course
            url = f'https://sigarra.up.pt/{faculty_acronym}/pt/cur_geral.cur_view?pv_ano_lectivo={year}&pv_origem=CUR&pv_tipo_cur_sigla=M&pv_curso_id={course_id}'
            yield scrapy.Request(url=url, callback=self.parse_course_page, meta={'course_id': course_id, 'year': year, 'faculty_acronym': faculty_acronym})

    def parse_course_page(self, response): #Scrape the course page , get the plan link and make request to the plan page
        plan_link = response.xpath('//h3[text()="Planos de Estudos"]/following-sibling::div//ul/li/a/@href').extract_first()
        if plan_link:
            plan_id = plan_link.split("pv_plano_id=")[1].split("&")[0]
            plan_url = f'https://sigarra.up.pt/{response.meta["faculty_acronym"]}/pt/cur_geral.cur_planos_estudos_view?pv_plano_id={plan_id}&pv_ano_lectivo={response.meta["year"]}&pv_tipo_cur_sigla=M'
            yield scrapy.Request(url=plan_url, callback=self.parse_course_paths, meta=response.meta)
        else:
            print(f"No Planos de Estudos link found for course ID: {response.meta['course_id']}")
            
    def parse_course_paths(self, response):
        percurso_divs = response.xpath('//div[starts-with(@id, "div_percursos_alt_ano_")]')
        course_id = response.meta.get('course_id', 'unknown')

        for percurso_div in percurso_divs:
            ramo_divs = percurso_div.xpath('.//div[starts-with(@id, "div_ano") and contains(@id, "_ramo")]')

            for ramo_div in ramo_divs:
                div_id = ramo_div.xpath('./@id').get()
                year_match = re.search(r'div_ano(\d+)_ramo(\d+)', div_id)
                if not year_match:
                    self.logger.warning(f"Could not extract year and ramo_id from {div_id}")
                    continue

                year = year_match.group(1)
                ramo_id = year_match.group(2)

                # Find the corresponding <a> with href="#div_anoX_ramoY"
                ramo_name = response.xpath(
                    f'//li/a[@href="#{div_id}"]/em/text()'
                ).get(default='Unknown').strip()

                rows = ramo_div.xpath('.//td[@class="t"]')
                try:
                    sql = """
                        INSERT INTO course_path (code, name, course_id)
                        VALUES (?, ?, ?)
                    """
                    params = (
                        ramo_id,
                        ramo_name,
                        course_id
                    )

                    self.db.cursor.execute(sql, params)
                    self.db.connection.commit()
                except:
                    print("Already in database")

                for row in rows:
                    link = row.xpath('.//a/@href').get()
                    if link:
                        if link.startswith("javascript:"):
                            div_id = link.split("'")[1]  
                            group_div = response.xpath(f"//div[@id='{div_id}']")
                            for div in group_div:
                                group_title = div.xpath('.//h3/text()').extract_first()
                                if group_title:
                                    group_name = group_title.strip()
                                    div_id = div.xpath('./@id').extract_first().split("_")[3]
                                    try:
                                        sql = """
                                            SELECT id FROM course_path
                                            WHERE code = ? AND course_id = ?
                                        """
                                        self.db.cursor.execute(sql, (ramo_id,course_id))
                                        path_id = self.db.cursor.fetchone()
                                        if (path_id):
                                            update_group = """
                                                UPDATE course_unit_group
                                                SET path_id = ?
                                                WHERE id = ?;
                                            """
                                            self.db.cursor.execute(update_group, (path_id[0], div_id))
                                            self.db.connection.commit()
                                    except Exception as e:
                                        print("ERROR updating unit group", e)

                                    # Extract the year from the corresponding <a> tag
                                    # year_element = response.xpath(f'//a[contains(@id, "bloco_acurr_ShowOrHide") and contains(@href, "{div_id}")]')
                                    # year_text = year_element.xpath('normalize-space(text())').get()
                                    # year = year_text.split("º")[0] if year_text else "Unknown"

                                    course_rows = div.xpath('.//table[contains(@class, "dadossz")]/tr')
                                    for row2 in course_rows:
                                        link = row2.xpath('.//td[@class="t"]/a/@href').extract_first()
                                        if link:
                                            try:
                                                course_unit_id = link.split("pv_ocorrencia_id=")[1].split("&")[0]

                                                course_unit_url = f'https://sigarra.up.pt/{response.meta["faculty_acronym"]}/pt/ucurr_geral.ficha_uc_view?pv_ocorrencia_id={course_unit_id}'
                                                yield scrapy.Request(
                                                    url=course_unit_url,
                                                    callback=self.parse_course_unit_page_path,
                                                    meta={
                                                        'course_id': course_id,
                                                        'ramo_id': ramo_id,
                                                        'course_unit_id': course_unit_id,
                                                        'year': year
                                                    }
                                                )
                                            except IndexError:
                                                self.logger.warning(f"Failed to parse course unit ID from link {link}")
                        else:
                            try:
                                course_unit_id = link.split("pv_ocorrencia_id=")[1].split("&")[0]
                                course_unit_url = f'https://sigarra.up.pt/{response.meta["faculty_acronym"]}/pt/ucurr_geral.ficha_uc_view?pv_ocorrencia_id={course_unit_id}'
                                yield scrapy.Request(
                                    url=course_unit_url,
                                    callback=self.parse_course_unit_page_path,
                                    meta={
                                        'course_id': course_id,
                                        'ramo_id': ramo_id,
                                        'course_unit_id': course_unit_id,
                                        'year': year
                                    }
                                )
                            except IndexError:
                                self.logger.warning(f"Failed to parse course unit ID from link {link}")
                    else:
                        self.logger.warning(f"No link found in ramo {ramo_name} (ID {ramo_id})")

    def parse_course_unit_page_path(self, response): #Scrape the course unit page to get the course unit name and acronym
        outras_ocorrencias_link = response.xpath('//a[text()="Outras ocorrências"]/@href').get()
        if outras_ocorrencias_link:
            course_unit_id = parse_qs(urlparse(outras_ocorrencias_link).query)['pv_ucurr_id'][0]
        else:
            self.logger.warning(f"No 'Outras ocorrências' link found for course unit in response URL: {response.url}")
            return
        Instance = response.css('#conteudoinner > h2::text').extract_first()
        semester = Instance[24:26].strip()

        sql = """
            SELECT id FROM course_path
            WHERE code = ? AND course_id = ?
        """
        self.db.cursor.execute(sql, (response.meta['ramo_id'],response.meta['course_id']))
        course_path_id = self.db.cursor.fetchone()

        if course_path_id:
            course_path_id = course_path_id[0]
        else:
            print("Course_path not found.")
            return
        sql = """
                SELECT id FROM course_course_unit
                WHERE course_unit_id = ? AND course_id = ? AND year = ? AND semester = ?
                """
        self.db.cursor.execute(sql, (course_unit_id, response.meta['course_id'], response.meta['year'], semester))
        course_course_unit_id = self.db.cursor.fetchone()
        if course_course_unit_id:
            course_course_unit_id = course_course_unit_id[0]
        else:
            print("course_course_unit_id not found.")
            return
        try:
            sql = """
                INSERT INTO course_course_unit_path (course_course_unit_id, course_path_id)
                VALUES (?, ?)
            """
            params = (course_course_unit_id, course_path_id)

            self.db.cursor.execute(sql, params)
            self.db.connection.commit()
        except:
            print("ERROR in insert course_course_unit_path")
     
  