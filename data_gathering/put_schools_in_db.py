import psycopg2, re

school_html = open("List of Schools III.html", 'r')
list_of_schools = re.findall("/index/11540\?org_id=(\d+).+>(.+)</a>", school_html.read())
school_html.close()

conn = psycopg2.connect("dbname=game_data user=michael")
cur = conn.cursor()

for school in list_of_schools:
    cur.execute(
        "INSERT INTO SCHOOLS (name,ncaa_id) VALUES (%s,%s)",
        (school[1], school[0])
    )
    
conn.commit()
cur.close()
conn.close()