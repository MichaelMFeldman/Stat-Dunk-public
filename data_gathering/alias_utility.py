import psycopg2, re, string

"""
roster: [ [player_id, last_name, first_name, title, jersey_string] ,
          [player_id, last_name, first_name, title, jersey_string] ,
          ... ]
school_info: [ school_id, name, ncaa_id ]
"""

def display(cur, roster, school_info):
    cur.execute("""
        SELECT count(*) from games
        WHERE %s in (home_school_id, away_school_id)""",
        (school_info[0],))
    print ("--- Roster for {name} #{id} ({games} games) "
          "http://stats.ncaa.org/team/roster/11540?org_id={ncaaid} ---").format(
              name=school_info[1], id=school_info[0], games=cur.fetchone()[0],
              ncaaid=school_info[2])
        
    for player, i in zip(roster, range(len(roster))):
        last = str(roster[i][1])
        first = str(roster[i][2])
        title = roster[i][3] if roster[i][3] else ""
        jersey = str(roster[i][4]) if roster[i][4] else ""
        name = "{L:15} | {f:15} | {t} | ".format(L=last, f=first, t=title)
        print "{i}.\t{n:30} {j}".format(i=i, n=name, j=jersey)

# add to alias table
def add_alias(cur, school_id, alias_last, alias_first,
              alias_title, real_player_id):
    cur.execute("""
        INSERT INTO aliases
        (school_id, alias_last, alias_first, alias_title, player_id)
        VALUES (%s,%s,%s,%s,%s)""",
        (school_id, alias_last, alias_first, alias_title, real_player_id))

# change play by play records from the alias to the real player
def associate_records(cur, real_player_id, alias_player_id):
    cur.execute("""
        UPDATE play_by_plays SET player_id = %s
        WHERE player_id = %s""",
        (real_player_id, alias_player_id))
        
# change alias player IDs
def redirect_old_aliases(cur, new_player_id, old_player_id):
    cur.execute("UPDATE aliases SET player_id = %s WHERE player_id = %s",
                (new_player_id, old_player_id))

# remove alias from players
def remove_alias_from_roster(cur, alias_player_id):
    cur.execute("DELETE FROM players WHERE player_id = %s",
                (alias_player_id,))

# remove rows in lineups from a school, because they'll probably reference
# player IDs that don't exist anymore.
def remove_lineup_rows(cur, school_id):
    cur.execute("""
        DELETE FROM lineups L WHERE L.play_id IN
           (SELECT pbp.play_id FROM play_by_plays pbp JOIN games g
            ON pbp.game_id = g.game_id
            WHERE %s in (home_school_id,away_school_id));""",
        (school_id,))

def main():
    cur = conn.cursor()
    cur.execute("SELECT school_id, name, ncaa_id FROM schools")
    list_of_schools = cur.fetchall()
    current_index = 0
    print "h for help"
    while True:
        school_info = list_of_schools[current_index]
        cur.execute("""
            SELECT player_id, last_name, first_name, title, jersey_string
            FROM players WHERE school_id = %s
            ORDER BY jersey_string IS NOT NULL, last_name, first_name""",
            (school_info[0],))
        roster = cur.fetchall()
        display(cur, roster, school_info)
        
        inp = raw_input()
        # end
        if inp == "end":
            break
        # alias
        option = re.match("a\s*(\d+)\s+(\d+)$", inp)
        if option:
            real_name_num = int(option.group(1))
            alias_num =     int(option.group(2))
            real_player_id =  roster[real_name_num][0]
            alias_player_id = roster[alias_num][0]
            alias_last =      roster[alias_num][1]
            alias_first =     roster[alias_num][2]
            alias_title =     roster[alias_num][3]
            
            add_alias(cur, school_info[0], alias_last,
                      alias_first, alias_title, real_player_id)
            associate_records(cur, real_player_id, alias_player_id)
            redirect_old_aliases(cur, real_player_id, alias_player_id)
            remove_alias_from_roster(cur, alias_player_id)
            remove_lineup_rows(cur, school_info[0])
            
            conn.commit()
            continue
        # rename
        option = re.match("r\s*(\d+)\s+(.+),(.+),(.*)$", inp)
        if option:
            #Note that the OLD, CURRENT name will become the alias!
            #The NEW name will replace the old in the roster.
            roster_num = int(option.group(1))
            player_id =     roster[roster_num][0]
            current_last =  roster[roster_num][1]
            current_first = roster[roster_num][2]
            current_title = roster[roster_num][3]
            new_last =  option.group(2)
            new_first = option.group(3)
            new_title = option.group(4)
            if new_title == "": new_title = None
            
            add_alias(cur, school_info[0], current_last,
                      current_first, current_title, player_id)
            cur.execute("""
                UPDATE players set last_name = %s, first_name = %s, title = %s
                WHERE player_id = %s""",
                (new_last, new_first, new_title, player_id))
            
            conn.commit()
            continue
        # jersey
        option = re.match("j\s*(\d+)\s+(\d+)$", inp)
        if option:
            roster_num = int(option.group(1))
            player_id =  roster[roster_num][0]
            jersey =     option.group(2)
            cur.execute("""
                UPDATE players SET jersey_string = %s WHERE
                player_id = %s""",
                (jersey, player_id))
            conn.commit()
            continue
        # next school
        option = re.match("n\s*(\d*)$", inp)
        if option:
            if option.group(1) == '':
                current_index += 1
            else:
                current_index += int(option.group(1))
            continue
        # previous school
        option = re.match("p\s*(\d*)$", inp)
        if option:
            if option.group(1) == '':
                current_index -= 1
            else:
                current_index -= int(option.group(1))
            continue
        # skip to school name
        option = re.match("s\s*(.+)\s*$", inp)
        if option:
            name = option.group(1)
            found_school = False
            for school, i in zip(list_of_schools, range(len(list_of_schools))):
                if school[1] == name:
                    current_index = i
                    found_school = True
                    break
            if not found_school:
                print "School not found."
            continue
        # change CAPS CAPS name to Caps Caps using python's title() function
        option = re.match("caps\s*(\d+)$", inp)
        if option:
            player = roster[int(option.group(1))]
            last_name  = player[1].title()
            first_name = player[2].title()
            cur.execute("""
                UPDATE players set last_name = %s, first_name = %s
                WHERE player_id = %s""",
                (last_name, first_name, player[0]))
            conn.commit()
            continue
        # change an entire team's capitalization
        if inp == "tc":
            for player in roster:
                if player[1] == "TEAM" or player[2] == "NA":
                    continue
                last_name  = player[1].title()
                first_name = player[2].title()
                cur.execute("""
                    UPDATE players set last_name = %s, first_name = %s
                    WHERE player_id = %s""",
                    (last_name, first_name, player[0]))
            conn.commit()
            continue
        # help
        if inp == "h":
            print ("h for help\n"
                   "a number_of_real_name number_of_alias #updates all records of the alias to the real name, adds to alias table, deletes alias from players\n"
                   "a number_of_real_name last, first [, title] #\n"
                   "r number_of_current_name last, first [, title] #renames in db with no alias\n"
                   "j number_of_player new_jersey_number\n"
                   "n [number of schools to skip] #goes to next school, optional number\n"
                   "p [number of schools to skip to previously] #goes to prev school, optional number\n"
                   "s name_of_school #goes to roster for this school\n"
                   "caps number_of_name #changes CAPS CAPS to Caps Caps")
            continue
        # nothing found
        print "Command not understood! Type h for help."
            
    cur.close()

conn = psycopg2.connect("dbname=game_data user=michael")
main()
conn.close()