from treys import Deck

class Dealer:
    def __init__(self):
        self.deck = Deck()
    
    def deal_hole_cards(self, players):
        for player in players:
            player.hand = [self.deck.draw()[0], self.deck.draw()[0]]
        
    def deal_flop(self):
        return [self.deck.draw()[0], self.deck.draw()[0], self.deck.draw()[0]]

    def deal_turn_or_river(self):
        return self.deck.draw()[0]
    
