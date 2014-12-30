There are two components to Stat Dunk:
      Data gathering - Take scraped data from the NCAA's site and process it into the db.
      Analysis - Identify lineups in play by play data and respond to statistical queries.
      
Data gathering
    First, scrape these .html files from the NCAA's site:
        A file listing all school page urls              eg http://stats.ncaa.org/team/inst_team_list/12020?division=3.0
          From that, get the following from each school:
        A directory containing each school's game list   eg http://stats.ncaa.org/team/index/12020?org_id=4
        A directory containing each school's roster      eg http://stats.ncaa.org/team/roster/12020?org_id=4
        A directory contianing each play-by-play         eg http://stats.ncaa.org/game/play_by_play/3509759
    Now run the following:
        put_schools_in_db.py
        put_games_in_db.py
        put_players_in_db.py
        get_pbps.py            Will call put_pbps_in_db.py.
        fix_titles_in_db.py    In these files, "titles" refer to Jr/Sr/III/II/etc in names. They're often inconsistent in this data.
        alias_utility.py       A tool to speed up fixing rosters. Things like improper name capitalization, duplicated players, etc.

Analysis
    The main analysis object is the StatsObject. Expected use is instantiating it and calling the add_games_from_school(ncaa_school_id) method.
    Use instances of the Question object, or its child MulticondQuestion objects, to call StatsObject.answer_Questions(list_of_Questions).
    
    The backbone of analysis is the Game object, which corresponds to one game of play-by-play data. It stores all the necessary data
    of each game, including the lineups present on court at each play (calculating and storing them in the db if not already done).