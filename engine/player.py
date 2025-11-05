class Player:
    def __init__(self, name, brain, starting_stack):
        self.wins = 0
        self.name = name
        if isinstance(brain, type):
            self.brain = brain()  # Instantiate it
        else:
            self.brain = brain
        self.hand = []
        self.stack = starting_stack
        self.bet = 0
        self.action = None
        self.position = None
        self.is_active = True
        self.is_all_in = False
        self.is_folded = False
        self.is_sitting_out = False



    def get_action(self, game_state):
        return self.brain.get_action(game_state)
    