import time

class GameState:
    def __init__(self, target_distance):
        self.target_distance = target_distance
        self.score = 0
        self.round = 1
        self.history = []
        self.start_time = time.time()
        self.last_action_time = None

    def update_state(self, action, result):
        current_time = time.time()
        self.history.append({
            'round': self.round,
            'action': action,
            'result': result,
            'timestamp': current_time
        })
        self.score += self.calculate_score(result)
        self.last_action_time = current_time
        self.round += 1

    def calculate_score(self, result):
        # Scoring based on how close the result is to the target
        distance_to_target = abs(self.target_distance - result)
        if distance_to_target == 0:
            # Perfect score
            return 10
        elif distance_to_target <= 5:
            # Close to the target
            return 5
        elif distance_to_target <= 10:
            # Moderately close to the target
            return 3
        else:
            # Far from the target
            return 1

    def generate_metadata(self):
        current_time = time.time()
        duration = current_time - self.start_time
        return {
            'score': self.score,
            'round': self.round,
            'game_duration': duration,
            'last_action_time': self.last_action_time,
            'history': self.history
        }

    def __str__(self):
        metadata = self.generate_metadata()
        return str(metadata)
