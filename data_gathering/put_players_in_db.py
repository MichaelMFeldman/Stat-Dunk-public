import psycopg2, re
from os import listdir
from bs4 import *

list_of_rosters = listdir("Rosters III")

conn = psycopg2.connect("dbname=game_data user=michael")
cur = conn.cursor()

for roster_file in list_of_rosters:
    f = open("Rosters III/" + roster_file, 'r')
    roster = f.read()
    f.close()
    
    try:
        ncaa_id = re.search("org_id=(\d+)", roster).group(1)
    except:
        #This school is the malformed exception...
        if roster_file == "Presentation roster.html":
            ncaa_id = "30034"
    cur.execute("SELECT school_id FROM SCHOOLS WHERE ncaa_id = %s", (ncaa_id,))
    school_id = cur.fetchone()[0]
    
    soup = BeautifulSoup(open("Rosters III/" + roster_file))
    
    GS_tag = soup.find(name="th", text = "GS")
    list_of_players = GS_tag.find_all_next(name="tr")
    
    players = open("players.txt", 'a')
    for player_tag in list_of_players:
        jersey_tag = player_tag.find_next(name="td")
        jersey = jersey_tag.text
        name = jersey_tag.find_next(name="td").text
        
        match = re.match(" *(.+) *, *(.+) *", name)
        if match:
            last_name = match.group(1)
            first_name = match.group(2)
            title = None
            
            if " " in last_name:
                match = re.match("(.*?) *\,? *((Jr.?)|([IVX]+))$", last_name)
                if match:
                    last_name = match.group(1)
                    title = match.group(2)
                    if last_name == "":
                        last_name = "FIX ME"
                        print "Check player_id " + str(p_id)                
            if " " in first_name:
                match = re.match("(.*?) *\,? *((Jr.?)|([IVX]+))$", first_name)
                if match:
                    first_name = match.group(1)
                    title = match.group(2)
                    if first_name == "":
                        first_name = "FIX ME"
                        print "Check player_id " + str(p_id)
            cur.execute("""
                SELECT player_id FROM players
                WHERE last_name = %s AND first_name = %s AND school_id = %s""",
                (last_name, first_name, school_id)
            )
            player = cur.fetchall()
            if len(player) == 0:
                cur.execute("""
                    INSERT INTO players
                    (last_name, first_name, title, school_id, jersey_string)
                    VALUES (%s,%s,%s,%s,%s)""",
                    (last_name, first_name, title, school_id, jersey)
                )
            else:
                for p_id in player:
                    cur.execute("""
                        UPDATE players SET jersey_string = %s
                        WHERE player_id = %s""",
                        (jersey, p_id)
                    )
        else:
            print "******** FAILED ON: " + roster_file + " " + ncaa_id + " " + name + " " + jersey
            players.write("******** FAILED ON: " + roster_file + " " + ncaa_id + " " + name + " " + jersey + "\n")
    players.close()
    print "Finished " + roster_file

print "Done!"
conn.commit()
cur.close()
conn.close()