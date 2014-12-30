import psycopg2, re

conn = psycopg2.connect("dbname=game_data user=michael")
cur = conn.cursor()

#Get only the names that contain spaces - this also has the effect
#of ignoring names like Sims, Jr which shouldn't be fixed.
cur.execute("SELECT player_id,last_name,first_name FROM PLAYERS WHERE first_name LIKE '% %' OR last_name LIKE '% %'")
for row in cur.fetchall():
    p_id = row[0]
    last = row[1]
    first = row[2]
    match = re.match("(.*?) *\,? *((Jr.?)|([IVX]+))$", last)
    if match:
        new_last = match.group(1)
        if new_last == "":
            new_last = "FIX ME"
            print "Check player_id " + str(p_id)
        title = match.group(2)
        cur.execute(
            "UPDATE PLAYERS SET last_name = %s, title = %s WHERE player_id = %s",
            (new_last, title, p_id)
        )
        print str(p_id) + " [" + first + "] [" + last + "] becomes [" + first + "] [" + new_last + "] " + title
    # It could be in the first name
    else:
        match = re.match("(.*?) *\,? *((Jr.?)|([IVX]+))$", first)
        if match:
            new_first = match.group(1)
            if new_first == "":
                new_first = "FIX ME"
                print "Check player_id " + str(p_id)
            title = match.group(2)
            cur.execute(
                "UPDATE PLAYERS SET first_name = %s, title = %s WHERE player_id = %s",
                (new_first, title, p_id)
            )
            print str(p_id) + " [" + first + "] [" + last + "] becomes [" + new_first + "] [" + last + "] " + title
        else:
            print str(p_id) + " [" + first + "] [" + last + "] left unchanged!"

print "Done!"
conn.commit()
cur.close()
conn.close()