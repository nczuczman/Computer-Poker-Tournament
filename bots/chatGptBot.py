# bestBot.py
from engine.brain import Brain
import math
from treys import Card, Evaluator

class BestBot(Brain):
    """
    Rule-based poker bot using:
      - Preflop starting-hand heuristics (pairs, suited, connectors, high cards)
      - Position awareness (button & late positions more aggressive)
      - Pot/stack thresholds (fold vs call vs raise depending on price)
      - Post-flop classification via treys.Evaluator.class_to_string
    Returns dictionaries like {"action": "fold"} or {"action": "raise", "amount": 123}
    """

    def __init__(self):
        super().__init__()
        self.evaluator = Evaluator()

        # Tunable parameters:
        self.aggression_button = 1.0   # multiplier for raise sizes in late position
        self.aggression_early = 0.6    # multiplier for raise sizes in early position
        self.speculative_call_ratio = 0.03  # call if amount_to_call < ratio * stack for speculative hands

    # Helpers to safely get rank and suit ints from treys.Card (works in common Treys distributions)
    def _card_rank(self, c):
        try:
            return Card.get_rank_int(c)  # 2..14 (14 = Ace)
        except Exception:
            # fallback: parse string
            s = Card.int_to_str(c)  # e.g. "As"
            rank_map = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}
            return rank_map[s[0]]

    def _card_suit(self, c):
        try:
            return Card.get_suit_int(c)  # typically 1..4
        except Exception:
            s = Card.int_to_str(c)
            return s[1]

    def _is_late_position(self, player, button_pos, num_players):
        # Simple: button and one to the right are "late"
        pos = player.get("position", 0)
        if player.get("is_button", False):
            return True
        # relative distance from button
        dist = (pos - button_pos) % num_players
        return dist >= num_players - 2  # last two seats considered late

    def _raise_amount(self, game_state, base_multiplier=1.0, prefer_all_in=False):
        player = game_state["player"]
        stack = player["stack"]
        pot = game_state["pot"]
        min_raise = game_state.get("min_raise", 0)
        max_raise = game_state.get("max_raise", stack)

        if prefer_all_in:
            return stack

        # size relative to pot
        target = int(pot * (1.0 * base_multiplier))
        # but don't undercut min_raise
        target = max(target, min_raise)
        # and don't exceed stack
        target = min(target, max_raise, stack)
        return target

    def get_action(self, game_state):
        """
        game_state: dictionary as provided by the environment.
        """
        player = game_state["player"]
        valid_actions = set(game_state.get("valid_actions", []))
        hand = player.get("hand", [])
        board = game_state.get("community_cards", [])
        street = game_state.get("street", "pre-flop").lower()
        amount_to_call = game_state.get("amount_to_call", 0)
        pot = game_state.get("pot", 0)
        button_pos = game_state.get("button_position", 0)
        num_players = game_state.get("num_players", 1)
        stack = player.get("stack", 0)
        min_raise = game_state.get("min_raise", 0)

        # Defensive: if only fold/call available, obey those.
        # If we're all-in already or stack is zero, just call/fold
        if stack <= 0:
            if "call" in valid_actions:
                return {"action": "call"}
            return {"action": "fold"}

        # --- PRE-FLOP STRATEGY ---
        if street == "pre-flop":
            # decode hole cards
            if len(hand) < 2:
                # fallback: call if possible
                if "call" in valid_actions:
                    return {"action": "call"}
                return {"action": "fold"}

            r1 = self._card_rank(hand[0])
            r2 = self._card_rank(hand[1])
            s1 = self._card_suit(hand[0])
            s2 = self._card_suit(hand[1])

            high = max(r1, r2)
            low = min(r1, r2)
            pair = (r1 == r2)
            suited = (s1 == s2)
            gap = abs(r1 - r2)

            in_late = self._is_late_position(player, button_pos, num_players)

            # Starting hand categories (common heuristics)
            is_ace_high = (high == 14)
            is_premium_pair = pair and high >= 10  # TT+
            is_medium_pair = pair and 6 <= high <= 9  # 66-99
            is_small_pair = pair and high < 6  # 22-55

            # strong broadways
            is_broadway = (high >= 10 and low >= 10)  # both T/J/Q/K/A
            is_ak = (set([r1, r2]) == set([14,13]))
            is_ak_suited = is_ak and suited
            is_AK = is_ak  # both suited/offsuit

            is_suited_connecter = suited and gap <= 1 and low >= 6  # 76s+
            is_suited_one_gap = suited and gap == 2 and low >= 7  # 97s+ (one gap)
            is_suited_ace = suited and (r1 == 14 or r2 == 14) and low <= 5  # A2s-A5s (wheel draws)

            # Aggressive actions for premium hands
            if is_premium_pair or is_AK or (is_broadway and suited and high >= 12):  # QQ+, AK, AQs+
                # raise or shove depending on stack and opponents
                if "raise" in valid_actions:
                    # larger raise in late position
                    mult = self.aggression_button if in_late else self.aggression_early
                    amount = self._raise_amount(game_state, base_multiplier=2.5 * mult,
                                                prefer_all_in=(stack <= pot * 0.5))
                    return {"action": "raise", "amount": amount}
                elif "call" in valid_actions:
                    return {"action": "call"}

            # Strong playable hands: medium pairs, suited broadways, suited connectors
            if is_medium_pair or (suited and high >= 11) or is_suited_connecter or is_suited_one_gap or is_suited_ace:
                # if facing large to-call relative to stack, fold; otherwise call
                if amount_to_call == 0:
                    # free to raise: small steal when in late position
                    if in_late and "raise" in valid_actions:
                        amount = self._raise_amount(game_state, base_multiplier=1.0)
                        return {"action": "raise", "amount": amount}
                    if "check" in valid_actions:
                        return {"action": "check"}
                    if "call" in valid_actions:
                        return {"action": "call"}

                # If amount_to_call is small relative to stack, call
                if amount_to_call <= stack * 0.1 or (amount_to_call <= stack * self.speculative_call_ratio and in_late):
                    if "call" in valid_actions:
                        return {"action": "call"}
                # If facing big raise, fold speculative non-pair hands
                if is_medium_pair and "call" in valid_actions:
                    return {"action": "call"}

            # Small pairs: set-mining if cheap multiway or late position
            if is_small_pair:
                if amount_to_call <= stack * 0.03 or in_late:
                    if "call" in valid_actions:
                        return {"action": "call"}
                # otherwise fold
                if "fold" in valid_actions:
                    return {"action": "fold"}

            # Suited small cards or offsuit connectors are marginal — fold to nontrivial raises
            if suited and (low >= 8) and gap <= 2 and in_late and amount_to_call <= stack * 0.02:
                if "call" in valid_actions:
                    return {"action": "call"}

            # If there is nothing special — be tight: call only if it's cheap or we are in blind with no to-call
            if amount_to_call == 0:
                # If we can check, check
                if "check" in valid_actions:
                    return {"action": "check"}
                # Otherwise call small blind defense
                if "call" in valid_actions and amount_to_call <= game_state.get("big_blind", 0):
                    return {"action": "call"}

            # Default preflop: fold to nontrivial bet, else call small bets
            if amount_to_call > 0:
                # caller only if cheap compared to stack and pot odds favorable
                pot_odds = amount_to_call / (pot + amount_to_call) if (pot + amount_to_call) > 0 else 1.0
                # be conservative: call if pot_odds < 0.2 and amount_to_call small vs stack
                if ("call" in valid_actions) and (pot_odds <= 0.2 or amount_to_call <= stack * 0.02):
                    return {"action": "call"}
                if "fold" in valid_actions:
                    return {"action": "fold"}
            else:
                # no money to call - take free card / check
                if "check" in valid_actions:
                    return {"action": "check"}
                if "call" in valid_actions:
                    return {"action": "call"}

            # final fallback
            if "fold" in valid_actions:
                return {"action": "fold"}
            if "call" in valid_actions:
                return {"action": "call"}

        # --- POST-FLOP (flop, turn, river) ---
        # Evaluate made hand
        try:
            if len(board) == 0:
                score = self.evaluator.evaluate([], hand)
            else:
                score = self.evaluator.evaluate(board, hand)
            hand_rank_class = self.evaluator.get_rank_class(score)
            hand_name = self.evaluator.class_to_string(hand_rank_class).lower()
        except Exception:
            hand_name = "unknown"

        # Quick mapping:
        # "royal flush", "straight flush", "four of a kind", "full house", "flush", "straight",
        # "three of a kind", "two pair", "pair", "high card"

        # Strong made hands -> value raise / shove
        if any(x in hand_name for x in ("royal flush", "straight flush", "four", "full house", "flush", "straight")):
            # very strong -> shove or big raise
            if "raise" in valid_actions:
                return {"action": "raise", "amount": self._raise_amount(game_state, base_multiplier=3.0, prefer_all_in=(stack <= pot))}
            if "bet" in valid_actions:
                return {"action": "bet", "amount": min(stack, int(pot * 0.9))}
            if "call" in valid_actions:
                return {"action": "call"}

        # Trips or better -> raise for value
        if "three of a kind" in hand_name:
            if "raise" in valid_actions:
                return {"action": "raise", "amount": self._raise_amount(game_state, base_multiplier=2.0)}
            if "call" in valid_actions:
                return {"action": "call"}

        # Two pair -> value bet/raise
        if "two pair" in hand_name:
            if "raise" in valid_actions:
                return {"action": "raise", "amount": self._raise_amount(game_state, base_multiplier=1.5)}
            if "call" in valid_actions:
                return {"action": "call"}

        # One pair -> cautious: call small bets, fold to large aggression
        if "pair" in hand_name:
            # If there is little to call, call
            if amount_to_call == 0:
                if "check" in valid_actions:
                    return {"action": "check"}
                if "call" in valid_actions:
                    return {"action": "call"}

            # if pot odds are good, call
            pot_odds = amount_to_call / (pot + amount_to_call) if (pot + amount_to_call) > 0 else 1.0
            if pot_odds < 0.3 or amount_to_call <= stack * 0.03:
                if "call" in valid_actions:
                    return {"action": "call"}
            # sometimes attempt a small raise as a probe if check-raise opportunity
            if "raise" in valid_actions and amount_to_call == 0:
                return {"action": "raise", "amount": self._raise_amount(game_state, base_multiplier=0.6)}

            if "fold" in valid_actions:
                return {"action": "fold"}

        # High card or unknown: try to bluff/steal only when checked to or very late position and pot small
        if "high card" in hand_name or hand_name == "unknown":
            # If we can check, do it
            if amount_to_call == 0 and "check" in valid_actions:
                return {"action": "check"}

            # small bluff occasionally: if in late position and pot small vs stack, and no one put large money
            if self._is_late_position(player, button_pos, num_players) and amount_to_call <= stack * 0.02 and pot <= stack * 0.2:
                if "raise" in valid_actions:
                    return {"action": "raise", "amount": self._raise_amount(game_state, base_multiplier=0.6)}

            # otherwise fold to larger bets
            if "fold" in valid_actions:
                return {"action": "fold"}
            if "call" in valid_actions and amount_to_call <= stack * 0.01:
                return {"action": "call"}

        # Final fallback conservative behavior
        if "check" in valid_actions:
            return {"action": "check"}
        if "call" in valid_actions:
            return {"action": "call"}
        return {"action": "fold"}
