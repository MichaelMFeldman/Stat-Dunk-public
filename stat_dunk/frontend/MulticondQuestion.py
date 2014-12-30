from __future__ import division
from Player import Player
from Question import Question
from StatsObject import StatsObject
from collections import defaultdict

"""
                     *** Multiconditional Questions ***
    For documentation of inherited or overridden attributes or methods,
see Question.py.
    Questions can only record stats in one condition: one set of players on
court, players not on court, players making actions, etc. Stats like assist
rate (player assists divided by teammate field goals) need to record stats in
*two* conditions, for instance:
    - Player X is on the court and his/her actions (to get assists)
    - Player X is on the court and teammates' actions (to get FGs)
    For simplicity, each multiconditional question will be its own class, so
overridden functions can handle/report data specifically to the stats they're
supposed to calculate.
    It's often only necessary to add a little functionality to certain methods
that initialize many attributes, so they'll sometimes be called from the parent
Question class first. Then the new attributes are initialized.
"""

class AST_rate_Q(Question):
    """Player assists / Teammate FGM
    
        Instance attributes:
    make_assists: frozenset of Players. Record assists by these Players.
    make_FGs: frozenset of Players. Record field goals by these Players.
    AST_id: int (action ID). Assist.
    FGM_ids: set of ints (action IDs). Field goals made.
    """

    # OVERRIDE
    # set of ints (game ids), set of Players or ints (player ids),
    #                                      same as prev, same as prev -> [void]
    def __init__(self, games=None, on_court=None, not_on_court=None,
                 requested_players=None):
    
        Question.__init__(self, games=games, on_court=on_court,
                          not_on_court=not_on_court)
        self.requested_players = requested_players if requested_players else set()

    # OVERRIDE
    # StatsObject -> [void]
    def get_attrs_from_SO(self, SO):
    
        Question.get_attrs_from_SO(self, SO)
        self.AST_id = self.get_action_ids_from_type("AST").pop()
        self.FGM_ids = self.get_action_ids_from_type("FGM")
        self.player_school = next(iter(self.requested_players)).s_id
    
    # OVERRIDE
    # {int (player ID): Player} -> [void]
    def turn_p_ids_into_Players(self, roster):
    
        Question.turn_p_ids_into_Players(self, roster)
        self.requested_players = Question.convert_set(
            self, self.requested_players, roster)
    
    # OVERRIDE
    # Play -> returns bool
    def play_is_requested(self, play):
        player = play.player
        a_id =   play.a_id
        is_req_player = player in self.requested_players and a_id == self.AST_id
        is_teammate = (player not in self.requested_players and
                       player.s_id == self.player_school and
                       a_id in self.FGM_ids)
        
        return is_req_player or is_teammate
    
    # OVERRIDE
    # [no args] -> returns list of basic info, and a float
    def get_results(self):
    
        AST_total = self.actions_totals[self.AST_id]
        FG_total = self.get_total_of_type("FGM")
        basic_info = Question.get_results(self)
        # If there's a div 0 error, then there are no FGs; therefore, there are
        # no assists either. Just return 0.
        try:
            result = AST_total / FG_total
        except ZeroDivisionError:
            result = 0
        return basic_info + [result]
            
            
