from engine.brain import Brain
import random
from treys import Card, Evaluator

class ClaudeBot(Brain):
    def __init__(self):
        super().__init__()
        self.evaluator = Evaluator()
        self.opponent_aggression = {}  # Track opponent behavior
        self.hand_history = []
        
    def get_action(self, game_state):
        """Main decision-making function"""
        valid_actions = game_state["valid_actions"]
        player = game_state["player"]
        hand = player["hand"]
        board = game_state.get("community_cards", [])
        street = game_state.get("street", "").lower()
        
        # Get key game metrics
        pot = game_state["pot"]
        amount_to_call = game_state["amount_to_call"]
        stack = player["stack"]
        pot_odds = game_state.get("pot_odds", 0)
        position = player["position"]
        num_active = game_state["num_active_players"]
        is_button = player.get("is_button", False)
        
        # === PRE-FLOP STRATEGY ===
        if street == "pre-flop":
            return self._preflop_strategy(
                hand, valid_actions, amount_to_call, stack, 
                pot, position, num_active, is_button, game_state
            )
        
        # === POST-FLOP STRATEGY ===
        return self._postflop_strategy(
            hand, board, valid_actions, amount_to_call, stack,
            pot, pot_odds, street, position, num_active, game_state
        )
    
    def _preflop_strategy(self, hand, valid_actions, amount_to_call, 
                         stack, pot, position, num_active, is_button, game_state):
        """Advanced pre-flop hand selection and betting"""
        
        hand_strength = self._evaluate_preflop_hand(hand)
        
        # Position adjustment: play tighter early, looser late
        position_factor = position / max(num_active - 1, 1)
        
        # Stack-to-pot ratio
        spr = stack / max(pot, 1)
        
        # Effective stack (for all-in decisions)
        effective_stack = min(stack, max([opp["stack"] for opp in game_state["opponents"]], default=stack))
        
        # Calculate risk/reward
        call_percentage = amount_to_call / stack if stack > 0 else 1
        
        # === PREMIUM HANDS (AA, KK, QQ, AK) ===
        if hand_strength >= 9.0:
            if "raise" in valid_actions:
                # 3-bet or 4-bet sizing
                current_bet = game_state["current_bet"]
                if current_bet > game_state["big_blind"] * 2:
                    # Facing a raise - re-raise
                    raise_size = min(current_bet * 3, stack)
                else:
                    # Opening raise
                    raise_size = min(game_state["big_blind"] * 3, stack)
                return {"action": "raise", "amount": max(game_state["min_raise"], raise_size)}
            elif "call" in valid_actions:
                return {"action": "call"}
        
        # === STRONG HANDS (JJ, TT, AQ, AJ) ===
        elif hand_strength >= 7.5:
            if call_percentage < 0.15:  # Less than 15% of stack
                if "raise" in valid_actions and position_factor > 0.5:
                    raise_size = min(game_state["big_blind"] * 2.5, stack)
                    return {"action": "raise", "amount": max(game_state["min_raise"], raise_size)}
                elif "call" in valid_actions:
                    return {"action": "call"}
            elif call_percentage < 0.25:  # 15-25% of stack
                if "call" in valid_actions:
                    return {"action": "call"}
        
        # === GOOD HANDS (99-77, ATs+, KQs, suited connectors) ===
        elif hand_strength >= 6.0:
            if call_percentage < 0.08:  # Less than 8% of stack
                if "call" in valid_actions:
                    return {"action": "call"}
                elif "check" in valid_actions:
                    return {"action": "check"}
            elif call_percentage < 0.15 and position_factor > 0.6:
                # Late position, reasonable price
                if "call" in valid_actions:
                    return {"action": "call"}
        
        # === SPECULATIVE HANDS (small pairs, suited connectors) ===
        elif hand_strength >= 4.5:
            # Only call if cheap and good implied odds
            if call_percentage < 0.05 and spr > 10 and num_active >= 2:
                if "call" in valid_actions:
                    return {"action": "call"}
        
        # === DEFAULT: FOLD OR CHECK ===
        if "check" in valid_actions:
            return {"action": "check"}
        return {"action": "fold"}
    
    def _postflop_strategy(self, hand, board, valid_actions, amount_to_call,
                          stack, pot, pot_odds, street, position, num_active, game_state):
        """Post-flop decision making with hand strength and pot odds"""
        
        # Evaluate current hand
        if len(board) == 0:
            return {"action": "check"} if "check" in valid_actions else {"action": "fold"}
        
        score = self.evaluator.evaluate(board, hand)
        hand_rank = self.evaluator.get_rank_class(score)
        
        # Normalize hand strength (1 = best, 0 = worst)
        hand_strength = (10 - hand_rank) / 9.0
        
        # Estimate drawing potential
        draw_potential = self._estimate_draw_potential(hand, board, street)
        
        # Combined strength
        total_strength = hand_strength + draw_potential * 0.3
        
        # Stack-to-pot ratio
        spr = stack / max(pot, 1)
        
        # Calculate pot odds value
        pot_odds_value = pot / (pot + amount_to_call) if amount_to_call > 0 else 1
        
        # === MONSTER HANDS (Straight or better) ===
        if hand_rank <= 5:
            if "raise" in valid_actions:
                # Value bet: aim for 60-80% pot
                raise_size = min(int(pot * random.uniform(0.6, 0.8)), stack)
                return {"action": "raise", "amount": max(game_state["min_raise"], raise_size)}
            elif "bet" in valid_actions:
                bet_size = min(int(pot * 0.7), stack)
                return {"action": "bet", "amount": bet_size}
            elif "call" in valid_actions:
                return {"action": "call"}
        
        # === STRONG HANDS (Two pair or better) ===
        elif hand_rank <= 7:
            if "raise" in valid_actions and amount_to_call < pot * 0.5:
                raise_size = min(int(pot * 0.5), stack)
                return {"action": "raise", "amount": max(game_state["min_raise"], raise_size)}
            elif "bet" in valid_actions:
                bet_size = min(int(pot * 0.5), stack)
                return {"action": "bet", "amount": bet_size}
            elif "call" in valid_actions and amount_to_call < pot * 0.5:
                return {"action": "call"}
        
        # === MEDIUM HANDS (Pair) ===
        elif hand_rank <= 8:
            # Use pot odds to decide
            if amount_to_call > 0:
                call_odds = amount_to_call / (pot + amount_to_call)
                if call_odds < 0.3:  # Getting good odds
                    if "call" in valid_actions:
                        return {"action": "call"}
                elif call_odds < 0.4 and total_strength > 0.5:
                    if "call" in valid_actions:
                        return {"action": "call"}
            else:
                if "bet" in valid_actions and num_active <= 2:
                    # Small probe bet
                    bet_size = min(int(pot * 0.3), stack)
                    return {"action": "bet", "amount": bet_size}
                elif "check" in valid_actions:
                    return {"action": "check"}
        
        # === DRAWING HANDS ===
        if draw_potential > 0.3:
            # Good draw with pot odds
            if pot_odds_value > 0.25:  # Getting better than 3:1
                if "call" in valid_actions and amount_to_call < pot * 0.5:
                    return {"action": "call"}
        
        # === BLUFF OPPORTUNITIES ===
        if num_active <= 2 and position > 0:
            if "bet" in valid_actions and random.random() < 0.15:  # 15% bluff frequency
                bet_size = min(int(pot * 0.6), stack)
                return {"action": "bet", "amount": bet_size}
        
        # === DEFAULT ===
        if "check" in valid_actions:
            return {"action": "check"}
        elif "call" in valid_actions and amount_to_call < pot * 0.2:
            return {"action": "call"}
        
        return {"action": "fold"}
    
    def _evaluate_preflop_hand(self, hand):
        """Rate pre-flop hand strength (0-10 scale)"""
        if len(hand) != 2:
            return 0
        
        # Convert to ranks and suits
        c1, c2 = hand[0], hand[1]
        rank1 = Card.get_rank_int(c1)
        rank2 = Card.get_rank_int(c2)
        suit1 = Card.get_suit_int(c1)
        suit2 = Card.get_suit_int(c2)
        
        high_rank = max(rank1, rank2)
        low_rank = min(rank1, rank2)
        is_pair = (rank1 == rank2)
        is_suited = (suit1 == suit2)
        gap = high_rank - low_rank
        
        # Pairs
        if is_pair:
            if high_rank >= 12:  # AA, KK
                return 10.0
            elif high_rank >= 10:  # QQ, JJ
                return 9.0
            elif high_rank >= 8:  # TT, 99
                return 7.5
            elif high_rank >= 5:  # 88-66
                return 6.5
            else:  # 55-22
                return 5.0
        
        # High cards
        if high_rank >= 12:  # Ace
            if low_rank >= 11:  # AK
                return 9.5 if is_suited else 9.0
            elif low_rank >= 10:  # AQ
                return 8.0 if is_suited else 7.5
            elif low_rank >= 9:  # AJ
                return 7.5 if is_suited else 7.0
            elif low_rank >= 8:  # AT
                return 7.0 if is_suited else 6.0
            elif is_suited and low_rank >= 6:  # A9s-A7s
                return 6.0
            elif is_suited:  # A6s-A2s
                return 5.5
        
        if high_rank >= 11:  # King
            if low_rank >= 10:  # KQ
                return 7.5 if is_suited else 7.0
            elif low_rank >= 9:  # KJ
                return 7.0 if is_suited else 6.0
            elif is_suited and low_rank >= 8:  # KTs
                return 6.5
        
        if high_rank >= 10:  # Queen
            if low_rank >= 9:  # QJ
                return 6.5 if is_suited else 5.5
            elif is_suited and low_rank >= 8:  # QTs
                return 6.0
        
        # Suited connectors and one-gappers
        if is_suited:
            if gap <= 1 and high_rank >= 7:  # JTs, T9s, 98s, etc.
                return 6.5
            elif gap <= 2 and high_rank >= 8:
                return 5.5
        
        # Connected cards
        if gap <= 1 and high_rank >= 9:
            return 5.0
        
        return 3.0  # Weak hand
    
    def _estimate_draw_potential(self, hand, board, street):
        """Estimate drawing potential (flush draws, straight draws)"""
        if len(board) < 3:
            return 0
        
        # Count suits
        all_cards = hand + board
        suit_counts = {}
        for card in all_cards:
            suit = Card.get_suit_int(card)
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        # Flush draw potential
        max_suit_count = max(suit_counts.values())
        flush_draw = 0
        if max_suit_count == 4 and street != "river":
            flush_draw = 0.35  # ~35% to hit flush
        
        # Straight draw potential (simplified)
        ranks = sorted([Card.get_rank_int(c) for c in all_cards])
        unique_ranks = sorted(set(ranks))
        
        straight_draw = 0
        if len(unique_ranks) >= 4:
            # Check for open-ended straight draw
            for i in range(len(unique_ranks) - 3):
                if unique_ranks[i+3] - unique_ranks[i] == 3:
                    straight_draw = 0.3
                    break
        
        return max(flush_draw, straight_draw)