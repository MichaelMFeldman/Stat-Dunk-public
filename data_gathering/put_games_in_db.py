from bs4 import *
import psycopg2, re
from os import listdir

list_of_schools = listdir("School pages III")

conn = psycopg2.connect("dbname=game_data user=michael")
cur = conn.cursor()

is_a_date = re.compile("^ *\d\d/\d\d/\d\d\d\d *$")
for school in list_of_schools:
    print school
    soup = BeautifulSoup(open("School pages III/" + school))
    
    #First try to get basic information: The name of the school and
    #the location of a tag right before the list of games.
    try:
        result_col_tag = soup.find(name="td", text="Result")
        school_ncaa_id_url = soup.find(name="a", text="Roster")['href']
        school_ncaa_id = re.search("org_id=(\d+)", school_ncaa_id_url).group(1)
        cur.execute("SELECT name FROM SCHOOLS WHERE ncaa_id = %s", (school_ncaa_id,))
        try:
            school_name = cur.fetchone()[0]
        except:
            print school + " is not in the database! Looked up ncaa id " + school_ncaa_id
    except AttributeError:
        print "***************** School " + school + " is a malformed file!"
        continue
        
    list_of_date_tags = result_col_tag.find_all_next(name="td", text=is_a_date)
    
    for date_tag in list_of_date_tags:
        #Get the three tag locations
        date_text = date_tag.string        
        opponent_tag = date_tag.find_next(name="td")
        result_tag = opponent_tag.find_next(name="td")
        
        #Get the date from "MM/DD/YYYY" to "YYYY-MM-DD"
        date_tuple = re.match(" *(\d+)/(\d+)/(\d+) *$", date_text)
        date = date_tuple.group(3) + "-" + date_tuple.group(1) + "-" + date_tuple.group(2)
        
        #This individual game's NCAA id
        game_url = result_tag.find_next(name="a")['href']
        game_ncaa_id = re.search("index/(\d+)\?", game_url).group(1)  
        
        #Check if game already exists in db
        cur.execute("SELECT EXISTS(SELECT 1 FROM GAMES WHERE ncaa_id = %s)", (game_ncaa_id,))
        if cur.fetchone()[0]:
            continue
        
        #Get opponent ncaa_id, if it exists
        opponent_ncaa_id = None
        for child in opponent_tag.contents:
            if child.name == "a":
                opponent_ncaa_id = re.search("org_id=(\d+)", child['href']).group(1)
                
        #The html has inconsistent whitespace, so combine every string into one.
        opponent_name_text = ""
        for string in opponent_tag.strings:
            opponent_name_text += string

        #Get name and home/away status - for this school,
        #is it a home game, away, or neither?
        opponent_name_text = re.sub("<br ?/>", "", opponent_name_text)
        opponent_info = re.search("""\s*
                                   ([^@]*[^\s@])? #Everything before an @, no trailing whitespace
                                   \s*
                                   #If there is an @, it must be followed by something
                                   (
                                     (@)
                                     \s*
                                     ([^@]*\S) #Everything after an @, no trailing whitespace
                                   )?
                                   \s*$""", opponent_name_text, re.X)
        before_at_exists = opponent_info.group(1)
        at_exists = opponent_info.group(3)
        after_at_exists = opponent_info.group(4)
        #Opponent - home game
        if before_at_exists and not at_exists and not after_at_exists:
            opponent_name = before_at_exists
            is_away = False
            both_are_away = False
        #@ Opponent - away game
        elif not before_at_exists and at_exists and after_at_exists:
            opponent_name = after_at_exists
            is_away = True
            both_are_away = False
        #Opponent @ Location - neutral game elsewhere
        elif before_at_exists and at_exists and after_at_exists:
            opponent_name = before_at_exists
            is_away = True
            both_are_away = True
        else:
            print "Something screwy happened with the home/away/location section in " + school
            continue
        
        #Add opponent to db if it doesn't exist already
        cur.execute("SELECT EXISTS(SELECT 1 FROM SCHOOLS WHERE name = %s)", (opponent_name,))
        if not cur.fetchone()[0]:
            cur.execute("INSERT INTO SCHOOLS (name, ncaa_id) VALUES (%s,%s)", (opponent_name, opponent_ncaa_id))
            print "Added [" + opponent_name + "] NCAA id #" + str(opponent_ncaa_id) + " to database" 
        
        #Determine which team won and what the home/away teams and scores were
        result_text = result_tag.find_next(name="a").string
        result_match = re.match("([WL]) *(\d+) *- *(\d+)", result_text)
        if result_match:
            if result_match.group(1) == "W":
                winner_name = school_name
            elif result_match.group(1) == "L":
                winner_name = opponent_name
            else:
                print "ERROR! Neither W nor L in the result! " + school
                continue
                
            if is_away:
                home_name = opponent_name
                away_name = school_name
                home_score = result_match.group(3)
                away_score = result_match.group(2)                
            else:
                home_name = school_name
                away_name = opponent_name
                home_score = result_match.group(2)
                away_score = result_match.group(3)
                           
        elif result_text == "-":
            #no game
            continue
            
        else:
            print "The result text is unmatched [" + result_text + "] " + school
            
        #Although NCAA id is a slightly better way to identify schools, several
        #schools don't have one.
        cur.execute("""
            INSERT INTO GAMES (home_school_id, away_school_id, winner,      ncaa_id,      home_score, away_score, date, both_are_away)
            VALUES ((SELECT school_id FROM SCHOOLS s WHERE s.name = %s),
                    (SELECT school_id FROM SCHOOLS s WHERE s.name = %s),
                    (SELECT school_id FROM SCHOOLS s WHERE s.name = %s),%s,%s,%s,%s, %s)""",
                              (home_name,      away_name,      winner_name, game_ncaa_id, home_score, away_score, date, both_are_away)
        )
    conn.commit()
        
print "Done!"
conn.commit()
cur.close()
conn.close()