class REB_rate_Q(Question):
    """Offensive or defensive rebound rate.
    
    "OREB"/"DREB" is referred to as the type in this class.
    
    This is the percentage of all [type] rebounds available to a player that
    he/she makes.
    
        Instance attributes:
    requested_players: frozenset of Players. Record [type] rebounds.
    player_school: int (school ID).
    rebound_type: string. "DREB" or "OREB". The type requested.
    REB_type_id: int (action ID).
    other_reb_type: string. "DREB" or "OREB".
    REB_other_type_id: int (action ID).
    player_rebounds: int. Number of [type] rebounds made by requested_players.
    team_rebounds: int. Number of [type] rebounds made by the team.
    opponent_rebounds: Number of opponent team's [other type] rebounds.
    """
    
    # OVERRIDE
    # set of ints (game ids), set of Players or ints (player ids),
    #                              same as prev, same as prev, string -> [void]
    def __init__(self, games=None, on_court=None, not_on_court=None,
                 requested_players=None, rebound_type="OREB"):
                 
        Question.__init__(self, games=games, on_court=on_court,
                          not_on_court=not_on_court)
        self.requested_players = requested_players if requested_players else set()
        self.rebound_type = rebound_type
        self.other_reb_type = "DREB" if rebound_type == "OREB" else "OREB"
        
        self.player_rebounds = 0
        self.team_rebounds = 0
        self.opponent_rebounds = 0

    # OVERRIDE
    # StatsObject -> [void]
    def get_attrs_from_SO(self, SO):
    
        Question.get_attrs_from_SO(self, SO)
        self.REB_type_id = StatsObject.get_one_id_matching_type(
            self.actions_attributes, self.rebound_type)
        self.REB_other_type_id = StatsObject.get_one_id_matching_type(
            self.actions_attributes, self.other_reb_type)
        self.player_school = next(iter(self.requested_players)).s_id
    
    # OVERRIDE
    # {int (player ID): Player} -> [void]
    def turn_p_ids_into_Players(self, roster):

        Question.turn_p_ids_into_Players(self, roster)
        self.requested_players = Question.convert_set(
            self, self.requested_players, roster)        
    
    # OVERRIDE
    # Play, int -> [void]
    def add_data_as_applicable(self, play, game_id):
        """Increment each total as according to the requested attributes.
        
            Verifying that this is a correct Play and adding information is
        generally separated, but because adding information is done differently
        depending on which type of Play this is, verification and addition is
        done most simply in one method.
        """
        
        lineup_is_correct_ans = self.lineup_is_correct(play.both_lineups())
        if lineup_is_correct_ans:
            self.games_played_in.add(game_id)
            player = play.player
            a_id =   play.a_id
            # Requested player makes the requested rebound type:
            if (player in self.requested_players and
                    a_id == self.REB_type_id):
                self.player_rebounds += 1
            # Requested players' team makes the requested rebound type:
            if (player.s_id == self.player_school and
                    a_id == self.REB_type_id):
                self.team_rebounds += 1
            # Opponent's team makes the other rebound type:
            elif (player.s_id != self.player_school and
                    a_id == self.REB_other_type_id):
                self.opponent_rebounds += 1
                    
        self.update_timeline(play.time, play.section,
                             lineup_is_correct_ans, game_id)
    
    # OVERRIDE
    # [no args] -> returns list of basic info, and a float
    def get_results(self):
        basic_info = Question.get_results(self)
        basic_info[0]["total_all"] = self.player_rebounds
        try:
            result = 100 * (self.player_rebounds /
                         (self.team_rebounds + self.opponent_rebounds))
        except ZeroDivisionError:
            result = "infinite" if self.player_rebounds > 0 else 0
        return basic_info + [result]


