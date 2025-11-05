from engine.brain import Brain
import random

class RandomBot(Brain):
    def __init__(self):
        super().__init__()

    def get_action(self, game_state):
        valid_actions = game_state["valid_actions"]
        action = random.choice(valid_actions)

        if action == "fold":
            return {"action": "fold"}
        # Check
        if action == "check":
            return {"action": "check"}
        # Call
        if action == "call":
            return {"action": "call"}

        # Bet 50 chips
        if action == "bet":
            return {"action": "bet", "amount": 50}

        # Raise by 100 chips
        if action == "raise":
            return {"action": "raise", "amount": 100}

        return random.choice(valid_actions)


