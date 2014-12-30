import re, psycopg2, sys

def error_msg(string, file):
    print string
    file.write(string + "\n")
    
def error_multiple_players(last, first, title, school_id, f):
    error_msg("Multiple player entries found for [" + str(last) +
        "] [" + str(first) + "] [" + str(title) +
        "] found! "+ str(school_id), f
    )
        
def error_multiple_aliases(last, first, title, school_id, f):
    error_msg("Multiple aliases found for [" + str(last) +
        "] [" + str(first) + "] [" + str(title) +
        "] found! "+ str(school_id), f
    )

def search_players(cur, school_id, last_name, first_name):
    cur.execute("""
        SELECT player_id FROM players
        WHERE school_id = %s AND last_name ILIKE %s
              AND first_name ILIKE %s""",
        (school_id, last_name, first_name)
    )
    return cur
    
def search_players_inc_title(cur, school_id, last_name, first_name, title):
    #Search players including title. Unfortunately these have to be
    #separate because '= NULL' doesn't work properly.
    if title:
        cur.execute("""
            SELECT player_id FROM players
            WHERE school_id = %s AND last_name ILIKE %s
                  AND first_name ILIKE %s AND title ILIKE %s""",
            (school_id, last_name, first_name, title)
        )
    else:
        cur.execute("""
            SELECT player_id FROM players
            WHERE school_id = %s AND last_name ILIKE %s
                  AND first_name ILIKE %s AND title IS NULL""",
            (school_id, last_name, first_name)
        )
    return cur

def search_alias_or_add_player(cur, school_id, last_name, first_name, title,f):
    name_string = "[" + last_name + "] [" + first_name + "] [" + str(title) + "]"
    if title:
        cur.execute("""
            SELECT player_id FROM aliases
            WHERE school_id = %s AND alias_last ILIKE %s AND
                  alias_first ILIKE %s AND alias_title ILIKE %s""",
           (school_id, last_name, first_name, title)
        )
    else:
        cur.execute("""
            SELECT player_id FROM aliases
            WHERE school_id = %s AND alias_last ILIKE %s AND
                  alias_first ILIKE %s AND alias_title IS NULL""",
           (school_id, last_name, first_name)
        )
    alias = cur.fetchall()
    
    if len(alias) == 1:
        player_id = alias[0]
    elif len(alias) > 1:
        error_multiple_aliases(last_name, first_name,
                               title, school_id, output
        )
        player_id = alias[0]
    else:
        cur.execute("""
            INSERT INTO players (last_name, first_name, title, school_id)
            VALUES (%s, %s, %s, %s)
            RETURNING player_id""",
            (last_name, first_name, title, school_id)
        )
        player_id = cur.fetchone()[0]
        error_msg("Added new player [" + last_name + "] [" + first_name +
            "] [" + str(title), f
        )
    return player_id

