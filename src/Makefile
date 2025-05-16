.PHONY: all clean
FILES = $(shell ls)
        
# all: info faculties courses course_units 
all: info faculties courses course_units professors course_unit_groups course_path


faculties: 
	scrapy crawl faculties 

courses: 
	scrapy crawl courses

course_units:
	scrapy crawl course_units

professors:
	scrapy crawl professors
info:
	python ./scrapper/info.py

course_unit_groups:
	scrapy crawl course_unit_groups

course_path:
	scrapy crawl course_path

exchange_faculties:
	scrapy crawl exchange_faculties

exchange_faculties_additional:
	scrapy crawl exchange_faculty_additional

dump:
	@echo "Dumping files..."
	python ./scripts/dump.py
	@echo "Completed!"

upload:
	@echo "Uploading files..."
	@python ./scripts/upload.py
	@echo "Upload completed!"

convert_postgres:
	@echo "Converting dump to postgres..."
	@bash ./scripts/sqlite3-to-mysql.sh ./scripts/dump/data/dump_sqlite3.sql > ./scripts/dump/data/01_data.sql
	@echo "Convertion completed!"

clean: 
	@echo "Removing database.db"
	@rm ./scrapper/database/dbs/database.db
