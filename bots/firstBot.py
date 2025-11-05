from engine.brain import Brain
import random
import json
from treys import Card, Evaluator

class FirstBot(Brain):
    def __init__(self):
        super().__init__()

    def get_action(self, game_state):
        valid_actions = game_state["valid_actions"]
        player = game_state["player"]
        hand = player["hand"]
        board = game_state.get("community_cards", [])
        street = game_state.get("street", "")
        evaluator = Evaluator()

        # --- PRE-FLOP LOGIC ---
        #Always call pre flop if possible
        if street.lower() == "pre-flop":
            if "call" in valid_actions:
                return {"action": "call"}
            else:
                return {"action": "fold"}

        # --- POST-FLOP EVALUATION ---
        if len(board) == 0:
            score = evaluator.evaluate([], hand)
        else:
            score = evaluator.evaluate(board, hand)

        hand_rank = evaluator.get_rank_class(score)
        hand_name = evaluator.class_to_string(hand_rank)

        # Mapping: 1=Royal Flush ... 10=High Card
        # Pair or better → rank <= 9
        # Straight or better → rank <= 6

        # --- FOLD if worse than Pair ---
        if hand_rank == 9:  # High card only
            if "fold" in valid_actions:
                return {"action": "fold"}

        # --- ALL-IN if Straight or better ---
        if hand_rank <= 6:
            if "raise" in valid_actions:
                return {"action": "raise", "amount": player["stack"]}
            elif "bet" in valid_actions:
                return {"action": "bet", "amount": player["stack"]}

        # --- Otherwise: Check or Call ---
        if "check" in valid_actions:
            return {"action": "check"}
        elif "call" in valid_actions:
            return {"action": "call"}

        # Fallback
        return {"action": "fold"}