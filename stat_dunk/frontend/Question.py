from __future__ import division
from collections import defaultdict
from Player import Player
from StatsObject import StatsObject

"""
Question
    Setup/initialization methods
    Play data processing methods
    Result calculation methods
    Timeline creation/reporting methods
"""

class Question:
    """Each Question is given all Play data, and then can answer itself.
    
        Instance attributes:
    SO: StatsObject.
    games: set of Games. These games' data will be processed.
    on_court: frozenset of Players. Only add Plays with these Players on court.
    not_on_court: frozenset of Players. Exclude Plays with these Players on court.
    who_made_action: frozenset of Players. Only add Plays made by these Players.
    not_made_action: frozenset of Players. Exclude Plays made by these Players.
    actions_requested: tuple of action IDs. Order is important to some
        calculations, eg rate and percent.
    how_to_calculate: tuple of Question methods.
    points_requested: bool. Determines whether the points or the sum of certain
        actions are what are calculated per minute, per game, etc.
    games_played_in: set() of Game IDs. This is to calculate "per game" stats.
    action_totals: {int (action ID): int}. A defaultdict mapping action IDs
        to the total number of times that action occured in the conditions
        specified by other attributes.
    type_totals: {string: int}. Used by get_total_of_type to return results
        more quickly. A dictionary mapping types (eg "missed_2FG" refers to one
        action; "FGA" (field goal attempt) refers to many actions, including
        "missed_2FG") to their total occurances similar to action_totals.
    timelines: {int (game ID): {int (section): [span]}}. See comment below.
    """

    # set of ints (game ids), set of Players or ints (player ids),
    #     same as prev, same as prev, same as prev, same as prev,
    #     tuple of ints, tuple of Question methods, bool -> [void]
    def __init__(self, games=None, on_court=None, not_on_court=None,
                 who_made_action=None, not_made_action=None,
                 actions_requested=None, how_to_calculate=None,
                 points_requested=False):
        # All 'set of Player' attrs will be turned into frozensets of Players.
        self.games =             games             if games             else set()
        self.on_court =          on_court          if on_court          else set()
        self.not_on_court =      not_on_court      if not_on_court      else set()
        self.who_made_action =   who_made_action   if who_made_action   else set()
        self.not_made_action =   not_made_action   if not_made_action   else set()
        self.actions_requested = actions_requested if actions_requested else ()
        self.how_to_calculate =  how_to_calculate  if how_to_calculate  else ()
        self.points_requested =  points_requested
        
        self.games_played_in = set()
        self.actions_totals = defaultdict(int) # All actions default to 0
        self.type_totals = {}
        self.timelines = {}
        
    # StatsObject -> [void]
    def get_attrs_from_SO(self, SO):
        """Take the necessary attributes from the relevant StatsObject."""
        
        self.SO = SO
        self.actions_attributes = SO.actions_attributes
        self.turn_p_ids_into_Players(SO.dict_of_Players)
            
    # {int (player ID): Player} -> [void]
    def turn_p_ids_into_Players(self, roster):
        """Turn the sets of player IDs into sets of Players.
        
            Also useful in child classes for initializations that require
        Player objects.
        """
        
        self.on_court =        self.convert_set(self.on_court, roster)
        self.not_on_court =    self.convert_set(self.not_on_court, roster)
        self.who_made_action = self.convert_set(self.who_made_action, roster)
        self.not_made_action = self.convert_set(self.not_made_action, roster)
        
    # set of ints or Players, dict -> returns frozenset of Players
    def convert_set(self, set, roster):
        players = []
        for P in set:
            if isinstance(P, Player): players += [P]
            else:                     players += [roster[P]]
        return frozenset(players)
    
    """
    BEGIN PLAY DATA PROCESSING METHODS
    """
    
    # Play, int -> [void]
    def add_data_as_applicable(self, play, game_id):
        """If this Play meets the conditions asked, increment the total."""
        
        lineup_is_correct_ans = self.lineup_is_correct(play.both_lineups())
        if lineup_is_correct_ans:
            self.games_played_in.add(game_id)
            if self.play_is_requested(play):
                self.actions_totals[play.a_id] += 1
                    
        self.update_timeline(play.time, play.section,
                             lineup_is_correct_ans, game_id)
    
    # frozenset of Players -> returns bool
    def lineup_is_correct(self, both_lineups):
        """Do the on_court and not_on_court sets match this Play?"""
    
        return (self.on_court <= both_lineups and
                self.not_on_court.isdisjoint(both_lineups))
            
    # Play -> returns bool
    def play_is_requested(self, play):
        """Did a requested Player make a requested action?
        
            Having the whole Play is necessary for child classes with more
        specific tests, eg which action is made.
        """
        
        player = play.player
        return (player in self.who_made_action and
                player not in self.not_made_action)
                
    """
    END PLAY DATA PROCESSING METHODS

    BEGIN RESULT CALCULATION METHODS
    """
            
    # [no args] -> returns list of ints or floats
    def get_results(self):
        """Calculate the results from totals per the requested methods.
        
            Answers are given as elements in a list in the order the requested
        methods were provided. The first element of the list is a dict containing:
        the number of each requested action, the single total of all those actions,
        the number of points, the games applicable, and the number of minutes
        all made/played under the conditions requested in this Question.
        """
    
        sum_of_actions = sum(self.actions_totals.itervalues())
        results = [{"total_each": self.actions_totals,
                    "total_all":  sum_of_actions,
                    "points":     self.get_points(),
                    "minutes":    self.get_minutes_played(),
                    "games":      self.games_played_in}]
        if self.points_requested:
            self.requested_total = self.get_points()
        else:
            self.requested_total = sum_of_actions
        
        for calculation_method in self.how_to_calculate:
            try:
                results += [calculation_method(self)]
            except ZeroDivisionError:
                results += ["infinite" if self.requested_total > 0 else 0]
                
        return results
    
    # [no args] -> int
    def get_points(self):
        """Get and store points of all actions recorded."""
        
        try:
            return self.points
        except AttributeError:
            self.points = self.calculate_points(self.actions_totals)
            return self.points
            
    # {int (action ID): int} -> int
    def calculate_points(self, actions_totals):
        """Get points of all actions from a specific dict."""
        
        self.points = 0
        for a_id, total in actions_totals.iteritems():
            self.points += total * self.actions_attributes[a_id]["points"]
        return self.points
            
    # [no args] -> int
    def calc_total(self):
        """The raw total of requested actions."""
    
        return self.requested_total
         
    # [no args] -> float
    def calc_per_game(self):
        """The total requested actions or points per game played."""
    
        return self.requested_total / len(self.games_played_in)
    
    # [no args] -> float    
    def calc_per_minute(self):
        """The total requested actions or points per minute played."""
    
        return self.requested_total / self.get_minutes_played()
    
    # [no args] -> float
    def calc_rate(self):
        """The simple rate of the first to the second action requested."""
    
        if len(self.actions_requested) != 2:
            return None
        numerator_action =   self.actions_totals[self.actions_requested[0]]
        denominator_action = self.actions_totals[self.actions_requested[1]]
        return numerator_action / denominator_action
    
    # [no args] -> float
    def calc_percent(self):
        """The rate of the first action requested to the total of the first and
        second actions requested, expressed as a percentage."""
    
        if len(self.actions_requested) != 2:
            return None
        made =   self.actions_totals[self.actions_requested[0]]
        missed = self.actions_totals[self.actions_requested[1]]
        return 100 * (made / (made + missed))
    
    # [no args] -> float
    def effective_field_goal_percentage(self):
        """(2PFG + 0.5*3PFG) / FGA"""
        
        twoFG =   self.get_total_of_type("made_2FG")
        threeFG = self.get_total_of_type("made_3FG")
        FGA =     self.get_total_of_type("FGA")
        return (twoFG + 0.5*threeFG) / FGA
    
    # [no args] -> float
    def true_shooting_percentage(self):
        
        PTS = self.get_points()
        FGA = self.get_total_of_type("FGA")
        FTA = self.get_total_of_type("FTA")
        return (PTS * 100) / (2 * (FGA + 0.475*FTA))
    
    # [no args] -> float
    def turnover_rate(self):
        
        TOV = self.get_total_of_type("TOV")
        FGA = self.get_total_of_type("FGA")
        FTA = self.get_total_of_type("FTA")
        return (100 * TOV) / (FGA + 0.475*FTA + TOV)
    
    # [no args] -> float
    def assist_turnover_ratio(self):
        
        return self.get_total_of_type("AST") / self.get_total_of_type("TOV")
                
    # [no args] -> int
    def get_possessions(self):
        """An approximation of player possessions."""
    
        FGA = self.get_total_of_type("FGA")
        FTA = self.get_total_of_type("FTA")
        TOV = self.get_total_of_type("TOV")
        ORB = self.get_total_of_type("OREB")
        return FGA - ORB + 0.475*FTA + TOV
        
    # string -> int
    def get_total_of_type(self, action_type):
        """Given an action type, get and store the total occurances."""
        
        try:
            return self.type_totals[action_type]
        except KeyError:
            total = self.calculate_totals(action_type, self.actions_totals)
            self.type_totals[action_type] = total
            return total
    
    # string, {int (action ID): int} -> int
    def calculate_totals(self, action_type, actions_totals):
        """Given an action type, get the total occurances."""
        
        action_ids = self.get_action_ids_from_type(action_type)
        total = sum([actions_totals[x] for x in action_ids])
        self.type_totals[action_type] = total
        return total
        
    # string -> returns set of ints
    def get_action_ids_from_type(self, action_type):
        """Get the set of action IDs associated with this type."""
    
        # This ensures that all types totals can be calculated with the
        # same function, and that even the "supertypes" (eg FGA, FTA) can be
        # stored in self.type_totals.
        action_ids = set() # All action ids this type refers to.
        if action_type == "FGA":
            action_ids.update(StatsObject.get_all_ids_matching_type(
                self.actions_attributes,
                "made_2FG", "missed_2FG", "made_3FG", "missed_3FG"))
        elif action_type == "FTA":
            action_ids.update(StatsObject.get_all_ids_matching_type(
                self.actions_attributes, "made_FT", "missed_FT"))
        elif action_type == "FGM":
            action_ids.update(StatsObject.get_all_ids_matching_type(
                self.actions_attributes, "made_2FG", "made_3FG"))
        else:
            action_ids.update(StatsObject.get_all_ids_matching_type(
                self.actions_attributes, action_type))
        return action_ids
        
    """
    END RESULT CALCULATION METHODS
    
    BEGIN TIMELINE METHODS
        self.timelines is {int (game ID): {int (section): [span]}}
        Each span is a dict with the following keys/values:
          {"type": bool,    Is this lineup the one specified in this Question?
           "start": int,    When this lineup type entered the court
           "end": int}      When this lineup type left the court
    So an example timeline might be: [{"type":True,"start":1200,"end":1185},
    {"type":False,"start":1183,"end":70}, {"type":True,"start":70,"end":3}]
        In this case, the lineup requested began on the court until 1185 and
    reentered at 70 until the end of the section.
        Note self.timelines[g_id][section][-1] refers to the most recent span.
    """
    
    # int, bool, int -> [void]
    def update_timeline(self, time, section, is_correct, g_id):
        """Make a record of which minutes a given lineup was on the court."""
        
        try:
          # If this Play is the same type as the most recent one, just update
          # the time that the lineup goes to.
          if self.timelines[g_id][section][-1]["type"] is is_correct:
              self.timelines[g_id][section][-1]["end"] = time
          # Else, this play is a different type. Add a new span.
          else:
              span = {"type":is_correct, "start":time, "end":time}
              self.timelines[g_id][section] += [span]
        # No spans for this section, so add the first.
        except KeyError:
          begin_time = 1200 if section <=2 else 300
          span = {"type": is_correct, "start": begin_time, "end": time}
          try:
            self.timelines[g_id][section] = [span]
          # No entries for this game at all!            
          except KeyError:
            self.timelines[g_id] = {section: [span]}
        
    # [no args] -> returns float
    def get_minutes_played(self):
        """Return the number of minutes played with the requested lineup."""
        
        try:
          return self.minutes_played
        except AttributeError:
          seconds = 0
          for game in self.timelines.itervalues():
              for section in game.itervalues():
                  # Iterate with an index because the compensate functions need
                  # to look at previous or next spans.
                  # Each section[i] is a span dict.
                  for i in range(len(section)):
                      lineup_is_correct = section[i]["type"]
                      start_time =        section[i]["start"]
                      end_time =          section[i]["end"]
                      if lineup_is_correct:
                          seconds += start_time - end_time
                          seconds += self.error_compensate_left(section, i)
                          seconds += self.error_compensate_right(section, i)
          self.minutes_played = seconds / 60
          return self.minutes_played
    
    # list of lists, int -> returns float
    def error_compensate_left(self, timeline, i):
        """Returns extra time a lineup might be on the court.
        
            This looks at the times between the current time span and the span
        before it, and returns extra time as appropriate.
        """
            
        # If there's nothing to the left to compensate: return 0, because all
        # timelines start at the correct time.
        if i == 0:
            return 0
        # Otherwise, return extra time in one of two ways:
        #     1) If the previous span begins and ends at the same time, don't
        # count it. (Lineups are sometimes poorly approximated for enter/leave
        # plays, which is otherwise not a problem.) Return all the time between
        # its end time and the current start time.
        #     2) In most cases, simply return half the time between the
        # previous end time and the current start time. Note that this is only
        # an approximation!
        elif timeline[i-1]["start"] == timeline[i-1]["end"]:
            return (timeline[i-1]["end"] - timeline[i]["start"])
        else:
            return (timeline[i-1]["end"] - timeline[i]["start"]) / 2
    
    # list of lists, int -> returns float             
    def error_compensate_right(self,timeline, i):
        """See error_compensate_left - this is essentially flipped."""
        
        # If there's nothing to the right to compensate: return all the extra
        # time, because there's no guarantee that the last span will end at 0.
        if i == len(timeline)-1:
            return timeline[i]["end"]
        elif timeline[i+1]["start"] == timeline[i+1]["end"]:
            return (timeline[i]["end"] - timeline[i+1]["start"])
        else:
            return (timeline[i]["end"] - timeline[i+1]["start"]) / 2
            
    """
    END TIMELINE METHODS
    """

