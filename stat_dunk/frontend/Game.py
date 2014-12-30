from __future__ import division
import psycopg2
from operator import itemgetter
import StatsObject
from Play import Play

"""
Game
    Setup/initialization methods
    Misc utility methods
"""

class Game:
    """This stores all information about a given game.
    
        Instance attributes:
    g_id: int. The database game_id.
    has_invalid_data: string. Empty strings evaluate to False. Replace this
        with a reason data is invalid if that's the case.
    home_id: int. The database school_id of the home team.
    away_id: int. See above.
    teams: {int (school id):string ("home"/"away")}. Use this to look up a
        school ID and get the string which is a key for various internal
        lookups, such as the lineups in Play objects.
    roster: {int (player id):Player}. Both teams' rosters in one dict.
    actions: {int (action id):string ("action")}.
    plays: a list of Play objects. They will include lineups.
    lineups: a set of frozensets of Players. All unique lineups in plays.
    section_indices: {int: int}. The index of the first Play in a given
        section (the key).
    """

    # connection, int, int, int, {int: Player}, {int: "action"} -> [void]
    def __init__(self, SO, conn, g_id, home=None, away=None,
                 roster=None, actions=None):
        cur = conn.cursor()
        self.SO = SO
        self.g_id = g_id
        self.has_invalid_data = ""
        if home is None or away is None:
            home, away = get_school_ids_from_game(g_id)
        else:
            self.home_id = home
            self.away_id = away
        self.teams = {home: "home", away: "away"}
        if roster is not None:
            self.roster = roster
        else:
            self.roster = dict(make_dict_of_players(home),
                               **make_dict_of_players(away))
        if actions:
            self.actions_attributes = actions
        else:
            self.actions_attributes = self.SO.make_action_attrs()
        self.section_indices = {}
        self.plays = self.get_plays_from_game(cur)
        self.lineups = {"home":self.get_lineups(home),
                        "away":self.get_lineups(away)}
        conn.commit() # Commit inserts made into the lineup table.
        cur.close()
        
    # cursor -> returns list of Plays with lineups
    def get_plays_from_game(self, cur):
        cur.execute("""
            SELECT pbp.play_id, pbp.player_id, pbp.action_id, pbp.time,
                pbp.section, L.home_lineup, L.away_lineup 
            FROM play_by_plays pbp LEFT JOIN lineups L 
                ON pbp.play_id = L.play_id 
            WHERE game_id = %s ORDER BY pbp.play_id""",
            (self.g_id,))
        plays = []
        lineup_not_found_in_table = False
        previous_section = 0
        rows = cur.fetchall()
        for i in range(len(rows)):
            row = rows[i]
            play_id =    row[0]
            player =     self.roster[row[1]]
            a_id =       row[2]
            time =       row[3]
            section =    row[4]
            home_array = row[5] # A postgres array of player IDs as the lineup
            away_array = row[6]
            # If there's no lineup for this Play, record that and call a
            # function to add all lineups as needed to the db and Plays.
            if home_array is None or away_array is None:
                lineup_not_found_in_table = True
                home_lineup, away_lineup = None, None
            else:
                home_lineup = [self.roster[i] for i in home_array]
                away_lineup = [self.roster[i] for i in away_array]
            plays += [Play(play_id, player, a_id, self.actions_attributes,
                           time, section, home_lineup, away_lineup)]
            if section > previous_section:
                self.section_indices[section] = i
            previous_section = section
                           
        # If the play by play page has no data...
        if len(plays) == 0:
            self.has_invalid_data = "No play data"
            return plays
        # Else, return or pass to the function that creates lineups.
        else:
            if lineup_not_found_in_table:
                return self.add_lineups_to_game(cur, plays)
            return plays
            
    # int -> returns int
    def get_other_team_id(self, school_id):
        """Get the other key in self.teams."""
        
        for k in self.teams:
            if k != school_id:
                return k
    
    # int, list of Plays -> returns slice of Plays
    def get_section(self, section, list_of_plays):
        """Return all the plays in a given section."""
    
        begin = self.section_indices[section]
        # If the next section doesn't exist, just go to the end.
        end = self.section_indices.get(section+1, None) 
        return list_of_plays[begin:end]
            
    """
    BEGIN LINEUP BUILDING METHODS
        Rather than relying strictly on the play by play entries showing
    players entering and leaving the game (which are often out of order or
    otherwise unreliable), this finds lineups for each individual play by
    finding the closest players. It uses the enter/leave information but not
    exclusively. (See self.add_lineups() for details.)
    """
    
    # cursor, list of Plays -> returns same list of Plays with lineups
    def add_lineups_to_game(self, cur, plays):
        """Add lineups to each section and return them combined."""
        
        plays_with_lineups = []
        for section in sorted(self.section_indices):
            plays_with_lineups += self.add_lineups(cur,
                self.get_section(section, plays))
        return plays_with_lineups
        
    # slice of list of Plays -> returns same slice with lineups
    def add_lineups(self, cur, plays_slice):
        """Add lineups to a slice of a list of Plays.
        
            Iterate through every Play. For each that doesn't have both
        lineups, get the 5 closest Players on each team who could be on
        the court, and add them to that Play and the lineups table in the db.
        """
        
        for i in range(len(plays_slice)):
            this_play = plays_slice[i]
            this_player = this_play.player
            if (this_play.lineups["home"] != set() and 
                    this_play.lineups["away"] != set()):
                continue # Skip those that already have lineups.
                
            if this_player.last == "TEAM":
                num_teammates_needed = 5 # TEAM won't go in the lineup
            else:
                num_teammates_needed = 4 # This player will go in the lineup
            team_id = this_player.s_id
            oppnt_id = self.get_other_team_id(team_id) # opponent school id
            
            teammates = self.closest_n_players_from_a_team(
                num_teammates_needed, i, team_id, plays_slice)
            opponents = self.closest_n_players_from_a_team(
                5,                    i, oppnt_id, plays_slice)
                
            # If the player is TEAM, the team lineup will already be full.
            if this_player.last != "TEAM":
                teammates.add(this_player)
            teammates = frozenset(teammates)
            opponents = frozenset(opponents)
            
            lineups = {self.teams[team_id]: teammates,
                       self.teams[oppnt_id]: opponents}
            plays_slice[i].lineups = lineups
            self.add_lineups_to_db(cur, this_play.play_id, lineups)
        return plays_slice
    
    # int, int, int, slice of list of Plays -> returns set of Players
    def closest_n_players_from_a_team(self, n, index, id_of_team, plays_slice):
        """Get the closest n players from a given Play.
        
            Look forward and backward, finding the closest n Players in both
        directions (where possible). Find the closest n unique Players among
        both lists and return those.
        """
        
        previous = self.get_next_or_prev_n("prev", n, index,
                                           id_of_team, plays_slice)
        next =     self.get_next_or_prev_n("next", n, index,
                                           id_of_team, plays_slice)
        # Combine the lists and sort by the distance from the index (first
        # element). Return a set of the first n unique Players.
        closest_n_players = set()
        for player_tuple in sorted(previous + next, key=itemgetter(0)):
            if len(closest_n_players) == n:
                break
            player = player_tuple[1]
            if player not in closest_n_players:
                closest_n_players.add(player)
        return closest_n_players

    # string, int, int, int, slice of list of Plays ->
    #                       returns list of (int (distance from index), Player)
    def get_next_or_prev_n(self, direction, n, index, id_of_team, plays_slice):
        """Get the closest n players from a given Play in one direction.
        
            Given "prev"/"next", find the n (or as many as possible, eg near
        the end of the slice) closest Players previous to or after
        plays_slice[index] on this team who make an action, and thus could be
        on the lineup of that Play.
            If they enter or leave such that they couldn't be in the lineup, or
        are the player making the action (and would thus already be included in
        the lineup), or are TEAM, don't include them.
        """
        
        if direction == "prev":
            # Players who leave before this play can be ruled out of the lineup.
            action_id_that_rules_out = StatsObject.get_one_id_matching_type(
                self.actions_attributes, "leave")
            # Start at the Play right before the index and go backwards, all
            # the way up to and including 0 (so end at -1).
            range_to_iterate = range(index - 1, -1, -1)
        elif direction == "next":
            # Similarly, Players who enter after can be ruled out.
            action_id_that_rules_out = StatsObject.get_one_id_matching_type(
                self.actions_attributes, "enter")
            # Start at the Play right after the index and go to the end.
            range_to_iterate = range(index + 1, len(plays_slice))
            
        # A set of Players that were either ruled out or already added
        dont_add = set()
        # A list of tuples (distance_from_index, Player)
        n_to_return = []
        distance_from_index = 1
        player_making_action = plays_slice[index].player
        for i in range_to_iterate:
            if len(n_to_return) == n:
                break
            current_play = plays_slice[i]
            current_player = current_play.player
            if (current_player.last == "TEAM" or
                    current_player in dont_add):
                continue
            if current_player.s_id == id_of_team:
                if current_play.a_id == action_id_that_rules_out:
                    dont_add.add(current_player)
                # If the current player is new and valid...
                elif (current_player is not player_making_action and
                        current_player not in dont_add):
                    n_to_return += [(distance_from_index, current_player)]
                    dont_add.add(current_player)
            distance_from_index += 1
        return n_to_return
        
    # cursor, int, {string ("home"/"away"): frozenset of Players} -> [void]
    def add_lineups_to_db(self, cur, play_id, lineups):
        """Add a Play's lineups to the lineups db table."""
        
        home_ids = [Player.p_id for Player in lineups["home"]]
        away_ids = [Player.p_id for Player in lineups["away"]]
        
        cur.execute("""
            INSERT INTO lineups (play_id, home_lineup, away_lineup)
            VALUES (%s, %s, %s)""",
            (play_id, home_ids, away_ids))
                    
    # [no args] -> returns set of frozenset of Players
    def both_lineups(self):
        return self.lineups["home"].union(self.lineups["away"])
    
    """
    END LINEUP BUILDING FUNCTIONS
    """
    
    # int -> returns set of frozensets of Players
    def get_lineups(self, school_id):
        set_of_lineups = set()
        team = self.teams[school_id]
        for p in self.plays:
            if not (self.actions_attributes[p.a_id]["type"] == "enter" or
                    self.actions_attributes[p.a_id]["type"] == "leave"):
                set_of_lineups.add(p.lineups[team])
        return set_of_lineups
        
    # list of Questions -> [void]
    def add_data_to_Questions(self, list_of_Questions):
        for p in self.plays:
            for q in list_of_Questions:
                # If this Question requests stats from this Game, add the Play.
                if self.g_id in q.games:
                    q.add_data_as_applicable(p, self.g_id)
       
    # [no args] -> string     
    def __repr__(self):
        string = str(self.g_id) + "\n"
        for p in self.plays:
            string += str(p) + "\n"
        return string