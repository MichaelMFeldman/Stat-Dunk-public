from bs4 import *
from os import listdir
import re, put_pbps_in_db, psycopg2

""" Notes on error handling:
      Descriptive messages are sent to error_message_pbp or error_message to be
    printed to the console and to error.log.
      As long as possible, the program will continue to extract data and put it
    into the db. If a line contains an error, all or some of the columns will
    be "FIX ME" if a string, or -1 if an int. This way, the affected lines can
    be found in the db, matched to the error log, and manually changed
    (usually the problem is a malformed name, which is simple to fix). """

output = open("output.txt", 'a')
errorlog = open("error.log", 'a')


#
#        Utility functions
#

def error_message_pbp(error, game, time):
    #Error message handling for a Play-By-Play entry
    errorlog.write("Game " + game + " at " + time + " --- " + error + "\n")
    print "*** ERROR *** Game " + game + " at " + time + " --- " + error
    
def error_message(error):
    #Error message handling for a generic error
    errorlog.write(error + "\n")
    print "*** ERROR *** " + error

def time_string_to_int(string, game):
    #eg "01:30" into 90
    time = re.search("(\d\d):(\d\d)", string)
    if not time:
        error_message_pbp("In time_string_to_int. Time string malformed.",
            game, string)
        return -1
    return int(time.group(1))*60 + int(time.group(2))
    
def score_string_to_tuple(string, game, time):
    #eg "25-27" into (25,27); away is first, home is second
    scores = re.search("(\d+)-(\d+)", string)
    if not scores:
        error_message_pbp("In score_string_to_tuple. Score string malformed: [" +
            string + "]", game, time)
        return (-1, -1)
    return (int(scores.group(1)), int(scores.group(2)))

# string, string, string ->
#                    {"last": string, "first": string, "title": None or string}
def standardized_names(name_string, game, time):
    """ Examples of titles in names:
        "SMITH JR.,JOHN"    "SMITH, JOHN JR"    "SMITH,JR, JOHN"
    Note that this also happens: "SMITH,JR" which does NOT count as JR!
    Return ("SMITH", "JOHN", "JR") or ("SMITH", "JOHN", None) """
    
    #"LAST,FIRST" with no spaces allowed - most common case
    name = re.match("([A-Z.'-]+),([A-Z.'-]+)$", name_string)
    if name:
        return {"last": name.group(1), "first": name.group(2), "title": None}
    
    #"JR" in the middle of the name - sometimes a comma before it, always after
    name = re.match("([A-Z .'-?()]+?)[ ,]+JR[ .]*, *([A-Z .'-?()]+?) *$", name_string)
    if name:
        return {"last": name.group(1), "first": name.group(2), "title": "JR"}
        
    #"JR" after name
    name = re.match("([A-Z .'-?()]+?)[ ,]+([A-Z .'-?()]+?)[ ,]+JR.?", name_string)
    if name:
        return {"last": name.group(1), "first": name.group(2), "title": "JR"}
        
    #Names with spaces (eg "VAN SMITH") - all "JR"s should be caught by now
    name = re.match("([A-Z .'-?()]+?) *, *([A-Z .'-?()]+?) *$", name_string)
    if name:
        return {"last": name.group(1), "first": name.group(2), "title": None}
    
    error_message_pbp("In standardized_names. No pattern matches this name " +
        "string: [" + name_string + "]", game, time)
    return {"last": name_string, "first": "FIX ME", "title": "FIX ME"}

# string, string, string, string -> {"team": string, "last": string,
#                      "first": string, "title": string/None, "action": string}
def plays_strings_to_dict(away, home, game, time):
    """ One of the args will be blank. The other - let's
    assume home - will be "SMITH,JOHN name of action".
    "[TEAM or TM] name of action" or "# name of action", # being a
    player's number, can occur as well. """
    
    if away and not home:
        string = away
        team = "away"
    elif home and not away:
        string = home
        team = "home"
    elif away and home:
        error_message_pbp("In plays_strings_to_tuple. Both away and home " +
            "strings exist. Away: [" + away + "] Home: [" + home+"]",game,time)
        return {i:"FIX ME" for i in ["team","last","first","title","action"]}
    else:
        error_message_pbp("In plays_strings_to_tuple. There is " +
            "neither an away nor home string.", game, time)
        return {i:"FIX ME" for i in ["team","last","first","title","action"]}
        
    team_action = re.match("(TEAM|TM) +(.+)", string)
    if team_action:
        return {"team": team, "last": "TEAM", "first": "NA", "title": None,
                "action": team_action.group(2)}
    player_action = re.match("(\d+) +([A-Za-z0-9 ]+)", string) #player number
    if player_action:
        return {"team": team, "last": player_action.group(1),
                "first": "NA", "title": None, "action": player_action.group(2)}
    player_action = re.match("([A-Z ,.'?()-]+) +([A-Za-z0-9 ]+)", string) #normal case
    if player_action:
        name = standardized_names(player_action.group(1), game, time)
        return dict([("team", team), ("action", player_action.group(2))] +
                    name.items())
    #Sometimes it's just an action, but always with a leading space
    only_action = re.match("\s+(.*\S)\s*", string)
    if only_action:
        return {"team": team, "last": "TEAM", "first": "NA", "title": None,
            "action": only_action.group(1)}
    else:
        error_message_pbp("In plays_strings_to_tuple. Play string " +
            "malformed: [" + string + "]", game, time)
        return {i:"FIX ME" for i in ["team","last","first","title","action"]}