class offensive_rtg_Q(Question):
    """Offensive rating.
    
        Instance attributes: 
    requested_players: frozenset of Players. Report their Offensive rtg.
    player_school: int (school ID). The school ID of the requested players.
    team_actions_totals: a defaultdict like actions_totals. Records actions by
        the whole players' team.
    opponent_DREB: int. Number of defensive rebounds made by the oppt. team.
    DREB_id: int (action ID).
    """
    
    # OVERRIDE
    # set of ints (game ids), set of Players or ints (player ids),
    #                                      same as prev, same as prev -> [void]
    def __init__(self, games=None, on_court=None, not_on_court=None,
                 requested_players=None):
    
        Question.__init__(self, games=games, on_court=on_court,
                          not_on_court=not_on_court)
        self.requested_players = requested_players if requested_players else set()
        # In addition to action_totals which is for the requested players:
        self.team_actions_totals = defaultdict(int) # All actions default to 0
        self.opponent_DREB = 0

    # OVERRIDE
    # StatsObject -> [void]
    def get_attrs_from_SO(self, SO):
    
        Question.get_attrs_from_SO(self, SO)
        self.player_school = next(iter(self.requested_players)).s_id
        self.DREB_id = self.get_action_ids_from_type("DREB").pop()

    # OVERRIDE
    # {int (player ID): Player} -> [void]
    def turn_p_ids_into_Players(self, roster):

        Question.turn_p_ids_into_Players(self, roster)
        self.requested_players = Question.convert_set(
            self, self.requested_players, roster)

    # OVERRIDE
    # Play, int -> [void]
    def add_data_as_applicable(self, play, game_id):
        
        lineup_is_correct_ans = self.lineup_is_correct(play.both_lineups())
        if lineup_is_correct_ans:
            self.games_played_in.add(game_id)
            player = play.player
            a_id =   play.a_id
            # Record all requested player actions actions:
            if player in self.requested_players:
                self.actions_totals[a_id] += 1
            # Record all team actions:
            if player.s_id == self.player_school:
                self.team_actions_totals[a_id] += 1
            # Opponent team makes a defensive rebound:
            elif a_id == self.DREB_id:
                self.opponent_DREB += 1
        
        self.update_timeline(play.time, play.section,
                             lineup_is_correct_ans, game_id)
    
    # OVERRIDE
    # [no args] -> returns [basic info, float]
    def get_results(self):
        basic_info = Question.get_results(self)
        
        # Formula from http://www.basketball-reference.com/about/ratings.html
        # Tweaked slightly to replace 0.4 with 0.475
        MP = self.get_minutes_played()
        FGM = self.calculate_totals("FGM", self.actions_totals)
        FGA = self.calculate_totals("FGA", self.actions_totals)
        FGM_3 = self.calculate_totals("made_3FG", self.actions_totals)
        FTM = self.calculate_totals("FTM", self.actions_totals)
        FTA = self.calculate_totals("FTA", self.actions_totals)
        TOV = self.calculate_totals("TOV", self.actions_totals)
        OREB = self.calculate_totals("OREB", self.actions_totals)
        AST = self.calculate_totals("AST", self.actions_totals)
        PTS = self.calculate_points(self.actions_totals)
        
        team_MP = self.SO.length_of_games(self.games_played_in)
        team_FGM = self.calculate_totals("FGM", self.team_actions_totals)
        team_FGA = self.calculate_totals("FGA", self.team_actions_totals)
        team_FGM_3 = self.calculate_totals("made_3FG", self.team_actions_totals)
        team_FTM = self.calculate_totals("FTM", self.team_actions_totals)
        team_FTA = self.calculate_totals("FTA", self.team_actions_totals)
        team_TOV = self.calculate_totals("TOV", self.team_actions_totals)
        team_AST = self.calculate_totals("AST", self.team_actions_totals)
        team_OREB = self.calculate_totals("OREB", self.team_actions_totals)
        team_PTS = self.calculate_points(self.team_actions_totals)
        
        opp_DREB = self.opponent_DREB
        
        # I apologize to anyone trying to read this. It's somewhat clearer on
        # the website linked above.
        
        # In the event of a division by zero, some action never occured. It can
        # be assumed that there is insufficient information to calculate ORtg,
        # so return 0.
        
        try:
         # - Scoring possessions -
         qAST = (((MP /(team_MP/5)) * (1.14 * ((team_AST - AST) / team_FGM))) +
                (  (((team_AST / team_MP) * MP * 5 - AST) /
                    ((team_FGM / team_MP) * MP * 5 - FGM)
                   ) *
                   (1 - (MP / (team_MP / 5)))
                ))
        
         FG_Part = FGM * (1 - 0.5*((PTS - FTM) / (2 * FGA)) * qAST)
         
         AST_Part = 0.5 * (((team_PTS - team_FTM) - (PTS - FTM)) / (2 * (team_FGA - FGA))) * AST
        
         FT_Part = (1 - (1 - (FTM/FTA))**2) * 0.475 * FTA
        
         Team_scoring_poss = team_FGM + (1 - (1 - (team_FTM / team_FTA))**2) * team_FTA * 0.475
        
         Team_OREB_percent = team_OREB / (team_OREB + opp_DREB)
        
         Team_play_percent = Team_scoring_poss / (team_FGA + team_FTA*0.475 + team_TOV)
        
         Team_OREB_Weight = (((1 - Team_OREB_percent) * Team_play_percent) / 
                             ((1 - Team_OREB_percent) * Team_play_percent + Team_OREB_percent * (1 - Team_play_percent))
                            )
                           
         OREB_Part = OREB * Team_OREB_Weight * Team_play_percent
        
         Scoring_possessions = (FG_Part + AST_Part + FT_Part) * (1 - (team_OREB / Team_scoring_poss) *
                                                                 Team_OREB_Weight * Team_play_percent) + OREB_Part
        
         # - Missed FG and Missed FT Possessions -
         FGxPoss = (FGA - FGM) * (1 - 1.07 * Team_OREB_percent)
         FTxPoss = ((1 - (FTM / FTA))**2) * 0.475 * FTA
        
         # --- Total possessions ---
         Total_possessions = Scoring_possessions + FGxPoss + FTxPoss + TOV
        
         # --- Individual points produced ---
         PProd_FG_Part = 2 * (FGM + 0.5*FGM_3) * (1 - 0.5 * ((PTS - FTM) / (2 * FGA)) * qAST)
        
         PProd_AST_Part = (2 * ((team_FGM - FGM + 0.5*(team_FGM_3 - FGM_3)) / (team_FGM - FGM)) * 0.5 *
                            (((team_PTS - team_FTM) - (PTS - FTM)) / (2 * (team_FGA - FGA))) * AST)
        
         PProd_ORB_Part = OREB * Team_OREB_Weight * Team_play_percent * (team_PTS / 
                          (team_FGM + (1 - (1 - (team_FTM / team_FTA))**2) * 0.475 * team_FTA))
        
         PProd = (PProd_FG_Part + PProd_AST_Part + FTM) * (1 - (team_OREB / Team_scoring_poss) * 
                  Team_OREB_Weight * Team_play_percent) + PProd_ORB_Part
        
         # --- Offensive rating ---
         ORtg = 100 * (PProd / Total_possessions)
        
         return basic_info + [ORtg]
        except ZeroDivisionError:
         return basic_info + [0]
    
    
