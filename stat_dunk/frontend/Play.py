from __future__ import division

class Play:
    """This stores attributes of a single play event."""

    # int, Player, int, dict, int, set of Players, set of Players -> [void]
    def __init__(self, play_id, player, a_id, act_attr, time, section,
                 h_lineup=None, a_lineup=None):
        self.play_id = play_id             # int
        self.player = player               # Player object
        self.a_id = a_id                   # int (action id)
        self.actions_attributes = act_attr # dict (see StatsObject)
        self.time = time                   # int (time remaining in the section)
        self.section = section             # int (eg 3 means the first OT)
        if h_lineup is None: h_lineup = set()
        if a_lineup is None: a_lineup = set()
        self.lineups = {"home":frozenset(h_lineup), "away":frozenset(a_lineup)}
      
    # [no args] -> frozenset of Players  
    def both_lineups(self):
        """Return the lineups of both teams for this Play."""
        
        return self.lineups["home"].union(self.lineups["away"])

    # [no args] -> string
    def __repr__(self):
        time_str = str(self.time//60).zfill(2) +":"+ str(self.time%60).zfill(2)
        return "{t}   {p:20} {a} with {hl} ||| {al}".format(
            t=time_str, p=self.player.p_id,
            a=self.actions_attributes[self.a_id]["name"],
            hl=self.lineups["home"], al=self.lineups["away"])
       
    # [no args] -> string     
    def __str__(self):
        time_str = str(self.time//60).zfill(2) +":"+ str(self.time%60).zfill(2)
        h_lineup = ""
        for p in self.lineups["home"]:
            h_lineup += p.last + "; "
        h_lineup = h_lineup[:-2]
        a_lineup = ""
        for p in self.lineups["away"]:
            a_lineup += p.last + "; "
        a_lineup = a_lineup[:-2]
        # ANSI color escape codes for readability in the terminal
        green =      "\033[92m"
        blue =       "\033[94m"
        purple =     "\033[95m"
        light_blue = "\033[96m"
        red =        "\033[31m"
        end_color =  "\033[0m"
        # If a play isn't enter/leave, and the length of either lineup != 5,
        # add a + or * symbol to show extra/fewer players (can only show one).
        if not (self.actions_attributes[self.a_id]["type"] == "enter" or
                self.actions_attributes[self.a_id]["type"] == "leave"):
            if (len(self.lineups["home"]) == 0 or
                    self.player.s_id == list(self.lineups["home"])[0].s_id):
                action_color = green
            else:
                action_color = light_blue
            symbol = " "
        else:
            if (self.player.last != "TEAM" and
                    self.player not in self.lineups["home"] and 
                    self.player not in self.lineups["away"]):
                action_color = red
            else:
                action_color = blue
            if (len(self.lineups["home"]) < 5 or
                    len(self.lineups["away"]) < 5):
                symbol = red + "*" + end_color
            elif (len(self.lineups["home"]) > 5 or
                    len(self.lineups["away"]) > 5):
                symbol = red + "+" + end_color
            else:
                symbol = " "
        
        return ("{t}   {p:20.20}{s}{ac}{a}{ec} {pp}with{ec} "
                "{hl} {bl}|||{ec} {al}").format(
                   t=time_str, p=str(self.player), s=symbol,
                   a=self.actions_attributes[self.a_id]["name"], hl=h_lineup,
                   al=a_lineup, ac=action_color,pp=purple,bl=blue,ec=end_color)