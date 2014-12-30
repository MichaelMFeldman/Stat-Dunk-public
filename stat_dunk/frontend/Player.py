class Player:
    """This stores attributes of a single player."""
    
    # int, int, string, string, string -> [void]
    def __init__(self, p_id, s_id, last, first, title):
        self.p_id = p_id # int (player id)
        self.s_id = s_id # int (school id)
        self.last = last
        self.first = first
        self.title = title
        
    def __repr__(self):
        if self.title:
            return "{L}, {f}, {t}".format(
                L=self.last, f=self.first, t=self.title)
        else:
            return "{L}, {f}".format(L=self.last, f=self.first)