def main(game_info, list_of_plays):
    conn = psycopg2.connect("dbname=game_data user=michael")
    cur = conn.cursor()
    output = open("pbp entry.log", 'a')
    
    #
    # Initial game data
    #
    
    game_ncaa_id = game_info["g_ncaa"]
    home_ncaa_id = game_info["h_ncaa"]
    away_ncaa_id = game_info["a_ncaa"]
    home_name    = game_info["home"]
    away_name    = game_info["away"]
    
    #Get the game id.
    cur.execute("SELECT game_id FROM games WHERE ncaa_id = %s",
                (game_ncaa_id,)
    )
    result = cur.fetchone()
    if result:
        game_id = result[0]
    else:
        error_msg("Game with NCAA id " + game_ncaa_id + " doesn't exist in db",
                  output
        )
        cur.close()
        conn.close()
        output.close()
        sys.exit()
    
    #Check if this game is already in the play by play table.
    cur.execute("SELECT exists(SELECT * from play_by_plays where game_id = %s)",
                (game_id,)
    )
    if cur.fetchone()[0]:
        error_msg("Game " + str(game_id) + " already exists in play by plays!",
                  output
        )
        
    
    #Get the home and away school primary key ids.
    #Get home by NCAA id:
    if home_ncaa_id:
        try:
            cur.execute("SELECT school_id FROM schools WHERE ncaa_id = %s", (home_ncaa_id,))
            home_id = cur.fetchone()[0]
        except:
            error_msg("Tried to retrieve school id of " + home_name + " by looking up NCAA id " + home_ncaa_id + " but no NCAA id found!\n",output)
    #Get home by name if no NCAA id:
    else:
        try:
            cur.execute("SELECT school_id FROM schools WHERE name = %s",    (home_name,))
            home_id = cur.fetchone()[0]
        except:
            error_msg("Tried to retrieve school id of " + home_name + " by name (no id existed) but no school found!\n",output)
    #Get away by NCAA id:
    if away_ncaa_id:
        try:
            cur.execute("SELECT school_id FROM schools WHERE ncaa_id = %s", (away_ncaa_id,))
            away_id = cur.fetchone()[0]
        except:
            error_msg("Tried to retrieve school id of " + away_name + " by looking up NCAA id " + away_ncaa_id + " but no NCAA id found!",output)
    #Get away by name if no NCAA id:
    else:
        try:
            cur.execute("SELECT school_id FROM schools WHERE name = %s",    (away_name,))
            away_id = cur.fetchone()[0]
        except:
            error_msg("Tried to retrieve school id of " + away_name +
                " by name (no id existed) but no school found!",output)
    
    #If the game is at a neutral location, make sure the home/away are accurate.
    cur.execute("SELECT both_are_away FROM games WHERE ncaa_id = %s",
                (game_ncaa_id,)
    )
    if cur.fetchone()[0]:
        cur.execute(
            """UPDATE games SET home_school_id = %s, away_school_id = %s
            WHERE ncaa_id = %s""",
            (home_id, away_id, game_ncaa_id)
        )
    
    #
    # Now, the actual play-by-play data
    #
    
    for play in list_of_plays:
        which_team = play["team"]
        last_name =  play["last"]
        first_name = play["first"]
        title =      play["title"]
        time =       play["time"]
        action =     play["action"]
        away_score = play["a_score"]
        home_score = play["h_score"]
        section =    play["section"]
        
        #Which school id made this play?
        if   which_team == "home": school_id = home_id
        elif which_team == "away": school_id = away_id
        
        #Get the player id.
        #This will be messy because it's searching by name rather than an ID.
        #This is what happens:
        #
        #  Search PLAYERS for school, last name, first name
        #  One result --> We're good! Use this ID.
        #  Multiple results --> Try again with title to narrow it down
        #      One result --> We're good! Use this ID.
        #      Multiple results --> Print an error and choose one.
        #      Zero results --> Search ALIASES (see below)
        #  Zero results --> Search ALIASES (see below)
        #
        #  (This is a function search_alias_or_add_player at the top)
        #  Search ALIASES for school, last name, first name, title
        #      One result --> We're good! Use this ID.
        #      Multiple results --> Print an error and choose one.
        #      Zero results --> Print an error and add to PLAYERS.
        
        
        name_string = "[" + last_name + "] [" + first_name + "] [" + str(title) + "]"
        cur = search_players(cur, school_id, last_name, first_name)
        player = cur.fetchall()
        if len(player) == 1:
            player_id = player[0]
        elif len(player) > 1:
            cur = search_players_inc_title(cur, school_id, last_name,
                                           first_name, title
            )
            player = cur.fetchall()
            if len(player) == 1:
                player_id = player[0]
            elif len(player) > 1:
                error_multiple_players(last_name, first_name,
                                       title, school_id, output
                )
                player_id = player[0]
            else:
                player_id = search_alias_or_add_player(
                    cur, school_id, last_name, first_name, title, output)
        else:
            player_id = search_alias_or_add_player(
                cur, school_id, last_name, first_name, title, output)
            
        #Get the action id.
        cur.execute(
            "SELECT action_id FROM actions WHERE action ILIKE %s",
            (action,)
        )
        result = cur.fetchone()
        if result:
            action_id = result[0]
        else:
            cur.execute(
                "INSERT INTO actions (action) VALUES (%s) RETURNING action_id",
                (action,)
            )
            action_id = cur.fetchone()[0]
            error_msg("Added a new action [" + action + "]", output)
        
        #Put it all together!
        cur.execute("""
            INSERT INTO play_by_plays (game_id, player_id, time,
            action_id, home_score, away_score, section)
            VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (game_id, player_id, time, action_id,
             home_score, away_score, section)
        )
        
    conn.commit()
    cur.close()
    conn.close()
    output.close()