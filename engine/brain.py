class Brain:
    def __init__(self):
        pass
    
    def get_action(self, game_state):
        """
        Must be implemented by subclasses.
        Returns a dict with 'action' key and optional 'amount' key.
        """
        raise NotImplementedError("Subclasses must implement get_action()")

