class Brain:
    def __init__(self, name):
        self.name = name
    
    def get_action(self, game_state):
        return {"action": "call", "amount":0}