class defensive_rtg_Q(Question):
    """Defensive rating.
    
        Instance attributes: 
    requested_players: frozenset of Players. Report their Offensive rtg.
    player_school: int (school ID). The school ID of the requested players.
    team_actions_totals: a defaultdict like actions_totals. Records actions by
        the whole players' team.
    opponent_actions_totals: same as above. Record actions by the oppt. team.
    """
    
    # OVERRIDE
    # set of ints (game ids), set of Players or ints (player ids),
    #                                      same as prev, same as prev -> [void]
    def __init__(self, games=None, on_court=None, not_on_court=None,
                 requested_players=None):
    
        Question.__init__(self, games=games, on_court=on_court,
                          not_on_court=not_on_court)
        self.requested_players = requested_players if requested_players else set()
        # In addition to action_totals which is for the requested players:
        self.team_actions_totals =     defaultdict(int)
        self.opponent_actions_totals = defaultdict(int)

    # OVERRIDE
    # StatsObject -> [void]
    def get_attrs_from_SO(self, SO):
    
        Question.get_attrs_from_SO(self, SO)
        self.player_school = next(iter(self.requested_players)).s_id
    
    # OVERRIDE
    # {int (player ID): Player} -> [void]
    def turn_p_ids_into_Players(self, roster):

        Question.turn_p_ids_into_Players(self, roster)
        self.requested_players = Question.convert_set(
            self, self.requested_players, roster)

    # OVERRIDE
    # Play, int -> [void]
    def add_data_as_applicable(self, play, game_id):
        """Increment each total as according to the requested attributes."""
        
        lineup_is_correct_ans = self.lineup_is_correct(play.both_lineups())
        if lineup_is_correct_ans:
            self.games_played_in.add(game_id)
            player = play.player
            a_id =   play.a_id
            # Record all requested player actions actions:
            if player in self.requested_players:
                self.actions_totals[a_id] += 1
            # Record all team actions:
            if player.s_id == self.player_school:
                self.team_actions_totals[a_id] += 1
            # Record all opponent team actions:
            else:
                self.opponent_actions_totals[a_id] += 1
        
        self.update_timeline(play.time, play.section,
                             lineup_is_correct_ans, game_id)
    
    # OVERRIDE
    # [no args] -> returns [basic info, float]
    def get_results(self):
        """See notes of get_results in the offensive rating class."""
        
        basic_info = Question.get_results(self)
        
        MP = self.get_minutes_played()
        STL = self.calculate_totals("STL", self.actions_totals)
        BLK = self.calculate_totals("BLK", self.actions_totals)
        DREB = self.calculate_totals("DREB", self.actions_totals)
        PF = self.calculate_totals("foul", self.actions_totals)
        
        team_MP = self.SO.length_of_games(self.games_played_in)
        team_OREB = self.calculate_totals("OREB", self.team_actions_totals)
        team_DREB = self.calculate_totals("DREB", self.team_actions_totals)
        team_FGM = self.calculate_totals("FGM", self.team_actions_totals)
        team_FGA = self.calculate_totals("FGA", self.team_actions_totals)
        team_FTA = self.calculate_totals("FTA", self.team_actions_totals)
        team_STL = self.calculate_totals("STL", self.team_actions_totals)
        team_BLK = self.calculate_totals("BLK", self.team_actions_totals)
        team_TOV = self.calculate_totals("TOV", self.team_actions_totals)
        team_PF = self.calculate_totals("foul", self.team_actions_totals)
        
        opponent_MP = team_MP
        opponent_OREB = self.calculate_totals("OREB", self.opponent_actions_totals)
        opponent_DREB = self.calculate_totals("DREB", self.opponent_actions_totals)
        opponent_FGM = self.calculate_totals("FGM", self.opponent_actions_totals)
        opponent_FGA = self.calculate_totals("FGA", self.opponent_actions_totals)
        opponent_FTM = self.calculate_totals("FTM", self.opponent_actions_totals)
        opponent_FTA = self.calculate_totals("FTA", self.opponent_actions_totals)
        opponent_TOV = self.calculate_totals("TOV", self.opponent_actions_totals)
        opponent_PTS = self.calculate_points(self.opponent_actions_totals)
        
        try:        
         DOR_percent = opponent_OREB / (opponent_OREB + team_DREB)
        
         DFG_percent = opponent_FGM / opponent_FGA
        
         FMwt = (DFG_percent * (1 - DOR_percent)) / (DFG_percent * (1 - DOR_percent) +
                                                   (1 - DFG_percent) * DOR_percent)
        
         Stops1 = STL + BLK * FMwt * (1 - 1.07 * DOR_percent) + DREB * (1 - FMwt)
        
         Stops2 = (((opponent_FGA - opponent_FGM - team_BLK) / team_MP) * FMwt * (1 - 1.07 * DOR_percent) +
                   ((opponent_TOV - team_STL) / team_MP)) * MP + (PF / team_PF) * 0.475*opponent_FTA * (1 - (opponent_FTM / opponent_FTA))**2
        
         Team_possessions = 0.5 * ((team_FGA + 0.475*team_FTA - 1.07*(team_OREB / (team_OREB + opponent_DREB)) * (team_FGA - team_FGM) + team_TOV) +
                             (opponent_FGA + 0.475*opponent_FTA - 1.07*(opponent_OREB / (opponent_OREB + team_DREB)) * (opponent_FGA - opponent_FGM) +
                             opponent_TOV))
        
         Stops = Stops1 + Stops2
        
         Stop_percent = (Stops * opponent_MP) / (Team_possessions * MP)
        
         Team_defensive_rating = 100 * (opponent_PTS / Team_possessions)
        
         D_Pts_per_ScPoss = opponent_PTS / (opponent_FGM + (1 - (1 - (opponent_FTM / opponent_FTA))**2) * opponent_FTA*0.475)
        
         DRtg = Team_defensive_rating + 0.2 * (100 * D_Pts_per_ScPoss * (1 - Stop_percent) - Team_defensive_rating)
        
         return basic_info + [DRtg]
        except ZeroDivisionError:
         return basic_info + [0]