from __future__ import division
import psycopg2
import itertools
from Game import Game
from Player import Player

class StatsObject:
    """This stores Game objects and distributes Questions to them.
    
        Instance attributes:
    dict_of_Games:      {int (game id):   Game}.
    dict_of_Players:    {int (player id): Player}.
    actions_attributes: {int (action id): {see actions_attributes()}}.
    """
    
    # [no args] -> [void]
    def __init__(self):
        conn = psycopg2.connect("dbname=game_data user=michael")
        cur = conn.cursor()
        self.dict_of_Games = {}
        self.dict_of_Players = {}
        self.actions_attributes = self.make_action_attrs(cur)
        cur.close()
        conn.close()
    
    # [no args] -> {int: dict(see body)}
    def make_action_attrs(self, cur):
        """Make the dict of action attributes.
        
           Each action ID maps to another dictionary containing that action's
        printable name, point value, and more permanent type (see the readme).
        """
        
        try:
            return self.actions_attributes
        except AttributeError:
            cur.execute("SELECT action_id, action, points, type FROM actions")
            self.actions_attributes = {}
            for row in cur.fetchall():
                action_id = row[0]
                self.actions_attributes[action_id] = {
                    "name":   row[1], # string: string
                    "points": row[2], # string: int
                    "type":   row[3]} # string: string
            return self.actions_attributes
        
    # cursor, int -> [void]
    def add_roster(self, cur, school_id):
        """Add a school's Players to dict_of_Players."""
        
        # If there are already Players from this school, do nothing.
        for P in self.dict_of_Players.itervalues():
            if P.s_id == school_id:
                return
                
        cur.execute("""
           SELECT player_id, school_id, last_name, first_name, title
           FROM players WHERE school_id = %s""",
           (school_id,))
        for row in cur.fetchall():
            p_id =  row[0]
            s_id =  row[1]
            last =  row[2]
            first = row[3]
            title = row[4]
            self.dict_of_Players[p_id] = Player(p_id, s_id, last, first, title)

    # int -> [void]
    def add_games_from_school(self, school_id):
        """Add all a school's games to dict_of_Games via add_game()."""
        
        conn = psycopg2.connect("dbname=game_data user=michael")
        cur = conn.cursor()
        cur.execute("""
            SELECT game_id, home_school_id, away_school_id
            FROM games WHERE %s IN (home_school_id, away_school_id)""",
            (school_id,))
        game_rows = cur.fetchall()
        
        for row in game_rows:
            self.add_game(g_id=row[0], conn=conn, home_id=row[1], away_id=row[2])
        cur.close()
        conn.close()
    
    # int, cursor, int, int, dict -> [void]
    def add_game(self, g_id, conn=None, home_id=None,away_id=None, roster=None):
        """Add individual games to dict_of_Games.
        
            This can be called by add_games_from_school, or independently. If
        called independently a new connection will have to be made and closed.
        """
        
        # Do nothing if it's already in the StatsObject.
        if g_id in self.dict_of_Games:
            return
        if conn is None:
            conn = psycopg2.connect("dbname=game_data user=michael")
            must_close_conn = True
        else:
            must_close_conn = False
        cur = conn.cursor()
        
        if home_id is None or away_id is None:
            cur.execute("""
                SELECT home_school_id, away_school_id
                FROM games WHERE game_id = %s""",
                (g_id,))
            home_id, away_id = cur.fetchone()
            
        # Ensure that the Player objects for this game are available.
        self.add_roster(cur, home_id)
        self.add_roster(cur, away_id)
        # If there's no roster provided, make a new dict from Players with
        # the right school IDs.
        if roster is None:
            roster = {p_id:P for p_id,P in self.dict_of_Players.iteritems()
                      if P.s_id in (home_id, away_id)}
                      
        # All actions dicts should be the same, so just use this object's.
        actions = self.actions_attributes
                
        self.dict_of_Games[g_id] = Game(
            self, conn, g_id, home=home_id, away=away_id, roster=roster,
            actions=actions)
            
        if must_close_conn:
            cur.close()
            conn.close()
    
    # list of Questions -> list of list of ints 
    def answer_Questions(self, list_of_Questions):
        """Distribute Questions and return their answers.
        
            Give each Question the roster so it can create Player objects. Then
        distribute them to each Game.
            See Question.get_result() for the return format.
        """
        
        for Q in list_of_Questions:
            Q.get_attrs_from_SO(self)
        for G in self.dict_of_Games.itervalues():
            G.add_data_to_Questions(list_of_Questions)
        
        results = [Q.get_results() for Q in list_of_Questions]
        return results
        
    # int, int -> set of frozensets of Players
    def get_combinations_size_n_from_school_lineups(self, n, school_id):
        """Get all combinations size n of Players of a team.
        
            By using the pool of player combinations that are already in
        lineups, the number of combinations is drastically reduced. There are
        15,504 combinations of 5 players from a team of 20, but in practice,
        there are only the low hundreds of them in use!
        """
        
        # All lineups of size 5 that have been used.
        lineups = set()
        for G in self.dict_of_Games.itervalues():
            lineups.update(G.get_lineups(school_id))
        combinations_of_Players = set()
        for lineup in lineups:
            combos = [frozenset(i) for i in itertools.combinations(lineup, n)]
            combinations_of_Players.update(combos)
        return combinations_of_Players
        
    # string -> int
    @staticmethod
    def get_one_id_matching_type(actions_attributes, action_type):
        """Get the first action ID matching the type given."""
        
        for action_id, attrs in actions_attributes.iteritems():
            if attrs["type"] == action_type:
                return action_id
                
    # string -> list of ints
    @staticmethod
    def get_all_ids_matching_type(actions_attributes, *action_types):
        """Get a list of all action IDs matching the type given."""
        
        ids = []
        types = tuple(action_types)
        for action_id, attrs in actions_attributes.iteritems():
            if attrs["type"] in types:
                ids += [action_id]
        return ids
    
    # set of ints (game IDs) -> return int
    def length_of_games(self, game_ids):
        """The length in minutes of all games given as input."""
    
        length = 0
        for game_id in game_ids:
            num_sections = len(self.dict_of_Games[game_id].section_indices)
            # The first two sections are 40 minutes; each one after is 5
            length += 40 + (num_sections - 2)*5
        return length
        
            
# string -> [void]
def error_msg(error):
    """Prints to the terminal and writes an error to statsobject.txt."""
    with open("statsobject.txt", 'a') as f:
        f.write(error + "\n")
    print error

# Just for debugging, not generally useful
# [no args] -> StatsObject
def getSO():
    SO = StatsObject()
    SO.add_games_from_school(554)
    for g in SO.dict_of_Games:
        print g