#
#        Main function
#

def analyze_games():
    list_of_games = listdir("Game Data III")

    starts_with_letter = re.compile("^[A-Za-z]")
    is_a_time = re.compile("\d\d:\d\d")
    
    counter = 0 #for debugging
    
    conn = psycopg2.connect("dbname=game_data user=michael")
    cur = conn.cursor()
    cur.execute("""
        SELECT g.ncaa_id FROM games g WHERE
        EXISTS (SELECT 1 FROM play_by_plays pbp
            WHERE pbp.game_id = g.game_id)""")
    already_done = [i[0] for i in cur.fetchall()]
    cur.close()
    conn.close()
    
    for game in list_of_games:
        game_ncaa_id = re.match("(\d+)\.html", game).group(1)
        if int(game_ncaa_id) in already_done:
            continue
            
        print "Reading from game " + game + \
            "\t#" + str(counter + 1)
            
        soup = BeautifulSoup(open("Game Data III/" + game))
        output.write("************************************ game " +
            game + " ************************************\n")
        
        """ First, get the away and home team names, which are located after
        <td align="center">Total</td> """
        try:
            away_team_tag = soup.find(
                name="td", align="center", text="Total").find_next(
                    name="td", text=starts_with_letter)
        except AttributeError:
            error_message("Game " + game + " is a malformed file!")
            counter += 1
            continue
        home_team_tag = away_team_tag.find_next(
            name="td", text=starts_with_letter)
            
        home_ncaa_id = None
        for child in home_team_tag.contents:
            if child.name == "a":
                home_ncaa_id = re.search("org_id=(\d+)", child['href']).group(1)
        away_ncaa_id = None
        for child in away_team_tag.contents:
            if child.name == "a":
                away_ncaa_id = re.search("org_id=(\d+)", child['href']).group(1)
                
        away_team = away_team_tag.string
        home_team = home_team_tag.string
        
        """ Next, get the plays. Play by play entries look like this:    
            <td class="smtext">01:23</td>                   <-- time
            <td class="smtext"></td>                        <-- either the away team's player and action, or blank
            <td class="smtext" align="center">0-2</td>      <-- score
            <td class="smtext">SMITH,JOHN Assist</td>       <-- either the home team's player and action, or blank 
        So, to get every play, find the time tags and the info that immediately follows.
        Maintain a list_of_plays which will consist of plays, each of which is a list in this form:
            [away or home, last name or TEAM, first name or NA, title or None, time (seconds), action, away score, home score, t/f (is first half)]
        Then call put_pbps_in_db.main(game_info, list_of_plays) """
        list_of_time_tags = home_team_tag.find_all_next(
            name="td", class_="smtext", text=is_a_time)
        list_of_plays = []
        section = 1 # First half
        previous_time = 1200 # Starting time of the first half
        
        for time_tag in list_of_time_tags:
            away_play_tag =  time_tag.find_next(name="td")
            score_tag = away_play_tag.find_next(name="td")
            home_play_tag = score_tag.find_next(name="td")
            
            time = time_string_to_int(time_tag.string, game)
            scores = score_string_to_tuple(
                score_tag.string, game, time_tag.string)
            play = plays_strings_to_dict(
                away_play_tag.string, home_play_tag.string,
                game, time_tag.string)
                
            # Next half or overtime section
            if time > previous_time:
                section += 1
            previous_time = time
            
            list_of_plays += [ dict(play.items() +
                {"time": time, "a_score": scores[0],
                "h_score": scores[1], "section": section}.items()) ]
            #for debugging:
            player_name = "{L}, {f}{t}".format(L=play["last"],f=play["first"],
                t=" {t_}".format(t_=play["title"]) if play["title"] else "")
            """output.write(
                "{s} {time} {n} {a} {h_s}-{a_s}\n".format(
                    s=section,time=time,n=player_name,a=play["action"],
                    a_s=scores[0],h_s=scores[1]))"""
            
        game_info = {"g_ncaa": game_ncaa_id, "h_ncaa": home_ncaa_id,
            "a_ncaa": away_ncaa_id, "home": home_team, "away": away_team}
        
        put_pbps_in_db.main(game_info, list_of_plays)
        counter += 1
        
    print "Done with all games in the directory."
    
analyze_games()
output.close()
errorlog.close()