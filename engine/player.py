class Player:
    def __init__(self, name, brain):
        self.name = name
        self.brain = brain
        self.hand = []
        self.stack = 1000
        self.bet = 0
        self.action = None
        self.position = None
        self.is_active = True
        self.is_all_in = False
        self.is_folded = False
        self.is_sitting_out = False

    
    def execute_action(self, action_dict):

        action = action_dict.get("action")
        amount = action_dict.get("amount", 0)

        if action == "call":
            return self.call(amount)

        elif action == "raise":
            return self.raise_bet(amount)

        elif action == "fold":
            return self.fold()

        elif action == "check":
            return self.check()

        else:
            raise ValueError(f"Unknown action: {action}")


    def call(self, amount):
        self.stack -= amount
        self.bet += amount
        return amount
    
    def raise_bet(self, amount):
        self.stack -= amount
        self.bet += amount
        return amount
    
    def fold(self):
        self.is_active = False
        self.is_folded = True
        return True
    
    def check(self):
        return True
    